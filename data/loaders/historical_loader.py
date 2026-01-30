"""
历史数据加载器 - 从Excel文件加载历史借用记录
"""
import pandas as pd
import re
from pathlib import Path

from config.settings import HISTORICAL_DATA_FILE
from data.loaders.category_mapper import mapper


class HistoricalDataLoader:
    """历史数据加载器"""
    
    # 原始列名到标准列名的映射
    COLUMN_MAPPING = {
        'started': 'Start',
        'finished': 'finished',
        'duration (hours)': 'duration (hours)',
        'item category': 'Category',
        'item name': 'item name(with num)'
    }
    
    @staticmethod
    def _strip_number(item_name: str) -> str:
        """去除物品名称末尾的编号"""
        if pd.isna(item_name):
            return ""
        # 移除末尾的空格和数字
        return re.sub(r'\s+\d+$', '', str(item_name)).strip()
    
    def load(self, file_path: str = None) -> pd.DataFrame:
        """
        加载历史数据
        
        Args:
            file_path: Excel文件路径，默认使用配置文件中的路径
            
        Returns:
            清洗后的DataFrame
        """
        if file_path is None:
            file_path = HISTORICAL_DATA_FILE
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"❌ 历史数据文件不存在: {file_path}")
        
        print(f"📂 正在加载历史数据: {file_path}")
        
        # 读取Excel
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # 重命名列
        df = df[list(self.COLUMN_MAPPING.keys())].rename(columns=self.COLUMN_MAPPING)
        
        # 生成不带编号的物品名称
        df['item name'] = df['item name(with num)'].apply(self._strip_number)
        
        # 添加数据源标识
        df['source'] = 'historical'
        df['sheet_source'] = 'Historical'
        
        # 清理无效数据
        df = df.dropna(subset=['Start', 'Category']).reset_index(drop=True)
        
        # 确保Category是字符串类型
        df['Category'] = df['Category'].astype(str)
        
        # 四舍五入duration
        if 'duration (hours)' in df.columns:
            df['duration (hours)'] = (
                pd.to_numeric(df['duration (hours)'], errors='coerce')
                .round(0)
                .astype('Int64')
            )
        
        print(f"✅ 成功加载 {len(df)} 条历史记录")
        
        return df


# 便捷函数
def load_historical_data(file_path: str = None) -> pd.DataFrame:
    """加载历史数据的快捷函数"""
    loader = HistoricalDataLoader()
    return loader.load(file_path)
