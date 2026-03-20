"""
analyzer.py — IMA Lab data layer.

KEY FIXES:
- fleet_health: COUNT uses ALL borrows (not just duration>0); span uses all records
  → previously filtering duration>0 caused items with old zero-dur records to appear
  as "new" items, hiding 2020-2024 history
- gantt domain: excludes NULL-finished (active) items from x-axis max
  → previously active items stretched x-axis to "now", compressing old bars to invisible
"""
import sqlite3, json, math
import pandas as pd
import numpy as np
from pathlib import Path
import re

_DB = Path(__file__).parent / "item_analysis.db"
_BUNDLE_RE = r'^\d+\s'

def _strip_number(name: str) -> str:
    if name is None:
        return ""
    return re.sub(r"\s+\d+$", "", str(name)).strip()


def _load(category=None, source=None, start=None, end=None) -> pd.DataFrame:
    conn = sqlite3.connect(str(_DB))
    conds, params = [], []
    if source:   conds.append("source = ?");      params.append(source)
    if category: conds.append('"Category" = ?');  params.append(category)
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
    df['finished_raw'] = df['finished'].copy()          # keep NaT for active detection
    df['finished']     = df['finished'].fillna(pd.Timestamp.now())
    df['is_active']    = df['finished_raw'].isna()      # truly active = no return date
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
    pos = df[df['duration_h'] > 0]
    kpi = {
        "total":        int(len(df)),
        "unique_items": int(df['item name(with num)'].nunique()),
        "active_now":   int(df['is_active'].sum()),
        "avg_hours":    round(float(pos['duration_h'].mean()), 1) if not pos.empty else 0,
    }
    df['ym'] = df['Start'].dt.to_period('M').astype(str)
    monthly = df.groupby('ym').size().reset_index(name='count').rename(columns={'ym': 'month'})
    cat = pos.groupby('Category').agg(
        count=('id', 'count'),
        med_h=('duration_h', 'median'),
        items=('item name(with num)', 'nunique'),
    ).reset_index()
    cat = cat[cat['count'] >= 10].copy()
    cat['med_h'] = cat['med_h'].round(1)
    return _j({"kpi": kpi, "monthly": monthly.to_dict('records'), "categories": cat.to_dict('records')})


# ── 2. FLEET HEALTH ──────────────────────────────────
def fleet_health(category=None, source=None, start=None, end=None, top_n=25) -> str:
    df = _load(category=category, source=source, start=start, end=end)
    # Remove bundles
    df = df[~df['item name(with num)'].str.match(_BUNDLE_RE, na=False)]
    if df.empty:
        return _j({"bars": [], "quadrant": [], "p95_h": 0, "p95_count": 0})

    # COUNT = all borrows (including zero-duration — these are real checkouts)
    # AVG_H = only from records with duration > 0
    agg_all = df.groupby('item name(with num)').agg(
        count=('id', 'count'),
        first=('Start', 'min'),
        last=('Start', 'max'),       # use Start for span to avoid "now" inflation
        category=('Category', 'first'),
        active=('is_active', 'any'),
    ).reset_index()

    dur_df = df[df['duration_h'] > 0]
    if not dur_df.empty:
        agg_dur = dur_df.groupby('item name(with num)').agg(
            total_h=('duration_h', 'sum'),
            avg_h=('duration_h', 'mean'),
            med_h=('duration_h', 'median'),
        ).reset_index()
        agg = agg_all.merge(agg_dur, on='item name(with num)', how='left')
    else:
        agg = agg_all.copy()
        agg['total_h'] = 0.0
        agg['avg_h']   = 0.0
        agg['med_h']   = 0.0

    agg = agg[agg['count'] >= 2].copy()
    if agg.empty:
        return _j({"bars": [], "quadrant": [], "p95_h": 0, "p95_count": 0})

    agg['total_h'] = agg['total_h'].fillna(0)
    agg['avg_h']   = agg['avg_h'].fillna(0).round(1)
    agg['med_h']   = agg['med_h'].fillna(0).round(1)

    # Span: days between first and last borrow start (not affected by NULL finished)
    agg['span_days'] = ((agg['last'] - agg['first']).dt.total_seconds() / 86400).clip(lower=1)
    agg['util']      = (agg['total_h'] / 24 / agg['span_days']).clip(0, 1).round(3)

    p95_h     = float(agg[agg['avg_h'] > 0]['avg_h'].quantile(0.95)) if (agg['avg_h'] > 0).any() else 0
    p95_count = float(agg['count'].quantile(0.95))

    # Sort bars by demand score (count × util), not just util
    agg['score'] = agg['count'] * agg['util']
    top = agg.nlargest(top_n, 'score')

    bars = [{"item": r['item name(with num)'], "util": float(r['util']),
              "count": int(r['count']), "avg_h": float(r['avg_h']),
              "med_h": float(r['med_h']), "score": float(r['score']),
              "category": r['category'], "active": bool(r['active'])}
            for _, r in top.iterrows()]

    quad = [{"item": r['item name(with num)'], "count": int(r['count']),
             "avg_h": float(r['avg_h']), "util": float(r['util']),
             "category": r['category'], "active": bool(r['active'])}
            for _, r in agg.iterrows()]

    return _j({"bars": bars, "quadrant": quad, "p95_h": p95_h, "p95_count": p95_count})


