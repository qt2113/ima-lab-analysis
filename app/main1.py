# ============================================================================
# IMA Lab — Equipment Borrowing Intelligence Platform (设备借用智能平台)
# ============================================================================
#
# 功能概述:
#   - D3.js 可视化图表，通过 Streamlit components.html 嵌入
#   - 滚动式 iframe (scrolling=True) 支持长图表内部滚动
#   - SVG 使用 viewBox 实现响应式缩放，修复 width=0 的 iframe bug
#   - analyzer.py 提供数据过滤和异常值处理
#
# 依赖:
#   - streamlit: Web 框架
#   - streamlit.components.v1: 嵌入自定义 HTML/JS
#   - analyzer: 数据分析模块
#   - anthropic: AI 分析 (Claude API)
#
# ============================================================================

"""
IMA Lab — Equipment Borrowing Intelligence Platform
- D3.js charts via components.html with scrolling=True for inner scroll
- SVG uses viewBox for responsive scaling (fixes width=0 iframe bug)
- analyzer.py filters bundles, caps outliers
"""
import sys, json
from pathlib import Path

# 将项目根目录添加到 Python 路径，以便导入 analyzer 模块
# sys.path.insert(0, ...) 确保可以导入父目录中的模块
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import streamlit.components.v1 as components

# ============================================================================
# 页面初始化配置
# ============================================================================
# st.set_page_config: 配置 Streamlit 页面的基本属性
# - page_title: 浏览器标签页显示的标题
# - page_icon: 页面图标 (◈ 是菱形符号)
# - layout: 页面布局，"wide" 表示宽屏模式
# - initial_sidebar_state: 初始侧边栏状态，"collapsed" 表示默认折叠
st.set_page_config(page_title="IMA Lab", page_icon="◈", layout="wide",
                   initial_sidebar_state="collapsed")

# 清除所有 Streamlit 的数据缓存
# 每次页面加载时清除缓存，确保获取最新数据
st.cache_data.clear()

# ============================================================================
# 导入并配置 analyzer 模块
# ============================================================================
# analyzer 模块负责数据分析和查询
# 需要设置数据库路径指向项目根目录的 item_analysis.db
import analyzer
analyzer._DB = Path(__file__).parent.parent / "item_analysis.db"

# ═══════════════════════════════════════════════════════════════════════════
# CSS 样式定义
# ═══════════════════════════════════════════════════════════════════════════
#
# 自定义样式说明:
# - 引入 Google Fonts: Syne (标题字体) 和 JetBrains Mono (等宽字体)
# - 全局字体设置: JetBrains Mono
# - 隐藏 Streamlit 默认元素: MainMenu, footer, toolbar
# - 自定义标签页样式: 绿色高亮选中状态 (#e2ff5d)
# - KPI 卡片样式: 紧凑的指标展示卡片
# - 分区标题样式: 小字号、大间距、分隔线
# - AI 分析块样式: 绿色系提示框
#
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* 引入外部字体: Syne (粗体标题) 和 JetBrains Mono (代码/数据) */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=JetBrains+Mono:wght@300;400;600&display=swap');

/* 全局字体设置: 所有元素使用 JetBrains Mono */
html,[class*="css"]{font-family:'JetBrains Mono',monospace !important;}

/* 隐藏 Streamlit 默认 UI 元素 */
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden;}

/* 主容器样式: 减小顶部padding，最大宽度100% */
.block-container{padding-top:.8rem !important;max-width:100% !important;}

