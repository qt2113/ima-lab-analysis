#!/usr/bin/env python3
"""
数据初始化脚本 - 首次运行时加载数据到数据库
"""
import sys
import pandas as pd
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.database import db
from data.loaders.historical_loader import load_historical_data
from data.loaders.realtime_loader import load_realtime_data


def init_database():
    """初始化数据库并加载数据"""
    print("=" * 60)
    print("IMA Lab 数据初始化")
    print("=" * 60)
    
    # 1. 加载历史数据
    print("\n[1/2] 正在加载历史数据...")
    try:
        df_historical = load_historical_data()
        db.insert_data(df_historical, source='historical', replace=True)
        print(f"✅ 历史数据加载成功：{len(df_historical)} 条记录")
    except FileNotFoundError as e:
        print(f"⚠️ 历史数据文件未找到，跳过: {e}")
        df_historical = None
    except Exception as e:
        print(f"❌ 历史数据加载失败: {e}")
        return False
    
    # 2. 加载实时数据
    print("\n[2/2] 正在从Google Sheets拉取实时数据...")
    try:
        df_realtime = load_realtime_data()
        if not df_realtime.empty:
            # 历史数据 vs 实时数据去重（以历史为准）
            if df_historical is not None and not df_historical.empty:
                df_historical['Start'] = pd.to_datetime(df_historical['Start'], errors='coerce')
                df_realtime['Start'] = pd.to_datetime(df_realtime['Start'], errors='coerce')
                
                # 秒级精确匹配（保留备用）
                # hist_keys = set(zip(df_historical['Start'], df_historical['item name(with num)']))
                
                # 分钟级匹配（去除毫秒后匹配，误差1分钟内算同一条）
                df_historical['Start_min'] = df_historical['Start'].dt.floor('min')
                df_realtime['Start_min'] = df_realtime['Start'].dt.floor('min')
                hist_keys = set(zip(df_historical['Start_min'], df_historical['item name(with num)']))
                
                original_count = len(df_realtime)
                df_realtime = df_realtime[
                    ~df_realtime.apply(lambda x: (x['Start_min'], x['item name(with num)']) in hist_keys, axis=1)
                ]
                removed_count = original_count - len(df_realtime)
                if removed_count > 0:
                    print(f"🗑️  去除 {removed_count} 条与历史重复的实时数据")
                
                # 去除临时列，避免插入数据库时报错
                df_realtime = df_realtime.drop(columns=['Start_min'], errors='ignore')
            
            db.insert_data(df_realtime, source='realtime', replace=True)
            print(f"✅ 实时数据加载成功：{len(df_realtime)} 条记录")
        else:
            print("⚠️ 未拉取到实时数据")
    except Exception as e:
        print(f"❌ 实时数据加载失败: {e}")
        print("提示：请检查Google Service Account配置")
        return False
    
    # 3. 显示统计
    print("\n" + "=" * 60)
    print("数据库统计")
    print("=" * 60)
    stats = db.get_statistics()
    print(f"总记录数: {stats['total_records']}")
    print("\n各数据源记录数:")
    for source, count in stats.get('by_source', {}).items():
        print(f"  - {source}: {count}")
    
    print("\nTop 10 类别:")
    for category, count in list(stats.get('top_categories', {}).items())[:10]:
        print(f"  - {category}: {count}")
    
    print("\n✅ 数据初始化完成！")
    print("=" * 60)
    
    return True


if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)