# ── 3. CATEGORY DEEP DIVE ────────────────────────────
def category_analysis(category: str, source=None, start=None, end=None) -> str:
    df = _load(category=category, source=source, start=start, end=end)
    if df.empty:
        return _j({"items": [], "timeline": [], "monthly": [], "top10": []})

    named = df[~df['item name(with num)'].str.match(_BUNDLE_RE, na=False)].copy()
    if named.empty:
        named = df.copy()

    agg = named.groupby('item name(with num)').agg(
        count=('id', 'count'),
        avg_h=('duration_h', 'mean'),
        med_h=('duration_h', 'median'),
        total_h=('duration_h', 'sum'),
        active=('is_active', 'any'),
    ).reset_index().sort_values('count', ascending=False)
    agg['avg_h']   = agg['avg_h'].round(1)
    agg['med_h']   = agg['med_h'].round(1)
    agg['total_h'] = agg['total_h'].round(1)

    items = [{"item": r['item name(with num)'], "count": int(r['count']),
              "avg_h": float(r['avg_h']), "med_h": float(r['med_h']),
              "total_h": float(r['total_h']), "active": bool(r['active'])}
             for _, r in agg.iterrows()]

    top10 = agg.head(10)['item name(with num)'].tolist()
    tl_df = named[named['item name(with num)'].isin(top10)].copy()
    tl_df['ym'] = tl_df['Start'].dt.to_period('M').astype(str)
    tl = (tl_df.groupby(['ym', 'item name(with num)'])
               .size().reset_index(name='count')
               .rename(columns={'ym': 'month'}))

    named['ym'] = named['Start'].dt.to_period('M').astype(str)
    monthly = named.groupby('ym').size().reset_index(name='count').rename(columns={'ym': 'month'})

    return _j({"items": items, "timeline": tl.to_dict('records'),
                "monthly": monthly.to_dict('records'), "top10": top10})


