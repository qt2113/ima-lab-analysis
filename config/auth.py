"""
Google API 认证配置 - 安全管理Google凭据
"""
import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any

class GoogleAuthConfig:
    """统一的Google认证管理"""
    
    @staticmethod
    def get_service_account_info() -> Dict[str, Any]:
        """
        获取Google Service Account凭据
        优先级：Streamlit Secrets > 本地文件 > 环境变量
        """
        # 1. 尝试从Streamlit Secrets读取（部署环境）
        try:
            if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
                return dict(st.secrets['gcp_service_account'])
        except Exception:
            pass
        
        # 2. 尝试从本地secrets.toml读取（开发环境）
        try:
            secrets_file = Path('.streamlit/secrets.toml')
            if secrets_file.exists():
                import toml
                secrets = toml.load(secrets_file)
                if 'gcp_service_account' in secrets:
                    return secrets['gcp_service_account']
        except Exception:
            pass
        
        # 3. 尝试从JSON文件读取（传统方式，不推荐）
        try:
            json_file = Path('service-account-key.json')
            if json_file.exists():
                with open(json_file) as f:
                    return json.load(f)
        except Exception:
            pass
        
        raise ValueError(
            "❌ 未找到Google Service Account凭据！\n"
            "请配置以下任一方式：\n"
            "1. Streamlit Secrets (推荐)\n"
            "2. .streamlit/secrets.toml\n"
            "3. service-account-key.json"
        )
    
    @staticmethod
    def get_scopes() -> list:
        """返回所需的API权限范围"""
        return [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
