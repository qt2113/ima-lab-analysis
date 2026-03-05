"""
IMA Lab — Equipment Borrowing Intelligence
Streamlit shell + D3.js charts. No Plotly/Matplotlib.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="IMA Lab", page_icon="◈", layout="wide",
                   initial_sidebar_state="expanded")
st.cache_data.clear()

import analyzer

# ── path fix (analyzer.py sits next to main.py in project root) ──
analyzer._DB = Path(__file__).parent.parent / "item_analysis.db"

# ══════════════════════════════════════════════════════════════════
# GLOBAL STYLES
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=JetBrains+Mono:wght@300;400;600&display=swap');

html,[class*="css"]{font-family:'JetBrains Mono',monospace;}
h1,h2,h3,.stTabs [data-baseweb="tab"]{font-family:'Syne',sans-serif!important;}

/* hide streamlit chrome */
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden;}

/* tab styling */
.stTabs [data-baseweb="tab-list"]{gap:0;border-bottom:1px solid #1c1c1c;}
.stTabs [data-baseweb="tab"]{
    background:transparent;border:none;color:#444;
    font-size:11px;letter-spacing:.12em;text-transform:uppercase;
    padding:10px 20px;font-family:'JetBrains Mono',monospace!important;
}
.stTabs [aria-selected="true"]{color:#e2ff5d!important;border-bottom:2px solid #e2ff5d!important;}

/* KPI cards */
.kpi-row{display:flex;gap:12px;margin:16px 0;}
.kpi{flex:1;background:#111;border:1px solid #1e1e1e;border-radius:6px;padding:18px 20px;}
.kpi-label{font-size:9px;color:#444;letter-spacing:.15em;text-transform:uppercase;margin-bottom:6px;}
.kpi-val{font-family:'Syne',sans-serif;font-size:36px;font-weight:800;color:#f0f0f0;line-height:1;}
.kpi-sub{font-size:10px;color:#333;margin-top:5px;}
.kpi.accent .kpi-val{color:#e2ff5d;}

/* section headers */
.sec{font-size:9px;color:#333;letter-spacing:.2em;text-transform:uppercase;
     border-top:1px solid #1c1c1c;padding-top:14px;margin:24px 0 12px 0;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# D3 CHART BUILDERS
# Each returns raw HTML string injected via components.html()
# ══════════════════════════════════════════════════════════════════

D3 = "https://d3js.org/d3.v7.min.js"

def _html(body: str, h: int) -> None:
    components.html(f"""
    <!DOCTYPE html><html><head>
    <script src="{D3}"></script>
    <style>
      *{{margin:0;padding:0;box-sizing:border-box;}}
      body{{background:#0a0a0a;overflow:hidden;}}
      .tt{{position:fixed;pointer-events:none;background:#161616;border:1px solid #2a2a2a;
           border-radius:5px;padding:9px 13px;font-family:'JetBrains Mono',monospace;
           font-size:10px;line-height:1.9;color:#aaa;opacity:0;z-index:999;
           transition:opacity .1s;}}
    </style>
    </head><body>
    <div class="tt" id="tt"></div>
    {body}
    </body></html>
    """, height=h)


# ── Monthly line ─────────────────────────────────────
def chart_monthly(data_json: str, h=240):
    _html(f"""
    <div id="c"></div><script>
    const D = {data_json}.monthly;
    const M={{t:20,r:20,b:44,l:46}};
    const W=document.body.clientWidth, H={h};
    const w=W-M.l-M.r, hh=H-M.t-M.b;
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const parse=d3.timeParse('%Y-%m');
    D.forEach(d=>d.dt=parse(d.month));
    const x=d3.scaleTime().domain(d3.extent(D,d=>d.dt)).range([0,w]);
    const y=d3.scaleLinear().domain([0,d3.max(D,d=>d.count)*1.12]).range([hh,0]);
    // area fill
    g.append('path').datum(D)
     .attr('d',d3.area().x(d=>x(d.dt)).y0(hh).y1(d=>y(d.count)).curve(d3.curveMonotoneX))
     .attr('fill','#e2ff5d').attr('opacity',.06);
    // gridlines
    g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(''))
     .selectAll('line').attr('stroke','#161616');
    g.select('.domain').remove();
    // line
    g.append('path').datum(D)
     .attr('d',d3.line().x(d=>x(d.dt)).y(d=>y(d.count)).curve(d3.curveMonotoneX))
     .attr('fill','none').attr('stroke','#e2ff5d').attr('stroke-width',1.5);
    // dots
    const tt=d3.select('#tt');
    g.selectAll('circle').data(D).enter().append('circle')
     .attr('cx',d=>x(d.dt)).attr('cy',d=>y(d.count)).attr('r',3)
     .attr('fill','#e2ff5d').attr('opacity',.7)
     .on('mousemove',(ev,d)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
       .html(`<span style="color:#e2ff5d">${{d.month}}</span><br><b style="color:#fff">${{d.count}}</b> borrows`))
     .on('mouseleave',()=>tt.style('opacity',0));
    // axes
    g.append('g').attr('transform',`translate(0,${{hh}})`)
     .call(d3.axisBottom(x).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat("%b '%y")))
     .selectAll('text').attr('fill','#333').style('font-size','9px').attr('transform','rotate(-25)').attr('text-anchor','end');
    g.append('g').call(d3.axisLeft(y).ticks(4))
     .selectAll('text').attr('fill','#333').style('font-size','9px');
    g.selectAll('.domain,.tick line').attr('stroke','#1e1e1e');
    </script>""", h)


# ── Bubble / scatter ─────────────────────────────────
def chart_bubble(data_json: str, h=360):
    _html(f"""
    <div id="c"></div><script>
    const D={data_json}.bubble;
    const M={{t:16,r:20,b:48,l:56}};
    const W=document.body.clientWidth,H={h};
    const w=W-M.l-M.r,hh=H-M.t-M.b;
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const x=d3.scaleLinear().domain([0,d3.max(D,d=>d.count)*1.08]).range([0,w]);
    const y=d3.scaleLinear().domain([0,d3.max(D,d=>d.med_h)*1.1]).range([hh,0]);
    const r=d3.scaleSqrt().domain([0,d3.max(D,d=>d.items)]).range([4,28]);
    const col=d3.scaleOrdinal(d3.schemeTableau10).domain(D.map(d=>d.Category));
    g.append('g').call(d3.axisLeft(y).ticks(5).tickSize(-w).tickFormat(d=>d+'h'))
     .selectAll('line').attr('stroke','#161616');
    g.select('.domain').remove();
    const tt=d3.select('#tt');
    g.selectAll('circle').data(D).enter().append('circle')
     .attr('cx',d=>x(d.count)).attr('cy',d=>y(d.med_h))
     .attr('r',d=>r(d.items)).attr('fill',d=>col(d.Category)).attr('opacity',.65)
     .on('mousemove',(ev,d)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
       .html(`<b style="color:#fff">${{d.Category}}</b><br>
              <span style="color:#555">BORROWS</span> <span style="color:#e2ff5d">${{d.count}}</span><br>
              <span style="color:#555">MEDIAN DUR</span> <span style="color:#fff">${{d.med_h}}h</span><br>
              <span style="color:#555">ITEMS</span> <span style="color:#aaa">${{d.items}}</span>`))
     .on('mouseleave',()=>tt.style('opacity',0));
    // labels for large bubbles
    g.selectAll('text.lbl').data(D.filter(d=>d.items>5)).enter().append('text').attr('class','lbl')
     .attr('x',d=>x(d.count)).attr('y',d=>y(d.med_h)+4)
     .text(d=>d.Category.length>12?d.Category.slice(0,11)+'…':d.Category)
     .attr('text-anchor','middle').attr('fill','#fff').attr('opacity',.5)
     .style('font-size','8px').style('pointer-events','none');
    g.append('g').attr('transform',`translate(0,${{hh}})`)
     .call(d3.axisBottom(x).ticks(5))
     .selectAll('text').attr('fill','#333').style('font-size','9px');
    g.append('g').call(d3.axisLeft(y).ticks(5).tickFormat(d=>d+'h'))
     .selectAll('text').attr('fill','#333').style('font-size','9px');
    g.selectAll('.domain,.tick line').attr('stroke','#1e1e1e');
    // axis labels
    svg.append('text').attr('x',M.l+w/2).attr('y',H-4)
       .text('borrow count').attr('fill','#2a2a2a').attr('text-anchor','middle').style('font-size','9px');
    svg.append('text').attr('transform','rotate(-90)').attr('x',-(M.t+hh/2)).attr('y',12)
       .text('median duration (h)').attr('fill','#2a2a2a').attr('text-anchor','middle').style('font-size','9px');
    </script>""", h)


# ── Utilization bars ─────────────────────────────────
def chart_util_bars(data_json: str, h=520):
    _html(f"""
    <div id="c"></div><script>
    const D={data_json}.bars;
    if(!D||!D.length){{document.body.innerHTML='<p style="color:#333;padding:20px;font-family:monospace">No data</p>';return;}}
    const M={{t:12,r:80,b:20,l:230}};
    const W=document.body.clientWidth,H={h};
    const w=W-M.l-M.r,hh=H-M.t-M.b;
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const y=d3.scaleBand().domain(D.map(d=>d.item)).range([0,hh]).padding(.3);
    const x=d3.scaleLinear().domain([0,1]).range([0,w]);
    const col=d3.scaleOrdinal(d3.schemeTableau10).domain([...new Set(D.map(d=>d.category))]);
    // grid
    g.append('g').call(d3.axisBottom(x).ticks(5).tickSize(hh).tickFormat(d=>(d*100).toFixed(0)+'%'))
     .attr('transform','translate(0,0)').selectAll('line').attr('stroke','#161616');
    g.select('.domain').remove();
    const tt=d3.select('#tt');
    // bars
    g.selectAll('rect').data(D).enter().append('rect')
     .attr('y',d=>y(d.item)).attr('height',y.bandwidth())
     .attr('x',0).attr('width',0).attr('rx',2)
     .attr('fill',d=>d.active?'#e2ff5d':col(d.category)).attr('opacity',d=>d.active?.9:.7)
     .on('mousemove',(ev,d)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
       .html(`<b style="color:#fff">${{d.item}}</b><br>
              <span style="color:#555">UTIL</span> <span style="color:#e2ff5d">${{(d.util*100).toFixed(1)}}%</span>
              &nbsp;<span style="color:#555">BORROWS</span> <span style="color:#fff">${{d.count}}</span><br>
              <span style="color:#555">AVG</span> <span style="color:#aaa">${{d.avg_h}}h</span>
              ${{d.active?' <span style="color:#e2ff5d">● ACTIVE</span>':''}}` ))
     .on('mouseleave',()=>tt.style('opacity',0))
     .transition().duration(500).delay((_,i)=>i*18).attr('width',d=>x(d.util));
    // item labels
    g.selectAll('.lbl').data(D).enter().append('text').attr('class','lbl')
     .attr('y',d=>y(d.item)+y.bandwidth()/2+4).attr('x',-6).attr('text-anchor','end')
     .text(d=>d.item.length>32?d.item.slice(0,31)+'…':d.item)
     .attr('fill','#3a3a3a').style('font-size','10px');
    // % label
    g.selectAll('.pct').data(D).enter().append('text').attr('class','pct')
     .attr('y',d=>y(d.item)+y.bandwidth()/2+4).attr('x',d=>x(d.util)+5)
     .text(d=>(d.util*100).toFixed(0)+'%')
     .attr('fill',d=>d.active?'#e2ff5d':'#333').style('font-size','9px');
    // x axis bottom
    g.append('g').attr('transform',`translate(0,${{hh}})`)
     .call(d3.axisBottom(x).ticks(5).tickFormat(d=>(d*100).toFixed(0)+'%'))
     .selectAll('text').attr('fill','#2a2a2a').style('font-size','9px');
    </script>""", h)


# ── Quadrant scatter ──────────────────────────────────
def chart_quadrant(data_json: str, h=400):
    _html(f"""
    <div id="c"></div><script>
    const raw={data_json}.quadrant;
    const D=raw.filter(d=>d.count>0&&d.avg_h>0);
    const M={{t:20,r:20,b:48,l:58}};
    const W=document.body.clientWidth,H={h};
    const w=W-M.l-M.r,hh=H-M.t-M.b;
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const x=d3.scaleLinear().domain([0,d3.max(D,d=>d.count)*1.08]).range([0,w]);
    const y=d3.scaleLinear().domain([0,d3.max(D,d=>d.avg_h)*1.08]).range([hh,0]);
    const col=d3.scaleOrdinal(d3.schemeTableau10).domain([...new Set(D.map(d=>d.category))]);
    // quadrant lines (medians)
    const mx=d3.median(D,d=>d.count), my=d3.median(D,d=>d.avg_h);
    g.append('line').attr('x1',x(mx)).attr('x2',x(mx)).attr('y1',0).attr('y2',hh)
     .attr('stroke','#1e1e1e').attr('stroke-dasharray','4,4');
    g.append('line').attr('x1',0).attr('x2',w).attr('y1',y(my)).attr('y2',y(my))
     .attr('stroke','#1e1e1e').attr('stroke-dasharray','4,4');
    // quadrant labels
    [['HIGH DEMAND\\nLONG HOLD',w*.75,hh*.15,'#2a2a2a'],
     ['FREQUENT\\nSHORT USE',w*.75,hh*.85,'#2a2a2a'],
     ['RARE\\nLONG HOLD',w*.1,hh*.15,'#2a2a2a'],
     ['LOW DEMAND\\nQUICK USE',w*.1,hh*.85,'#2a2a2a']].forEach(([t,tx,ty,fc])=>{{
       t.split('\\n').forEach((line,i)=>
         g.append('text').attr('x',tx).attr('y',ty+i*11)
          .text(line).attr('fill',fc).style('font-size','8px').attr('text-anchor','middle')
          .style('letter-spacing','.1em'));
    }});
    const tt=d3.select('#tt');
    g.selectAll('circle').data(D).enter().append('circle')
     .attr('cx',d=>x(d.count)).attr('cy',d=>y(d.avg_h))
     .attr('r',d=>d.active?6:4)
     .attr('fill',d=>d.active?'#e2ff5d':col(d.category))
     .attr('opacity',d=>d.active?1:.5)
     .on('mousemove',(ev,d)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
       .html(`<b style="color:#fff">${{d.item}}</b><br>
              <span style="color:#555">CAT</span> <span style="color:#aaa">${{d.category}}</span><br>
              <span style="color:#555">BORROWS</span> <span style="color:#e2ff5d">${{d.count}}</span>  
              <span style="color:#555">AVG</span> <span style="color:#fff">${{d.avg_h}}h</span>`))
     .on('mouseleave',()=>tt.style('opacity',0));
    g.append('g').attr('transform',`translate(0,${{hh}})`)
     .call(d3.axisBottom(x).ticks(5)).selectAll('text').attr('fill','#333').style('font-size','9px');
    g.append('g').call(d3.axisLeft(y).ticks(5).tickFormat(d=>d+'h'))
     .selectAll('text').attr('fill','#333').style('font-size','9px');
    g.selectAll('.domain,.tick line').attr('stroke','#1e1e1e');
    svg.append('text').attr('x',M.l+w/2).attr('y',H-4)
       .text('borrow frequency').attr('fill','#222').attr('text-anchor','middle').style('font-size','9px');
    svg.append('text').attr('transform','rotate(-90)').attr('x',-(M.t+hh/2)).attr('y',13)
       .text('avg hold duration (h)').attr('fill','#222').attr('text-anchor','middle').style('font-size','9px');
    </script>""", h)


# ── Gantt ─────────────────────────────────────────────
def chart_gantt(data_json: str, h=380):
    _html(f"""
    <div id="c"></div><script>
    const raw={data_json};
    const D=raw.gantt; const stats=raw.stats;
    if(!D||!D.length){{document.body.innerHTML='<p style="color:#333;padding:20px;font-family:monospace">No records</p>';return;}}
    const parse=d3.timeParse('%Y-%m-%dT%H:%M:%S');
    D.forEach(d=>{{d.s=parse(d.start);d.e=parse(d.end);}});
    const M={{t:16,r:20,b:44,l:16}};
    const W=document.body.clientWidth,H={h};
    const w=W-M.l-M.r,hh=H-M.t-M.b;
    const barH=Math.max(5,Math.min(20,(hh-20)/D.length-2));
    const gap=Math.max(1,barH*.2);
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const allT=D.flatMap(d=>[d.s,d.e]).filter(Boolean);
    const x=d3.scaleTime().domain([d3.min(allT),d3.max(allT)]).range([0,w]);
    // grid
    g.append('g').call(d3.axisBottom(x).ticks(6).tickSize(hh).tickFormat(''))
     .attr('transform','translate(0,0)').selectAll('line').attr('stroke','#141414');
    g.select('.domain').remove();
    const tt=d3.select('#tt');
    D.forEach((d,i)=>{{
      const clr=d.active?'#e2ff5d':d.source==='realtime'?'#4ade80':'#60a5fa';
      const bw=Math.max(2,x(d.e)-x(d.s));
      g.append('rect')
       .attr('x',x(d.s)).attr('y',i*(barH+gap))
       .attr('width',bw).attr('height',barH).attr('rx',1.5)
       .attr('fill',clr).attr('opacity',.8)
       .on('mousemove',(ev)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
         .html(`<span style="color:#555">START</span> <span style="color:#fff">${{d.start.replace('T',' ')}}</span><br>
                <span style="color:#555">END &nbsp;</span> <span style="color:#aaa">${{d.end.replace('T',' ')}}</span><br>
                <span style="color:#555">DUR &nbsp;</span> <span style="color:#e2ff5d">${{d.hours!=null?d.hours+'h':'ongoing'}}</span>
                <span style="color:#555"> · ${{d.source}}</span>`))
       .on('mouseleave',()=>tt.style('opacity',0));
    }});
    g.append('g').attr('transform',`translate(0,${{hh}})`)
     .call(d3.axisBottom(x).ticks(7).tickFormat(d3.timeFormat('%b %Y')))
     .selectAll('text').attr('fill','#333').style('font-size','9px');
    g.selectAll('.domain,.tick line').attr('stroke','#1e1e1e');
    // legend
    [['historical','#60a5fa'],['realtime','#4ade80'],['active','#e2ff5d']].forEach(([l,c],i)=>{{
      const lg=svg.append('g').attr('transform',`translate(${{M.l+i*90}},${{H-6}})`);
      lg.append('rect').attr('width',8).attr('height',8).attr('rx',1).attr('fill',c).attr('opacity',.8);
      lg.append('text').attr('x',12).attr('y',8).text(l).attr('fill','#333').style('font-size','9px');
    }});
    </script>""", h)


# ── Monthly bars (item detail) ────────────────────────
def chart_monthly_bars(data_json: str, h=200):
    _html(f"""
    <div id="c"></div><script>
    const D={data_json}.monthly;
    if(!D||!D.length) return;
    const M={{t:12,r:16,b:48,l:44}};
    const W=document.body.clientWidth,H={h};
    const w=W-M.l-M.r,hh=H-M.t-M.b;
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const x=d3.scaleBand().domain(D.map(d=>d.month)).range([0,w]).padding(.25);
    const y=d3.scaleLinear().domain([0,d3.max(D,d=>d.total_h)*1.12]).range([hh,0]);
    g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(d=>d+'h'))
     .selectAll('line').attr('stroke','#161616');
    g.select('.domain').remove();
    const tt=d3.select('#tt');
    g.selectAll('rect').data(D).enter().append('rect')
     .attr('x',d=>x(d.month)).attr('y',d=>y(d.total_h))
     .attr('width',x.bandwidth()).attr('height',d=>hh-y(d.total_h))
     .attr('rx',2).attr('fill','#60a5fa').attr('opacity',.7)
     .on('mousemove',(ev,d)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
       .html(`<span style="color:#aaa">${{d.month}}</span><br>
              <span style="color:#60a5fa">${{d.total_h}}h</span> · <span style="color:#fff">${{d.count}} borrows</span>`))
     .on('mouseleave',()=>tt.style('opacity',0));
    g.append('g').attr('transform',`translate(0,${{hh}})`)
     .call(d3.axisBottom(x).tickValues(x.domain().filter((_,i)=>i%Math.ceil(D.length/8)===0)))
     .selectAll('text').attr('fill','#333').style('font-size','9px').attr('transform','rotate(-30)').attr('text-anchor','end');
    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d=>d+'h'))
     .selectAll('text').attr('fill','#333').style('font-size','9px');
    g.selectAll('.domain,.tick line').attr('stroke','#1e1e1e');
    </script>""", h)


# ── Temporal heatmap (weekday × hour) ────────────────
def chart_temporal(data_json: str, h=220):
    _html(f"""
    <div id="c"></div><script>
    const raw={data_json};
    const D=raw.heatmap;
    const DAYS=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    const cs=14, gap=2, unit=cs+gap;
    const M={{t:20,r:16,b:28,l:36}};
    const W=document.body.clientWidth;
    const gW=24*unit, gH=7*unit;
    const H=gH+M.t+M.b;
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
    const maxC=d3.max(D,d=>d.count)||1;
    const col=d3.scaleSequential().domain([0,maxC]).interpolator(d3.interpolate('#141414','#e2ff5d'));
    // empty grid
    for(let wd=0;wd<7;wd++) for(let h=0;h<24;h++)
      g.append('rect').attr('x',h*unit).attr('y',wd*unit)
       .attr('width',cs).attr('height',cs).attr('rx',2).attr('fill','#141414');
    const tt=d3.select('#tt');
    D.forEach(d=>{{
      g.append('rect')
       .attr('x',d.hour*unit).attr('y',d.weekday*unit)
       .attr('width',cs).attr('height',cs).attr('rx',2)
       .attr('fill',col(d.count))
       .on('mousemove',(ev)=>tt.style('opacity',1).style('left',ev.clientX+12+'px').style('top',ev.clientY-8+'px')
         .html(`<span style="color:#555">${{DAYS[d.weekday]}} ${{String(d.hour).padStart(2,'0')}}:00</span><br><b style="color:#e2ff5d">${{d.count}}</b> borrows`))
       .on('mouseleave',()=>tt.style('opacity',0));
    }});
    DAYS.forEach((l,i)=>g.append('text').attr('x',-4).attr('y',i*unit+cs-2)
      .text(l).attr('fill','#2a2a2a').style('font-size','9px').attr('text-anchor','end'));
    [0,6,12,18,23].forEach(h=>g.append('text').attr('x',h*unit+cs/2).attr('y',-6)
      .text(String(h).padStart(2,'0')+'h').attr('fill','#2a2a2a').style('font-size','9px').attr('text-anchor','middle'));
    </script>""", h)


# ── Weekday + month bars ──────────────────────────────
def chart_by_weekday_month(data_json: str, h=200):
    _html(f"""
    <div id="c"></div><script>
    const raw={data_json};
    const WD=raw.by_weekday, MO=raw.by_month;
    const M={{t:12,r:16,b:36,l:40}};
    const W=document.body.clientWidth,H={h};
    const hw=(W-M.l-M.r)/2-8, hh=H-M.t-M.b;

    function drawBars(sel,data,xKey,yKey,color,offX){{
      const g=sel.append('g').attr('transform',`translate(${{offX}},${{M.t}})`);
      const x=d3.scaleBand().domain(data.map(d=>d[xKey])).range([0,hw]).padding(.25);
      const y=d3.scaleLinear().domain([0,d3.max(data,d=>d[yKey])*1.12]).range([hh,0]);
      g.selectAll('rect').data(data).enter().append('rect')
       .attr('x',d=>x(d[xKey])).attr('y',d=>y(d[yKey]))
       .attr('width',x.bandwidth()).attr('height',d=>hh-y(d[yKey]))
       .attr('rx',2).attr('fill',color).attr('opacity',.75);
      g.append('g').attr('transform',`translate(0,${{hh}})`)
       .call(d3.axisBottom(x)).selectAll('text').attr('fill','#333').style('font-size','9px');
      g.append('g').call(d3.axisLeft(y).ticks(3))
       .selectAll('text').attr('fill','#333').style('font-size','9px');
      g.selectAll('.domain,.tick line').attr('stroke','#1e1e1e');
    }}
    const svg=d3.select('#c').append('svg').attr('width',W).attr('height',H);
    drawBars(svg,WD,'label','count','#60a5fa',M.l);
    drawBars(svg,MO,'label','count','#4ade80',M.l+hw+24);
    svg.append('text').attr('x',M.l+hw/2).attr('y',H).text('by weekday')
       .attr('fill','#222').attr('text-anchor','middle').style('font-size','9px');
    svg.append('text').attr('x',M.l+hw+24+hw/2).attr('y',H).text('by month')
       .attr('fill','#222').attr('text-anchor','middle').style('font-size','9px');
    </script>""", h)


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ◈ IMA Lab")
    st.markdown("---")

    src_opt = st.radio("Source", ["All", "Historical", "Realtime"],
                       horizontal=True, label_visibility="collapsed")
    _src = {"All": None, "Historical": "historical", "Realtime": "realtime"}[src_opt]

    bounds = analyzer.get_bounds(_src)
    c1, c2 = st.columns(2)
    with c1:
        _start = st.text_input("From", value=bounds['min'],
                                label_visibility="collapsed", placeholder="YYYY-MM-DD")
    with c2:
        _end = st.text_input("To", value=bounds['max'],
                              label_visibility="collapsed", placeholder="YYYY-MM-DD")

    st.markdown("---")
    if st.button("↺  Refresh realtime", use_container_width=True):
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

    st.markdown("---")
    from data.database import db as _db
    stats = _db.get_statistics()
    st.caption(f"historical  {stats['by_source'].get('historical',0):,}")
    st.caption(f"realtime    {stats['by_source'].get('realtime',0):,}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
st.markdown(
    "<h1 style='font-family:Syne,sans-serif;font-weight:800;font-size:2.4rem;"
    "letter-spacing:-.04em;margin-bottom:0'>IMA Lab</h1>"
    "<p style='font-family:JetBrains Mono,monospace;font-size:10px;color:#333;"
    "letter-spacing:.15em;margin-top:4px'>EQUIPMENT BORROWING INTELLIGENCE</p>",
    unsafe_allow_html=True
)

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Fleet Health", "Item Detail", "Patterns"])


# ══════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════
with tab1:
    ov = json.loads(analyzer.overview(source=_src, start=_start or None, end=_end or None))
    kpi = ov['kpi']

    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-label">Total Borrows</div>
        <div class="kpi-val">{kpi['total']:,}</div></div>
      <div class="kpi"><div class="kpi-label">Unique Items</div>
        <div class="kpi-val">{kpi['unique_items']:,}</div></div>
      <div class="kpi accent"><div class="kpi-label">Currently Out</div>
        <div class="kpi-val">{kpi['active_now']}</div></div>
      <div class="kpi"><div class="kpi-label">Avg Hold</div>
        <div class="kpi-val">{kpi['avg_hours']:.0f}<span style="font-size:18px;color:#333">h</span></div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Monthly Borrow Volume</div>', unsafe_allow_html=True)
    chart_monthly(json.dumps(ov), h=240)

    st.markdown('<div class="sec">Category Landscape — size = unique items · x = volume · y = median hold</div>',
                unsafe_allow_html=True)
    chart_bubble(json.dumps(ov), h=360)


# ══════════════════════════════════════════════════════════════════
# TAB 2 — FLEET HEALTH
# ══════════════════════════════════════════════════════════════════
with tab2:
    cats = ["(All categories)"] + analyzer.get_categories()
    c1, c2 = st.columns([3, 1])
    with c1:
        sel_cat = st.selectbox("Category", cats, key="fh_cat",
                               label_visibility="collapsed")
    with c2:
        top_n = st.slider("Top N", 10, 50, 25, key="fh_n",
                          label_visibility="collapsed")

    fh = json.loads(analyzer.fleet_health(
        category=None if sel_cat.startswith("(") else sel_cat,
        source=_src, start=_start or None, end=_end or None, top_n=top_n
    ))

    st.markdown(
        '<div class="sec">Utilization Ranking — cumulative borrow days ÷ active lifespan</div>',
        unsafe_allow_html=True)
    st.caption("Yellow = currently checked out")
    bar_h = max(320, top_n * 26 + 80)
    chart_util_bars(json.dumps(fh), h=bar_h)

    st.markdown(
        '<div class="sec">Demand × Hold Duration — four quadrants reveal usage archetypes</div>',
        unsafe_allow_html=True)
    chart_quadrant(json.dumps(fh), h=400)


# ══════════════════════════════════════════════════════════════════
# TAB 3 — ITEM DETAIL
# ══════════════════════════════════════════════════════════════════
with tab3:
    cats3 = ["(All)"] + analyzer.get_categories()
    c1, c2 = st.columns([1, 2])
    with c1:
        sel_cat3 = st.selectbox("Category", cats3, key="id_cat",
                                label_visibility="collapsed")
    with c2:
        items = analyzer.get_items(
            category=None if sel_cat3 == "(All)" else sel_cat3,
            source=_src)
        query = st.text_input("Filter item", placeholder="type to search…",
                              key="id_q", label_visibility="collapsed")
        if query:
            items = [i for i in items if query.lower() in i.lower()]

    sel_item = st.selectbox("Item", items, key="id_item",
                            label_visibility="collapsed") if items else None

    if sel_item:
        det = json.loads(analyzer.item_detail(
            sel_item, start=_start or None, end=_end or None))
        s = det['stats']

        if s:
            st.markdown(f"""
            <div class="kpi-row">
              <div class="kpi"><div class="kpi-label">Category</div>
                <div class="kpi-val" style="font-size:18px;padding-top:6px">{s.get('category','—')}</div></div>
              <div class="kpi"><div class="kpi-label">Total Borrows</div>
                <div class="kpi-val">{s['total']}</div></div>
              <div class="kpi"><div class="kpi-label">Avg Hold</div>
                <div class="kpi-val">{s['avg_h']}<span style="font-size:16px;color:#333">h</span></div></div>
              <div class="kpi"><div class="kpi-label">Max Hold</div>
                <div class="kpi-val">{s['max_h']}<span style="font-size:16px;color:#333">h</span></div></div>
              <div class="kpi {'accent' if s['active_now'] else ''}">
                <div class="kpi-label">Status</div>
                <div class="kpi-val" style="font-size:20px;padding-top:6px">
                  {"● OUT" if s['active_now'] else "✓ IN"}</div></div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec">Full Borrow Timeline</div>', unsafe_allow_html=True)
        n = len(det['gantt'])
        g_h = max(280, min(n * 22 + 100, 680))
        chart_gantt(json.dumps(det), h=g_h)

        if det['monthly']:
            st.markdown('<div class="sec">Monthly Hold Hours</div>', unsafe_allow_html=True)
            chart_monthly_bars(json.dumps(det), h=200)
    else:
        st.markdown(
            "<p style='color:#2a2a2a;font-family:JetBrains Mono,monospace;"
            "font-size:12px;margin-top:40px;text-align:center'>"
            "select a category → filter → pick an item</p>",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# TAB 4 — TEMPORAL PATTERNS
# ══════════════════════════════════════════════════════════════════
with tab4:
    cats4 = ["(All)"] + analyzer.get_categories()
    sel_cat4 = st.selectbox("Category", cats4, key="tp_cat",
                            label_visibility="collapsed")

    tp = json.loads(analyzer.temporal_patterns(
        category=None if sel_cat4 == "(All)" else sel_cat4,
        source=_src, start=_start or None, end=_end or None
    ))

    st.markdown('<div class="sec">Borrow Initiation Heatmap — weekday × hour of day</div>',
                unsafe_allow_html=True)
    chart_temporal(json.dumps(tp), h=200)

    st.markdown('<div class="sec">Volume by Weekday and Month</div>', unsafe_allow_html=True)
    chart_by_weekday_month(json.dumps(tp), h=200)
