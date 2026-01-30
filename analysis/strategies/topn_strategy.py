"""
Top N分析策略 - 分析高频借用物品
"""
import pandas as pd
import plotly.graph_objs as go
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy
from config.settings import TIME_PERIODS


class TopNAnalysis(AnalysisStrategy):
    """Top N高频物品分析"""
    
    def analyze(
        self,
        category: str,
        mode: str = 'all',
        top_n: int = 5,
        period: str = 'Week',
        item_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        分析Top N高频物品
        
        Args:
            category: 物品类别
            mode: 数据模式
            top_n: Top N数量
            period: 时间周期 ('Day', 'Week', 'Month', 'Year')
            item_name: 可选，只分析指定物品名称的编号
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            分析结果
        """
        # 加载数据
        df = self.load_data(
            mode=mode,
            category=category,
            start_date=start_date,
            end_date=end_date
        )
        
        # 如果指定了item_name，只分析该物品
        if item_name:
            df = df[df['item name'] == item_name].copy()
        
        if df.empty:
            return {
                'success': False,
                'message': '没有找到匹配的借用记录',
                'pivot': pd.DataFrame(),
                'detail_data': pd.DataFrame()
            }
        
        # 统计Top N
        top_items = df['item name(with num)'].value_counts().head(top_n).index
        df_top = df[df['item name(with num)'].isin(top_items)].copy()
        
        # 生成时间序列透视表
        pivot = self._create_time_series(df_top, period)
        
        # 确保Top N顺序
        pivot = pivot[top_items.intersection(pivot.columns)]
        
        return {
            'success': True,
            'pivot': pivot,
            'detail_data': df_top,
            'top_n': top_n,
            'period': period,
            'category': category
        }
    
    def _create_time_series(
        self,
        df: pd.DataFrame,
        period: str
    ) -> pd.DataFrame:
        """
        创建时间序列透视表
        
        Args:
            df: 借用记录
            period: 时间周期
            
        Returns:
            透视表 (period x items)
        """
        # 使用事件模型（只计算Check Out事件）
        df['period'] = df['Start'].dt.to_period(
            TIME_PERIODS[period]
        ).dt.start_time
        
        # 按时间段和物品分组计数
        pivot = df.groupby(['period', 'item name(with num)']).size().unstack(fill_value=0)
        
        return pivot
    
    def visualize(self, analysis_result: dict) -> tuple:
        """
        可视化Top N分析结果
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            (时间线图, 时长分布饼图)
        """
        if not analysis_result['success']:
            return None, None
        
        pivot = analysis_result['pivot']
        df_detail = analysis_result['detail_data']
        category = analysis_result['category']
        top_n = analysis_result['top_n']
        
        # 图1: 借用次数时间线
        fig_timeline = self._create_timeline_chart(pivot, category, top_n)
        
        # 图2: 借用时长分布饼图
        fig_pie = self._create_duration_pie_chart(df_detail)
        
        return fig_timeline, fig_pie
    
    def _create_timeline_chart(
        self,
        pivot: pd.DataFrame,
        category: str,
        top_n: int
    ) -> go.Figure:
        """创建时间线图表"""
        fig = go.Figure()
        
        for col in pivot.columns:
            fig.add_trace(go.Scatter(
                x=pivot.index,
                y=pivot[col],
                mode='lines+markers',
                name=col,
                line=dict(width=2),
                marker=dict(size=6)
            ))
        
        fig.update_layout(
            title=f'{category} - Top {top_n} 高频编号借用次数时间线',
            xaxis_title='时间',
            yaxis_title='借用次数',
            legend_title='物品编号',
            xaxis_rangeslider_visible=True,
            height=560,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_duration_pie_chart(self, df: pd.DataFrame) -> go.Figure:
        """创建借用时长分布饼图"""
        if 'duration (hours)' not in df.columns or df['duration (hours)'].isna().all():
            return None
        
        # 统计各时长的频次
        duration_counts = df['duration (hours)'].dropna().value_counts().reset_index()
        duration_counts.columns = ['Duration (hours)', 'Frequency']
        
        # 为每个时长生成物品列表（用于hover）
        hover_texts = {}
        for duration in duration_counts['Duration (hours)']:
            items = df.loc[
                df['duration (hours)'] == duration,
                'item name(with num)'
            ].unique().tolist()
            
            # 只显示编号后3位
            short_items = [item[-3:] if len(item) >= 3 else item for item in items]
            hover_texts[duration] = ', '.join(short_items)
        
        fig = go.Figure(go.Pie(
            labels=duration_counts['Duration (hours)'],
            values=duration_counts['Frequency'],
            hole=0.4,
            hovertemplate=(
                '<b>时长:</b> %{label} 小时<br>'
                '<b>频次:</b> %{value}<br>'
                '<b>物品:</b> %{customdata}<extra></extra>'
            ),
            customdata=duration_counts['Duration (hours)'].map(hover_texts).tolist(),
            textinfo='label+percent',
            textposition='inside'
        ))
        
        fig.update_layout(
            title='借用时长分布（Top N物品）',
            height=500,
            template='plotly_white'
        )
        
        return fig
