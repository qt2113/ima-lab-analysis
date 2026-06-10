#!/usr/bin/env python3
"""
数据初始化脚本 - 首次运行时加载数据到数据库
"""
import sys
import logging
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from data.database import db
from data.loaders.historical_loader import load_historical_data
from data.loaders.realtime_loader import load_realtime_data


def init_database():
    """初始化数据库并加载数据"""
    logger.info("IMA Lab data initialization")

    # 1. 加载历史数据
    logger.info("Step 1/2: Loading historical data")
    try:
        df_historical = load_historical_data()
        db.insert_data(df_historical, source='historical', replace=True)
        logger.info(f"Historical data loaded: {len(df_historical)} records")
    except FileNotFoundError as e:
        logger.warning(f"Historical data files not found, skipping: {e}")
        df_historical = None
    except (OSError, ValueError) as e:
        logger.error(f"Historical data load failed: {e}")
        return False

    # 2. 加载实时数据
    logger.info("Step 2/2: Fetching realtime data from Google Sheets")
    try:
        df_realtime = load_realtime_data()
        if not df_realtime.empty:
            if df_historical is not None and not df_historical.empty:
                df_historical['Start'] = pd.to_datetime(df_historical['Start'], errors='coerce')
                df_realtime['Start'] = pd.to_datetime(df_realtime['Start'], errors='coerce')

                df_historical['Start_min'] = df_historical['Start'].dt.floor('min')
                df_realtime['Start_min'] = df_realtime['Start'].dt.floor('min')
                hist_keys = set(zip(df_historical['Start_min'], df_historical['item name(with num)']))

                original_count = len(df_realtime)
                df_realtime = df_realtime[
                    ~df_realtime.apply(lambda x: (x['Start_min'], x['item name(with num)']) in hist_keys, axis=1)
                ]
                removed_count = original_count - len(df_realtime)
                if removed_count > 0:
                    logger.info(f"Deduplication: removed {removed_count} records overlapping with historical data")

                df_realtime = df_realtime.drop(columns=['Start_min'], errors='ignore')

            db.insert_data(df_realtime, source='realtime', replace=True)
            logger.info(f"Realtime data loaded: {len(df_realtime)} records")
        else:
            logger.warning("No realtime data fetched")
    except (ImportError, OSError, ValueError) as e:
        logger.error(f"Realtime data load failed: {e}")
        logger.warning("Check Google Service Account configuration")
        return False

    # 3. 显示统计
    stats = db.get_statistics()
    logger.info(f"Total records: {stats['total_records']}")
    logger.info(f"Records by source: {stats.get('by_source', {})}")
    top_cats = list(stats.get('top_categories', {}).items())[:10]
    logger.info(f"Top 10 categories: {top_cats}")

    logger.info("Data initialization complete")
    return True


if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
