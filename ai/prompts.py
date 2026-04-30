SYSTEM_PROMPT = """你是 IMA Lab 的智能分析助手，专注于分析实验室设备借用数据。

关于 IMA Lab：
- 这是一个实验室设备借用管理系统
- 数据包含设备名称、借用时间、归还时间、借用时长、设备类别等信息
- 设备类别包括：Cables, Sensor, Batteries, Cameras, Tripods, Microphones, Lenses, 
  Lighting, Projectors, VR Equipment, Computer, Computer Accessories, Robotics, 
  Soldering Equipment, Audio Equipment 等 30+ 类别
- 数据来源包括历史记录和实时 Google Sheets

你可以根据数据帮助用户：
1. 分析设备使用频率和热门程度
2. 识别借用模式和时间规律
3. 发现异常借用情况（如长期未归还）
4. 提供采购和库存建议
5. 解答关于设备借用的任何问题

如果数据不足以回答，请如实说明，并给出基于现有信息的合理推测。
回答时请简洁明了，使用中文。"""

QUICK_QUESTIONS = [
    "这学期最受欢迎的设备是什么？",
    "哪些设备经常被连续借走？",
    "给出采购建议",
    "有哪些异常借用情况？",
    "哪些设备长期无人使用？",
]


def _format_kpis(kpis: dict) -> str:
    lines = []
    for key, value in kpis.items():
        label = key.replace("_", " ").title()
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def _format_dataframe(df, max_rows: int = 10) -> str:
    if df is None or len(df) == 0:
        return "无数据"
    
    sample = df.head(max_rows)
    lines = []
    for _, row in sample.iterrows():
        row_str = " | ".join(str(v) for v in row.values)
        lines.append(row_str)
    
    if len(df) > max_rows:
        lines.append(f"... (共 {len(df)} 行)")
    
    return "\n".join(lines)


def get_overview_prompt(kpis: dict, monthly_data, category_data) -> str:
    kpi_str = _format_kpis(kpis)
    monthly_str = _format_dataframe(monthly_data, 6)
    category_str = _format_dataframe(category_data, 10)
    
    return f"""请分析以下 IMA Lab 全局数据，给出简洁的洞察（100字以内）：

关键指标：
{kpi_str}

月度借用趋势：
{monthly_str}

类别借用排名（前10）：
{category_str}
"""


def get_fleet_health_prompt(top_items_df, quadrant_data) -> str:
    top_str = _format_dataframe(top_items_df, 10)
    
    return f"""请分析以下设备健康度数据，给出简洁洞察（100字以内）：

高需求设备（按借用次数排序前10）：
{top_str}

四象限分布：
{quadrant_data}
"""


def get_category_prompt(category_stats, top_items) -> str:
    stats_str = _format_dataframe(category_stats, 10)
    items_str = _format_dataframe(top_items, 10)
    
    return f"""请分析以下类别数据，给出简洁洞察（100字以内）：

类别统计：
{stats_str}

类别内热门设备：
{items_str}
"""


def get_item_detail_prompt(item_name: str, item_stats, recent_borrows) -> str:
    stats_str = _format_kpis(item_stats)
    borrows_str = _format_dataframe(recent_borrows, 5)
    
    return f"""请分析以下单品「{item_name}」的数据，给出简洁洞察（100字以内）：

单品统计：
{stats_str}

最近借用记录：
{borrows_str}
"""


def get_patterns_prompt(temporal_stats) -> str:
    stats_str = _format_dataframe(temporal_stats, 20)
    
    return f"""请分析以下借用时间模式数据，给出简洁洞察（100字以内）：

时间分布统计：
{stats_str}
"""
