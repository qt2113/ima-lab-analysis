"""
时间线分析策略 - 日历热力图展示使用强度
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy


class DurationAnalysis(AnalysisStrategy):

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
        now = pd.Timestamp.now()
        df_item['_end'] = df_item['finished'].fillna(now)

        # 构建日粒度数据：每天借出了多少小时
        range_start = pd.to_datetime(start_date) if start_date else df_item['Start'].min().normalize()
        range_end = pd.to_datetime(end_date) if end_date else now.normalize()

        daily = self._build_daily_hours(df_item, range_start, range_end)

        total_days = len(daily)
        borrowed_days = (daily['hours'] > 0).sum()
        total_borrow_hours = daily['hours'].sum()

        return {
            'success': True,
            'item_name': item_with_num,
            'df': df_item,
            'daily': daily,
            'total_borrows': len(df_item),
            'borrowed_days': int(borrowed_days),
            'total_days': total_days,
            'total_borrow_hours': float(total_borrow_hours),
            'utilization': borrowed_days / total_days if total_days > 0 else 0,
            'date_range': {'start': range_start, 'end': range_end}
        }

    def _build_daily_hours(self, df: pd.DataFrame,
                            range_start: pd.Timestamp,
                            range_end: pd.Timestamp) -> pd.DataFrame:
        """计算每天的借用小时数"""
        all_days = pd.date_range(range_start.normalize(), range_end.normalize(), freq='D')
        hours = pd.Series(0.0, index=all_days)

        for _, row in df.iterrows():
            start = max(row['Start'], range_start)
            end = min(row['_end'], range_end + pd.Timedelta(days=1))
            if start >= end:
                continue
            # 按天分配小时数
            day = start.normalize()
            while day <= end.normalize():
                day_start = max(start, day)
                day_end = min(end, day + pd.Timedelta(days=1))
                h = (day_end - day_start).total_seconds() / 3600
                if day in hours.index:
                    hours[day] += h
                day += pd.Timedelta(days=1)

        daily = pd.DataFrame({'date': all_days, 'hours': hours.values})
        daily['hours'] = daily['hours'].clip(upper=24).round(1)
        daily['week'] = daily['date'].dt.isocalendar().week.astype(int)
        daily['weekday'] = daily['date'].dt.weekday   # 0=Mon
        daily['year_week'] = daily['date'].dt.strftime('%Y-W%U')
        daily['month'] = daily['date'].dt.strftime('%Y-%m')
        return daily

    def visualize(self, result: dict):
        if not result['success']:
            return None

        daily = result['daily'].copy()
        item_name = result['item_name']

        # ── 图1：日历热力图 ──
        # 用 scatter 模拟 GitHub contribution 风格
        daily['weekday_name'] = daily['date'].dt.strftime('%a')
        daily['date_str'] = daily['date'].dt.strftime('%Y-%m-%d')

        # 按周分组，x=周，y=星期
        WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        daily['dow'] = daily['date'].dt.weekday  # 0=Mon
        daily['week_num'] = (
            (daily['date'] - daily['date'].min()).dt.days // 7
        )

        fig_cal = go.Figure(go.Heatmap(
            x=daily['week_num'],
            y=daily['dow'],
            z=daily['hours'],
            text=daily['date_str'] + '<br>' + daily['hours'].astype(str) + 'h',
            hovertemplate='%{text}<extra></extra>',
            colorscale=[
                [0,    '#EBEDF0'],
                [0.01, '#C6E9A7'],
                [0.25, '#7BC96F'],
                [0.5,  '#239A3B'],
                [1.0,  '#196127'],
            ],
            zmin=0,
            zmax=24,
            xgap=2,
            ygap=2,
            showscale=True,
            colorbar=dict(title='小时', thickness=12, len=0.6),
        ))

        # 月份标签：取每月第一天所在的 week_num
        month_ticks = (
            daily.groupby('month')['week_num'].min()
            .reset_index()
        )

        fig_cal.update_layout(
            title=f'📅 {item_name} — 日历借用热力图',
            xaxis=dict(
                tickvals=month_ticks['week_num'].tolist(),
                ticktext=month_ticks['month'].tolist(),
                showgrid=False,
                zeroline=False,
            ),
            yaxis=dict(
                tickvals=list(range(7)),
                ticktext=WEEKDAYS,
                showgrid=False,
                autorange='reversed',
            ),
            template='plotly_white',
            height=250,
            margin=dict(l=50, r=20, t=60, b=40),
        )

        # ── 图2：月度柱状图 ──
        monthly = (
            daily.groupby('month')['hours']
            .sum()
            .reset_index()
        )
        monthly.columns = ['月份', '借用时长(h)']

        fig_bar = px.bar(
            monthly, x='月份', y='借用时长(h)',
            title='📊 每月借用时长',
            color='借用时长(h)',
            color_continuous_scale='Greens',
            text='借用时长(h)',
        )
        fig_bar.update_traces(texttemplate='%{text:.0f}h', textposition='outside')
        fig_bar.update_layout(
            template='plotly_white',
            height=350,
            coloraxis_showscale=False,
            xaxis_tickangle=-30,
            margin=dict(l=20, r=20, t=60, b=60),
        )

        return fig_cal, fig_bar
