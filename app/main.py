"""
IMA Lab — Equipment Borrowing Intelligence Platform

FIXES IN THIS VERSION:
1. DATA: fleet_health now counts ALL borrows (incl zero-duration historical records)
   → previously only duration>0 filtered out 2020-2024 data, making items look new
2. GANTT: x-axis domain uses only real return dates (not active "end=now")
   → previously active items stretched axis to today, compressing old bars to 1-2px
3. RENDERING: SVG uses runtime VW (clientWidth) not fixed 1100 + viewBox scaling
   → viewBox scaling made rendered height > iframe height → content clipped/blank
4. TEXT: all in-chart labels brightened (#888 → #ccc/#ddd), section headers white
5. FONTS: section title 13px, sec-note 12px, chart labels 12-13px throughout
"""
import sys, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components
import re

from config.settings import GOOGLE_SHEET_ID, TARGET_SHEETS
from config.sheet_config import load_sheet_config, save_sheet_config, clear_sheet_config

st.set_page_config(page_title="IMA Lab", page_icon="◈", layout="wide",
                   initial_sidebar_state="collapsed")

import analyzer

DB_DIR = Path(os.getcwd()) / ".streamlit_data"
DB_DIR.mkdir(parents=True, exist_ok=True)
analyzer._DB = DB_DIR / "item_analysis.db"

from data.database import DatabaseManager
DatabaseManager._instance = None
DatabaseManager.set_db_path(analyzer._DB)

from data.database import db

def initialize_data():
    """页面加载时自动初始化/刷新数据"""
    from data.database import db
    
    has_historical = False
    try:
        stats = db.get_statistics()
        has_historical = stats.get('by_source', {}).get('historical', 0) > 0
    except Exception:
        pass
    
    if not has_historical:
        try:
            from data.loaders.historical_loader import load_historical_data
            df_historical = load_historical_data()
            if not df_historical.empty:
                db.insert_data(df_historical, source='historical', replace=True)
                st.cache_data.clear()
        except Exception:
            pass
    
    try:
        from data.loaders.realtime_loader import load_realtime_data
        df_realtime = load_realtime_data()
        if not df_realtime.empty:
            db.insert_data(df_realtime, source='realtime', replace=True)
            st.cache_data.clear()
    except Exception:
        pass

initialize_data()

# ══════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=JetBrains+Mono:wght@300;400;600&display=swap');

html, [class*="css"] { font-family: 'JetBrains Mono', monospace !important; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }
.block-container {
    padding-top: .7rem !important;
    max-width: 100% !important;
    padding-left: 1.4rem !important;
    padding-right: 1.4rem !important;
}

/* Sidebar toggle always visible when collapsed */
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #1e1e1e; }
.stTabs [data-baseweb="tab"] {
    background: transparent; border: none; color: #444;
    font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
    padding: 10px 22px; font-family: 'JetBrains Mono', monospace !important; }
.stTabs [aria-selected="true"] {
    color: #e2ff5d !important;
    border-bottom: 2px solid #e2ff5d !important;
    background: transparent !important; }

/* KPI cards */
.kpi-row { display: flex; gap: 10px; margin: 10px 0 18px 0; flex-wrap: wrap; }
.kpi {
    flex: 1; min-width: 120px;
    background: #0d0d0d; border: 1px solid #1c1c1c;
    border-radius: 4px; padding: 16px 18px; }
