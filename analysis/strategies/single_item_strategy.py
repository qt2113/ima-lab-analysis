"""
单品分析策略 - 分析单个物品的借用时间线
"""
import pandas as pd
import plotly.graph_objs as go
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy


class SingleItemAnalysis(AnalysisStrategy):
    """单品借用时间线分析"""
    
    def analyze(
        self,
        item_with_num: str,
        category: Optional[str],
        mode: str = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        分析单个物品的借用状态
        
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
        
        # 构建时间线（使用事件模型）
        timeline = self._build_timeline(df_item)
        
        # 确定日期范围：优先使用用户输入，否则使用数据实际范围
        if start_date:
            range_start = pd.to_datetime(start_date)
        else:
            range_start = df_item['Start'].min()
        
        if end_date:
            range_end = pd.to_datetime(end_date)
        else:
            range_end = df_item['finished'].max()
        
        return {
            'success': True,
            'item_name': item_with_num,
            'timeline': timeline,
            'total_borrows': len(df_item),
            'date_range': {
                'start': range_start,
                'end': range_end
            }
        }
    
    def _build_timeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建借用状态时间线
        
        Args:
            df: 物品的借用记录
            
        Returns:
            时间线DataFrame (date, status)
        """
        # 创建事件序列（借出+1，归还-1）
        starts = df['Start']
        ends = df['finished'].fillna(pd.Timestamp.now())
        
        timeline = pd.DataFrame({
            'date': pd.concat([starts, ends]),
            'delta': [1] * len(starts) + [-1] * len(ends)
        }).sort_values('date').reset_index(drop=True)
        
        # 计算累计状态
        timeline['status'] = timeline['delta'].cumsum()
        
        # 转换为二进制状态（0=可用，1=借出）
        timeline['status'] = (timeline['status'] > 0).astype(int)
        
        return timeline
    
    def visualize(self, analysis_result: dict) -> go.Figure:
        """
        可视化单品时间线
        
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
            hovertemplate='时间: %{x}<br>状态: %{y}<extra></extra>'
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
            title=f'物品借用时间线: {item_name}',
            xaxis_title='日期',
            yaxis_title='状态',
            yaxis=dict(
                tickvals=[0, 1],
                ticktext=['在库', '已借出'],
                range=[-0.1, 1.1],
                fixedrange=False
            ),
            xaxis_rangeslider_visible=True,
            hovermode='x unified',
            height=600,
            template='plotly_white'
        )
        
        return fig
