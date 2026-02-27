"""
Top N analysis strategy.
"""
import pandas as pd
import plotly.graph_objs as go
from typing import Optional

from analysis.strategies.base_strategy import AnalysisStrategy
from config.settings import TIME_PERIODS


class TopNAnalysis(AnalysisStrategy):
    """Top N analysis for high-frequency items."""

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
        """
        Analyze Top N items.

        Args:
            category: Item category (optional).
            mode: Data mode.
            top_n: Top N size.
            period: Time period ('Day', 'Week', 'Month', 'Year').
            metric: Sort metric ('Count', 'Total Duration', 'Avg Duration').
            item_name: Optional item name (without number) to filter.
            start_date: Start date.
            end_date: End date.

        Returns:
            Analysis result dict.
        """
        # Load data
        df = self.load_data(
            mode=mode,
            category=category,
            start_date=start_date,
            end_date=end_date
        )

        # Filter by item name if provided
        if item_name:
            df = df[df['item name'] == item_name].copy()

        if df.empty:
            return {
                'success': False,
                'message': 'No matching borrow records found',
                'pivot': pd.DataFrame(),
                'detail_data': pd.DataFrame()
            }

        # Compute Top N by selected metric
        duration_col = 'duration (hours)'
        if metric == 'Count':
            metric_series = df['item name(with num)'].value_counts()
        else:
            if duration_col not in df.columns:
                return {
                    'success': False,
                    'message': 'Duration column missing; cannot sort by duration',
                    'pivot': pd.DataFrame(),
                    'detail_data': pd.DataFrame()
                }
            df_duration = df[df[duration_col].notna()].copy()
            if df_duration.empty:
                return {
                    'success': False,
                    'message': 'No non-empty duration values; cannot sort by duration',
                    'pivot': pd.DataFrame(),
                    'detail_data': pd.DataFrame()
                }

            if metric == 'Total Duration':
                metric_series = (
                    df_duration.groupby('item name(with num)')[duration_col]
                    .sum()
                    .sort_values(ascending=False)
                )
            else:  # Avg Duration
                metric_series = (
                    df_duration.groupby('item name(with num)')[duration_col]
                    .mean()
                    .sort_values(ascending=False)
                )

        top_items = metric_series.head(top_n).index
        df_top = df[df['item name(with num)'].isin(top_items)].copy()

        # Create time series pivot
        pivot = self._create_time_series(df_top, period)

        # Keep Top N order
        pivot = pivot[top_items.intersection(pivot.columns)]

        category_label = category if category else 'All Categories'
        
        # 确定日期范围：优先使用用户输入，否则使用数据实际范围
        if start_date:
            range_start = pd.to_datetime(start_date)
        else:
            range_start = df['Start'].min()
        
        if end_date:
            range_end = pd.to_datetime(end_date)
        else:
            range_end = df['Start'].max()
        
        return {
            'success': True,
            'pivot': pivot,
            'detail_data': df_top,
            'top_n': top_n,
            'period': period,
            'metric': metric,
            'category': category_label,
            'date_range': {
                'start': range_start,
                'end': range_end
            }
        }

    def _create_time_series(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """Create time series pivot table."""
        df['period'] = df['Start'].dt.to_period(TIME_PERIODS[period]).dt.start_time
        pivot = df.groupby(['period', 'item name(with num)']).size().unstack(fill_value=0)
        return pivot

    def visualize(self, analysis_result: dict) -> tuple:
        """Visualize Top N results."""
        if not analysis_result['success']:
            return None, None

        pivot = analysis_result['pivot']
        df_detail = analysis_result['detail_data']
        category = analysis_result['category']
        top_n = analysis_result['top_n']
        metric = analysis_result.get('metric', 'Count')

        fig_timeline = self._create_timeline_chart(pivot, category, top_n, metric)
        fig_pie = self._create_duration_pie_chart(df_detail)

        return fig_timeline, fig_pie

    def _create_timeline_chart(self, pivot: pd.DataFrame, category: str, top_n: int, metric: str) -> go.Figure:
        """Create timeline chart."""
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
            title=f'{category} - Top {top_n} ({metric}) Timeline',
            xaxis_title='Time',
            yaxis_title='Borrow Count',
            legend_title='Item Number',
            xaxis_rangeslider_visible=True,
            height=560,
            template='plotly_white',
            hovermode='x unified'
        )

        return fig

    def _create_duration_pie_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create duration distribution pie chart."""
        if 'duration (hours)' not in df.columns or df['duration (hours)'].isna().all():
            return None

        duration_counts = df['duration (hours)'].dropna().value_counts().reset_index()
        duration_counts.columns = ['Duration (hours)', 'Frequency']

        hover_texts = {}
        for duration in duration_counts['Duration (hours)']:
            items = df.loc[
                df['duration (hours)'] == duration,
                'item name(with num)'
            ].unique().tolist()

            short_items = [item[-3:] if len(item) >= 3 else item for item in items]
            hover_texts[duration] = ', '.join(short_items)

        fig = go.Figure(go.Pie(
            labels=duration_counts['Duration (hours)'],
            values=duration_counts['Frequency'],
            hole=0.4,
            hovertemplate=(
                '<b>Duration:</b> %{label} hours<br>'
                '<b>Frequency:</b> %{value}<br>'
                '<b>Items:</b> %{customdata}<extra></extra>'
            ),
            customdata=duration_counts['Duration (hours)'].map(hover_texts).tolist(),
            textinfo='label+percent',
            textposition='inside'
        ))

        fig.update_layout(
            title='Duration Distribution (Top N Items)',
            height=500,
            template='plotly_white'
        )

        return fig

