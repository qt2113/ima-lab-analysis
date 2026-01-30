#!/usr/bin/env python3
"""
更新实时数据脚本 - 快速从Google Sheets更新最新数据
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.database import db
from data.loaders.realtime_loader import load_realtime_data


def update_realtime_data():
    """更新实时数据"""
    print("=" * 60)
    print("更新实时数据")
    print("=" * 60)
    
    try:
        print("\n🌐 正在从Google Sheets拉取最新数据...")
        df_realtime = load_realtime_data()
        
        if df_realtime.empty:
            print("⚠️ 未拉取到数据")
            return False
        
        # 替换数据库中的实时数据
        db.insert_data(df_realtime, source='realtime', replace=True)
        
        print(f"\n✅ 实时数据更新成功：{len(df_realtime)} 条记录")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        print("\n提示：")
        print("1. 检查网络连接")
        print("2. 确认Google Service Account配置正确")
        print("3. 验证Service Account已添加到Google Sheet")
        print("=" * 60)
        return False


if __name__ == '__main__':
    success = update_realtime_data()
    sys.exit(0 if success else 1)
