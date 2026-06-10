#!/usr/bin/env python3
"""
更新实时数据脚本 - 快速从Google Sheets更新最新数据
"""
import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from data.database import db
from data.loaders.realtime_loader import load_realtime_data


def update_realtime_data():
    """更新实时数据"""
    logger.info("Realtime data update")

    try:
        logger.info("Fetching latest data from Google Sheets")
        df_realtime = load_realtime_data()

        if df_realtime.empty:
            logger.warning("No data fetched from Google Sheets")
            return False

        db.insert_data(df_realtime, source='realtime', replace=True)
        logger.info(f"Realtime data updated: {len(df_realtime)} records")
        return True

    except (ImportError, OSError, ValueError) as e:
        logger.error(f"Update failed: {e}")
        logger.warning("Tips: check network, Google Service Account config, and Sheet sharing")
        return False


if __name__ == '__main__':
    success = update_realtime_data()
    sys.exit(0 if success else 1)
