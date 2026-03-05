"""
分析策略基类
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

from data.database import db
from data.processors.data_processor import DataProcessor


class AnalysisStrategy(ABC):

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
        从数据库加载并处理数据。

        注意：start_date / end_date 直接传给 SQL 做过滤，
        格式为 'YYYY-MM-DD'，由 db.query() 内部处理。
        """
        source = None if mode == 'all' else mode
        exclude_inventory = (mode == 'realtime')

        df = db.query(
            source=source,
            category=category,
            start_date=start_date,
            end_date=end_date,
            exclude_inventory=exclude_inventory
        )

        return self.processor.prepare_for_analysis(df)

    @abstractmethod
    def analyze(self, **kwargs) -> dict:
        pass

    @abstractmethod
    def visualize(self, analysis_result: dict):
        pass
