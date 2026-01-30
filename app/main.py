"""
IMA Lab 数据分析平台 - Streamlit主应用
"""
import streamlit as st
import pandas as pd
from pathlib import Path

# 配置页面
st.set_page_config(
    page_title="IMA Lab 物品分析",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入模块
from config.settings import CATEGORIES
from data.database import db
from data.loaders.historical_loader import load_historical_data
from data.loaders.realtime_loader import load_realtime_data
from data.processors.data_processor import DataProcessor
from analysis.strategies.single_item_strategy import SingleItemAnalysis
from analysis.strategies.topn_strategy import TopNAnalysis
from analysis.strategies.duration_strategy import DurationAnalysis


# ==================== 辅助函数 ====================

@st.cache_data(ttl=300)  # 缓存5分钟
def get_available_items(category: str, mode: str = 'all') -> list:
    """获取指定类别的所有物品（带编号）"""
    source = None if mode == 'all' else mode
    exclude_inventory = (mode == 'realtime')
    
    df = db.query(source=source, category=category, exclude_inventory=exclude_inventory)
    
    if df.empty:
        return []
    
    return sorted(df['item name(with num)'].dropna().unique().tolist())


def fuzzy_search_items(category: str, query: str, mode: str = 'all') -> list:
    """模糊搜索物品"""
    all_items = get_available_items(category, mode)
    
    if not query:
        return all_items
    
    query_lower = query.lower()
    matches = [item for item in all_items if query_lower in item.lower()]
    
    # 排序：优先匹配开头的
    return sorted(matches, key=lambda x: (not x.lower().startswith(query_lower), x))


def refresh_data(mode: str):
    """刷新数据"""
    with st.spinner('正在更新数据...'):
        try:
            if mode == 'all':
                # 加载历史数据
                df_hist = load_historical_data()
                db.insert_data(df_hist, source='historical', replace=True)
                
                # 加载实时数据
                df_real = load_realtime_data()
                db.insert_data(df_real, source='realtime', replace=True)
                
                st.success(f'✅ 数据更新成功！历史: {len(df_hist)} 条，实时: {len(df_real)} 条')
            else:
                # 只加载实时数据
                df_real = load_realtime_data()
                db.insert_data(df_real, source='realtime', replace=True)
                
                st.success(f'✅ 实时数据更新成功！共 {len(df_real)} 条记录')
            
            # 清除缓存
            st.cache_data.clear()
            
        except Exception as e:
            st.error(f'❌ 数据更新失败: {str(e)}')


# ==================== 侧边栏配置 ====================

with st.sidebar:
    st.title('🔬 IMA Lab')
    st.markdown('---')
    
    # 数据模式选择
    st.subheader('📊 数据模式')
    mode = st.radio(
        '选择数据源',
        options=['all', 'realtime'],
        format_func=lambda x: '📚 全部数据' if x == 'all' else '🔄 仅实时数据',
        key='data_mode'
    )
    
    # 显示数据统计
    if mode == 'all':
        st.info('包含历史数据 + 实时数据')
    else:
        st.info('仅显示实时数据（排除Inventory）')
    
    # 刷新按钮
    if st.button('🔄 刷新数据', use_container_width=True):
        refresh_data(mode)
    
    st.markdown('---')
    
    # 数据库统计
    with st.expander('📈 数据统计', expanded=False):
        stats = db.get_statistics()
        st.metric('总记录数', stats['total_records'])
        
        if 'by_source' in stats and stats['by_source']:
            st.write('**各来源记录数:**')
            for source, count in stats['by_source'].items():
                st.write(f'- {source}: {count}')
    
    st.markdown('---')
    st.caption('Powered by Streamlit')


# ==================== 主页面 ====================

st.title('🔬 IMA Lab 物品借用分析平台')

# 创建选项卡
tab1, tab2, tab3 = st.tabs(['📈 单品分析', '🏆 Top N分析', '📊 时间线分析'])

# ==================== Tab 1: 单品分析 ====================
with tab1:
    st.header('单品借用时间线')
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        category_si = st.selectbox(
            '类别',
            options=CATEGORIES,
            key='single_item_category'
        )
    
    with col2:
        search_query_si = st.text_input(
            '搜索物品',
            placeholder='输入物品名称或编号...',
            key='single_item_search'
        )
    
    # 物品选择
    if search_query_si:
        items_si = fuzzy_search_items(category_si, search_query_si, mode)
    else:
        items_si = get_available_items(category_si, mode)
    
    item_si = st.selectbox(
        '选择物品（带编号）',
        options=items_si,
        key='single_item_select'
    )
    
    # 时间范围
    col3, col4 = st.columns(2)
    with col3:
        start_date_si = st.text_input('开始日期', placeholder='2025/1/1', key='si_start')
    with col4:
        end_date_si = st.text_input('结束日期', placeholder='2025/12/31', key='si_end')
    
    # 运行分析
    if st.button('🚀 运行分析', key='run_single_item', use_container_width=True):
        if not item_si:
            st.warning('⚠️ 请先选择一个物品')
        else:
            with st.spinner('正在分析...'):
                analyzer = SingleItemAnalysis()
                result = analyzer.analyze(
                    item_with_num=item_si,
                    category=category_si,
                    mode=mode,
                    start_date=start_date_si if start_date_si else None,
                    end_date=end_date_si if end_date_si else None
                )
                
                if result['success']:
                    # 显示统计信息
                    col5, col6, col7 = st.columns(3)
                    with col5:
                        st.metric('总借用次数', result['total_borrows'])
                    with col6:
                        st.metric('起始日期', result['date_range']['start'].strftime('%Y-%m-%d'))
                    with col7:
                        st.metric('结束日期', result['date_range']['end'].strftime('%Y-%m-%d'))
                    
                    # 显示图表
                    fig = analyzer.visualize(result)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(result['message'])


# ==================== Tab 2: Top N分析 ====================
with tab2:
    st.header('Top N 高频物品分析')
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        category_tn = st.selectbox(
            '类别',
            options=CATEGORIES,
            key='topn_category'
        )
    
    with col2:
        top_n = st.number_input('Top N', min_value=1, max_value=20, value=5, key='topn_n')
    
    with col3:
        period_tn = st.selectbox(
            '时间周期',
            options=['Day', 'Week', 'Month', 'Year'],
            index=1,
            key='topn_period'
        )
    
    # 可选：限定物品名称
    col4, col5 = st.columns([1, 1])
    with col4:
        search_query_tn = st.text_input(
            '搜索物品（可选）',
            placeholder='留空则分析全类别',
            key='topn_search'
        )
    
    with col5:
        if search_query_tn:
            df_temp = db.query(category=category_tn)
            item_names = DataProcessor.fuzzy_search(df_temp, search_query_tn, 'item name')
            item_name_tn = st.selectbox('物品名称', options=[''] + item_names, key='topn_item_name')
        else:
            item_name_tn = None
    
    # 时间范围
    col6, col7 = st.columns(2)
    with col6:
        start_date_tn = st.text_input('开始日期', placeholder='2025/1/1', key='tn_start')
    with col7:
        end_date_tn = st.text_input('结束日期', placeholder='2025/12/31', key='tn_end')
    
    # 运行分析
    if st.button('🚀 运行分析', key='run_topn', use_container_width=True):
        with st.spinner('正在分析...'):
            analyzer = TopNAnalysis()
            result = analyzer.analyze(
                category=category_tn,
                mode=mode,
                top_n=top_n,
                period=period_tn,
                item_name=item_name_tn if item_name_tn else None,
                start_date=start_date_tn if start_date_tn else None,
                end_date=end_date_tn if end_date_tn else None
            )
            
            if result['success']:
                fig_timeline, fig_pie = analyzer.visualize(result)
                
                # 显示时间线图
                st.subheader('📈 借用次数时间线')
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                # 显示饼图
                if fig_pie:
                    st.subheader('🍰 借用时长分布')
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.error(result['message'])


# ==================== Tab 3: 时间线分析 ====================
with tab3:
    st.header('物品借用时间线（日粒度）')
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        category_dur = st.selectbox(
            '类别',
            options=CATEGORIES,
            key='duration_category'
        )
    
    with col2:
        search_query_dur = st.text_input(
            '搜索物品',
            placeholder='输入物品名称或编号...',
            key='duration_search'
        )
    
    # 物品选择
    if search_query_dur:
        items_dur = fuzzy_search_items(category_dur, search_query_dur, mode)
    else:
        items_dur = get_available_items(category_dur, mode)
    
    item_dur = st.selectbox(
        '选择物品（带编号）',
        options=items_dur,
        key='duration_select'
    )
    
    # 时间范围
    col3, col4 = st.columns(2)
    with col3:
        start_date_dur = st.text_input('开始日期', placeholder='2025/1/1', key='dur_start')
    with col4:
        end_date_dur = st.text_input('结束日期', placeholder='2025/12/31', key='dur_end')
    
    # 运行分析
    if st.button('🚀 运行分析', key='run_duration', use_container_width=True):
        if not item_dur:
            st.warning('⚠️ 请先选择一个物品')
        else:
            with st.spinner('正在分析...'):
                analyzer = DurationAnalysis()
                result = analyzer.analyze(
                    item_with_num=item_dur,
                    category=category_dur,
                    mode=mode,
                    start_date=start_date_dur if start_date_dur else None,
                    end_date=end_date_dur if end_date_dur else None
                )
                
                if result['success']:
                    # 显示统计信息
                    col5, col6, col7, col8 = st.columns(4)
                    with col5:
                        st.metric('总借用次数', result['total_borrows'])
                    with col6:
                        total_days = (result['date_range']['end'] - result['date_range']['start']).days + 1
                        st.metric('时间跨度', f'{total_days} 天')
                    with col7:
                        borrowed_days = result['timeline']['status'].sum()
                        st.metric('借出天数', borrowed_days)
                    with col8:
                        utilization = (borrowed_days / total_days * 100) if total_days > 0 else 0
                        st.metric('使用率', f'{utilization:.1f}%')
                    
                    # 显示图表
                    fig = analyzer.visualize(result)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 显示详细数据（可选）
                    with st.expander('📊 查看详细数据'):
                        st.dataframe(result['timeline'], use_container_width=True)
                else:
                    st.error(result['message'])


# ==================== 页脚 ====================
st.markdown('---')
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <p>IMA Lab 物品借用分析平台 | 数据来源: Google Sheets + 历史记录</p>
    </div>
    """,
    unsafe_allow_html=True
)
