"""
Top N 分析策略 - 用 px.bar 和 px.line 展示趋势，px.box 展示时长分布
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy
from config.settings import TIME_PERIODS


class TopNAnalysis(AnalysisStrategy):

    def analyze(
        self,
        category: Optional[str],
        mode: str = 'all',
        top_n: int = 5,
        period: str = 'Week',
        metric: str = 'Count',
        item_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        df = self.load_data(mode=mode, category=category,
                            start_date=start_date, end_date=end_date)

        if item_name:
            df = df[df['item name'] == item_name].copy()

        if df.empty:
            return {'success': False, 'message': '没有找到匹配的借用记录'}

        # 计算各物品的指标，确定 Top N
        dur_col = 'duration (hours)'
        if metric == 'Count':
            scores = df['item name(with num)'].value_counts()
        elif metric == 'Total Duration':
            scores = df.groupby('item name(with num)')[dur_col].sum().sort_values(ascending=False)
        else:  # Avg Duration
            scores = df.groupby('item name(with num)')[dur_col].mean().sort_values(ascending=False)

        top_items = scores.head(top_n).index.tolist()
        df_top = df[df['item name(with num)'].isin(top_items)].copy()

        # 时间分组
        freq = TIME_PERIODS[period]
        df_top['_period'] = df_top['Start'].dt.to_period(freq).dt.start_time

        # 构建时间线 pivot（用于折线图）
        pivot = (
            df_top.groupby(['_period', 'item name(with num)'])
            .size()
            .reset_index(name='count')
        )
        # 保持 Top N 顺序
        pivot['item name(with num)'] = pd.Categorical(
            pivot['item name(with num)'], categories=top_items, ordered=True
        )
        pivot = pivot.sort_values(['_period', 'item name(with num)'])

        return {
            'success': True,
            'df_top': df_top,
            'pivot': pivot,
            'top_items': top_items,
            'scores': scores.head(top_n),
            'top_n': top_n,
            'period': period,
            'metric': metric,
            'category': category or 'All',
            'date_range': {
                'start': pd.to_datetime(start_date) if start_date else df['Start'].min(),
                'end': pd.to_datetime(end_date) if end_date else df['Start'].max(),
            }
        }

    def visualize(self, result: dict):
        if not result['success']:
            return None, None, None

        df_top = result['df_top']
        pivot = result['pivot']
        scores = result['scores']
        top_items = result['top_items']
        metric = result['metric']
        period = result['period']
        category = result['category']
        top_n = result['top_n']

        # ── 图1：总量横向柱状图（排行榜）──
        bar_df = scores.reset_index()
        bar_df.columns = ['物品', '数值']
        bar_df['物品'] = pd.Categorical(bar_df['物品'], categories=top_items[::-1], ordered=True)
        bar_df = bar_df.sort_values('物品')

        label_map = {'Count': '借用次数', 'Total Duration': '总借用时长 (h)', 'Avg Duration': '平均借用时长 (h)'}
        fig_bar = px.bar(
            bar_df, x='数值', y='物品', orientation='h',
            color='数值',
            color_continuous_scale='Blues',
            text='数值',
            title=f'🏆 {category} — Top {top_n} ({label_map[metric]})',
            labels={'数值': label_map[metric], '物品': ''},
        )
        fig_bar.update_traces(texttemplate='%{text:.0f}', textposition='outside')
        fig_bar.update_layout(
            template='plotly_white',
            height=max(300, top_n * 50 + 120),
            coloraxis_showscale=False,
            margin=dict(l=20, r=60, t=60, b=40),
        )

        # ── 图2：时间趋势折线图 ──
        fig_line = px.line(
            pivot, x='_period', y='count',
            color='item name(with num)',
            markers=True,
            title=f'📈 借用趋势 — 按{period}',
            labels={'_period': '时间', 'count': '借用次数', 'item name(with num)': '物品'},
        )
        fig_line.update_layout(
            template='plotly_white',
            height=450,
            hovermode='x unified',
            xaxis=dict(rangeslider_visible=True),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(l=20, r=20, t=60, b=40),
        )

        # ── 图3：借用时长箱线图 ──
        dur_col = 'duration (hours)'
        df_dur = df_top[df_top[dur_col].notna() & (df_top[dur_col] > 0)].copy()
        fig_box = None
        if not df_dur.empty:
            df_dur['item name(with num)'] = pd.Categorical(
                df_dur['item name(with num)'], categories=top_items, ordered=True
            )
            fig_box = px.box(
                df_dur.sort_values('item name(with num)'),
                x='item name(with num)', y=dur_col,
                color='item name(with num)',
                title='📊 借用时长分布',
                labels={dur_col: '时长 (小时)', 'item name(with num)': ''},
                points='outliers',
            )
            fig_box.update_layout(
                template='plotly_white',
                height=400,
                showlegend=False,
                xaxis_tickangle=-20,
                margin=dict(l=20, r=20, t=60, b=80),
            )

        return fig_bar, fig_line, fig_box
