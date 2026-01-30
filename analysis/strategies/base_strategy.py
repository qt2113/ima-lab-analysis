"""
分析策略基类 - 定义统一的分析接口
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

from data.database import db
from data.processors.data_processor import DataProcessor


class AnalysisStrategy(ABC):
    """分析策略抽象基类"""
    
    def __init__(self):
        self.processor = DataProcessor()
    
    def load_data(
        self,
        mode: str = 'all',
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        加载分析所需数据
        
        Args:
            mode: 数据模式 ('all', 'realtime', 'historical')
            category: 类别过滤
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            处理后的DataFrame
        """
        # 确定数据源
        source = None if mode == 'all' else mode
        
        # 是否排除Inventory
        exclude_inventory = (mode == 'realtime')
        
        # 从数据库查询
        df = db.query(
            source=source,
            category=category,
            start_date=start_date,
            end_date=end_date,
            exclude_inventory=exclude_inventory
        )
        
        # 数据处理
        df = self.processor.prepare_for_analysis(df)
        
        return df
    
    @abstractmethod
    def analyze(self, **kwargs) -> dict:
        """
        执行分析（子类必须实现）
        
        Returns:
            分析结果字典
        """
        pass
    
    @abstractmethod
    def visualize(self, analysis_result: dict):
        """
        可视化分析结果（子类必须实现）
        
        Args:
            analysis_result: analyze()方法返回的结果
        """
        pass
