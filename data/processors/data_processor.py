"""
数据处理器 - 统一的数据清洗、转换和日期处理
"""
import pandas as pd
from typing import Optional


class DataProcessor:
    """数据处理器 - 提供统一的数据处理方法"""

    @staticmethod
    def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
        """
        解析日期列，支持所有格式：
          - historical: '2020-05-18 10:30:25.816000' (ISO含微秒)
          - historical: '2024-12-13 19:02:23'        (ISO无微秒)
          - realtime:   '12/11/2025 11:46:17'        (MM/DD/YYYY)
        """
        for col in ['Start', 'finished']:
            if col not in df.columns:
                continue
            series = (
                df[col]
                .astype(str)
                .replace({'None': pd.NA, 'nan': pd.NA, 'NaT': pd.NA, 'nat': pd.NA})
            )
            df[col] = pd.to_datetime(series, format='mixed', dayfirst=False, errors='coerce')
        return df

    @staticmethod
    def prepare_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
        """
        分析前的标准处理流程：
        1. 解析日期
        2. 删除 Start 为空的记录
        3. 填充 finished（未归还 → 当前时间）
        4. duration 转整数
        """
        if df.empty:
            return df

        df = df.copy()
        df = DataProcessor.parse_dates(df)
        df = df.dropna(subset=['Start'])

        if 'finished' in df.columns:
            df['finished'] = df['finished'].fillna(pd.Timestamp.now())

        if 'duration (hours)' in df.columns:
            df['duration (hours)'] = (
                pd.to_numeric(df['duration (hours)'], errors='coerce')
                .round(0)
                .astype('Int64')
            )

        return df.reset_index(drop=True)

    @staticmethod
    def fuzzy_search(df: pd.DataFrame, query: str, column: str) -> list:
        """模糊搜索，返回排序后的匹配列表"""
        if df.empty or column not in df.columns:
            return []
        candidates = df[column].dropna().astype(str).unique()
        query_lower = query.lower().strip()
        if not query_lower:
            return sorted(candidates.tolist())
        matches = [x for x in candidates if query_lower in x.lower()]
        return sorted(matches, key=lambda x: (not x.lower().startswith(query_lower), x.lower()))
