"""
项目配置文件 - 统一管理所有配置项
"""
import os
from pathlib import Path

# ==================== 路径配置 ====================
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = PROJECT_ROOT / "item_analysis.db"

# ==================== Google Sheets 配置 ====================
#GOOGLE_SHEET_ID = "1gMibpWSaxtfPyTq4FJ8wqdpE0ZMrWgEhmP-ReApwg-4"
GOOGLE_SHEET_ID = "16-ijuA0O8x1Ckt3oEKldxmglGanSYUxXkDXOZMrY0VE"
TARGET_SHEETS = ["Fall 2025", "Spring 2026"]  # 要抓取的Sheet名称

# ==================== 数据文件配置 ====================
# 这些文件路径可以通过环境变量覆盖
HISTORICAL_DATA_FILE = os.getenv("HISTORICAL_DATA_FILE", "historical_raw_data.xlsx")
CODE_CATEGORY_MAP_FILE = os.getenv("CODE_MAP_FILE", "code_to_category_map.xlsx")

# ==================== 数据库配置 ====================
DB_CONFIG = {
    "table_name": "unified_records",
    "schema": {
        "Start": "TIMESTAMP",
        "finished": "TIMESTAMP", 
        "duration (hours)": "REAL",
        "item name": "TEXT",
        "item name(with num)": "TEXT",
        "Category": "TEXT",
        "source": "TEXT",  # 'historical' 或 'realtime'
        "sheet_source": "TEXT"  # 数据来源的具体Sheet名称
    }
}

# ==================== 分析配置 ====================
CATEGORIES = [
    "Cables", "Sensor", "Batteries", "Cameras", "Tool", "Stationery",
    "Circuit Boards", "Adapter", "Tripods", "Chargers", "Motors",
    "Microphones", "Headphones", "Recording Equipment", "Lighting",
    "Computer Accessories", "Stabilizer", "Projectors", "VR Equipment",
    "Computer", "Audio Equipment", "Soldering Machines", "Screen",
    "Soldering Tools", "Game equipment", "Speaker", "Keyboards",
    "TVs", "Robotics", "Drawing Tablets", "Remote Controls",
    "Digital", "Lenses", "DIY"
]

TIME_PERIODS = {
    "Day": "D",
    "Week": "W", 
    "Month": "M",
    "Year": "Y"
}

# ==================== UI 配置 ====================
UI_CONFIG = {
    "title": "🔬 IMA Lab 物品分析平台",
    "page_icon": "🔬",
    "layout": "wide",
    "sidebar_state": "expanded"
}

# ==================== 日期格式配置 ====================
DATE_FORMATS = {
    "realtime": '%m/%d/%Y %H:%M:%S',
    "historical": ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']
}