.kpi-l { font-size: 12px; color: #ffffff; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 6px; }
.kpi-v { font-family: 'Syne', sans-serif; font-size: 30px; font-weight: 800; color: #ccc; line-height: 1; }
.kpi.hi .kpi-v { color: #e2ff5d; }
.kpi.bl .kpi-v { color: #60a5fa; }
.kpi.gr .kpi-v { color: #4ade80; }
.kpi.sm .kpi-v { font-size: 16px; padding-top: 8px; }

/* Section headers — WHITE and readable */
.sec {
    font-size: 15px; color: #ffffff; letter-spacing: .14em;
    text-transform: uppercase; font-weight: 600;
    border-top: 1px solid #1c1c1c; padding-top: 14px;
    margin: 24px 0 6px 0; }
.sec-note { font-size: 13px; color: #aaaaaa; margin: 0 0 10px 0; }

/* AI block */
.ai-block { background: #0a150a; border: 1px solid #1a301a; border-radius: 4px; padding: 16px 18px; margin-top: 10px; }
.ai-lbl   { font-size: 8px; color: #264026; letter-spacing: .2em; text-transform: uppercase; margin-bottom: 8px; }
.ai-text  { font-size: 12px; color: #6a9a6a; line-height: 1.8; }

iframe { border: none !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# CHART ENGINE
# SVG uses explicit px width/height = runtime clientWidth × given height.
# This prevents viewBox-scaling from making rendered height > iframe height.
# ══════════════════════════════════════════════════════
D3 = "https://d3js.org/d3.v7.min.js"


def _chart(js_body: str, height: int, scrollable: bool = False):
    overflow = "auto" if scrollable else "hidden"
    components.html(f"""<!DOCTYPE html>
<html><head>
<script src="{D3}"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html {{ background:#0a0a0a; }}
  body {{ background:#0a0a0a; overflow-x:hidden; overflow-y:{overflow}; width:100%; }}
  svg  {{ display:block; }}
  ::-webkit-scrollbar {{ width:6px; height:6px; }}
  ::-webkit-scrollbar-track {{ background:#111; }}
  ::-webkit-scrollbar-thumb {{ background:#333; border-radius:3px; }}
  #tt {{
    position:fixed; pointer-events:none; z-index:9999;
    background:#111; border:1px solid #2a2a2a; border-radius:4px;
    padding:8px 13px; font-family:'JetBrains Mono',monospace;
    font-size:11px; line-height:1.9; color:#888;
    opacity:0; transition:opacity .1s; max-width:300px; white-space:pre-wrap;
  }}
</style>
</head><body>
<div id="tt"></div>
<div id="root"></div>
<script>
const VW = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0) - 4;
const VH = {height};
const _tt = document.getElementById('tt');
function showTT(html, ev) {{
  _tt.innerHTML = html; _tt.style.opacity = 1;
  const rx = Math.min(ev.clientX + 14, window.innerWidth - 310);
  _tt.style.left = rx + 'px';
  _tt.style.top  = (ev.clientY - 8) + 'px';
}}
function hideTT() {{ _tt.style.opacity = 0; }}
{js_body}
</script>
</body></html>""",
        height=height + 22,
        scrolling=scrollable)


# helper: create SVG with exact pixel dimensions
_SVG = "d3.select('#root').append('svg').attr('width', VW).attr('height', {H})"


# ─── Monthly line ─────────────────────────────────────
def chart_monthly(monthly: list, height=240):
    _chart(f"""
const data = {json.dumps(monthly)};
const M = {{t:16, r:20, b:52, l:56}};
const w = VW-M.l-M.r, h = VH-M.t-M.b;
const svg = {_SVG.format(H='VH')};
const g = svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const parse = d3.timeParse('%Y-%m');
data.forEach(d => d.dt = parse(d.month));
const x = d3.scaleTime().domain(d3.extent(data, d=>d.dt)).range([0,w]);
const y = d3.scaleLinear().domain([0, d3.max(data,d=>d.count)*1.15]).range([h,0]).nice();
g.append('g').call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(''))
  .selectAll('line').attr('stroke','#161616').attr('stroke-dasharray','3,3');
g.selectAll('.domain').remove();
g.append('path').datum(data)
  .attr('d',d3.area().x(d=>x(d.dt)).y0(h).y1(d=>y(d.count)).curve(d3.curveMonotoneX))
  .attr('fill','#e2ff5d').attr('opacity',.09);
g.append('path').datum(data)
  .attr('d',d3.line().x(d=>x(d.dt)).y(d=>y(d.count)).curve(d3.curveMonotoneX))
  .attr('fill','none').attr('stroke','#e2ff5d').attr('stroke-width',2);
g.selectAll('circle').data(data).enter().append('circle')
  .attr('cx',d=>x(d.dt)).attr('cy',d=>y(d.count)).attr('r',3.5)
  .attr('fill','#e2ff5d').attr('opacity',.85)
  .on('mousemove',(ev,d)=>showTT(`<span style="color:#e2ff5d">${{d.month}}</span>\\n<b style="color:#fff">${{d.count}}</b> borrows`,ev))
  .on('mouseleave',hideTT);
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat("%b '%y")))
  .selectAll('text').attr('fill','#666').style('font-size','12px')
  .attr('transform','rotate(-20)').attr('text-anchor','end');
g.append('g').call(d3.axisLeft(y).ticks(5))
  .selectAll('text').attr('fill','#666').style('font-size','12px');
g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
""", height)


# ─── Category treemap ─────────────────────────────────
def chart_treemap(categories: list, height=320):
    _chart(f"""
const raw = {json.dumps(categories)};
const M = {{t:20, r:20, b:40, l:20}};
const w = Math.max(10, VW - M.l - M.r);
const h = Math.max(10, VH - M.t - M.b);
const maxMed = d3.max(raw, d=>d.med_h) || 1;
const root = d3.hierarchy({{children:raw}}).sum(d=>d.count).sort((a,b)=>b.value-a.value);
d3.treemap().size([w, h]).padding(2).round(true)(root);
const color = d3.scaleSequential().domain([0,maxMed]).interpolator(d3.interpolate('#0d1a0d','#22c55e'));
const svg = {_SVG.format(H='VH')};
const g = svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const cell = g.selectAll('g').data(root.leaves()).enter().append('g')
  .attr('transform',d=>`translate(${{d.x0}},${{d.y0}})`);
cell.append('rect')
  .attr('width',d=>Math.max(0,d.x1-d.x0)).attr('height',d=>Math.max(0,d.y1-d.y0))
  .attr('fill',d=>color(d.data.med_h)).attr('rx',2)
  .on('mousemove',(ev,d)=>showTT(`<b style="color:#fff">${{d.data.Category}}</b>\\n<span style="color:#555">BORROWS </span><span style="color:#e2ff5d">${{d.data.count}}</span>\\n<span style="color:#555">MED HOLD </span><span style="color:#fff">${{d.data.med_h}}h</span>\\n<span style="color:#555">ITEMS </span><span style="color:#aaa">${{d.data.items}}</span>`,ev))
  .on('mouseleave',hideTT);
cell.filter(d=>(d.x1-d.x0)>60&&(d.y1-d.y0)>24).append('text').attr('x',6).attr('y',17).text(d=>d.data.Category.length>17?d.data.Category.slice(0,16)+'…':d.data.Category).attr('fill','rgba(255,255,255,.65)').style('font-size','12px').style('pointer-events','none');
cell.filter(d=>(d.x1-d.x0)>75&&(d.y1-d.y0)>38).append('text').attr('x',6).attr('y',33).text(d=>`${{d.data.count}} · ${{d.data.med_h}}h`).attr('fill','rgba(255,255,255,.3)').style('font-size','11px').style('pointer-events','none');
const defs=svg.append('defs');
const lg=defs.append('linearGradient').attr('id','lg').attr('x1','0%').attr('x2','100%');
lg.append('stop').attr('offset','0%').attr('stop-color','#0d1a0d');
lg.append('stop').attr('offset','100%').attr('stop-color','#22c55e');
const legend=svg.append('g').attr('transform',`translate(${{VW-190}},${{M.t}})`);
legend.append('rect').attr('width',140).attr('height',7).attr('rx',2).attr('fill','url(#lg)').attr('opacity',.6);
legend.append('text').attr('y',19).text('short hold').attr('fill','#3a3a3a').style('font-size','10px');
legend.append('text').attr('x',140).attr('y',19).attr('text-anchor','end').text('long hold').attr('fill','#3a3a3a').style('font-size','10px');
""", height)


# ─── Utilization bars (scrollable) ────────────────────
def chart_util_bars(bars: list, sort_by: str = "score"):
    if sort_by == "count":   bars = sorted(bars, key=lambda x: -x['count'])
    elif sort_by == "util":  bars = sorted(bars, key=lambda x: -x['util'])
    else:                    bars = sorted(bars, key=lambda x: -(x.get('score', x['count']*x['util'])))

    ROW = 28
    svg_h = len(bars) * ROW + 60
    iframe_h = min(svg_h, 560)

    _chart(f"""
const D = {json.dumps(bars)};
const ROW = {ROW};
const M = {{t:8, r:90, b:34, l:272}};
const w = VW-M.l-M.r;
const h = D.length*ROW;
const svgH = h+M.t+M.b;
const svg = {_SVG.format(H='svgH')};
const g = svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const y = d3.scaleBand().domain(D.map(d=>d.item)).range([0,h]).padding(.24);
const x = d3.scaleLinear().domain([0,1]).range([0,w]);
const cats = [...new Set(D.map(d=>d.category))];
const col = d3.scaleOrdinal(d3.schemeTableau10).domain(cats);
[.25,.5,.75,1].forEach(v=>
  g.append('line').attr('x1',x(v)).attr('x2',x(v)).attr('y1',0).attr('y2',h)
   .attr('stroke','#1a1a1a').attr('stroke-dasharray','3,3'));
g.selectAll('rect.bar').data(D).enter().append('rect').attr('class','bar')
  .attr('y',d=>y(d.item)).attr('height',y.bandwidth()).attr('x',0).attr('rx',2)
  .attr('fill',d=>d.active?'#e2ff5d':col(d.category))
  .attr('opacity',d=>d.active?.92:.62).attr('width',0)
  .on('mousemove',(ev,d)=>showTT(
    `<b style="color:#fff">${{d.item}}</b>\\n`+
    `<span style="color:#555">UTIL &nbsp;&nbsp;</span><span style="color:#e2ff5d">${{(d.util*100).toFixed(1)}}%</span>\\n`+
    `<span style="color:#555">BORROWS</span> <span style="color:#fff">${{d.count}}</span>\\n`+
    `<span style="color:#555">AVG HOLD</span> <span style="color:#aaa">${{d.avg_h}}h</span>`+
    (d.active?'\\n<span style="color:#e2ff5d">● OUT NOW</span>':''),ev))
  .on('mouseleave',hideTT)
  .transition().duration(400).delay((_,i)=>i*6).attr('width',d=>x(d.util));
g.selectAll('text.lbl').data(D).enter().append('text').attr('class','lbl')
  .attr('y',d=>y(d.item)+y.bandwidth()/2+4.5).attr('x',-7).attr('text-anchor','end')
  .text(d=>d.item.length>34?d.item.slice(0,33)+'…':d.item)
  .attr('fill','#ccc').style('font-size','12px');
g.selectAll('text.pct').data(D).enter().append('text').attr('class','pct')
  .attr('y',d=>y(d.item)+y.bandwidth()/2+4.5).attr('x',d=>x(d.util)+5)
  .text(d=>(d.util*100).toFixed(0)+'%')
  .attr('fill',d=>d.active?'#e2ff5d':'#444').style('font-size','11px');
g.selectAll('text.cnt').data(D).enter().append('text').attr('class','cnt')
  .attr('y',d=>y(d.item)+y.bandwidth()/2+4.5).attr('x',w+68).attr('text-anchor','end')
  .text(d=>`×${{d.count}}`).attr('fill','#555').style('font-size','11px');
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(4).tickFormat(d=>(d*100)+'%'))
  .selectAll('text').attr('fill','#555').style('font-size','11px');
g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
""", iframe_h, scrollable=True)


# ─── Quadrant scatter ─────────────────────────────────
def _quantile(values: list, q: float) -> float:
    s = sorted(v for v in values if v is not None and v == v)
    if not s: return 0.0
    idx = q * (len(s)-1)
    lo, hi = int(idx), min(int(idx)+1, len(s)-1)
    return s[lo] + (s[hi]-s[lo])*(idx-lo)

def chart_quadrant(quadrant: list, p95_h: float, p95_count: float, height=400):
    cap_h = _quantile([q['avg_h'] for q in quadrant], 0.97)
    cap_c = _quantile([q['count'] for q in quadrant], 0.97)
    _chart(f"""
const raw = {json.dumps(quadrant)};
const D = raw.filter(d=>d.count>0&&d.avg_h>0);
const CAP_H={cap_h:.1f}, CAP_C={cap_c:.1f};
const M={{t:28,r:20,b:56,l:66}};
const w=Math.max(10,VW-M.l-M.r), h=Math.max(10,VH-M.t-M.b);
const svg={_SVG.format(H='VH')};
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const x=d3.scaleLinear().domain([0,CAP_C*1.06]).range([0,w]).nice();
const y=d3.scaleLinear().domain([0,CAP_H*1.06]).range([h,0]).nice();
const cats=[...new Set(D.map(d=>d.category))];
const col=d3.scaleOrdinal(d3.schemeTableau10).domain(cats);
const mx=d3.median(D,d=>Math.min(d.count,CAP_C));
const my=d3.median(D,d=>Math.min(d.avg_h,CAP_H));
g.append('line').attr('x1',x(mx)).attr('x2',x(mx)).attr('y1',0).attr('y2',h).attr('stroke','#222').attr('stroke-dasharray','4,3');
g.append('line').attr('x1',0).attr('x2',w).attr('y1',y(my)).attr('y2',y(my)).attr('stroke','#222').attr('stroke-dasharray','4,3');
[['HIGH DEMAND / LONG HOLD',w*.82,h*.08],['FREQUENT / QUICK USE',w*.82,h*.92],
  ['RARE / LONG HOLD',w*.10,h*.08],['LOW ACTIVITY',w*.10,h*.92]].forEach(([t,tx,ty])=>
  t.split(' / ').forEach((line,i)=>
    g.append('text').attr('x',tx).attr('y',ty+i*16).text(line)
     .attr('fill','#ffffff').style('font-size','14px').style('font-weight','600').style('letter-spacing','.05em').attr('text-anchor','middle')));
g.selectAll('circle').data(D).enter().append('circle')
  .attr('cx',d=>x(Math.min(d.count,CAP_C))).attr('cy',d=>y(Math.min(d.avg_h,CAP_H)))
  .attr('r',d=>d.active?7:3.5)
  .attr('fill',d=>d.active?'#e2ff5d':col(d.category)).attr('opacity',d=>d.active?1:.42)
  .on('mousemove',(ev,d)=>showTT(
    `<b style="color:#fff">${{d.item}}</b>\\n<span style="color:#555">${{d.category}}</span>\\n`+
    `<span style="color:#555">BORROWS </span><span style="color:#e2ff5d">${{d.count}}</span>  `+
    `<span style="color:#555">AVG </span><span style="color:#fff">${{d.avg_h}}h</span>`,ev))
  .on('mouseleave',hideTT);
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(6)).selectAll('text').attr('fill','#555').style('font-size','12px');
g.append('g').call(d3.axisLeft(y).ticks(6).tickFormat(d=>d+'h'))
  .selectAll('text').attr('fill','#555').style('font-size','12px');
g.selectAll('.domain,.tick line').attr('stroke','#1c1c1c');
svg.append('text').attr('x',M.l+w/2).attr('y',VH-6)
  .text('borrow frequency').attr('fill','#333').attr('text-anchor','middle').style('font-size','11px').style('letter-spacing','.09em');
svg.append('text').attr('transform','rotate(-90)').attr('x',-(M.t+h/2)).attr('y',16)
  .text('avg hold (h)').attr('fill','#333').attr('text-anchor','middle').style('font-size','11px').style('letter-spacing','.09em');
""", height)


# ─── Category items dual bar (scrollable) ─────────────
def chart_cat_items(items: list):
    top = items[:40]
    ROW = 30
    svg_h = len(top)*ROW + 64
    iframe_h = min(svg_h, 520)
    _chart(f"""
const D={json.dumps(top)};
const ROW={ROW};
const M={{t:30,r:20,b:10,l:20}};
const w=Math.max(10,VW-M.l-M.r), mid=w*0.48;
const LEFT_END=mid-130, RIGHT_START=mid+130;
const h=D.length*ROW;
const svgH=h+M.t+M.b;
const svg={_SVG.format(H='svgH')};
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const band=d3.scaleBand().domain(D.map(d=>d.item)).range([0,h]).padding(.24);
const xL=d3.scaleLinear().domain([0,d3.max(D,d=>d.count)*1.1]).range([0,LEFT_END]);
const xR=d3.scaleLinear().domain([0,d3.max(D,d=>d.avg_h)*1.1]).range([0,w-RIGHT_START]);
svg.append('text').attr('x',M.l+LEFT_END/2).attr('y',19)
  .text('BORROW COUNT').attr('fill','#555').attr('text-anchor','middle').style('font-size','10px').style('letter-spacing','.12em');
svg.append('text').attr('x',M.l+RIGHT_START+(w-RIGHT_START)/2).attr('y',19)
  .text('AVG HOLD DURATION').attr('fill','#555').attr('text-anchor','middle').style('font-size','10px').style('letter-spacing','.12em');
g.append('line').attr('x1',mid).attr('x2',mid).attr('y1',0).attr('y2',h).attr('stroke','#171717');
g.selectAll('rect.L').data(D).enter().append('rect').attr('class','L')
  .attr('y',d=>band(d.item)).attr('height',band.bandwidth()).attr('rx',2)
  .attr('fill','#3b82f6').attr('opacity',.65)
  .attr('x',LEFT_END).attr('width',0)
  .transition().duration(380).delay((_,i)=>i*9)
  .attr('x',d=>LEFT_END-xL(d.count)).attr('width',d=>xL(d.count));
g.selectAll('text.Lv').data(D).enter().append('text').attr('class','Lv')
  .attr('y',d=>band(d.item)+band.bandwidth()/2+4.5)
  .attr('x',d=>LEFT_END-xL(d.count)-5).attr('text-anchor','end')
  .text(d=>d.count).attr('fill','#aaa').style('font-size','11px');
g.selectAll('rect.R').data(D).enter().append('rect').attr('class','R')
  .attr('y',d=>band(d.item)).attr('height',band.bandwidth())
  .attr('x',RIGHT_START).attr('rx',2)
  .attr('fill',d=>d.active?'#e2ff5d':'#22c55e').attr('opacity',d=>d.active?.9:.62)
  .attr('width',0)
  .transition().duration(380).delay((_,i)=>i*9)
  .attr('width',d=>xR(d.avg_h));
g.selectAll('text.Rv').data(D).enter().append('text').attr('class','Rv')
  .attr('y',d=>band(d.item)+band.bandwidth()/2+4.5)
  .attr('x',d=>RIGHT_START+xR(d.avg_h)+5)
  .text(d=>d.avg_h+'h').attr('fill','#aaa').style('font-size','11px');
g.selectAll('text.C').data(D).enter().append('text').attr('class','C')
  .attr('y',d=>band(d.item)+band.bandwidth()/2+4.5).attr('x',mid).attr('text-anchor','middle')
  .text(d=>{{const s=d.item.replace(/\\s+\\d+$/,'');return s.length>26?s.slice(0,25)+'…':s;}})
  .attr('fill',d=>d.active?'#e2ff5d':'#ddd').style('font-size','12px');
g.selectAll('circle.act').data(D.filter(d=>d.active)).enter()
  .append('circle').attr('class','act')
  .attr('cx',mid+124).attr('cy',d=>band(d.item)+band.bandwidth()/2)
  .attr('r',3.5).attr('fill','#e2ff5d');
g.selectAll('rect.hov').data(D).enter().append('rect').attr('class','hov')
  .attr('y',d=>band(d.item)).attr('height',band.bandwidth())
  .attr('x',0).attr('width',w).attr('fill','transparent')
  .on('mousemove',(ev,d)=>showTT(
    `<b style="color:#fff">${{d.item}}</b>\\n`+
    `<span style="color:#555">BORROWS </span><span style="color:#3b82f6">${{d.count}}</span>\\n`+
    `<span style="color:#555">AVG DUR &nbsp;</span><span style="color:#22c55e">${{d.avg_h}}h</span>  `+
    `<span style="color:#555">MED </span><span style="color:#aaa">${{d.med_h}}h</span>`+
    (d.active?'\\n<span style="color:#e2ff5d">● OUT NOW</span>':''),ev))
  .on('mouseleave',hideTT);
""", iframe_h, scrollable=True)


# ─── Category multi-line timeline ─────────────────────
def chart_cat_timeline(timeline: list, top10: list, height=300):
    _chart(f"""
const raw={json.dumps(timeline)};
const items={json.dumps(top10[:10])};
const parse=d3.timeParse('%Y-%m');
const byItem={{}};
items.forEach(it=>byItem[it]=[]);
raw.forEach(d=>{{if(byItem[d['item name(with num)']])byItem[d['item name(with num)']].push({{dt:parse(d.month),count:d.count}});}});
const M={{t:16,r:175,b:50,l:50}};
const w=Math.max(10,VW-M.l-M.r), h=Math.max(10,VH-M.t-M.b);
const svg={_SVG.format(H='VH')};
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const allDates=raw.map(d=>parse(d.month)).filter(Boolean);
const x=d3.scaleTime().domain(d3.extent(allDates)).range([0,w]);
const y=d3.scaleLinear().domain([0,d3.max(raw,d=>d.count)*1.15]).range([h,0]).nice();
const col=d3.scaleOrdinal(d3.schemeTableau10).domain(items);
g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(''))
  .selectAll('line').attr('stroke','#161616').attr('stroke-dasharray','3,3');
g.selectAll('.domain').remove();
items.forEach(item=>{{
  const pts=(byItem[item]||[]).filter(d=>d.dt);
  if(!pts.length)return;
  g.append('path').datum(pts)
    .attr('d',d3.line().x(d=>x(d.dt)).y(d=>y(d.count)).curve(d3.curveMonotoneX))
    .attr('fill','none').attr('stroke',col(item)).attr('stroke-width',1.8).attr('opacity',.72)
    .attr('data-item',item).attr('class','timeline-line');
  g.selectAll(null).data(pts).enter().append('circle')
    .attr('cx',d=>x(d.dt)).attr('cy',d=>y(d.count)).attr('r',3)
    .attr('fill',col(item)).attr('opacity',.88)
    .attr('data-item',item)
    .on('mousemove',(ev,d)=>showTT(
      `<span style="color:${{col(item)}}">${{item}}</span>\\n`+
      `<span style="color:#555">${{d3.timeFormat('%b %Y')(d.dt)}}</span>  `+
      `<span style="color:#fff">${{d.count}} borrows</span>`,ev))
    .on('mouseleave',hideTT);
}});
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat("%b '%y")))
  .selectAll('text').attr('fill','#666').style('font-size','11px')
  .attr('transform','rotate(-20)').attr('text-anchor','end');
g.append('g').call(d3.axisLeft(y).ticks(4))
  .selectAll('text').attr('fill','#666').style('font-size','11px');
g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
items.forEach((item,i)=>{{
  const lg=svg.append('g').attr('transform',`translate(${{VW-168}},${{M.t+i*19}})`).style('cursor','pointer');
  const legendLine=lg.append('line').attr('x1',0).attr('x2',12).attr('y1',7).attr('y2',7)
    .attr('stroke',col(item)).attr('stroke-width',2).attr('opacity',.8).attr('data-item',item).attr('class','legend-line');
  lg.append('text').attr('x',16).attr('y',11)
    .text(item.length>20?item.slice(0,19)+'…':item).attr('fill','#bbb').style('font-size','10px');
  lg.on('click',function(){{
    const isHidden=d3.select('path[data-item="'+item+'"]').attr('opacity')==='0';
    d3.select('path[data-item="'+item+'"]').transition().duration(200).attr('opacity',isHidden?0.72:0);
    d3.selectAll('circle[data-item="'+item+'"]').transition().duration(200).attr('opacity',isHidden?0.88:0);
    legendLine.transition().duration(200).attr('opacity',isHidden?0.8:0.15);
  }});
  lg.append('title').text('点击切换显示/隐藏');
}});
""", height)


# ─── Single item Gantt (scrollable) ───────────────────
def chart_gantt(gantt: list):
    if not gantt:
        st.markdown("<p style='color:#333;padding:20px;font-size:13px'>No records found.</p>",
                    unsafe_allow_html=True)
        return
    ROW, GAP = 24, 4
    svg_h   = len(gantt)*(ROW+GAP) + 80
    iframe_h = min(svg_h, 540)

    _chart(f"""
const D = {json.dumps(gantt)};
const parse = d3.timeParse('%Y-%m-%dT%H:%M:%S');
D.forEach(d=>{{ d.s=parse(d.start); d.e=parse(d.end); }});

const ROW={ROW}, GAP={GAP};
const M={{t:10,r:20,b:54,l:16}};
const w=Math.max(10,VW-M.l-M.r);
const h=D.length*(ROW+GAP);
const svgH=h+M.t+M.b;
const svg={_SVG.format(H='svgH')};
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);

// KEY FIX: x-axis domain uses only REAL start/end dates.
// Active items' end is clamped to last real return date (not "now = 2026")
// so old 2021 bars aren't compressed to invisible 2px.
const realEnds   = D.filter(d=>!d.active).map(d=>d.e).filter(Boolean);
const allStarts  = D.map(d=>d.s).filter(Boolean);
const domainMin  = d3.min(allStarts);
const domainMax  = realEnds.length
  ? d3.max(realEnds)
  : new Date(d3.max(allStarts).getTime() + 90*24*3600*1000);

const x = d3.scaleTime().domain([domainMin, domainMax]).range([0,w]);

// Year bands
const years=[...new Set(D.map(d=>d.s?d.s.getFullYear():null).filter(Boolean))];
years.forEach((yr,i)=>{{
  const xs=Math.max(0, x(new Date(yr,0,1)));
  const xe=Math.min(w, x(new Date(yr,11,31)));
  if(xe>xs){{
    g.append('rect').attr('x',xs).attr('y',0).attr('width',xe-xs).attr('height',h)
     .attr('fill',i%2?'#0d0d0d':'#0a0a0a');
    g.append('text').attr('x',(xs+xe)/2).attr('y',h+33)
     .text(yr).attr('fill','#444').style('font-size','12px').attr('text-anchor','middle');
  }}
}});

g.append('g').call(d3.axisBottom(x).ticks(10).tickSize(h).tickFormat(''))
  .selectAll('line').attr('stroke','#141414');
g.select('.domain').remove();

D.forEach((d,i)=>{{
  const clr=d.active?'#e2ff5d':(d.source==='realtime'?'#4ade80':'#3b82f6');
  // Active items draw to domainMax to show "still out"
  const barEnd = d.active ? domainMax : d.e;
  const bw = Math.max(3, x(barEnd)-x(d.s));
  g.append('rect')
    .attr('x',x(d.s)).attr('y',i*(ROW+GAP))
    .attr('width',bw).attr('height',ROW)
    .attr('rx',2).attr('fill',clr).attr('opacity',d.active?.88:.78)
    .on('mousemove',ev=>showTT(
      `<span style="color:#555">START </span><span style="color:#fff">${{d.start.replace('T',' ')}}</span>\\n`+
      `<span style="color:#555">END   </span><span style="color:#aaa">${{d.active?'currently out':d.end.replace('T',' ')}}</span>\\n`+
      `<span style="color:#e2ff5d">${{d.hours!=null?d.hours+'h':'ongoing'}}</span>`+
      `<span style="color:#333">  ${{d.source}}</span>`,ev))
    .on('mouseleave',hideTT);
}});

g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(10).tickFormat(d3.timeFormat('%b %Y')))
  .selectAll('text').attr('fill','#666').style('font-size','12px');
g.selectAll('.tick line').attr('stroke','#1a1a1a');

[['historical','#3b82f6'],['realtime','#4ade80'],['active (ongoing)','#e2ff5d']].forEach(([l,c],i)=>{{
  const lg=svg.append('g').attr('transform',`translate(${{i*145+M.l}},${{svgH-8}})`);
  lg.append('rect').attr('width',9).attr('height',9).attr('rx',1).attr('fill',c).attr('opacity',.85);
  lg.append('text').attr('x',13).attr('y',9).text(l).attr('fill','#666').style('font-size','11px');
}});
""", iframe_h, scrollable=True)


# ─── Monthly bars ─────────────────────────────────────
# ─── Calendar Heatmap ─────────────────────────────────
def chart_heatmap(gantt: list, height=220):
    """日历热力图 - 按天展示借用频率"""
    if not gantt:
        st.markdown("<p style='color:#333;padding:20px;font-size:13px'>No records found.</p>",
                    unsafe_allow_html=True)
        return
    
    _chart(f"""
const D={json.dumps(gantt)};
if(!D || !D.length) {{
  document.body.innerHTML = '<p style="color:#444;padding:40px;font-family:monospace">No borrow data</p>';
}} else {{
const dayMap={{}};
D.forEach(d=>{{if(!d.start)return;const date=d.start.split('T')[0];if(!dayMap[date])dayMap[date]={{c:0,h:0,r:[]}};dayMap[date].c++;if(d.hours)dayMap[date].h+=d.hours;dayMap[date].r.push(d)}});
const dates=Object.keys(dayMap).sort();
if(!dates.length) {{
  document.body.innerHTML = '<p style="color:#444;padding:40px;font-family:monospace">No valid dates</p>';
}} else {{
const sD=new Date(dates[0]);
const eD=new Date(dates[dates.length-1]);
const c=12,gap=3;
const sW=new Date(sD);sW.setDate(sW.getDate()-sW.getDay());
const tD=Math.ceil((eD-sW)/86400000)+1;
const tW=Math.ceil(tD/7);
const lW=30,mT=26,mB=40;
const sVW=Math.max(tW*(c+gap)+lW+20,VW);
const sVH=7*(c+gap)+mT+mB;
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{sVW}} ${{sVH}}`).attr('preserveAspectRatio','xMidYMid meet');
const maxC=d3.max(Object.values(dayMap),d=>d.c)||1;
const clr=d3.scaleQuantize().domain([0,maxC]).range(['#161b22','#0e4429','#006d32','#26a641']);
const g2=svg.append('g').attr('transform',`translate(${{lW}},${{mT}})`);
const wds=[[0,'Sun'],[2,'Mon'],[4,'Tue'],[6,'Wed']];
wds.forEach(([i,n])=>{{svg.append('text').attr('x',lW-4).attr('y',mT+i/2*(c+gap)+c/2+4).text(n).attr('fill','#555').style('font-size','10px').attr('text-anchor','end')}});
const today=new Date();
for(let w=0;w<tW;w++){{for(let d=0;d<7;d++){{const dD=new Date(sW);dD.setDate(dD.getDate()+w*7+d);const ds=dD.toISOString().split('T')[0];const info=dayMap[ds];const inR=dD>=sD&&dD<=eD;const isF=dD>today;const fill=info?clr(info.c):(inR&&!isF?'#1c1c1c':'transparent');const op=isF?0.3:(info?1:0.5);g2.append('rect').attr('x',w*(c+gap)).attr('y',d*(c+gap)).attr('width',c).attr('height',c).attr('rx',2).attr('fill',fill).attr('opacity',op).attr('stroke',inR&&!isF?'#252525':'none').attr('stroke-width',0.5).on('mouseover',function(ev){{if(!info)return;const hrs=info.h.toFixed(1);const rec=info.r.length===1?info.r[0].start.replace('T',' '):info.r.length+' borrows';showTT('<span style="color:#888">'+ds+'</span> <span style="color:#26a641">'+info.c+'</span> <span style="color:#666">'+hrs+'h</span> <span style="color:#444;font-size:10px">'+rec+'</span>',ev)}}).on('mouseout',hideTT)}}}}
const months=d3.timeMonths(sD,eD);
months.forEach(m=>{{const wN=Math.floor((m-sW)/7);svg.append('text').attr('x',lW+wN*(c+gap)).attr('y',sVH-12).text(d3.timeFormat('%b')(m)).attr('fill','#555').style('font-size','10px')}});
const lX=sVW-110;
[['0','#161b22'],['1','#0e4429'],['2','#006d32'],['3+','#26a641']].forEach(([l,c],i)=>{{svg.append('rect').attr('x',lX+i*26).attr('y',sVH-12).attr('width',9).attr('height',9).attr('rx',2).attr('fill',c)}});
svg.append('text').attr('x',lX-6).attr('y',sVH-4).text('borrows').attr('fill','#555').style('font-size','9px');
}}}}
""", height, False)


def chart_monthly_bars(monthly: list, height=210):
    try:
        json.dumps(monthly)
    except:
        monthly = []
    _chart(f"""
const D={json.dumps(monthly)};
if(!D || !D.length) {{
  document.body.innerHTML = '<p style="color:#444;padding:40px;font-family:monospace;text-align:center">No monthly data</p>';
}} else {{
try {{
const maxVal=d3.max(D,d=>d.total_h)||1;
const M={{t:10,r:20,b:54,l:56}};
const w=Math.max(10,VW-M.l-M.r), h=Math.max(10,VH-M.t-M.b);
const svg={_SVG.format(H='VH')};
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const x=d3.scaleBand().domain(D.map(d=>d.month)).range([0,w]).padding(.22);
const y=d3.scaleLinear().domain([0,maxVal*1.12]).range([h,0]).nice();
g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(''))
  .selectAll('line').attr('stroke','#141414').attr('stroke-dasharray','3,3');
g.selectAll('.domain').remove();
g.selectAll('rect').data(D).enter().append('rect')
  .attr('x',d=>x(d.month)).attr('y',d=>y(d.total_h))
  .attr('width',x.bandwidth()).attr('height',d=>Math.max(0,h-y(d.total_h)))
  .attr('rx',2).attr('fill','#3b82f6').attr('opacity',.65)
  .on('mousemove',(ev,d)=>showTT(
    `<span style="color:#aaa">${{d.month}}</span>\\n`+
    `<span style="color:#3b82f6">${{d.total_h}}h</span>  <span style="color:#fff">${{d.count}} borrows</span>`,ev))
  .on('mouseleave',hideTT);
const skip=Math.ceil(D.length/10);
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).tickValues(x.domain().filter((_,i)=>i%skip===0)))
  .selectAll('text').attr('fill','#666').style('font-size','12px')
  .attr('transform','rotate(-30)').attr('text-anchor','end');
g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d=>d+'h'))
  .selectAll('text').attr('fill','#666').style('font-size','12px');
g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
}} catch(e) {{
  document.body.innerHTML = '<p style="color:red;padding:40px;font-family:monospace">Error: '+e.message+'</p>';
}}
}}
""", height)


# ─── Temporal heatmap ─────────────────────────────────
def chart_temporal_heatmap(heatmap: list, height=280, scrollable=False):
    js_scrollable = "true" if scrollable else "false"
    _chart(f"""
const D={json.dumps(heatmap)};
const DAYS=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
const labelW=46;
const cs=Math.max(10, Math.floor((VW-labelW-24)/25));
const gap=2, unit=cs+gap;
const topPad=26;
const contentH = 7 * unit + topPad + 10;
const actualH = {js_scrollable} ? Math.max(VH, contentH) : VH;
const svg=d3.select('#root').append('svg').attr('width', VW).attr('height', actualH);
const g=svg.append('g').attr('transform',`translate(${{labelW}},${{topPad}})`);
const maxC=d3.max(D,d=>d.count)||1;
const col=d3.scaleSequential().domain([0,maxC]).interpolator(d3.interpolate('#111','#e2ff5d'));
for(let wd=0;wd<7;wd++)for(let hr=0;hr<24;hr++)
  g.append('rect').attr('x',hr*unit).attr('y',wd*unit)
   .attr('width',cs).attr('height',cs).attr('rx',1.5).attr('fill','#111');
D.forEach(d=>
  g.append('rect').attr('x',d.hour*unit).attr('y',d.weekday*unit)
   .attr('width',cs).attr('height',cs).attr('rx',1.5).attr('fill',col(d.count))
   .on('mousemove',ev=>showTT(
     `<span style="color:#555">${{DAYS[d.weekday]}} ${{String(d.hour).padStart(2,'0')}}:00</span>\\n`+
     `<b style="color:#e2ff5d">${{d.count}}</b> borrows`,ev))
   .on('mouseleave',hideTT));
DAYS.forEach((l,i)=>g.append('text').attr('x',-6).attr('y',i*unit+cs-2)
  .text(l).attr('fill','#888').style('font-size','13px').attr('text-anchor','end'));
[0,4,8,12,16,20,23].forEach(hr=>g.append('text').attr('x',hr*unit+cs/2).attr('y',-6)
  .text(String(hr).padStart(2,'0')+'h').attr('fill','#777').style('font-size','11px').attr('text-anchor','middle'));
""", height, scrollable=scrollable)


# ─── Weekday + Month bars ─────────────────────────────
def chart_wd_month(by_weekday: list, by_month: list, height=220):
    _chart(f"""
const WD={json.dumps(by_weekday)}, MO={json.dumps(by_month)};
const M={{t:20,r:10,b:46,l:46}};
const hw=(VW-M.l-M.r)/2-20, h=VH-M.t-M.b;
function drawBars(data,xKey,yKey,color,offX){{
  const g=svg.append('g').attr('transform',`translate(${{offX}},${{M.t}})`);
  const x=d3.scaleBand().domain(data.map(d=>d[xKey])).range([0,hw]).padding(.26);
  const y=d3.scaleLinear().domain([0,d3.max(data,d=>d[yKey])*1.12]).range([h,0]).nice();
  g.append('g').call(d3.axisLeft(y).ticks(3).tickSize(-hw).tickFormat(''))
    .selectAll('line').attr('stroke','#141414').attr('stroke-dasharray','3,3');
  g.selectAll('.domain').remove();
  g.selectAll('rect').data(data).enter().append('rect')
    .attr('x',d=>x(d[xKey])).attr('y',d=>y(d[yKey]))
    .attr('width',x.bandwidth()).attr('height',d=>Math.max(0,h-y(d[yKey])))
    .attr('rx',2).attr('fill',color).attr('opacity',.7)
    .on('mousemove',(ev,d)=>showTT(`<span style="color:#aaa">${{d[xKey]}}</span>  <b style="color:#fff">${{d[yKey]}}</b>`,ev))
    .on('mouseleave',hideTT);
  g.append('g').attr('transform',`translate(0,${{h}})`)
    .call(d3.axisBottom(x)).selectAll('text').attr('fill','#666').style('font-size','12px');
  g.append('g').call(d3.axisLeft(y).ticks(3))
    .selectAll('text').attr('fill','#666').style('font-size','12px');
  g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
}}
const svg={_SVG.format(H='VH')};
drawBars(WD,'label','count','#60a5fa',M.l);
drawBars(MO,'label','count','#4ade80',M.l+hw+40);
svg.append('text').attr('x',M.l+hw/2).attr('y',VH-4)
  .text('BY WEEKDAY').attr('fill','#333').attr('text-anchor','middle').style('font-size','10px').style('letter-spacing','.12em');
svg.append('text').attr('x',M.l+hw+40+hw/2).attr('y',VH-4)
  .text('BY MONTH').attr('fill','#333').attr('text-anchor','middle').style('font-size','10px').style('letter-spacing','.12em');
""", height)


# ══════════════════════════════════════════════════════
# AI BUTTON
# ══════════════════════════════════════════════════════
def ai_button(prompt: str, key: str):
    col, _ = st.columns([1, 6])
    with col:
        clicked = st.button("⚡ AI Insight", key=f"ai_{key}", use_container_width=True)
    if clicked:
        with st.spinner("Analyzing…"):
            try:
                import anthropic
                client = anthropic.Anthropic()
                msg = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=350,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = msg.content[0].text
                st.markdown(
                    f'<div class="ai-block"><div class="ai-lbl">◈ AI Insight</div>'
                    f'<div class="ai-text">{text}</div></div>',
                    unsafe_allow_html=True)
            except ImportError:
                st.error("Run: pip install anthropic")
            except Exception as e:
                st.error(f"API error: {e}")


# ══════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ◈ IMA Lab")
    src_opt = st.radio("Source", ["All", "Historical", "Realtime"],
                       horizontal=True, label_visibility="collapsed", key="src_opt")
    _src = {"All": None, "Historical": "historical", "Realtime": "realtime"}[src_opt]
    st.markdown("---")
    if st.button("↺ Refresh realtime", use_container_width=True):
        with st.spinner("Fetching…"):
            try:
                from data.loaders.realtime_loader import load_realtime_data
                from data.database import db
                df_r = load_realtime_data()
                db.insert_data(df_r, source='realtime', replace=True)
                st.success(f"Updated: {len(df_r)} records")
                st.cache_data.clear()
            except Exception as e:
                st.error(str(e))
    try:
        from data.database import db as _db
        s = _db.get_statistics()
        st.markdown("---")
        st.caption(f"historical  {s['by_source'].get('historical',0):,}")
        st.caption(f"realtime    {s['by_source'].get('realtime',0):,}")
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# HEADER + GLOBAL DATE RANGE
# ══════════════════════════════════════════════════════
_ha, _hb = st.columns([2, 7])
with _ha:
    st.markdown(
        "<h1 style='font-family:Syne,sans-serif;font-weight:800;font-size:1.7rem;"
        "letter-spacing:-.04em;margin:0;padding:0'>IMA Lab ◈</h1>"
        "<p style='font-size:9px;color:#222;letter-spacing:.2em;margin:3px 0 0 0'>"
        "EQUIPMENT BORROWING INTELLIGENCE</p>",
        unsafe_allow_html=True)

bounds = analyzer.get_bounds(_src)
all_bounds = analyzer.get_bounds(None) or {}
if not all_bounds:
    all_bounds = {"min": "", "max": ""}
with _hb:
    _dc1, _dc2, _dc3, _dc4 = st.columns([2, 2, 1, 2])
    with _dc1:
        _start = st.text_input("From", value=bounds['min'],
                               placeholder="YYYY-MM-DD", key="g_start")
    with _dc2:
        _end = st.text_input("To", value=bounds['max'],
                             placeholder="YYYY-MM-DD", key="g_end")
    with _dc3:
        st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        if st.button("↻", key="apply", help="Apply date range"):
            start_input = _start.strip() if _start else ""
            end_input = _end.strip() if _end else ""
            data_min = all_bounds.get('min', '')
            data_max = all_bounds.get('max', '')
            errors = []
            if start_input and data_min:
                if start_input < data_min:
                    errors.append(f"开始日期不能早于数据最小日期 ({data_min})")
            if end_input and data_max:
                if end_input > data_max:
                    errors.append(f"结束日期不能晚于数据最大日期 ({data_max})")
            if errors:
                for err in errors:
                    st.error(err)
            else:
                st.cache_data.clear()
    with _dc4:
        st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("Reset → All", key="reset_all", help="Reset source + date range"):
                st.session_state["g_start"] = all_bounds.get("min", "")
                st.session_state["g_end"] = all_bounds.get("max", "")
                st.session_state["src_opt"] = "All"
                st.cache_data.clear()
        with c2:
            if st.button("⚙️", key="open_sheet_settings", help="Google Sheet 设置"):
                st.session_state['show_sheet_settings'] = not st.session_state.get('show_sheet_settings', False)

    if st.session_state.get('show_sheet_settings', False):
        st.markdown("### ⚙️ Google Sheet 设置")
        st.info("📧 新Sheet需分享给: qt2113@imalab-2025.iam.gserviceaccount.com")
        custom_cfg = load_sheet_config()
        current_id = custom_cfg.get('sheet_id', GOOGLE_SHEET_ID)
        current_names = custom_cfg.get('sheet_names', TARGET_SHEETS)
        
        default_url = f"https://docs.google.com/spreadsheets/d/{current_id}/edit"
        
        sheet_url = st.text_input(
            "Sheet 链接",
            value=st.session_state.get('custom_sheet_url', default_url),
            placeholder="https://docs.google.com/spreadsheets/d/...",
            key="sheet_url_input2"
        )
        
        sheet_names_input = st.text_input(
            "Sheet名称（逗号分隔）",
            value=st.session_state.get('custom_sheet_names', ','.join(current_names)),
            help="多个Sheet用逗号分隔，如: Fall 2025,Spring 2026",
            key="sheet_names_input2"
        )
        
        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("💾 保存并应用", key="save_sheet_config2", use_container_width=True):
                match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
                if match:
                    new_id = match.group(1)
                    new_names = [s.strip() for s in sheet_names_input.split(',') if s.strip()]
                    
                    st.session_state['custom_sheet_url'] = sheet_url
                    st.session_state['custom_sheet_names'] = sheet_names_input
                    
                    save_sheet_config(new_id, new_names)
                    
                    try:
                        from data.loaders.realtime_loader import load_realtime_data
                        from data.database import db
                        df_r = load_realtime_data()
                        db.insert_data(df_r, source='realtime', replace=True)
                        st.cache_data.clear()
                        
                        if not df_r.empty:
                            min_date = df_r['Start'].min()
                            max_date = df_r['Start'].max()
                            st.session_state["g_start"] = min_date.strftime('%Y-%m-%d')
                            st.session_state["g_end"] = max_date.strftime('%Y-%m-%d')
                        
                        st.success(f"已保存并刷新: {len(df_r)} 条记录")
                    except Exception as e:
                        st.success(f"已保存! Sheet ID: {new_id} (刷新失败: {e})")
                    
                    st.session_state['show_sheet_settings'] = False
                    st.rerun()
                else:
                    st.error("无效的Sheet链接")
        
        with col_reset:
            if st.button("↺ 恢复默认", key="reset_sheet_config2", use_container_width=True):
                st.session_state.pop('custom_sheet_url', None)
                st.session_state.pop('custom_sheet_names', None)
                clear_sheet_config()
                st.session_state['show_sheet_settings'] = False
                st.rerun()
        
        if custom_cfg.get('is_custom'):
            st.caption("✅ 当前使用自定义配置")
        
        if st.button("关闭", key="close_sheet_settings"):
            st.session_state['show_sheet_settings'] = False
            st.rerun()

        st.markdown("---")

src_label = "All" if _src is None else ("Historical" if _src == "historical" else "Realtime")
st.caption(
    f"Filter — Source: {src_label} · Range: {bounds.get('min','')} → {bounds.get('max','')} "
    f"(All: {all_bounds.get('min','')} → {all_bounds.get('max','')})"
)

_s = _start or None
_e = _end   or None

st.markdown("<hr style='border:none;border-top:1px solid #131313;margin:5px 0 0 0'>",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════
tab_ov, tab_fleet, tab_cat, tab_item, tab_pat = st.tabs([
    "Overview", "Fleet Health", "Category", "Single Item", "Patterns"
])


# ── OVERVIEW ─────────────────────────────────────────
with tab_ov:
    ov = json.loads(analyzer.overview(source=_src, start=_s, end=_e))
    k  = ov['kpi']
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-l">Total Borrows</div>
        <div class="kpi-v">{k['total']:,}</div></div>
      <div class="kpi"><div class="kpi-l">Unique Items</div>
        <div class="kpi-v">{k['unique_items']:,}</div></div>
      <div class="kpi hi"><div class="kpi-l">Currently Out</div>
        <div class="kpi-v">{k['active_now']}</div></div>
      <div class="kpi bl"><div class="kpi-l">Avg Hold</div>
        <div class="kpi-v">{k['avg_hours']:.0f}<span style="font-size:14px;color:#222">h</span></div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Monthly Borrow Volume</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">展示每月借用次数，用于观察设备需求的季节性变化和整体使用走势</div>',
                unsafe_allow_html=True)
    chart_monthly(ov['monthly'], height=240)

    st.markdown('<div class="sec">Category Map</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">矩形面积=该类别总借用次数，颜色深度=中位持有时长（颜色越深表示借用周期越长，可能存在周转问题）</div>',
                unsafe_allow_html=True)
    chart_treemap(ov['categories'], height=320)

    ai_button(
        f"Analyze IMA Lab equipment borrowing. KPIs: {json.dumps(k)}. "
        f"Top categories: {json.dumps(sorted(ov['categories'],key=lambda x:-x['count'])[:5])}. "
        f"Monthly trend last 6m: {json.dumps(ov['monthly'][-6:])}. "
        "3-4 insights, plain text, no bullets, 120 words max.", key="ov")


# ── FLEET HEALTH ─────────────────────────────────────
with tab_fleet:
    fc1, fc2 = st.columns([2, 3])
    with fc1:
        fh_cat = st.selectbox("Category", ["(All)"] + analyzer.get_categories(),
                              key="fh_cat", label_visibility="collapsed")
    with fc2:
        fh_n = st.slider("Top N", 10, 100, 40, key="fh_n", label_visibility="collapsed")

    st.markdown('<div class="sec">Sort Options</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sec-note">
    <b>Demand Score（需求指数）</b>：借用次数 × 利用率的综合得分，反映物品热门程度<br>
    <b>Utilization（利用率）</b>：借用次数/时间跨度，值越高说明使用越频繁<br>
    <b>Frequency（借用频次）</b>：仅按借用次数排序，最常被借用的物品
    </div>
    """, unsafe_allow_html=True)

    sort_by = st.selectbox("Sort by", ["Demand Score", "Utilization", "Frequency"],
                           key="fh_sort", label_visibility="collapsed")

    sort_map = {"Utilization": "util", "Frequency": "count", "Demand Score": "score"}
    fh = json.loads(analyzer.fleet_health(
        category=None if fh_cat.startswith("(") else fh_cat,
        source=_src, start=_s, end=_e, top_n=fh_n))

    st.markdown('<div class="sec">Item Utilization Rate</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">统计具名物品（排除捆绑套装）的借用频率，需至少2次借用方可纳入。横轴为借用次数，黄色表示当前正在外借</div>',
                unsafe_allow_html=True)
    if fh['bars']:
        chart_util_bars(fh['bars'], sort_by=sort_map[sort_by])
    else:
        st.caption("No data.")

    st.markdown('<div class="sec">Demand × Hold Duration Quadrant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">横轴为借用频率，纵轴为平均持有时长。右上象限为高频率长周期（热门急需品），左下象限为低频率短周期（低热度闲置品），辅助采购决策</div>',
                unsafe_allow_html=True)
    if fh['quadrant']:
        chart_quadrant(fh['quadrant'], fh['p95_h'], fh['p95_count'], height=420)
    else:
        st.caption("暂无数据 - 该分类下物品借用数据不足")

    ai_button(
        f"Fleet health. Top 8 by demand score: {json.dumps(sorted(fh['bars'],key=lambda x:-(x.get('score',x['count']*x['util'])))[:8])}. "
        f"Total items analyzed: {len(fh['quadrant'])}. "
        "Procurement needs, underused items. Plain text, 120 words max.", key="fleet")


# ── CATEGORY ─────────────────────────────────────────
with tab_cat:
    cc1, _ = st.columns([2, 5])
    with cc1:
        sel_cat = st.selectbox("Category", analyzer.get_categories(),
                               key="cat_sel", label_visibility="collapsed")

    cat_d      = json.loads(analyzer.category_analysis(sel_cat, source=_src, start=_s, end=_e))
    n_items    = len(cat_d['items'])
    active_n   = sum(1 for x in cat_d['items'] if x.get('active'))
    tot_borrow = sum(x['count'] for x in cat_d['items'])

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-l">Named Items</div>
        <div class="kpi-v">{n_items}</div></div>
      <div class="kpi hi"><div class="kpi-l">Currently Out</div>
        <div class="kpi-v">{active_n}</div></div>
      <div class="kpi bl"><div class="kpi-l">Total Borrows</div>
        <div class="kpi-v">{tot_borrow:,}</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Item Frequency & Avg Duration</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">左柱为借用次数，右柱为平均持有时长，黄色标注为当前在借物品</div>',
                unsafe_allow_html=True)
    if cat_d['items']:
        chart_cat_items(cat_d['items'])

    if cat_d.get('timeline'):
        st.markdown('<div class="sec">Monthly Borrow Trend — top 10 items</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="sec-note">展示该类别Top 10物品的逐月借用变化，用于对比不同物品的需求走势</div>',
                    unsafe_allow_html=True)
        chart_cat_timeline(cat_d['timeline'], cat_d.get('top10', []), height=300)

    ai_button(
        f"Category: {sel_cat}. Top items: {json.dumps(cat_d['items'][:8])}. "
        f"Active: {active_n}/{n_items}. "
        "Demand patterns, popular items, fleet adequacy. Plain text, 120 words max.", key="cat")


# ── SINGLE ITEM ──────────────────────────────────────
with tab_item:
    ic1, ic2 = st.columns([1, 2])
    with ic1:
        item_cat = st.selectbox("Category", ["(All)"] + analyzer.get_categories(),
                                key="item_cat", label_visibility="collapsed")
    with ic2:
        all_items = analyzer.get_items(
            category=None if item_cat == "(All)" else item_cat,
            source=_src)
        q_txt = st.text_input("Search item", placeholder="filter by name…",
                              key="item_q", label_visibility="collapsed")
        filtered = [i for i in all_items if q_txt.lower() in i.lower()] if q_txt else all_items

    sel_item = (st.selectbox("Item", filtered, key="item_sel", label_visibility="collapsed")
                if filtered else None)

    if sel_item:
        match_base = st.checkbox(
            "按型号汇总（忽略末尾编号）",
            value=True,
            key="item_match_base",
            help="推荐开启：把同型号不同编号（如 012/013/017）合并到同一条时间线里。",
        )
        det = json.loads(analyzer.item_detail(sel_item, start=_s, end=_e, match_base=match_base))
        s   = det['stats']

        if s:
            if s.get("match_mode") == "base":
                st.caption(f"型号级视图：`{s.get('base_name','')}` · 覆盖 {s.get('units',0)} 个编号/子型号")
            gap_str = f"{s['avg_gap_days']}d" if s.get('avg_gap_days') else "—"
            active  = s.get('active_now', False)
            st.markdown(f"""
            <div class="kpi-row">
              <div class="kpi sm"><div class="kpi-l">Category</div>
                <div class="kpi-v">{s.get('category','—')}</div></div>
              <div class="kpi"><div class="kpi-l">Total Borrows</div>
                <div class="kpi-v">{s['total']}</div></div>
              <div class="kpi bl"><div class="kpi-l">Avg Hold</div>
                <div class="kpi-v">{s['avg_h']}<span style="font-size:13px;color:#222">h</span></div></div>
              <div class="kpi"><div class="kpi-l">Max Hold</div>
                <div class="kpi-v">{s['max_h']}<span style="font-size:13px;color:#222">h</span></div></div>
              <div class="kpi sm"><div class="kpi-l">Avg Gap</div>
                <div class="kpi-v">{gap_str}</div></div>
              <div class="kpi {'hi' if active else 'gr'}">
                <div class="kpi-l">Status</div>
                <div class="kpi-v" style="font-size:17px;padding-top:8px">
                  {'● OUT' if active else '✓  IN'}</div></div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec">Borrow Timeline</div>', unsafe_allow_html=True)
        vc1, vc2 = st.columns([1, 4])
        with vc1:
            view_opt = st.radio(
                "View",
                ["Gantt", "Heatmap"],
                horizontal=True,
                label_visibility="collapsed"
            )
        if view_opt == "Gantt":
            st.markdown('<div class="sec-note">每条横条代表一次借用记录。灰色=历史已归还，绿色=近期数据，黄色=当前仍在借（使用中）</div>',
                        unsafe_allow_html=True)
            chart_gantt(det['gantt'])
        else:
            st.markdown('<div class="sec-note">颜色深浅表示借用频率，悬停查看详情</div>',
                        unsafe_allow_html=True)
            chart_heatmap(det['gantt'], height=220)

        if det.get('monthly'):
            st.markdown('<div class="sec">Monthly Hold Hours</div>', unsafe_allow_html=True)
            st.markdown('<div class="sec-note">每月累计借用时长的柱状统计，反映设备占用的繁忙程度</div>',
                        unsafe_allow_html=True)
            chart_monthly_bars(det['monthly'], height=210)

        ai_button(
            f"Item: {sel_item}. Stats: {json.dumps(s)}. "
            f"Last 5 borrows: {json.dumps(det['gantt'][-5:])}. "
            "Lifecycle, demand peaks, availability. Plain text, 120 words max.", key="item")
    else:
        st.markdown(
            "<p style='color:#1e1e1e;text-align:center;margin-top:60px;font-size:13px'>"
            "select category → search → pick item</p>",
            unsafe_allow_html=True)


# ── PATTERNS ─────────────────────────────────────────
with tab_pat:
    pc1, _ = st.columns([2, 5])
    with pc1:
        pat_cat = st.selectbox("Category", ["(All)"] + analyzer.get_categories(),
                               key="pat_cat", label_visibility="collapsed")

    tp = json.loads(analyzer.temporal_patterns(
        category=None if pat_cat == "(All)" else pat_cat,
        source=_src, start=_s, end=_e))

    st.markdown('<div class="sec">Borrow Initiation Heatmap</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">横轴为小时(0-23)，纵轴为星期(Mon-Sun)，颜色越亮表示该时段借用越密集。用于分析高峰借用时段，辅助设备补充与人员调度</div>',
                unsafe_allow_html=True)
    chart_temporal_heatmap(tp['heatmap'], height=280, scrollable=True)

    st.markdown('<div class="sec">Seasonal Distribution</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">左图为按星期分布，右图为按月份分布，展示借用需求的周期性规律，辅助资源规划</div>',
                unsafe_allow_html=True)
    chart_wd_month(tp['by_weekday'], tp['by_month'], height=220)

    ai_button(
        f"Temporal patterns. By weekday: {json.dumps(tp['by_weekday'])}. "
        f"By month: {json.dumps(tp['by_month'])}. "
        f"Peak times: {json.dumps(sorted(tp['heatmap'],key=lambda x:-x['count'])[:5])}. "
        "Peak hours, seasonal trends, operational tips. Plain text, 120 words max.", key="pat")