"""
数据处理器 - 统一的数据清洗、转换和日期处理
"""
import pandas as pd
from typing import Optional

from config.settings import DATE_FORMATS


class DataProcessor:
    """数据处理器 - 提供统一的数据处理方法"""
    
    @staticmethod
    def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
        """
        智能解析日期列（支持多种格式）
        
        Args:
            df: 输入DataFrame
            
        Returns:
            日期解析后的DataFrame
        """
        date_columns = ['Start', 'finished']
        
        for col in date_columns:
            if col not in df.columns:
                continue
            
            # 转换为字符串
            series = df[col].astype(str)
            
            # 1. 先尝试实时数据格式（MM/DD/YYYY HH:MM:SS）
            df[col] = pd.to_datetime(
                series,
                format=DATE_FORMATS['realtime'],
                errors='coerce'
            )
            
            # 2. 对仍为NaT的值，尝试历史数据格式
            mask_nat = df[col].isna()
            if mask_nat.any():
                for fmt in DATE_FORMATS['historical']:
                    df.loc[mask_nat, col] = pd.to_datetime(
                        series.loc[mask_nat],
                        format=fmt,
                        errors='coerce'
                    )
                    mask_nat = df[col].isna()
                    if not mask_nat.any():
                        break
            
            # 3. 最终回退：自动推断格式
            if mask_nat.any():
                df.loc[mask_nat, col] = pd.to_datetime(
                    series.loc[mask_nat],
                    errors='coerce'
                )
        
        return df
    
    @staticmethod
    def filter_by_date(
        df: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        按日期范围过滤数据
        
        Args:
            df: 输入DataFrame
            start_date: 开始日期（字符串格式）
            end_date: 结束日期（字符串格式）
            
        Returns:
            过滤后的DataFrame
        """
        if 'Start' not in df.columns:
            return df
        
        df = df.copy()
        
        # 解析日期字符串
        def parse_date_str(date_str: str) -> Optional[pd.Timestamp]:
            if not date_str:
                return None
            
            # 标准化分隔符
            date_str = date_str.strip().replace('.', '/').replace('-', '/')
            
            # 处理两位年份
            import re
            if re.match(r'^\d{2}/\d{1,2}/\d{1,2}$', date_str):
                parts = date_str.split('/')
                date_str = f"20{parts[0]}/{parts[1]}/{parts[2]}"
            
            return pd.to_datetime(date_str, errors='coerce')
        
        # 应用过滤
        if start_date:
            start = parse_date_str(start_date)
            if start:
                df = df[df['Start'] >= start]
        
        if end_date:
            end = parse_date_str(end_date)
            if end:
                # 结束日期包含整天
                end_of_day = end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
                df = df[df['Start'] <= end_of_day]
        
        return df.reset_index(drop=True)
    
    @staticmethod
    def filter_by_category(df: pd.DataFrame, category: str) -> pd.DataFrame:
        """按类别过滤"""
        if 'Category' not in df.columns:
            return df
        return df[df['Category'] == category].copy()
    
    @staticmethod
    def fuzzy_search(
        df: pd.DataFrame,
        query: str,
        column: str
    ) -> list:
        """
        模糊搜索
        
        Args:
            df: 输入DataFrame
            query: 搜索关键词
            column: 搜索的列名
            
        Returns:
            匹配的唯一值列表（排序后）
        """
        if df.empty or column not in df.columns:
            return []
        
        # 获取唯一值
        candidates = df[column].dropna().astype(str).unique()
        
        query_lower = query.lower().strip()
        
        if not query_lower:
            matches = list(candidates)
        else:
            # 模糊匹配
            matches = [x for x in candidates if query_lower in x.lower()]
        
        # 排序：优先匹配开头的
        matches = sorted(
            matches,
            key=lambda x: (not x.lower().startswith(query_lower), x.lower())
        )
        
        return matches
    
    @staticmethod
    def calculate_statistics(df: pd.DataFrame) -> dict:
        """
        计算数据统计信息
        
        Args:
            df: 输入DataFrame
            
        Returns:
            统计信息字典
        """
        stats = {
            'total_records': len(df),
            'date_range': None,
            'categories': {},
            'items': {}
        }
        
        # 日期范围
        if 'Start' in df.columns and not df.empty:
            stats['date_range'] = {
                'min': df['Start'].min(),
                'max': df['Start'].max()
            }
        
        # 类别统计
        if 'Category' in df.columns:
            stats['categories'] = df['Category'].value_counts().to_dict()
        
        # 物品统计
        if 'item name(with num)' in df.columns:
            stats['items'] = df['item name(with num)'].value_counts().head(10).to_dict()
        
        return stats
    
    @staticmethod
    def prepare_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
        """
        为分析准备数据（标准化流程）
        
        Args:
            df: 原始数据
            
        Returns:
            处理后的数据
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # 1. 解析日期
        df = DataProcessor.parse_dates(df)
        
        # 2. 删除Start为空的记录
        df = df.dropna(subset=['Start'])
        
        # 3. 填充finished为当前时间（未归还的记录）
        if 'finished' in df.columns:
            df['finished'] = df['finished'].fillna(pd.Timestamp.now())
        
        # 4. 确保duration为整数
        if 'duration (hours)' in df.columns:
            df['duration (hours)'] = (
                pd.to_numeric(df['duration (hours)'], errors='coerce')
                .round(0)
                .astype('Int64')
            )
        
        return df.reset_index(drop=True)


# 便捷函数
def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """准备数据的快捷函数"""
    return DataProcessor.prepare_for_analysis(df)
