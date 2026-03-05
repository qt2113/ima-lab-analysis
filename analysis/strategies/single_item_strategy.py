"""
单品分析策略 - Gantt图展示每次借用的时间段
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy


class SingleItemAnalysis(AnalysisStrategy):

    def analyze(
        self,
        item_with_num: str,
        category: Optional[str],
        mode: str = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        df = self.load_data(mode=mode, category=category,
                            start_date=start_date, end_date=end_date)

        df_item = df[df['item name(with num)'] == item_with_num].copy()

        if df_item.empty:
            return {'success': False,
                    'message': f'未找到物品 "{item_with_num}" 的借用记录'}

        df_item = df_item.sort_values('Start').reset_index(drop=True)

        # 统计
        total = len(df_item)
        avg_hours = df_item['duration (hours)'].dropna()
        avg_h = float(avg_hours.mean()) if not avg_hours.empty else 0
        currently_out = df_item['finished'].isna().any()

        return {
            'success': True,
            'item_name': item_with_num,
            'df': df_item,
            'total_borrows': total,
            'avg_duration_hours': avg_h,
            'currently_checked_out': currently_out,
            'date_range': {
                'start': pd.to_datetime(start_date) if start_date else df_item['Start'].min(),
                'end': pd.to_datetime(end_date) if end_date else df_item['finished'].max()
            }
        }

    def visualize(self, result: dict):
        if not result['success']:
            return None

        df = result['df'].copy()
        now = pd.Timestamp.now()

        # 未归还的用当前时间作为结束，标注颜色
        df['_end'] = df['finished'].fillna(now)
        df['_status'] = df['finished'].isna().map({True: '借出中', False: '已归还'})
        df['_duration_str'] = df['duration (hours)'].apply(
            lambda x: f"{int(x)}h" if pd.notna(x) else "借出中"
        )
        df['_borrow_num'] = [f"第{i+1}次" for i in range(len(df))]

        # Gantt 图：每行一次借用
        fig = px.timeline(
            df,
            x_start='Start',
            x_end='_end',
            y='_borrow_num',
            color='_status',
            color_discrete_map={'已归还': '#4F8EF7', '借出中': '#F7634F'},
            hover_data={
                'Start': '|%Y-%m-%d %H:%M',
                '_end': '|%Y-%m-%d %H:%M',
                '_duration_str': True,
                '_borrow_num': False,
                '_status': False,
            },
            labels={
                'Start': '借出时间',
                '_end': '归还时间',
                '_duration_str': '时长',
                '_borrow_num': '',
                '_status': '状态'
            },
            title=f'📦 {result["item_name"]} — 借用记录',
        )

        fig.update_yaxes(autorange='reversed', title='')
        fig.update_xaxes(title='日期', rangeslider_visible=True)
        fig.update_layout(
            height=max(300, min(60 * len(df) + 120, 700)),
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(l=20, r=20, t=60, b=40),
        )

        return fig
