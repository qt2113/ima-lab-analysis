"""
数据库管理模块 - 统一的数据库操作接口
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from config.settings import DATABASE_PATH, DB_CONFIG


class DatabaseManager:
    """数据库管理器 - 单例模式"""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._connection = self._create_connection()
            self._initialize_database()
    
    @staticmethod
    def _create_connection() -> sqlite3.Connection:
        """创建数据库连接"""
        db_path = Path(DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        # 优化性能
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    
    def _initialize_database(self):
        """初始化数据库表结构"""
        table_name = DB_CONFIG["table_name"]
        schema = DB_CONFIG["schema"]
        
        # 构建CREATE TABLE语句
        columns_def = ", ".join([
            f'"{name}" {dtype}' for name, dtype in schema.items()
        ])
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {columns_def}
        )
        """
        
        self._connection.execute(create_table_sql)
        self._connection.commit()
        
        # 创建索引以加速查询
        self._create_indexes()
    
    def _create_indexes(self):
        """创建索引优化查询性能"""
        table_name = DB_CONFIG["table_name"]
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_source ON {table_name}(source)",
            f"CREATE INDEX IF NOT EXISTS idx_category ON {table_name}(Category)",
            f"CREATE INDEX IF NOT EXISTS idx_start_date ON {table_name}(Start)",
            f"CREATE INDEX IF NOT EXISTS idx_sheet_source ON {table_name}(sheet_source)"
        ]
        
        for index_sql in indexes:
            try:
                self._connection.execute(index_sql)
            except sqlite3.OperationalError:
                pass  # 索引已存在
        
        self._connection.commit()
    
    @property
    def connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return self._connection
    
    def insert_data(self, df: pd.DataFrame, source: str = None, replace: bool = False):
        """
        插入数据到数据库
        
        Args:
            df: 要插入的数据
            source: 数据源标识 ('historical' 或 'realtime')
            replace: 是否替换同源数据
        """
        table_name = DB_CONFIG["table_name"]
        
        if replace and source:
            # 先删除同源的旧数据
            self._connection.execute(
                f"DELETE FROM {table_name} WHERE source = ?", 
                (source,)
            )
            self._connection.commit()
        
        # 插入新数据
        df.to_sql(
            table_name, 
            self._connection, 
            if_exists='append', 
            index=False
        )
        print(f"✅ 成功插入 {len(df)} 条记录 (source={source})")
    
    def query(
        self, 
        source: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exclude_inventory: bool = False
    ) -> pd.DataFrame:
        """
        查询数据
        
        Args:
            source: 数据源过滤 ('historical', 'realtime', None=全部)
            category: 类别过滤
            start_date: 开始日期
            end_date: 结束日期
            exclude_inventory: 是否排除Inventory sheet的数据
        """
        table_name = DB_CONFIG["table_name"]
        
        # 构建查询条件
        conditions = []
        params = []
        
        if source:
            conditions.append("source = ?")
            params.append(source)
        
        if category:
            conditions.append("Category = ?")
            params.append(category)
        
        if start_date:
            conditions.append("Start >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("Start <= ?")
            params.append(end_date)
        
        if exclude_inventory:
            conditions.append("sheet_source != 'Inventory'")
        
        # 构建SQL
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {table_name} WHERE {where_clause}"
        
        return pd.read_sql(sql, self._connection, params=params)
    
    def clear_source(self, source: str):
        """清空指定源的数据"""
        table_name = DB_CONFIG["table_name"]
        self._connection.execute(
            f"DELETE FROM {table_name} WHERE source = ?",
            (source,)
        )
        self._connection.commit()
        print(f"✅ 已清空 {source} 数据")
    
    def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        table_name = DB_CONFIG["table_name"]
        
        stats = {}
        
        # 总记录数
        cursor = self._connection.execute(f"SELECT COUNT(*) FROM {table_name}")
        stats['total_records'] = cursor.fetchone()[0]
        
        # 各数据源记录数
        cursor = self._connection.execute(
            f"SELECT source, COUNT(*) FROM {table_name} GROUP BY source"
        )
        stats['by_source'] = dict(cursor.fetchall())
        
        # 各类别记录数
        cursor = self._connection.execute(
            f"SELECT Category, COUNT(*) FROM {table_name} GROUP BY Category ORDER BY COUNT(*) DESC LIMIT 10"
        )
        stats['top_categories'] = dict(cursor.fetchall())
        
        return stats
    
    def close(self):
        """关闭数据库连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def __del__(self):
        """析构函数，确保连接关闭"""
        self.close()


# 全局数据库实例
db = DatabaseManager()
