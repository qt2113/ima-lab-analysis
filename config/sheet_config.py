"""Google Sheet 动态配置管理"""
import os
import toml
from pathlib import Path
from typing import List, Optional

CONFIG_FILE = Path("/tmp/ima_lab_sheet_config.toml")

def load_sheet_config() -> dict:
    """读取配置：优先用户自定义，其次默认"""
    if CONFIG_FILE.exists():
        secrets = toml.load(CONFIG_FILE)
        custom = secrets.get('custom_sheet', {})
        if custom.get('sheet_id'):
            return {
                'sheet_id': custom['sheet_id'],
                'sheet_names': custom.get('sheet_names', ['Fall 2025', 'Spring 2026']),
                'is_custom': True
            }
    return {'is_custom': False}

def save_sheet_config(sheet_id: str, sheet_names: List[str]):
    """保存用户配置到secrets.toml"""
    config = {}
    if CONFIG_FILE.exists():
        try:
            config = toml.load(CONFIG_FILE)
        except Exception:
            pass
    
    config['custom_sheet'] = {
        'sheet_id': sheet_id,
        'sheet_names': sheet_names
    }
    
    with open(CONFIG_FILE, 'w') as f:
        toml.dump(config, f)

def get_effective_sheet_id() -> str:
    """获取当前生效的Sheet ID"""
    from config.settings import GOOGLE_SHEET_ID
    custom = load_sheet_config()
    return custom.get('sheet_id', GOOGLE_SHEET_ID)

def get_effective_sheet_names() -> List[str]:
    """获取当前生效的Sheet名称列表"""
    from config.settings import TARGET_SHEETS
    custom = load_sheet_config()
    return custom.get('sheet_names', TARGET_SHEETS)

def clear_sheet_config():
    """清除用户自定义配置，恢复默认"""
    if CONFIG_FILE.exists():
        try:
            config = toml.load(CONFIG_FILE)
            if 'custom_sheet' in config:
                del config['custom_sheet']
                with open(CONFIG_FILE, 'w') as f:
                    toml.dump(config, f)
        except Exception:
            pass
