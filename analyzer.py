"""
analyzer.py — IMA Lab 数据分析层
- 直接读 SQLite，不依赖任何旧模块
- 所有函数返回 JSON 字符串，供前端 D3 直接消费
"""

import sqlite3, json, math
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

_DB = Path(__file__).parent / "item_analysis.db"


def _load(category=None, source=None, start=None, end=None) -> pd.DataFrame:
    conn = sqlite3.connect(str(_DB))
    conds, params = [], []
    if source:   conds.append("source = ?");       params.append(source)
    if category: conds.append('"Category" = ?');   params.append(category)
    if start:
        t = pd.to_datetime(start, errors='coerce')
        if pd.notna(t): conds.append('"Start" >= ?'); params.append(t.strftime('%Y-%m-%d'))
    if end:
        t = pd.to_datetime(end, errors='coerce')
        if pd.notna(t): conds.append('"Start" <= ?'); params.append(t.strftime('%Y-%m-%d 23:59:59'))
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    df = pd.read_sql(f"SELECT * FROM unified_records {where}", conn, params=params)
    conn.close()

    for col in ['Start', 'finished']:
        s = df[col].astype(str).replace({'None': pd.NA, 'nan': pd.NA, 'NaT': pd.NA})
        df[col] = pd.to_datetime(s, format='mixed', dayfirst=False, errors='coerce')

    df = df.dropna(subset=['Start']).copy()
    df['duration_h'] = pd.to_numeric(df['duration (hours)'], errors='coerce').fillna(0)
    df['finished']   = df['finished'].fillna(pd.Timestamp.now())
    df['is_active']  = df['finished'] > pd.Timestamp.now() - pd.Timedelta(hours=2)
    return df


def _serial(obj):
    if isinstance(obj, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(obj).strftime('%Y-%m-%dT%H:%M:%S')
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, 'item'):
        return obj.item()
    return obj

def _j(data) -> str:
    return json.dumps(data, default=_serial, ensure_ascii=False)


# ── 1. OVERVIEW ──────────────────────────────────────
def overview(source=None, start=None, end=None) -> str:
    df = _load(source=source, start=start, end=end)
    kpi = {
        "total":        int(len(df)),
        "unique_items": int(df['item name(with num)'].nunique()),
        "active_now":   int(df['is_active'].sum()),
        "avg_hours":    round(float(df[df['duration_h']>0]['duration_h'].mean()), 1),
    }
    df['ym'] = df['Start'].dt.to_period('M').astype(str)
    monthly = df.groupby('ym').size().reset_index(name='count').rename(columns={'ym':'month'})

    cat = df[df['duration_h']>0].groupby('Category').agg(
        count=('id','count'), med_h=('duration_h','median'), items=('item name(with num)','nunique')
    ).reset_index()
    cat = cat[cat['count'] >= 10].copy()
    cat['med_h'] = cat['med_h'].round(1)

    return _j({"kpi": kpi, "monthly": monthly.to_dict('records'), "bubble": cat.to_dict('records')})


# ── 2. FLEET HEALTH ──────────────────────────────────
def fleet_health(category=None, source=None, start=None, end=None, top_n=25) -> str:
    df = _load(category=category, source=source, start=start, end=end)
    df = df[df['duration_h'] > 0]
    if df.empty:
        return _j({"bars": [], "quadrant": []})

    agg = df.groupby('item name(with num)').agg(
        count=('id','count'), total_h=('duration_h','sum'), avg_h=('duration_h','mean'),
        first=('Start','min'), last=('finished','max'),
        category=('Category','first'), active=('is_active','any'),
    ).reset_index()
    agg['span_days'] = ((agg['last']-agg['first']).dt.total_seconds()/86400).clip(lower=1)
    agg['util']      = (agg['total_h']/24/agg['span_days']).clip(0,1).round(3)
    agg['avg_h']     = agg['avg_h'].round(1)

    top = agg.nlargest(top_n, 'util')
    bars = [{"item":r['item name(with num)'],"util":float(r['util']),"count":int(r['count']),
              "avg_h":float(r['avg_h']),"category":r['category'],"active":bool(r['active'])}
            for _,r in top.iterrows()]

    quad = [{"item":r['item name(with num)'],"count":int(r['count']),"avg_h":float(r['avg_h']),
             "util":float(r['util']),"category":r['category'],"active":bool(r['active'])}
            for _,r in agg.iterrows()]

    return _j({"bars": bars, "quadrant": quad})


