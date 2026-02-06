"""
Duration分析策略 - 分析单个物品的完整借用时间线（日粒度）
"""
import pandas as pd
import plotly.graph_objs as go
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy


class DurationAnalysis(AnalysisStrategy):
    """物品借用时间线分析（日粒度状态）"""
    
    def analyze(
        self,
        item_with_num: str,
        category: Optional[str],
        mode: str = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        分析单个物品的日粒度借用状态
        
        Args:
            item_with_num: 物品名称（带编号）
            category: 物品类别
            mode: 数据模式
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
        
        # 筛选指定物品
        df_item = df[df['item name(with num)'] == item_with_num].copy()
        
        if df_item.empty:
            return {
                'success': False,
                'message': f'未找到物品 "{item_with_num}" 的借用记录',
                'timeline': pd.DataFrame()
            }
        
        # 构建日粒度时间线
        timeline = self._build_daily_timeline(df_item)
        
        return {
            'success': True,
            'item_name': item_with_num,
            'timeline': timeline,
            'total_borrows': len(df_item),
            'date_range': {
                'start': timeline['date'].min(),
                'end': timeline['date'].max()
            }
        }
    
    def _build_daily_timeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建日粒度借用状态时间线
        
        Args:
            df: 物品的借用记录
            
        Returns:
            时间线DataFrame (date, status)
        """
        # 填充未归还记录的finished时间
        df['finished'] = df['finished'].fillna(pd.Timestamp.now())
        
        # 创建事件序列
        events = pd.DataFrame({
            'time': pd.concat([df['Start'], df['finished']]),
            'delta': [1] * len(df) + [-1] * len(df)
        }).sort_values('time').reset_index(drop=True)
        
        # 确定日期范围
        start_day = events['time'].min().normalize()
        end_day = events['time'].max().normalize()
        
        # 创建日期序列
        date_range = pd.date_range(start_day, end_day, freq='D')
        timeline = pd.DataFrame({'date': date_range})
        
        # 计算每一天的状态
        def get_status_on_day(day):
            """计算指定日期的借用状态（0或1）"""
            cutoff = day + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            cumsum = events.loc[events['time'] <= cutoff, 'delta'].sum()
            return int(cumsum > 0)
        
        timeline['status'] = timeline['date'].apply(get_status_on_day)
        
        return timeline
    
    def visualize(self, analysis_result: dict) -> go.Figure:
        """
        可视化日粒度借用时间线
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            Plotly图表对象
        """
        if not analysis_result['success']:
            return None
        
        timeline = analysis_result['timeline']
        item_name = analysis_result['item_name']
        
        fig = go.Figure()
        
        # 添加线条
        fig.add_trace(go.Scatter(
            x=timeline['date'],
            y=timeline['status'],
            mode='lines',
            line=dict(color='#6514F2', width=3),
            name='借用状态',
            fill='tozeroy',
            fillcolor='rgba(101, 20, 242, 0.2)',
            hovertemplate='日期: %{x}<br>状态: %{y}<extra></extra>'
        ))
        
        # 添加标记点
        fig.add_trace(go.Scatter(
            x=timeline['date'],
            y=timeline['status'],
            mode='markers',
            marker=dict(color='#6514F2', size=6),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # 布局设置
        fig.update_layout(
            title=f'物品借用时间线（日粒度）: {item_name}',
            xaxis_title='日期',
            yaxis_title='状态',
            yaxis=dict(
                tickvals=[0, 1],
                ticktext=['在库', '已借出'],
                range=[-0.2, 1.2],
                fixedrange=False
            ),
            xaxis_rangeslider_visible=True,
            hovermode='x unified',
            height=620,
            template='plotly_white'
        )
        
        # 美化网格
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
        
        return fig