# ── 4. SINGLE ITEM DETAIL ────────────────────────────
def item_detail(item: str, start=None, end=None, match_base: bool = False) -> str:
    df = _load(start=start, end=end)
    if match_base:
        base = _strip_number(item)
        df = df[df["item name(with num)"].apply(_strip_number) == base]
    else:
        df = df[df["item name(with num)"] == item]
    df = df.sort_values("Start").reset_index(drop=True)
    if df.empty:
        return _j({"gantt": [], "monthly": [], "stats": {}, "gaps": []})

    now = pd.Timestamp.now()
    gantt = []
    for i, r in df.iterrows():
        end_t = r['finished_raw'] if pd.notna(r['finished_raw']) else now
        end_t = min(end_t, now)
        gantt.append({
            "idx":    i,
            "start":  r['Start'],
            "end":    end_t,
            "hours":  float(r['duration_h']) if r['duration_h'] > 0 else None,
            "source": r['source'],
            "active": bool(r['is_active']),
        })

    gaps = []
    for i in range(1, len(df)):
        prev_end = df.iloc[i-1]['finished_raw'] if pd.notna(df.iloc[i-1]['finished_raw']) else df.iloc[i-1]['Start']
        gap_d = (df.iloc[i]['Start'] - prev_end).total_seconds() / 86400
        if gap_d > 0:
            gaps.append({"gap_days": round(float(gap_d), 1),
                         "from": prev_end,
                         "to":   df.iloc[i]['Start']})

    df['ym'] = df['Start'].dt.to_period('M').astype(str)
    monthly = (df.groupby('ym')
                 .agg(count=('id', 'count'), total_h=('duration_h', 'sum'))
                 .reset_index().rename(columns={'ym': 'month'}))
    monthly['total_h'] = monthly['total_h'].round(1)

    valid = df[df['duration_h'] > 0]['duration_h']
    base_name = _strip_number(item) if match_base else _strip_number(item)
    stats = {
        "total":        int(len(df)),
        "avg_h":        round(float(valid.mean()), 1) if not valid.empty else 0,
        "max_h":        round(float(valid.max()), 1)  if not valid.empty else 0,
        "first":        df['Start'].min(),
        "last":         df['Start'].max(),
        "active_now":   bool(df['is_active'].any()),
        "category":     str(df['Category'].iloc[0]) if len(df) else "",
        "avg_gap_days": round(float(np.mean([g['gap_days'] for g in gaps])), 1) if gaps else None,
        "match_mode":   "base" if match_base else "exact",
        "base_name":    base_name,
        "units":        int(df["item name(with num)"].nunique()),
    }
    return _j({"gantt": gantt, "monthly": monthly.to_dict('records'),
                "stats": stats, "gaps": gaps})


# ── 5. TEMPORAL PATTERNS ─────────────────────────────
def temporal_patterns(category=None, source=None, start=None, end=None) -> str:
    df = _load(category=category, source=source, start=start, end=end)
    if df.empty:
        return _j({"heatmap": [], "by_month": [], "by_weekday": []})

    df['weekday'] = df['Start'].dt.weekday
    df['hour']    = df['Start'].dt.hour
    df['month_n'] = df['Start'].dt.month

    heatmap  = df.groupby(['weekday', 'hour']).size().reset_index(name='count').to_dict('records')
    by_month = df.groupby('month_n').size().reset_index(name='count').rename(columns={'month_n': 'month'})
    by_month['label'] = by_month['month'].apply(
        lambda m: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1])
    by_wd = df.groupby('weekday').size().reset_index(name='count')
    by_wd['label'] = by_wd['weekday'].apply(lambda d: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d])

    return _j({"heatmap": heatmap, "by_month": by_month.to_dict('records'),
                "by_weekday": by_wd.to_dict('records')})


# ── UI HELPERS ────────────────────────────────────────
def get_categories() -> list:
    conn = sqlite3.connect(str(_DB))
    df = pd.read_sql(
        'SELECT "Category", COUNT(*) c FROM unified_records '
        "WHERE \"Category\" NOT IN ('nan','Unknown','') "
        'GROUP BY "Category" ORDER BY c DESC', conn)
    conn.close()
    return [r for r in df['Category'].tolist() if r and str(r) != 'nan']


def get_items(category=None, source=None) -> list:
    conn = sqlite3.connect(str(_DB))
    conds, params = [], []
    if category: conds.append('"Category"=?'); params.append(category)
    if source:   conds.append('"source"=?');   params.append(source)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    df = pd.read_sql(
        f'SELECT DISTINCT "item name(with num)" n FROM unified_records {where} ORDER BY n',
        conn, params=params)
    conn.close()
    return df['n'].dropna().tolist()


def get_bounds(source=None) -> dict:
    try:
        conn = sqlite3.connect(str(_DB))
        if source:
            row = pd.read_sql(
                'SELECT MIN("Start") mn, MAX("Start") mx FROM unified_records WHERE source=?',
                conn, params=[source])
        else:
            row = pd.read_sql(
                'SELECT MIN("Start") mn, MAX("Start") mx FROM unified_records', conn)
        conn.close()
        mn = pd.to_datetime(row['mn'][0], errors='coerce') if not row.empty else pd.NaT
        mx = pd.to_datetime(row['mx'][0], errors='coerce') if not row.empty else pd.NaT
        return {'min': mn.strftime('%Y-%m-%d') if pd.notna(mn) else '',
                'max': mx.strftime('%Y-%m-%d') if pd.notna(mx) else ''}
    except Exception:
        return {'min': '', 'max': ''}