"""
类别映射加载器 - 负责加载Code到Category的映射关系
"""
import pandas as pd
import re
from pathlib import Path
from typing import Dict

from config.settings import CODE_CATEGORY_MAP_FILE


class CategoryMapper:
    """类别映射器 - 单例模式"""
    
    _instance = None
    _code_map: Dict[str, str] = {}
    _name_map: Dict[str, str] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._code_map:  # 只加载一次
            self._load_mapping()
    
    def _load_mapping(self):
        """从Excel加载映射关系"""
        map_file = Path(CODE_CATEGORY_MAP_FILE)
        
        if not map_file.exists():
            raise FileNotFoundError(
                f"❌ 未找到映射文件: {CODE_CATEGORY_MAP_FILE}\n"
                "请确保文件存在于项目根目录"
            )
        
        df = pd.read_excel(map_file, engine='openpyxl')
        df.columns = [str(col).strip() for col in df.columns]
        
        if 'Code' not in df.columns or 'Category' not in df.columns:
            raise ValueError("映射文件必须包含 'Code' 和 'Category' 列")
        
        # 加载Code映射
        self._load_code_mapping(df)
        
        # 加载Name映射
        if 'Name' in df.columns:
            self._load_name_mapping(df)
        
        print(f"✅ 已加载 {len(self._code_map)} 条Code映射")
        print(f"✅ 已加载 {len(self._name_map)} 条Name映射")
    
    def _load_code_mapping(self, df: pd.DataFrame):
        """加载Code到Category的映射"""
        for _, row in df.iterrows():
            code_str = str(row['Code']).strip().upper()
            category = str(row['Category']).strip()
            
            if not code_str or not category:
                continue
            
            # 处理区间格式 (如 "CAM1-10")
            match_range = re.match(r'^([A-Z0-9]+?)\d+-', code_str)
            if match_range:
                prefix = match_range.group(1)
                self._code_map[prefix] = category
            
            # 处理单个编号格式 (如 "CAM1")
            match_single = re.match(r'^([A-Z0-9]+?)\d+$', code_str)
            if match_single:
                prefix = match_single.group(1)
                self._code_map[prefix] = category
            
            # 添加前缀映射（长度4和3）
            for length in [4, 3]:
                if len(code_str) >= length:
                    prefix = code_str[:length]
                    if prefix not in self._code_map:
                        self._code_map[prefix] = category
            
            # 添加完整Code映射
            self._code_map[code_str] = category
    
    def _load_name_mapping(self, df: pd.DataFrame):
        """加载Name到Category的映射"""
        df_valid = df[df['Name'].notna() & df['Category'].notna()].copy()
        
        for _, row in df_valid.iterrows():
            name = str(row['Name']).strip().lower()
            category = str(row['Category']).strip()
            
            if name and category:
                self._name_map[name] = category
    
    def get_category_by_code(self, code: str) -> str:
        """
        根据Code获取Category
        
        Args:
            code: 设备编号
            
        Returns:
            类别名称，未找到返回 'Unknown'
        """
        if pd.isna(code):
            return 'Unknown'
        
        code = str(code).strip().upper()
        
        # 逐步缩短前缀进行匹配
        for length in range(min(len(code), 4), 2, -1):
            prefix = code[:length]
            if prefix in self._code_map:
                return self._code_map[prefix]
        
        # 精确匹配
        if code in self._code_map:
            return self._code_map[code]
        
        return 'Unknown'
    
    def get_category_by_name(self, name: str) -> str:
        """
        根据Name获取Category
        
        Args:
            name: 物品名称
            
        Returns:
            类别名称，未找到返回None
        """
        if pd.isna(name):
            return None
        
        name_lower = str(name).strip().lower()
        return self._name_map.get(name_lower)
    
    def get_category(self, code: str = None, name: str = None) -> str:
        """
        智能获取Category (优先Code，回退Name)
        
        Args:
            code: 设备编号
            name: 物品名称
            
        Returns:
            类别名称
        """
        # 先尝试Code映射
        if code:
            category = self.get_category_by_code(code)
            if category != 'Unknown':
                return category
        
        # Code失败，尝试Name映射
        if name:
            category = self.get_category_by_name(name)
            if category:
                return category
        
        return 'Unknown'


# 全局映射器实例
mapper = CategoryMapper()
