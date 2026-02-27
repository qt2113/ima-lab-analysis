"""
历史数据加载器 - 从Excel文件加载历史借用记录
"""
import pandas as pd
import re
from pathlib import Path

from config.settings import HISTORICAL_DATA_FILES
from data.loaders.category_mapper import mapper


class HistoricalDataLoader:
    """历史数据加载器"""
    
    # 原始列名到标准列名的映射
    COLUMN_MAPPING = {
        'started': 'Start',
        'finished': 'finished',
        'duration (hours)': 'duration (hours)',
        'item category': 'Category',
        'name': 'item name(with num)'
    }
    
    @staticmethod
    def _strip_number(item_name: str) -> str:
        """去除物品名称末尾的编号"""
        if pd.isna(item_name):
            return ""
        # 移除末尾的空格和数字
        return re.sub(r'\s+\d+$', '', str(item_name)).strip()
    
    def load(self, file_paths: list = None) -> pd.DataFrame:
        """
        加载历史数据
        
        Args:
            file_paths: Excel文件路径列表，默认使用配置文件中的路径
            
        Returns:
            清洗后的DataFrame
        """
        if file_paths is None:
            file_paths = HISTORICAL_DATA_FILES
        
        all_dfs = []
        
        for file_path in file_paths:
            file_path = Path(file_path.strip())
            
            if not file_path.exists():
                print(f"⚠️ 跳过不存在的文件: {file_path}")
                continue
            
            print(f"📂 正在加载历史数据: {file_path}")
            
            df = pd.read_excel(file_path, engine='openpyxl')
            
            df = df[list(self.COLUMN_MAPPING.keys())].rename(columns=self.COLUMN_MAPPING)
            
            df['item name'] = df['item name(with num)'].apply(self._strip_number)
            
            df['source'] = 'historical'
            df['sheet_source'] = file_path.stem
            
            df = df.dropna(subset=['Start', 'Category']).reset_index(drop=True)
            
            df['Category'] = df['Category'].astype(str)
            
            if 'duration (hours)' in df.columns:
                df['duration (hours)'] = (
                    pd.to_numeric(df['duration (hours)'], errors='coerce')
                    .round(0)
                    .astype('Int64')
                )
            
            all_dfs.append(df)
            print(f"✅ 成功加载 {len(df)} 条记录 from {file_path.name}")
        
        if not all_dfs:
            raise FileNotFoundError("❌ 没有找到任何历史数据文件")
        
        result_df = pd.concat(all_dfs, ignore_index=True)
        result_df = result_df.drop_duplicates(subset=['Start', 'item name(with num)'], keep='first')
        print(f"✅ 共加载 {len(result_df)} 条历史记录（去重后）")
        
        return result_df


# 便捷函数
def load_historical_data(file_paths: list = None) -> pd.DataFrame:
    """加载历史数据的快捷函数"""
    loader = HistoricalDataLoader()
    return loader.load(file_paths)