/* ─────────────────────────────────────────────────────────────────── */
/* 标签页 (Tabs) 样式 */
/* ─────────────────────────────────────────────────────────────────── */
/* 标签列表: 无边框，底部1px深灰分隔线 */
.stTabs [data-baseweb="tab-list"]{gap:0;border-bottom:1px solid #1c1c1c;}

/* 单个标签: 透明背景、无边框、深灰色文字、小字号、大字母间距 */
.stTabs [data-baseweb="tab"]{
  background:transparent;border:none;color:#363636;
  font-size:12px;letter-spacing:.14em;text-transform:uppercase;
  padding:10px 20px;font-family:'JetBrains Mono',monospace !important;}

/* 选中标签: 亮绿色高亮，底部2px绿色边框 */
.stTabs [aria-selected="true"]{
  color:#e2ff5d !important;border-bottom:2px solid #e2ff5d !important;
  background:transparent !important;}

/* ─────────────────────────────────────────────────────────────────── */
/* KPI (关键指标) 卡片样式 */
/* ─────────────────────────────────────────────────────────────────── */
/* KPI 行容器: flex 布局，10px 间距 */
.kpi-row{display:flex;gap:10px;margin:10px 0 18px 0;}

/* 单个 KPI 卡片: 深黑背景，细灰边框，圆角4px */
.kpi{flex:1;background:#0d0d0d;border:1px solid #1a1a1a;border-radius:4px;padding:14px 16px;min-width:0;}

/* KPI 标签: 极小字号、深灰色、超大字母间距、大写 */
.kpi-l{font-size:10px;color:#2e2e2e;letter-spacing:.18em;text-transform:uppercase;margin-bottom:5px;}

/* KPI 数值: Syne 字体、超大字号、粗体、浅灰色 */
.kpi-v{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;color:#ccc;line-height:1;}

/* KPI 高亮状态: 亮绿色 (如"当前外出"状态) */
.kpi.hi .kpi-v{color:#e2ff5d;}

/* KPI 蓝色状态: 蓝色 (如"平均借用时长") */
.kpi.bl .kpi-v{color:#60a5fa;}

/* KPI 绿色状态: 绿色 (如"在库"状态) */
.kpi.gr .kpi-v{color:#4ade80;}

/* ─────────────────────────────────────────────────────────────────── */
/* 分区标题样式 (Section Headers) */
/* ─────────────────────────────────────────────────────────────────── */
/* 分区标题: 极小字号、灰色、上边框分隔线 */
.sec{font-size:10px;color:#888;letter-spacing:.22em;text-transform:uppercase;
     border-top:1px solid #111;padding-top:10px;margin:18px 0 6px 0;}

/* 分区副标题/备注: 稍小字号、灰色、负上边距 */
.sec-note{font-size:11px;color:#888;margin:-4px 0 8px 0;}

/* ─────────────────────────────────────────────────────────────────── */
/* AI 分析结果块样式 */
/* ─────────────────────────────────────────────────────────────────── */
/* AI 块容器: 深绿色背景、边框、圆角 */
.ai-block{background:#0a150a;border:1px solid #1a301a;border-radius:4px;padding:14px 16px;margin-top:8px;}

/* AI 块标签: 极小字号、深绿色、超大字母间距 */
.ai-lbl{font-size:8px;color:#264026;letter-spacing:.2em;text-transform:uppercase;margin-bottom:8px;}

/* AI 块正文: 较小字号、绿色文字、行高1.75 */
.ai-text{font-size:11px;color:#6a9a6a;line-height:1.75;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# D3.js 图表引擎
# ═══════════════════════════════════════════════════════════════════════════
#
# 核心设计理念:
# 1. SVG viewBox 属性: 让 SVG 可以响应式缩放，修复某些浏览器中 iframe width=0 的 bug
# 2. scrolling=True: 允许 iframe 内部滚动，适合宽/高图表
# 3. overflow:auto: body 样式支持内部滚动
#
# 技术细节:
# - D3.js v7 从 CDN 加载
# - 内部画布宽度 VW=1100px (D3 坐标系宽度)
# - 工具提示 (tooltip) 使用固定定位的 div 实现
# - 所有图表通过 components.html 嵌入为 iframe
#
# ═══════════════════════════════════════════════════════════════════════════

# D3.js CDN 地址 (v7 版本)
D3 = "https://d3js.org/d3.v7.min.js"

# 内部 SVG 画布宽度 (D3 坐标系)
# 所有图表基于这个宽度计算坐标，然后通过 viewBox 缩放到实际显示尺寸
VW = 1100  # internal canvas width


def _chart(js: str, height: int, scrollable: bool = False):
    """
    渲染 D3 图表的核心函数
    
    参数:
        js (str): D3.js JavaScript 代码，包含图表绘制逻辑
        height (int): iframe 高度 (像素)
        scrollable (bool): 是否允许 iframe 内部滚动
            - True: 用于宽/高图表，iframe 出现滚动条
            - False: 固定高度，无滚动 (适合紧凑图表)
    
    实现细节:
        1. 构建完整的 HTML 文档结构
        2. 注入 D3.js 和自定义样式
        3. 定义工具提示函数 showTT/hideTT
        4. 通过 Streamlit components.html 渲染
    
    工具提示 (tooltip) 功能:
        - 固定定位，不干扰鼠标事件
        - 半透明深色背景，圆角边框
        - 支持 HTML 内容显示
        - 鼠标移动时跟随光标，自动边缘检测
    """
    # 根据 scrollable 参数决定是否显示垂直滚动条
    overflow_y = "auto" if scrollable else "hidden"
    
    # 构建完整的 HTML 模板
    components.html(f"""<!DOCTYPE html><html><head>
<!-- 加载 D3.js v7 -->
<script src="{D3}"></script>
<style>
  /* 基础重置: 清除所有元素默认的 margin 和 padding */
  *{{margin:0;padding:0;box-sizing:border-box;}}
  
  /* html 和 body 背景色设置为深黑 (#0a0a0a) */
  html{{background:#0a0a0a;}}
  body{{background:#0a0a0a;overflow-x:auto;overflow-y:{overflow_y};width:100%;}}
  
  /* SVG 样式: 块级显示，宽度100%自适应，高度自动 */
  svg{{display:block;width:100%;height:auto;}}
  
  /* 自定义滚动条样式 (Webkit 浏览器: Chrome, Safari, Edge) */
  ::-webkit-scrollbar{{height:10px;width:10px;}}
  ::-webkit-scrollbar-track{{background:#111;}}
  ::-webkit-scrollbar-thumb{{background:#444;border-radius:5px;}}
  ::-webkit-scrollbar-thumb:hover{{background:#555;}}
  
  /* 工具提示 (tooltip) 样式 */
  #tt{{
    position:fixed;              /* 固定定位，不随滚动移动 */
    pointer-events:none;          /* 允许鼠标事件穿透 */
    z-index:9999;                /* 置顶显示 */
    background:#111;             /* 深黑背景 */
    border:1px solid #333;       /* 灰色边框 */
    border-radius:4px;           /* 圆角 */
    padding:8px 12px;            /* 内边距 */
    font-family:'JetBrains Mono',monospace;
    font-size:12px;line-height:1.85;color:#ccc;
    opacity:0;                   /* 默认隐藏 */
    transition:opacity .1s;      /* 淡入淡出动画 */
    max-width:300px;white-space:pre-wrap;  /* 最大宽度和换行 */
  }}
</style></head><body>
<!-- 工具提示容器 -->
<div id="tt"></div>
<!-- 图表根容器 -->
<div id="root"></div>
<script>
/* ─────────────────────────────────────────────────────────────────── */
/* 全局常量和工具函数 */
/* ──────────────────────────────────── */
const VW={VW};                    /* SVG 内部画布宽度 */
const _tt=document.getElementById('tt');  /* 获取 tooltip 元素 */

/**
 * 显示工具提示
 * @param {string} html - 要显示的 HTML 内容
 * @param {Event} ev - 鼠标事件对象
 */
function showTT(html,ev){{
  _tt.innerHTML=html;             /* 设置提示内容 */
  _tt.style.opacity=1;            /* 显示 tooltip */
  
  /* 计算 tooltip 位置: 从鼠标位置向右偏移 14px */
  const rx=Math.min(ev.clientX+14,window.innerWidth-310);
  _tt.style.left=rx+'px';         /* 设置水平位置 */
  _tt.style.top=(ev.clientY-8)+'px';  /* 设置垂直位置，向上偏移 8px */
}}

/* 隐藏工具提示 */
function hideTT(){{_tt.style.opacity=0;}}

/* ─────────────────────────────────────────────────────────────────── */
/* 用户图表代码注入点 */
/* ──────────────────────────────────── */
{js}
</script></body></html>""",
        height=height, scrolling=scrollable)


# ───────────────────────────────────────────────────────────────────────
# 图表 1: 月度借用趋势折线图 (Monthly Line Chart)
# ───────────────────────────────────────────────────────────────────────
#
# 功能: 显示每月的设备借用数量趋势
# 图表类型: 面积图 + 折线图 + 数据点
# 特点:
#   - 绿色 (#e2ff5d) 配色方案
#   - 底部浅色面积填充
#   - 顶部折线 + 圆形数据点
#   - 鼠标悬停显示详细数值
#
# 参数:
#   monthly: [{"month": "2024-01", "count": 120}, ...] 每月数据列表
#   height: 图表高度 (默认 220px)
#
# ───────────────────────────────────────────────────────────────────────
def chart_monthly(monthly: list, height=220):
    _chart(f"""
/* ─────────────────────────────────────────────────────────────────── */
/* 月度借用趋势折线图 D3.js 代码 */
/* ──────────────────────────────────── */

/* 数据: JSON 格式的月度借用数据 */
const D={json.dumps(monthly)};

/* 边距设置: top=16, right=20, bottom=46, left=52 */
const M={{t:16,r:20,b:46,l:52}};

/* 计算绘图区域尺寸 */
const H={height},w=VW-M.l-M.r,h=H-M.t-M.b;

/* 创建 SVG 画布，设置 viewBox 实现响应式缩放 */
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{VW}} ${{H}}`);

/* 创建主 G 组，设置边距偏移 */
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);

/* 日期解析: 将 "YYYY-MM" 格式转换为 Date 对象 */
const parse=d3.timeParse('%Y-%m');

/* 为每条数据添加解析后的日期字段 */
D.forEach(d=>d.dt=parse(d.month));

/* ─────────────────────────────────────────────────────────────────── */
/* 比例尺 (Scales) */
/* ─────────────────────────────────────────────────────────────────── */
/* X 轴: 时间比例尺，根据数据日期范围映射到绘图区域宽度 */
const x=d3.scaleTime().domain(d3.extent(D,d=>d.dt)).range([0,w]);

/* Y 轴: 线性比例尺，从 0 到最大值的 1.15 倍 (留出顶部空间) */
const y=d3.scaleLinear().domain([0,d3.max(D,d=>d.count)*1.15]).range([h,0]).nice();

/* ─────────────────────────────────────────────────────────────────── */
/* 背景网格线 (右侧) */
/* ─────────────────────────────────────────────────────────────────── */
/* 左侧 Y 轴网格线: 水平虚线，用于参考 */
g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(''))
  .selectAll('line').attr('stroke','#161616').attr('stroke-dasharray','3,3');

/* 移除坐标轴主轴线 */
g.selectAll('.domain').remove();

/* ─────────────────────────────────────────────────────────────────── */
/* 面积填充 (Area) */
/* ─────────────────────────────────────────────────────────────────── */
/* 底部浅绿色面积: 从底部 (h) 到数据点 */
g.append('path').datum(D)
  .attr('d',d3.area().x(d=>x(d.dt)).y0(h).y1(d=>y(d.count)).curve(d3.curveMonotoneX))
  .attr('fill','#e2ff5d').attr('opacity',.07);

/* ─────────────────────────────────────────────────────────────────── */
/* 折线 (Line) */
/* ─────────────────────────────────────────────────────────────────── */
/* 顶部绿色折线: 连接所有数据点，使用平滑曲线 */
g.append('path').datum(D)
  .attr('d',d3.line().x(d=>x(d.dt)).y(d=>y(d.count)).curve(d3.curveMonotoneX))
  .attr('fill','none').attr('stroke','#e2ff5d').attr('stroke-width',2);

/* ─────────────────────────────────────────────────────────────────── */
/* 数据点 (Circles) */
/* ─────────────────────────────────────────────────────────────────── */
/* 为每个数据点添加圆形 */
g.selectAll('circle').data(D).enter().append('circle')
  .attr('cx',d=>x(d.dt)).attr('cy',d=>y(d.count)).attr('r',3.5)
  .attr('fill','#e2ff5d').attr('opacity',.8)
  /* 鼠标悬停显示工具提示 */
  .on('mousemove',(ev,d)=>showTT(`<span style="color:#e2ff5d">${{d.month}}</span>\\n<b style="color:#fff">${{d.count}}</b> borrows`,ev))
  .on('mouseleave',hideTT);

/* ─────────────────────────────────────────────────────────────────── */
/* X 轴 (底部月份) */
/* ─────────────────────────────────────────────────────────────────── */
/* 每 3 个月显示一个刻度，格式为 "Jan '24" */
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat("%b '%y")))
  .selectAll('text').attr('fill','#2a2a2a').style('font-size','13px')
  .attr('transform','rotate(-20)').attr('text-anchor','end');

/* ─────────────────────────────────────────────────────────────────── */
/* Y 轴 (左侧数量) */
/* ─────────────────────────────────────────────────────────────────── */
g.append('g').call(d3.axisLeft(y).ticks(4))
  .selectAll('text').attr('fill','#2a2a2a').style('font-size','13px');

/* 坐标轴线条颜色 */
g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
""", height, scrollable=True)


# ───────────────────────────────────────────────────────────────────────
# 图表 2: 类别树地图 (Category Treemap)
# ───────────────────────────────────────────────────────────────────────
#
# 功能: 以矩形面积展示各类别的借用数量，颜色深浅表示中位借用时长
# 图表类型: 树地图 (Treemap/D3.js Hierarchy)
# 特点:
#   - 矩形面积 = 该类别的总借用次数 (count)
#   - 颜色渐变 = 中位借用时长 (浅色=短，深色=长)
#   - 悬停显示详细信息 (借用次数、中位时长、物品种类数)
#
# 参数:
#   categories: [{"Category": "相机", "count": 500, "med_h": 24, "items": 20}, ...]
#   height: 图表高度 (默认 300px)
#
# D3 树地图原理:
#   1. d3.hierarchy() 将数据组织为层次结构
#   2. .sum(d=>d.count) 计算每个节点的值 (借用次数)
#   3. .sort() 按值降序排列
#   4. d3.treemap() 计算每个矩形的 x0, y0, x1, y1 坐标
#   5. 矩形大小按 count 比例分配
#
# 颜色比例尺:
#   - 使用 d3.scaleSequential() 顺序比例尺
#   - 从深绿 (#0d1a0d) 到亮绿 (#22c55e)
#   - 映射域: [0, maxMed] (最大中位借用时长)
#
# ───────────────────────────────────────────────────────────────────────
def chart_treemap(categories: list, height=300):
    _chart(f"""
/* ─────────────────────────────────────────────────────────────────── */
/* 类别树地图 D3.js 代码 */
/* ──────────────────────────────────── */

/* 原始类别数据: JSON 格式传入 */
const raw={json.dumps(categories)};

/* 图表高度 */
const H={height};

/* 计算颜色比例尺的最大值 (中位借用时长的最大值，用于颜色映射) */
const maxMed=d3.max(raw,d=>d.med_h)||1;

/* ─────────────────────────────────────────────────────────────────── */
/* 构建层次数据结构 (Hierarchy) */
/* ─────────────────────────────────────────────────────────────────── */
/* 创建 hierarchy，children 即原始数据数组 */
const root=d3.hierarchy({{children:raw}})
  /* sum: 计算每个叶子节点的值 = 借用次数 (count) */
  .sum(d=>d.count)
  /* sort: 按值降序排列，大的矩形排在前面 */
  .sort((a,b)=>b.value-a.value);

/* 创建树地图布局 */
d3.treemap()
  .size([VW,H])      /* 画布尺寸: 宽×高 */
  .padding(2)        /* 矩形间距 (像素) */
  .round(true)       /* 像素取整，避免渲染模糊 */(root);

/* ─────────────────────────────────────────────────────────────────── */
/* 颜色比例尺 */
/* ─────────────────────────────────────────────────────────────────── */
/* 顺序颜色比例尺: 从深绿 (#0d1a0d) 到亮绿 (#22c55e) */
/* 用于根据中位借用时长显示颜色深浅 */
const color=d3.scaleSequential()
  .domain([0,maxMed])  /* 域: 从 0 到最大中位时长 */
  .interpolator(d3.interpolate('#0d1a0d','#22c55e'));  /* 插值器 */

/* 创建 SVG 画布，设置 viewBox 实现响应式缩放 */
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{VW}} ${{H}}`);

/* ─────────────────────────────────────────────────────────────────── */
/* 绘制矩形单元格 (Cells) */
/* ─────────────────────────────────────────────────────────────────── */
/* 为每个叶子节点创建一个 G 组 (包含矩形和文字) */
const cell=svg.selectAll('g').data(root.leaves()).enter().append('g')
  /* 将 G 组移动到矩形位置 */
  .attr('transform',d=>`translate(${{d.x0}},${{d.y0}})`);

/* 绘制矩形: 宽= x1-x0, 高= y1-y0, 填充色= 中位时长对应的颜色 */
cell.append('rect')
  /* 宽高至少为 0，避免负值 */
  .attr('width',d=>Math.max(0,d.x1-d.x0))
  .attr('height',d=>Math.max(0,d.y1-d.y0))
  /* 填充色根据中位借用时长映射 */
  .attr('fill',d=>color(d.data.med_h))
  .attr('rx',2)  /* 圆角 2px */
  /* ── 鼠标悬停交互 ── */
  .on('mousemove',(ev,d)=>showTT(
    /* 显示: 类别名称、借用次数、中位时长、物品种类数 */
    `<b style="color:#fff">${{d.data.Category}}</b>\\n`+
    `<span style="color:#555">BORROWS &nbsp;</span><span style="color:#e2ff5d">${{d.data.count}}</span>\\n`+
    `<span style="color:#555">MED HOLD </span><span style="color:#fff">${{d.data.med_h}}h</span>\\n`+
    `<span style="color:#555">ITEMS &nbsp;&nbsp;&nbsp;</span><span style="color:#aaa">${{d.data.items}}</span>`,ev))
  .on('mouseleave',hideTT);

/* ─────────────────────────────────────────────────────────────────── */
/* 类别名称标签 (仅当单元格足够大时显示) */
/* ─────────────────────────────────────────────────────────────────── */
/* 条件: 宽度>55 且 高度>20 才显示名称，避免小格子文字拥挤 */
cell.filter(d=>(d.x1-d.x0)>55&&(d.y1-d.y0)>20).append('text')
  .attr('x',5).attr('y',14)  /* 文字位置: 左边 5px, 上边 14px */
  .text(d=>d.data.Category.length>16?d.data.Category.slice(0,15)+'…':d.data.Category)  /* 截断长名称 */
  .attr('fill','rgba(255,255,255,.5)').style('font-size','13px').style('pointer-events','none');

/* 借用次数和时长标签 (仅当单元格更大时显示) */
/* 条件: 宽度>70 且 高度>34 */
cell.filter(d=>(d.x1-d.x0)>70&&(d.y1-d.y0)>34).append('text')
  .attr('x',5).attr('y',28)  /* 在名称下方显示 */
  .text(d=>`${{d.data.count}} · ${{d.data.med_h}}h`)  /* "数量 · 时长" 格式 */
  .attr('fill','rgba(255,255,255,.25)').style('font-size','12px').style('pointer-events','none');

/* ─────────────────────────────────────────────────────────────────── */
/* 图例 (Legend) */
/* ─────────────────────────────────────────────────────────────────── */
/* 定义 SVG 渐变: 从深绿到亮绿 */
const defs=svg.append('defs');
const lg=defs.append('linearGradient').attr('id','lg').attr('x1','0%').attr('x2','100%');
lg.append('stop').attr('offset','0%').attr('stop-color','#0d1a0d');   /* 起始: 深绿 */
lg.append('stop').attr('offset','100%').attr('stop-color','#22c55e'); /* 结束: 亮绿 */

/* 图例容器: 右上角位置 */
const legend=svg.append('g').attr('transform',`translate(${{VW-185}},8)`);

/* 图例色条: 使用渐变填充 */
legend.append('rect')
  .attr('width',135).attr('height',7).attr('rx',2)
  .attr('fill','url(#lg)').attr('opacity',.6);

/* 图例标签: "short hold" 和 "long hold" */
legend.append('text').attr('y',18).text('short hold')
  .attr('fill','#888').style('font-size','13px');
legend.append('text').attr('x',135).attr('y',18).attr('text-anchor','end').text('long hold')
  .attr('fill','#888').style('font-size','13px');
""", height, scrollable=True)


# ───────────────────────────────────────────────────────────────────────
# 图表 3: 设备利用率条形图 (Utilization Bar Chart)
# ───────────────────────────────────────────────────────────────────────
#
# 功能: 展示设备的利用率排名，支持多种排序方式
# 图表类型: 水平条形图 (Horizontal Bar Chart)
# 特点:
#   - 水平条形展示每个设备的利用率 (0-100%)
#   - 颜色: 黄色=当前外出中, 其他=按类别着色
#   - 动画: 条形从左向右展开
#   - 支持按利用率、借阅次数、需求分数排序
#
# 参数:
#   bars: [{"item": "设备名", "util": 0.85, "count": 50, "avg_h": 24, "category": "相机", "active": true}, ...]
#   sort_by: 排序方式
#       - "util": 按利用率排序 (默认)
#       - "count": 按借阅次数排序
#       - "score": 按需求分数排序 (count × util)
#
# 高度计算:
#   - SVG 高度 = 数据条数 × (条形高度 + 间距) + 边距
#   - iframe 高度 = min(SVG高度, 520px)，超过则出现滚动条
#
# ───────────────────────────────────────────────────────────────────────
def chart_util_bars(bars: list, sort_by: str = "util"):
    """
    绘制设备利用率条形图
    
    参数:
        bars: 设备利用率数据列表
        sort_by: 排序方式 ("util", "count", "score")
    """
    # ── 数据排序处理 ──
    # 根据 sort_by 参数选择不同的排序方式
    if sort_by == "count":
        # 按借阅次数降序排列
        bars = sorted(bars, key=lambda x: -x['count'])
    elif sort_by == "score":
        # 按需求分数 (借用次数 × 利用率) 降序排列
        bars = sorted(bars, key=lambda x: -(x['count'] * x['util']))
    else:
        # 按利用率 (默认) 降序排列
        bars = sorted(bars, key=lambda x: -x['util'])

    # ── 高度计算 ──
    bar_h = 26    # 每条条形的固定高度 (像素)
    n = len(bars) # 设备数量
    SVG_H = n * bar_h + 80  # SVG 总高度 = 数量×条形高 + 边距
    # iframe 高度: 最多显示 520px，超过则滚动
    iframe_h = min(SVG_H, 520)

    _chart(f"""
/* ─────────────────────────────────────────────────────────────────── */
/* 设备利用率条形图 D3.js 代码 */
/* ──────────────────────────────────── */

/* 数据: 排序后的设备列表 */
const D={json.dumps(bars)};

/* 条形参数 */
const barH=26,  /* 单条条形高度 */
      gap=4;    /* 条形间距 */

/* 边距设置: top=10, right=90, bottom=32, left=260 (左侧留空间显示设备名) */
const M={{t:10,r:90,b:32,l:260}};

/* 计算 SVG 和绘图区域尺寸 */
const svgH=D.length*(barH+gap)+M.t+M.b;  /* SVG 高度 */
const w=VW-M.l-M.r;  /* 绘图区域宽度 */
const h=D.length*(barH+gap);  /* 绘图区域高度 */

/* 创建 SVG 画布: 设置 viewBox 和 preserveAspectRatio 实现响应式 */
const svg=d3.select('#root').append('svg')
  .attr('viewBox',`0 0 ${{VW}} ${{svgH}}`)
  .attr('preserveAspectRatio','xMidYMid meet');

/* 主 G 组: 设置边距偏移 */
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);

/* ─────────────────────────────────────────────────────────────────── */
/* 比例尺 (Scales) */
/* ─────────────────────────────────────────────────────────────────── */
/* Y 轴: 带宽比例尺，将设备名映射到垂直位置 */
const y=d3.scaleBand()
  .domain(D.map(d=>d.item))  /* 设备名作为域 */
  .range([0,h])              /* 映射到 0 到 h 的范围 */
  .padding(.25);             /* 条形之间的间距 */

/* X 轴: 线性比例尺，利用率 0-1 映射到 0-w */
const x=d3.scaleLinear()
  .domain([0,1])
  .range([0,w]);

/* 颜色比例尺: 类别配色方案 (Tableau10) */
const cats=[...new Set(D.map(d=>d.category))];  /* 获取所有唯一类别 */
const col=d3.scaleOrdinal(d3.schemeTableau10).domain(cats);

/* ─────────────────────────────────────────────────────────────────── */
/* 背景网格线 (4条: 25%, 50%, 75%, 100%) */
/* ─────────────────────────────────────────────────────────────────── */
[.25,.5,.75,1].forEach(v=>{{
  g.append('line')
    .attr('x1',x(v)).attr('x2',x(v))  /* 垂直线位置 */
    .attr('y1',0).attr('y2',h)        /* 从顶到底 */
    .attr('stroke','#1a1a1a')         /* 深灰色 */
    .attr('stroke-dasharray','3,3');   /* 虚线样式 */
}});

/* ─────────────────────────────────────────────────────────────────── */
/* 绘制条形 (Bars) */
/* ─────────────────────────────────────────────────────────────────── */
g.selectAll('rect.bar').data(D).enter().append('rect')
  .attr('class','bar')
  /* 位置和尺寸 */
  .attr('y',d=>y(d.item))                    /* Y 位置: 设备名对应的高度 */
  .attr('height',y.bandwidth())              /* 高度: 带宽 */
  .attr('x',0)                               /* X 起始位置 */
  .attr('rx',2)                              /* 圆角 */
  /* 颜色: 外出中(黄色) 或按类别着色 */
  .attr('fill',d=>d.active?'#e2ff5d':col(d.category))
  .attr('opacity',d=>d.active?.9:.65)        /* 外出中不透明度更高 */
  .attr('width',0)                           /* 初始宽度为 0，用于动画 */
  /* ── 鼠标悬停交互 ── */
  .on('mousemove',(ev,d)=>showTT(
    `<b style="color:#fff">${{d.item}}</b>\\n`+
    `<span style="color:#555">UTIL &nbsp;&nbsp;</span><span style="color:#e2ff5d">${{(d.util*100).toFixed(1)}}%</span>\\n`+
    `<span style="color:#555">BORROWS</span> <span style="color:#fff">${{d.count}}</span>\\n`+
    `<span style="color:#555">AVG HOLD</span> <span style="color:#aaa">${{d.avg_h}}h</span>`+
    (d.active?'\\n<span style="color:#e2ff5d">● OUT NOW</span>':''),ev))
  .on('mouseleave',hideTT)
  /* ── 动画效果: 从左向右展开 ── */
  .transition()
  .duration(400)              /* 动画时长 400ms */
  .delay((_,i)=>i*8)          /* 每条延迟 8ms，形成错落效果 */
  .attr('width',d=>x(d.util));  /* 展开到实际宽度 */

/* ─────────────────────────────────────────────────────────────────── */
/* 设备名称标签 (左侧) */
/* ─────────────────────────────────────────────────────────────────── */
g.selectAll('text.lbl').data(D).enter().append('text')
  .attr('class','lbl')
  /* 位置: 条形左侧，垂直居中 */
  .attr('y',d=>y(d.item)+y.bandwidth()/2+4)
  .attr('x',-6)                              /* 条形左侧 6px */
  .attr('text-anchor','end')                 /* 右对齐 */
  .text(d=>d.item.length>33?d.item.slice(0,32)+'…':d.item)  /* 截断长名称 */
  .attr('fill','#2e2e2e').style('font-size','12px');

/* ─────────────────────────────────────────────────────────────────── */
/* 利用率百分比标签 (条形右侧) */
/* ─────────────────────────────────────────────────────────────────── */
g.selectAll('text.pct').data(D).enter().append('text')
  .attr('class','pct')
  .attr('y',d=>y(d.item)+y.bandwidth()/2+4)
  .attr('x',d=>x(d.util)+4)                   /* 条形结束位置 + 4px */
  .text(d=>(d.util*100).toFixed(0)+'%')      /* 显示百分比整数 */
  .attr('fill',d=>d.active?'#e2ff5d':'#282828').style('font-size','13px');

/* ─────────────────────────────────────────────────────────────────── */
/* 借用次数标签 (最右侧) */
/* ─────────────────────────────────────────────────────────────────── */
g.selectAll('text.cnt').data(D).enter().append('text')
  .attr('class','cnt')
  .attr('y',d=>y(d.item)+y.bandwidth()/2+4)
  .attr('x',w+60)                            /* 绘图区域右侧 */
  .attr('text-anchor','end')                 /* 右对齐 */
  .text(d=>`×${{d.count}}`)                  /* "×数量" 格式 */
  .attr('fill','#888').style('font-size','13px');

/* ─────────────────────────────────────────────────────────────────── */
/* X 轴 (底部利用率刻度) */
/* ─────────────────────────────────────────────────────────────────── */
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(4).tickFormat(d=>(d*100)+'%'))
  .selectAll('text').attr('fill','#888').style('font-size','12px');

/* 坐标轴线条颜色 */
g.selectAll('.domain,.tick line').attr('stroke','#1a1a1a');
""", iframe_h, scrollable=True)


# ───────────────────────────────────────────────────────────────────────
# 图表 4: 四象限散点图 (Quadrant Scatter Plot)
# ───────────────────────────────────────────────────────────────────────
#
# 功能: 将设备按借用频率和平均借用时长分布在四象限中，分析使用模式
# 图表类型: 散点图 (Scatter Plot) + 分位数分割线
# 特点:
#   - X 轴: 借用频率 (count)
#   - Y 轴: 平均借用时长 (avg_h)
#   - 中位数分割线将图表分为四个象限
#   - 异常值处理: 使用 97 分位数 cap 轴范围，避免极端值压扁图表
#   - 外出中设备高亮显示 (大圆点、黄色)
#
# 四象限含义:
#   - 高需求/长借用: 热门但借阅时间长的设备
#   - 频繁/短期使用: 高周转设备
#   - 稀有/长借用: 低频但借阅时间长的设备
#   - 低活动: 冷门设备
#
# 参数:
#   quadrant: [{"item": "设备名", "count": 50, "avg_h": 24, "category": "相机", "active": true}, ...]
#   p95_h: 平均借用时长的 95 分位数 (用于显示)
#   p95_count: 借用次数的 95 分位数 (用于显示)
#   height: 图表高度 (默认 380px)
#
# ───────────────────────────────────────────────────────────────────────

def _quantile(values: list, q: float) -> float:
    """
    计算给定列表的 q 分位数 (不使用 pandas)
    
    参数:
        values: 数值列表
        q: 分位数 (0-1 之间，如 0.97 表示 97 分位数)
    
    返回:
        float: 指定分位数对应的值
    
    算法:
        1. 对列表排序
        2. 计算索引位置: idx = q × (n-1)
        3. 使用线性插值计算分位数值
    """
    s = sorted(values)  # 排序
    n = len(s)
    if n == 0:
        return 0.0
    # 计算分位数的索引位置
    idx = q * (n - 1)
    # 获取相邻两个位置的索引
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    # 线性插值
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def chart_quadrant(quadrant: list, p95_h: float, p95_count: float, height=380):
    """
    绘制四象限散点图
    
    参数:
        quadrant: 设备四象限数据
        p95_h: 借用时长的 95 分位数
        p95_count: 借用次数的 95 分位数
        height: 图表高度
    """
    # ── 异常值处理 ──
    # 计算 97 分位数作为显示上限 (比 95 稍高，减少截断)
    # 这样可以压缩极端异常值到图表边缘，同时保留大部分数据在合理范围内
    cap_h = _quantile([q['avg_h'] for q in quadrant if q['avg_h'] > 0], 0.97)
    cap_c = _quantile([q['count'] for q in quadrant if q['count'] > 0], 0.97)
    
    _chart(f"""
/* ─────────────────────────────────────────────────────────────────── */
/* 四象限散点图 D3.js 代码 */
/* ──────────────────────────────────── */

/* 原始数据 */
const raw={json.dumps(quadrant)};

/* 过滤掉借用次数或时长为 0 的无效数据 */
const D=raw.filter(d=>d.count>0&&d.avg_h>0);

/* 轴显示上限 (97 分位数，用于压缩异常值) */
const CAP_H={cap_h:.1f}, CAP_C={cap_c:.1f};

/* 边距设置 */
const M={{t:28,r:20,b:54,l:64}};
const H={height},w=VW-M.l-M.r,h=H-M.t-M.b;

/* 创建 SVG 和主 G 组 */
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{VW}} ${{H}}`);
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);

/* ─────────────────────────────────────────────────────────────────── */
/* 比例尺 (Scales) - 使用 cap 值限制轴范围 */
/* ─────────────────────────────────────────────────────────────────── */
/* X 轴: 借用次数 (0 到 CAP_C*1.05，留 5% 边距) */
const x=d3.scaleLinear().domain([0,CAP_C*1.05]).range([0,w]).nice();

/* Y 轴: 平均借用时长 (0 到 CAP_H*1.05) */
const y=d3.scaleLinear().domain([0,CAP_H*1.05]).range([h,0]).nice();

/* 颜色比例尺: 类别配色 */
const cats=[...new Set(D.map(d=>d.category))];
const col=d3.scaleOrdinal(d3.schemeTableau10).domain(cats);

/* ─────────────────────────────────────────────────────────────────── */
/* 计算中位数分割线位置 */
/* ─────────────────────────────────────────────────────────────────── */
/* 计算借用次数的中位数 (使用 cap 值) */
const mx=d3.median(D,d=>Math.min(d.count,CAP_C));

/* 计算借用时长的中位数 (使用 cap 值) */
const my=d3.median(D,d=>Math.min(d.avg_h,CAP_C));

/* 绘制垂直分割线 (借用次数中位数) */
g.append('line').attr('x1',x(mx)).attr('x2',x(mx)).attr('y1',0).attr('y2',h)
  .attr('stroke','#888').attr('stroke-dasharray','4,3');

/* 绘制水平分割线 (借用时长中位数) */
g.append('line').attr('x1',0).attr('x2',w).attr('y1',y(my)).attr('y2',y(my))
  .attr('stroke','#888').attr('stroke-dasharray','4,3');

/* ─────────────────────────────────────────────────────────────────── */
/* 象限标签 */
/* ─────────────────────────────────────────────────────────────────── */
/* 四个象限的标签文本和位置 */
[['HIGH DEMAND / LONG HOLD',w*.82,h*.09],
 ['FREQUENT / QUICK USE',w*.82,h*.91],
 ['RARE / LONG HOLD',w*.10,h*.09],
 ['LOW ACTIVITY',w*.10,h*.91]].forEach(([t,tx,ty])=>{{
  /* 标签可能包含 "/" ，需要分行显示 */
  t.split(' / ').forEach((line,i)=>
    g.append('text').attr('x',tx).attr('y',ty+i*13).text(line)
     .attr('fill','#1c1c1c').style('font-size','13px').style('letter-spacing','.08em')
     .attr('text-anchor','middle'));
}});

/* ─────────────────────────────────────────────────────────────────── */
/* 绘制散点 (Circles) */
/* ─────────────────────────────────────────────────────────────────── */
g.selectAll('circle').data(D).enter().append('circle')
  /* 位置: 使用 min() 将异常值压缩到显示范围内 */
  .attr('cx',d=>x(Math.min(d.count,CAP_C)))
  .attr('cy',d=>y(Math.min(d.avg_h,CAP_H)))
  /* 半径: 外出中设备显示更大 (7px)，其他 (3.5px) */
  .attr('r',d=>d.active?7:3.5)
  /* 颜色: 外出中黄色，其他按类别 */
  .attr('fill',d=>d.active?'#e2ff5d':col(d.category))
  /* 不透明度: 外出中 1，其他 0.42 */
  .attr('opacity',d=>d.active?1:.42)
  /* ── 鼠标悬停交互 ── */
  .on('mousemove',(ev,d)=>showTT(
    `<b style="color:#fff">${{d.item}}</b>\\n`+
    `<span style="color:#555">${{d.category}}</span>\\n`+
    `<span style="color:#555">BORROWS </span><span style="color:#e2ff5d">${{d.count}}</span>  `+
    `<span style="color:#555">AVG </span><span style="color:#fff">${{d.avg_h}}h</span>`,ev))
  .on('mouseleave',hideTT);

/* ─────────────────────────────────────────────────────────────────── */
/* 坐标轴 */
/* ─────────────────────────────────────────────────────────────────── */
/* X 轴 (底部) */
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(5))
  .selectAll('text').attr('fill','#888').style('font-size','13px');

/* Y 轴 (左侧) */
g.append('g').call(d3.axisLeft(y).ticks(5).tickFormat(d=>d+'h'))
  .selectAll('text').attr('fill','#888').style('font-size','13px');

/* 坐标轴线条颜色 */
g.selectAll('.domain,.tick line').attr('stroke','#181818');

/* ─────────────────────────────────────────────────────────────────── */
/* 轴标签 */
/* ─────────────────────────────────────────────────────────────────── */
/* X 轴标题: "borrow frequency" */
svg.append('text').attr('x',M.l+w/2).attr('y',H-4)
  .text('borrow frequency').attr('fill','#888').attr('text-anchor','middle')
  .style('font-size','12px').style('letter-spacing','.1em');

/* Y 轴标题: "avg hold duration (h)" (旋转 -90 度) */
svg.append('text').attr('transform','rotate(-90)').attr('x',-(M.t+h/2)).attr('y',15)
  .text('avg hold duration (h)').attr('fill','#888').attr('text-anchor','middle')
  .style('font-size','12px').style('letter-spacing','.1em');
""", height, scrollable=True)


# ─── Category items dual bar (scrollable) ────────────
def chart_cat_items(items: list):
    n = len(items[:40])
    bar_h = 28
    SVG_H = n * bar_h + 60
    iframe_h = min(SVG_H, 480)

    _chart(f"""
const D={json.dumps(items[:40])};
const barH=28,gap=4;
const M={{t:28,r:20,b:24,l:20}};
const w=VW-M.l-M.r, mid=w*0.48;
const LEFT_END=mid-130, RIGHT_START=mid+130;
const h=D.length*(barH+gap);
const svgH=h+M.t+M.b;

const svg=d3.select('#root').append('svg')
  .attr('viewBox',`0 0 ${{VW}} ${{svgH}}`)
  .attr('preserveAspectRatio','xMidYMid meet');
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);

const band=d3.scaleBand().domain(D.map(d=>d.item)).range([0,h]).padding(.25);
const xL=d3.scaleLinear().domain([0,d3.max(D,d=>d.count)*1.1]).range([0,LEFT_END]);
const xR=d3.scaleLinear().domain([0,d3.max(D,d=>d.avg_h)*1.1]).range([0,w-RIGHT_START]);

svg.append('text').attr('x',M.l+LEFT_END/2).attr('y',18)
  .text('BORROW COUNT').attr('fill','#888').attr('text-anchor','middle')
  .style('font-size','13px').style('letter-spacing','.14em');
svg.append('text').attr('x',M.l+RIGHT_START+(w-RIGHT_START)/2).attr('y',18)
  .text('AVG HOLD DURATION').attr('fill','#888').attr('text-anchor','middle')
  .style('font-size','13px').style('letter-spacing','.14em');

g.append('line').attr('x1',mid).attr('x2',mid).attr('y1',0).attr('y2',h)
  .attr('stroke','#141414');

// Left bars (right-aligned)
g.selectAll('rect.L').data(D).enter().append('rect').attr('class','L')
  .attr('y',d=>band(d.item)).attr('height',band.bandwidth()).attr('rx',2)
  .attr('fill','#3b82f6').attr('opacity',.65)
  .attr('x',d=>LEFT_END-0).attr('width',0)
  .transition().duration(400).delay((_,i)=>i*10)
  .attr('x',d=>LEFT_END-xL(d.count)).attr('width',d=>xL(d.count));

g.selectAll('text.Lv').data(D).enter().append('text').attr('class','Lv')
  .attr('y',d=>band(d.item)+band.bandwidth()/2+4)
  .attr('x',d=>LEFT_END-xL(d.count)-4).attr('text-anchor','end')
  .text(d=>d.count).attr('fill','#2a2a2a').style('font-size','13px');

// Right bars
g.selectAll('rect.R').data(D).enter().append('rect').attr('class','R')
  .attr('y',d=>band(d.item)).attr('height',band.bandwidth())
  .attr('x',RIGHT_START).attr('rx',2)
  .attr('fill',d=>d.active?'#e2ff5d':'#22c55e')
  .attr('opacity',d=>d.active?.9:.6)
  .attr('width',0)
  .transition().duration(400).delay((_,i)=>i*10)
  .attr('width',d=>xR(d.avg_h));

g.selectAll('text.Rv').data(D).enter().append('text').attr('class','Rv')
  .attr('y',d=>band(d.item)+band.bandwidth()/2+4)
  .attr('x',d=>RIGHT_START+xR(d.avg_h)+4)
  .text(d=>d.avg_h+'h').attr('fill','#888').style('font-size','13px');

// Center labels
g.selectAll('text.C').data(D).enter().append('text').attr('class','C')
  .attr('y',d=>band(d.item)+band.bandwidth()/2+4)
  .attr('x',mid).attr('text-anchor','middle')
  .text(d=>{{const s=d.item.replace(/\\s+\\d+$/,'');return s.length>24?s.slice(0,23)+'…':s;}})
  .attr('fill',d=>d.active?'#e2ff5d':'#2a2a2a').style('font-size','12px');

// Active dot
g.selectAll('circle.act').data(D.filter(d=>d.active)).enter()
  .append('circle').attr('class','act')
  .attr('cx',mid+120).attr('cy',d=>band(d.item)+band.bandwidth()/2)
  .attr('r',3).attr('fill','#e2ff5d');

// Hover
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
def chart_cat_timeline(timeline: list, top10: list, height=280):
    _chart(f"""
const raw={json.dumps(timeline)};
const items={json.dumps(top10[:10])};
const parse=d3.timeParse('%Y-%m');
const byItem={{}};
items.forEach(it=>byItem[it]=[]);
raw.forEach(d=>{{if(byItem[d['item name(with num)']])byItem[d['item name(with num)']].push({{dt:parse(d.month),count:d.count}});}});
const M={{t:16,r:170,b:48,l:48}};
const H={height},w=VW-M.l-M.r,h=H-M.t-M.b;
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{VW}} ${{H}}`);
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const allDates=raw.map(d=>parse(d.month)).filter(Boolean);
const x=d3.scaleTime().domain(d3.extent(allDates)).range([0,w]);
const y=d3.scaleLinear().domain([0,d3.max(raw,d=>d.count)*1.15]).range([h,0]).nice();
const col=d3.scaleOrdinal(d3.schemeTableau10).domain(items);
g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(''))
  .selectAll('line').attr('stroke','#141414').attr('stroke-dasharray','3,3');
g.selectAll('.domain').remove();
items.forEach(item=>{{
  const pts=(byItem[item]||[]).filter(d=>d.dt);
  if(!pts.length)return;
  g.append('path').datum(pts)
    .attr('d',d3.line().x(d=>x(d.dt)).y(d=>y(d.count)).curve(d3.curveMonotoneX))
    .attr('fill','none').attr('stroke',col(item)).attr('stroke-width',1.8).attr('opacity',.72);
  g.selectAll(null).data(pts).enter().append('circle')
    .attr('cx',d=>x(d.dt)).attr('cy',d=>y(d.count)).attr('r',3)
    .attr('fill',col(item)).attr('opacity',.85)
    .on('mousemove',(ev,d)=>showTT(
      `<span style="color:${{col(item)}}">${{item}}</span>\\n`+
      `<span style="color:#555">${{d3.timeFormat('%b %Y')(d.dt)}}</span>  `+
      `<span style="color:#fff">${{d.count}} borrows</span>`,ev))
    .on('mouseleave',hideTT);
}});
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(d3.timeMonth.every(3)).tickFormat(d3.timeFormat("%b '%y")))
  .selectAll('text').attr('fill','#888').style('font-size','12px')
  .attr('transform','rotate(-20)').attr('text-anchor','end');
g.append('g').call(d3.axisLeft(y).ticks(4))
  .selectAll('text').attr('fill','#888').style('font-size','12px');
g.selectAll('.domain,.tick line').attr('stroke','#181818');
items.forEach((item,i)=>{{
  const lg=svg.append('g').attr('transform',`translate(${{VW-162}},${{M.t+i*17}})`);
  lg.append('line').attr('x1',0).attr('x2',12).attr('y1',6).attr('y2',6)
    .attr('stroke',col(item)).attr('stroke-width',2).attr('opacity',.8);
  lg.append('text').attr('x',16).attr('y',10)
    .text(item.length>18?item.slice(0,17)+'…':item)
    .attr('fill','#888').style('font-size','13px');
}});
""", height, scrollable=True)


# ─── Single item Gantt (scrollable) ───────────────────
def chart_gantt(gantt: list):
    n = len(gantt)
    bar_h, gap = 20, 3
    SVG_H = n * (bar_h + gap) + 100
    iframe_h = min(SVG_H, 500)

    _chart(f"""
const D={json.dumps(gantt)};
if(!D.length){{
  d3.select('#root').append('p').text('No borrow records found.')
    .style('color','#2a2a2a').style('padding','30px').style('font-family','monospace');
  return;
}}
const parse=d3.timeParse('%Y-%m-%dT%H:%M:%S');
D.forEach(d=>{{d.s=parse(d.start);d.e=parse(d.end);}});
const barH={bar_h},gap={gap};
const M={{t:16,r:16,b:46,l:16}};
const w=VW-M.l-M.r;
const h=D.length*(barH+gap);
const svgH=h+M.t+M.b+20;

const svg=d3.select('#root').append('svg')
  .attr('viewBox',`0 0 ${{VW}} ${{svgH}}`)
  .attr('preserveAspectRatio','xMidYMid meet');
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);

const allT=D.flatMap(d=>[d.s,d.e]).filter(Boolean);
const x=d3.scaleTime().domain([d3.min(allT),d3.max(allT)]).range([0,w]);

// Year bands
const years=[...new Set(D.map(d=>d.s?d.s.getFullYear():null).filter(Boolean))];
years.forEach((yr,i)=>{{
  g.append('rect')
    .attr('x',Math.max(0,x(new Date(yr,0,1))))
    .attr('y',0)
    .attr('width',Math.max(0,x(new Date(yr,11,31))-x(new Date(yr,0,1))))
    .attr('height',h).attr('fill',i%2?'#0c0c0c':'#0a0a0a');
  g.append('text')
    .attr('x',x(new Date(yr,6,1))).attr('y',h+30)
    .text(yr).attr('fill','#888').style('font-size','12px').attr('text-anchor','middle');
}});

// Grid
g.append('g').call(d3.axisBottom(x).ticks(10).tickSize(h).tickFormat(''))
  .selectAll('line').attr('stroke','#131313');
g.select('.domain').remove();

// Bars
D.forEach((d,i)=>{{
  const clr=d.active?'#e2ff5d':d.source==='realtime'?'#4ade80':'#3b82f6';
  const bw=Math.max(2,x(d.e)-x(d.s));
  g.append('rect')
    .attr('x',x(d.s)).attr('y',i*(barH+gap))
    .attr('width',bw).attr('height',barH)
    .attr('rx',1.5).attr('fill',clr).attr('opacity',.82)
    .on('mousemove',ev=>showTT(
      `<span style="color:#555">START </span><span style="color:#fff">${{d.start.replace('T',' ')}}</span>\\n`+
      `<span style="color:#555">END &nbsp;&nbsp;</span><span style="color:#aaa">${{d.end.replace('T',' ')}}</span>\\n`+
      `<span style="color:#e2ff5d">${{d.hours!=null?d.hours+'h':'ongoing'}}</span>`+
      `<span style="color:#333">  ${{d.source}}</span>`,ev))
    .on('mouseleave',hideTT);
}});

// Month axis
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).ticks(10).tickFormat(d3.timeFormat('%b %Y')))
  .selectAll('text').attr('fill','#888').style('font-size','12px');
g.selectAll('.tick line').attr('stroke','#181818');

// Legend
[['historical','#3b82f6'],['realtime','#4ade80'],['active now','#e2ff5d']].forEach(([l,c],i)=>{{
  const lg=svg.append('g').attr('transform',`translate(${{i*110+M.l}},${{svgH-6}})`);
  lg.append('rect').attr('width',8).attr('height',8).attr('rx',1).attr('fill',c).attr('opacity',.8);
  lg.append('text').attr('x',12).attr('y',8).text(l).attr('fill','#888').style('font-size','13px');
}});
""", iframe_h, scrollable=True)


# ─── Monthly bars ─────────────────────────────────────
def chart_monthly_bars(monthly: list, height=190):
    _chart(f"""
const D={json.dumps(monthly)};
if(!D.length)return;
const M={{t:10,r:20,b:50,l:52}};
const H={height},w=VW-M.l-M.r,h=H-M.t-M.b;
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{VW}} ${{H}}`);
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const x=d3.scaleBand().domain(D.map(d=>d.month)).range([0,w]).padding(.22);
const y=d3.scaleLinear().domain([0,d3.max(D,d=>d.total_h)*1.12]).range([h,0]).nice();
g.append('g').call(d3.axisLeft(y).ticks(4).tickSize(-w).tickFormat(d=>d+'h'))
  .selectAll('line').attr('stroke','#131313').attr('stroke-dasharray','3,3');
g.selectAll('.domain').remove();
g.selectAll('rect').data(D).enter().append('rect')
  .attr('x',d=>x(d.month)).attr('y',d=>y(d.total_h))
  .attr('width',x.bandwidth()).attr('height',d=>Math.max(0,h-y(d.total_h)))
  .attr('rx',2).attr('fill','#3b82f6').attr('opacity',.65)
  .on('mousemove',(ev,d)=>showTT(
    `<span style="color:#aaa">${{d.month}}</span>\\n`+
    `<span style="color:#3b82f6">${{d.total_h}}h total</span>  <span style="color:#fff">${{d.count}} borrows</span>`,ev))
  .on('mouseleave',hideTT);
const skip=Math.ceil(D.length/10);
g.append('g').attr('transform',`translate(0,${{h}})`)
  .call(d3.axisBottom(x).tickValues(x.domain().filter((_,i)=>i%skip===0)))
  .selectAll('text').attr('fill','#888').style('font-size','12px')
  .attr('transform','rotate(-30)').attr('text-anchor','end');
g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d=>d+'h'))
  .selectAll('text').attr('fill','#888').style('font-size','12px');
g.selectAll('.domain,.tick line').attr('stroke','#181818');
""", height, scrollable=True)


# ─── Temporal heatmap (weekday × hour) ────────────────
def chart_temporal_heatmap(heatmap: list, height=200):
    _chart(f"""
const D={json.dumps(heatmap)};
const DAYS=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
const cs=28,gap=2,unit=cs+gap;
const M={{t:20,r:12,b:12,l:36}};
const W=24*unit+M.l+M.r;
const H=7*unit+M.t+M.b;
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{W}} ${{H}}`);
const g=svg.append('g').attr('transform',`translate(${{M.l}},${{M.t}})`);
const maxC=d3.max(D,d=>d.count)||1;
const col=d3.scaleSequential().domain([0,maxC]).interpolator(d3.interpolate('#111','#e2ff5d'));
for(let wd=0;wd<7;wd++)for(let hr=0;hr<24;hr++)
  g.append('rect').attr('x',hr*unit).attr('y',wd*unit)
   .attr('width',cs).attr('height',cs).attr('rx',1.5).attr('fill','#111');
D.forEach(d=>{{
  g.append('rect').attr('x',d.hour*unit).attr('y',d.weekday*unit)
   .attr('width',cs).attr('height',cs).attr('rx',1.5).attr('fill',col(d.count))
   .on('mousemove',ev=>showTT(
     `<span style="color:#555">${{DAYS[d.weekday]}} ${{String(d.hour).padStart(2,'0')}}:00</span>\\n`+
     `<b style="color:#e2ff5d">${{d.count}}</b> borrows`,ev))
   .on('mouseleave',hideTT);
}});
DAYS.forEach((l,i)=>g.append('text').attr('x',-4).attr('y',i*unit+cs-2)
  .text(l).attr('fill','#888').style('font-size','13px').attr('text-anchor','end'));
[0,4,8,12,16,20,23].forEach(hr=>g.append('text').attr('x',hr*unit+cs/2).attr('y',-4)
  .text(String(hr).padStart(2,'0')+'h').attr('fill','#888').style('font-size','12px')
  .attr('text-anchor','middle'));
""", height, scrollable=True)


# ─── Weekday + month bars ─────────────────────────────
def chart_wd_month(by_weekday: list, by_month: list, height=200):
    _chart(f"""
const WD={json.dumps(by_weekday)},MO={json.dumps(by_month)};
const M={{t:18,r:10,b:40,l:44}};
const H={height},hw=(VW-M.l-M.r)/2-16,h=H-M.t-M.b;
function drawBars(data,xKey,yKey,color,offX){{
  const g=svg.append('g').attr('transform',`translate(${{offX}},${{M.t}})`);
  const x=d3.scaleBand().domain(data.map(d=>d[xKey])).range([0,hw]).padding(.25);
  const y=d3.scaleLinear().domain([0,d3.max(data,d=>d[yKey])*1.12]).range([h,0]).nice();
  g.append('g').call(d3.axisLeft(y).ticks(3).tickSize(-hw).tickFormat(''))
    .selectAll('line').attr('stroke','#131313').attr('stroke-dasharray','3,3');
  g.selectAll('.domain').remove();
  g.selectAll('rect').data(data).enter().append('rect')
    .attr('x',d=>x(d[xKey])).attr('y',d=>y(d[yKey]))
    .attr('width',x.bandwidth()).attr('height',d=>Math.max(0,h-y(d[yKey])))
    .attr('rx',2).attr('fill',color).attr('opacity',.7)
    .on('mousemove',(ev,d)=>showTT(`<span style="color:#aaa">${{d[xKey]}}</span>  <b style="color:#fff">${{d[yKey]}}</b>`,ev))
    .on('mouseleave',hideTT);
  g.append('g').attr('transform',`translate(0,${{h}})`)
    .call(d3.axisBottom(x)).selectAll('text').attr('fill','#888').style('font-size','12px');
  g.append('g').call(d3.axisLeft(y).ticks(3))
    .selectAll('text').attr('fill','#888').style('font-size','12px');
  g.selectAll('.domain,.tick line').attr('stroke','#181818');
}}
const svg=d3.select('#root').append('svg').attr('viewBox',`0 0 ${{VW}} ${{H}}`);
drawBars(WD,'label','count','#60a5fa',M.l);
drawBars(MO,'label','count','#4ade80',M.l+hw+32);
svg.append('text').attr('x',M.l+hw/2).attr('y',H).text('BY WEEKDAY')
  .attr('fill','#888').attr('text-anchor','middle').style('font-size','13px').style('letter-spacing','.12em');
svg.append('text').attr('x',M.l+hw+32+hw/2).attr('y',H).text('BY MONTH')
  .attr('fill','#888').attr('text-anchor','middle').style('font-size','13px').style('letter-spacing','.12em');
""", height, scrollable=True)


# ══════════════════════════════════════════════════════
# AI ANALYSIS BUTTON
# ══════════════════════════════════════════════════════
def ai_button(prompt: str, key: str):
    col, _ = st.columns([1, 5])
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
_ha, _hb = st.columns([2, 6])
with _ha:
    st.markdown(
        "<h1 style='font-family:Syne,sans-serif;font-weight:800;font-size:1.7rem;"
        "letter-spacing:-.04em;margin:0;padding:0'>IMA Lab ◈</h1>"
        "<p style='font-size:8px;color:#888;letter-spacing:.2em;margin:2px 0 0 0'>"
        "EQUIPMENT BORROWING INTELLIGENCE</p>",
        unsafe_allow_html=True)

bounds = analyzer.get_bounds(_src)
all_bounds = analyzer.get_bounds(None)
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
        if st.button("↻", key="apply", help="Apply"):
            st.cache_data.clear()
    with _dc4:
        st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        if st.button("Reset → All", key="reset_all", help="Reset source + date range"):
            st.session_state["g_start"] = all_bounds.get("min", "")
            st.session_state["g_end"] = all_bounds.get("max", "")
            st.session_state["src_opt"] = "All"
            st.cache_data.clear()

src_label = "All" if _src is None else ("Historical" if _src == "historical" else "Realtime")
st.caption(
    f"Filter — Source: {src_label} · Range: {bounds.get('min','')} → {bounds.get('max','')} "
    f"(All: {all_bounds.get('min','')} → {all_bounds.get('max','')})"
)

_s = _start or None
_e = _end or None

st.markdown("<hr style='border:none;border-top:1px solid #111;margin:6px 0 0 0'>",
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════
tab_ov, tab_fleet, tab_cat, tab_item, tab_pat = st.tabs([
    "Overview", "Fleet Health", "Category", "Single Item", "Patterns"
])


# ── TAB 1: OVERVIEW ──────────────────────────────────
with tab_ov:
    ov = json.loads(analyzer.overview(source=_src, start=_s, end=_e))
    k = ov['kpi']
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><div class="kpi-l">Total Borrows</div>
        <div class="kpi-v">{k['total']:,}</div></div>
      <div class="kpi"><div class="kpi-l">Unique Items</div>
        <div class="kpi-v">{k['unique_items']:,}</div></div>
      <div class="kpi hi"><div class="kpi-l">Currently Out</div>
        <div class="kpi-v">{k['active_now']}</div></div>
      <div class="kpi bl"><div class="kpi-l">Avg Hold</div>
        <div class="kpi-v">{k['avg_hours']:.0f}<span style="font-size:14px;color:#888">h</span></div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec">Monthly Borrow Volume</div>', unsafe_allow_html=True)
    chart_monthly(ov['monthly'], height=220)

    st.markdown('<div class="sec">Category Map</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">Box area = total borrows · color depth = median hold duration</div>',
                unsafe_allow_html=True)
    chart_treemap(ov['categories'], height=300)

    ai_button(
        f"Analyze equipment borrowing overview. KPIs: {json.dumps(k)}. "
        f"Top categories: {json.dumps(sorted(ov['categories'],key=lambda x:-x['count'])[:5])}. "
        f"Monthly trend last 6m: {json.dumps(ov['monthly'][-6:])}. "
        "3-4 insights, plain text, no bullets, 120 words max.",
        key="ov")


# ── TAB 2: FLEET HEALTH ──────────────────────────────
with tab_fleet:
    fc1, fc2, fc3, _ = st.columns([2, 1, 1, 2])
    with fc1:
        fh_cat = st.selectbox("Category", ["(All)"] + analyzer.get_categories(),
                              key="fh_cat", label_visibility="collapsed")
    with fc2:
        fh_n = st.slider("Top N", 10, 100, 40, key="fh_n", label_visibility="collapsed")
    with fc3:
        sort_by = st.selectbox("Sort by", ["Utilization", "Frequency", "Demand Score"],
                               key="fh_sort", label_visibility="collapsed")

    sort_map = {"Utilization": "util", "Frequency": "count", "Demand Score": "score"}

    fh = json.loads(analyzer.fleet_health(
        category=None if fh_cat.startswith("(") else fh_cat,
        source=_src, start=_s, end=_e, top_n=fh_n))

    st.markdown('<div class="sec">Item Utilization</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">Named items only (bundles excluded) · min 2 borrows · yellow = currently out</div>',
                unsafe_allow_html=True)
    if fh['bars']:
        chart_util_bars(fh['bars'], sort_by=sort_map[sort_by])
    else:
        st.caption("No data.")

    st.markdown('<div class="sec">Demand × Hold Duration</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">Axes capped at 97th percentile · outliers compressed to edge</div>',
                unsafe_allow_html=True)
    if fh['quadrant']:
        chart_quadrant(fh['quadrant'], fh['p95_h'], fh['p95_count'], height=380)

    ai_button(
        f"Analyze fleet health. "
        f"Top 8 by demand score: {json.dumps(sorted(fh['bars'],key=lambda x:-(x['count']*x['util']))[:8])}. "
        f"Total named items: {len(fh['quadrant'])}. "
        "Which need procurement, which are underused? Plain text, 120 words max.",
        key="fleet")


# ── TAB 3: CATEGORY ──────────────────────────────────
with tab_cat:
    cats = analyzer.get_categories()
    cc1, _ = st.columns([2, 5])
    with cc1:
        sel_cat = st.selectbox("Category", cats, key="cat_sel", label_visibility="collapsed")

    cat_d = json.loads(analyzer.category_analysis(sel_cat, source=_src, start=_s, end=_e))
    n_items   = len(cat_d['items'])
    active_n  = sum(1 for x in cat_d['items'] if x.get('active'))
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
    st.markdown('<div class="sec-note">Left = borrow count · Right = avg hold hours · yellow name = currently out</div>',
                unsafe_allow_html=True)
    if cat_d['items']:
        chart_cat_items(cat_d['items'])

    if cat_d.get('timeline'):
        st.markdown('<div class="sec">Monthly Borrow Trend — top 10 items</div>', unsafe_allow_html=True)
        chart_cat_timeline(cat_d['timeline'], cat_d.get('top10', []), height=280)

    ai_button(
        f"Category: {sel_cat}. Top items: {json.dumps(cat_d['items'][:8])}. "
        f"Active now: {active_n}/{n_items}. "
        "Demand patterns, popular items, fleet adequacy. Plain text, 120 words max.",
        key="cat")


# ── TAB 4: SINGLE ITEM ───────────────────────────────
with tab_item:
    ic1, ic2 = st.columns([1, 2])
    with ic1:
        item_cat = st.selectbox("Category", ["(All)"] + analyzer.get_categories(),
                                key="item_cat", label_visibility="collapsed")
    with ic2:
        items = analyzer.get_items(
            category=None if item_cat == "(All)" else item_cat, source=_src)
        q = st.text_input("Search item", placeholder="filter by name…",
                          key="item_q", label_visibility="collapsed")
        if q:
            items = [i for i in items if q.lower() in i.lower()]

    sel_item = (st.selectbox("Item", items, key="item_sel", label_visibility="collapsed")
                if items else None)

    if sel_item:
        match_base = st.checkbox(
            "按型号汇总（忽略末尾编号）",
            value=True,
            key="item_match_base",
            help="推荐开启：把同型号不同编号（如 012/013/017）合并到同一条时间线里。",
        )
        det = json.loads(analyzer.item_detail(sel_item, start=_s, end=_e, match_base=match_base))
        s = det['stats']

        if s:
            if s.get("match_mode") == "base":
                st.caption(f"型号级视图：`{s.get('base_name','')}` · 覆盖 {s.get('units',0)} 个编号/子型号")
            gap_str = f"{s['avg_gap_days']}d" if s.get('avg_gap_days') else "—"
            st.markdown(f"""
            <div class="kpi-row">
              <div class="kpi"><div class="kpi-l">Category</div>
                <div class="kpi-v" style="font-size:14px;padding-top:9px">{s.get('category','—')}</div></div>
              <div class="kpi"><div class="kpi-l">Total Borrows</div>
                <div class="kpi-v">{s['total']}</div></div>
              <div class="kpi bl"><div class="kpi-l">Avg Hold</div>
                <div class="kpi-v">{s['avg_h']}<span style="font-size:12px;color:#888">h</span></div></div>
              <div class="kpi"><div class="kpi-l">Max Hold</div>
                <div class="kpi-v">{s['max_h']}<span style="font-size:12px;color:#888">h</span></div></div>
              <div class="kpi"><div class="kpi-l">Avg Gap</div>
                <div class="kpi-v" style="font-size:18px;padding-top:6px">{gap_str}</div></div>
              <div class="kpi {'hi' if s['active_now'] else 'gr'}">
                <div class="kpi-l">Status</div>
                <div class="kpi-v" style="font-size:16px;padding-top:7px">
                  {'● OUT' if s['active_now'] else '✓ IN'}</div></div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="sec">Complete Borrow Timeline</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-note">Each bar = one checkout · scroll to see all records</div>',
                    unsafe_allow_html=True)
        chart_gantt(det['gantt'])

        if det.get('monthly'):
            st.markdown('<div class="sec">Monthly Hold Hours</div>', unsafe_allow_html=True)
            chart_monthly_bars(det['monthly'], height=190)

        ai_button(
            f"Item: {sel_item}. Stats: {json.dumps(s)}. "
            f"Last 5 borrows: {json.dumps(det['gantt'][-5:])}. "
            "Lifecycle, peak demand, availability concerns. Plain text, 120 words max.",
            key="item")
    else:
        st.markdown(
            "<p style='color:#888;text-align:center;margin-top:50px;font-size:12px'>"
            "select category → search → pick item</p>",
            unsafe_allow_html=True)


# ── TAB 5: PATTERNS ──────────────────────────────────
with tab_pat:
    pc1, _ = st.columns([2, 5])
    with pc1:
        pat_cat = st.selectbox("Category", ["(All)"] + analyzer.get_categories(),
                               key="pat_cat", label_visibility="collapsed")

    tp = json.loads(analyzer.temporal_patterns(
        category=None if pat_cat == "(All)" else pat_cat,
        source=_src, start=_s, end=_e))

    st.markdown('<div class="sec">Borrow Initiation Heatmap</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-note">Weekday × hour — brighter = more borrows started at that time</div>',
                unsafe_allow_html=True)
    chart_temporal_heatmap(tp['heatmap'], height=240)

    st.markdown('<div class="sec">Seasonal Distribution</div>', unsafe_allow_html=True)
    chart_wd_month(tp['by_weekday'], tp['by_month'], height=200)

    ai_button(
        f"Temporal patterns. By weekday: {json.dumps(tp['by_weekday'])}. "
        f"By month: {json.dumps(tp['by_month'])}. "
        f"Peak times: {json.dumps(sorted(tp['heatmap'],key=lambda x:-x['count'])[:5])}. "
        "Peak hours, seasonal trends, operational recommendations. Plain text, 120 words max.",
        key="pat")