# ── 3. ITEM DETAIL ────────────────────────────────────
def item_detail(item: str, start=None, end=None) -> str:
    df = _load(start=start, end=end)
    df = df[df['item name(with num)']==item].sort_values('Start').reset_index(drop=True)
    if df.empty:
        return _j({"gantt":[],"monthly":[],"stats":{}})

    now = pd.Timestamp.now()
    gantt = [{"idx":i,"start":r['Start'],"end":min(r['finished'],now),
              "hours":float(r['duration_h']) if r['duration_h']>0 else None,
              "source":r['source'],"active":bool(r['is_active'])}
             for i,r in df.iterrows()]

    df['ym'] = df['Start'].dt.to_period('M').astype(str)
    monthly = (df.groupby('ym').agg(count=('id','count'),total_h=('duration_h','sum'))
                 .reset_index().rename(columns={'ym':'month'}))
    monthly['total_h'] = monthly['total_h'].round(1)

    valid = df[df['duration_h']>0]['duration_h']
    stats = {
        "total":      int(len(df)),
        "avg_h":      round(float(valid.mean()),1) if not valid.empty else 0,
        "max_h":      round(float(valid.max()),1)  if not valid.empty else 0,
        "first":      df['Start'].min(),
        "last":       df['Start'].max(),
        "active_now": bool(df['is_active'].any()),
        "category":   str(df['Category'].iloc[0]) if len(df) else "",
    }
    return _j({"gantt":gantt,"monthly":monthly.to_dict('records'),"stats":stats})


# ── 4. TEMPORAL PATTERNS ─────────────────────────────
def temporal_patterns(category=None, source=None, start=None, end=None) -> str:
    df = _load(category=category, source=source, start=start, end=end)
    if df.empty:
        return _j({"heatmap":[],"by_month":[],"by_weekday":[]})

    df['weekday'] = df['Start'].dt.weekday
    df['hour']    = df['Start'].dt.hour
    df['month_n'] = df['Start'].dt.month

    heatmap = df.groupby(['weekday','hour']).size().reset_index(name='count').to_dict('records')

    by_month = df.groupby('month_n').size().reset_index(name='count').rename(columns={'month_n':'month'})
    by_month['label'] = by_month['month'].apply(
        lambda m: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1])

    by_wd = df.groupby('weekday').size().reset_index(name='count')
    by_wd['label'] = by_wd['weekday'].apply(lambda d: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d])

    return _j({"heatmap":heatmap,"by_month":by_month.to_dict('records'),"by_weekday":by_wd.to_dict('records')})


# ── UI helpers ────────────────────────────────────────
def get_categories() -> list:
    conn = sqlite3.connect(str(_DB))
    df = pd.read_sql(
        'SELECT "Category", COUNT(*) c FROM unified_records '
        'WHERE "Category" NOT IN ("nan","Unknown","") GROUP BY "Category" ORDER BY c DESC', conn)
    conn.close()
    return [r for r in df['Category'].tolist() if r and str(r) != 'nan']

def get_items(category=None, source=None) -> list:
    conn = sqlite3.connect(str(_DB))
    conds, params = [], []
    if category: conds.append('"Category"=?'); params.append(category)
    if source:   conds.append('"source"=?');   params.append(source)
    where = ("WHERE "+" AND ".join(conds)) if conds else ""
    df = pd.read_sql(
        f'SELECT DISTINCT "item name(with num)" n FROM unified_records {where} ORDER BY n',
        conn, params=params)
    conn.close()
    return df['n'].dropna().tolist()

def get_bounds(source=None) -> dict:
    conn = sqlite3.connect(str(_DB))
    where = f'WHERE source="{source}"' if source else ''
    row = pd.read_sql(f'SELECT MIN("Start") mn, MAX("Start") mx FROM unified_records {where}', conn)
    conn.close()
    mn = pd.to_datetime(row['mn'][0], errors='coerce')
    mx = pd.to_datetime(row['mx'][0], errors='coerce')
    return {'min': mn.strftime('%Y-%m-%d') if pd.notna(mn) else '',
            'max': mx.strftime('%Y-%m-%d') if pd.notna(mx) else ''}
