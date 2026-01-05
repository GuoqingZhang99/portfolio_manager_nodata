"""
高级图表组件库
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


class ChartBuilder:
    """图表构建器"""

    def __init__(self):
        """初始化图表构建器"""
        self.default_layout = {
            'font': {'family': 'Arial, sans-serif'},
            'paper_bgcolor': 'rgba(0,0,0,0)',
            'plot_bgcolor': 'rgba(0,0,0,0)',
        }

    def create_sunburst_chart(self, holdings, title='持仓结构旭日图'):
        """
        创建旭日图

        层级：账户 → 板块 → 个股
        """
        if holdings.empty:
            return self._empty_chart('暂无持仓数据')

        labels = ['总资产']
        parents = ['']
        values = [holdings['总投入'].sum()]
        colors = ['#636EFA']

        # 按账户分组
        if '账户' in holdings.columns:
            accounts = holdings.groupby('账户')['总投入'].sum()

            for account, value in accounts.items():
                labels.append(account)
                parents.append('总资产')
                values.append(value)
                colors.append('#EF553B' if '长期' in account else '#00CC96')

                # 该账户下的股票
                account_stocks = holdings[holdings['账户'] == account]
                for _, stock in account_stocks.iterrows():
                    labels.append(f"{stock['股票代码']}")
                    parents.append(account)
                    values.append(stock['总投入'])
                    colors.append('#AB63FA')
        else:
            # 没有账户列，直接显示股票
            for _, stock in holdings.iterrows():
                labels.append(stock['股票代码'])
                parents.append('总资产')
                values.append(stock['总投入'])
                colors.append('#EF553B')

        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(colors=colors),
            textinfo='label+percent entry',
            insidetextorientation='radial'
        ))

        fig.update_layout(
            title=title,
            width=600,
            height=600,
            **self.default_layout
        )

        return fig

    def create_sankey_diagram(self, cash_flows, title='现金流流向图'):
        """
        创建桑基图

        展示现金流流向
        """
        if not cash_flows or not cash_flows.get('经营活动现金流'):
            return self._empty_chart('暂无现金流数据')

        labels = ['期初现金', '经营活动', '投资活动', '融资活动', '期末现金']
        sources = []
        targets = []
        values = []
        colors = []

        # 经营活动
        operating = cash_flows.get('经营活动现金流', {}).get('小计', 0)
        if operating > 0:
            sources.append(1)  # 经营活动
            targets.append(4)  # 期末现金
            values.append(abs(operating))
            colors.append('rgba(0,200,0,0.5)')
        elif operating < 0:
            sources.append(0)  # 期初现金
            targets.append(1)  # 经营活动
            values.append(abs(operating))
            colors.append('rgba(200,0,0,0.5)')

        # 投资活动
        investing = cash_flows.get('投资活动现金流', {}).get('小计', 0)
        if investing > 0:
            sources.append(2)  # 投资活动
            targets.append(4)  # 期末现金
            values.append(abs(investing))
            colors.append('rgba(0,200,0,0.5)')
        elif investing < 0:
            sources.append(0)  # 期初现金
            targets.append(2)  # 投资活动
            values.append(abs(investing))
            colors.append('rgba(200,0,0,0.5)')

        # 融资活动
        financing = cash_flows.get('融资活动现金流', {}).get('小计', 0)
        if financing > 0:
            sources.append(3)  # 融资活动
            targets.append(4)  # 期末现金
            values.append(abs(financing))
            colors.append('rgba(0,200,0,0.5)')
        elif financing < 0:
            sources.append(0)  # 期初现金
            targets.append(3)  # 融资活动
            values.append(abs(financing))
            colors.append('rgba(200,0,0,0.5)')

        if not values:
            return self._empty_chart('暂无现金流数据')

        fig = go.Figure(go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=labels,
                color=['#636EFA', '#00CC96', '#EF553B', '#AB63FA', '#FFA15A']
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=colors
            )
        ))

        fig.update_layout(
            title=title,
            width=800,
            height=500,
            **self.default_layout
        )

        return fig

    def create_waterfall_chart(self, attribution, title='收益归因瀑布图'):
        """
        创建瀑布图

        展示收益分解
        """
        if not attribution or 'total_return' not in attribution:
            return self._empty_chart('暂无归因数据')

        categories = ['基准收益', 'Beta贡献', '选股Alpha', '择时Alpha', '策略Alpha', '总收益']
        values = [
            attribution.get('benchmark_return', 0) * 100,
            attribution.get('beta_contribution', 0) * 100,
            attribution.get('selection_alpha', 0) * 100,
            attribution.get('timing_alpha', 0) * 100,
            attribution.get('strategy_alpha', 0) * 100,
            0  # 总收益作为汇总
        ]

        measures = ['relative', 'relative', 'relative', 'relative', 'relative', 'total']

        fig = go.Figure(go.Waterfall(
            name="收益归因",
            orientation="v",
            measure=measures,
            x=categories,
            y=values,
            textposition="outside",
            text=[f"{v:.2f}%" for v in values[:-1]] + [f"{attribution.get('total_return', 0)*100:.2f}%"],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "#00CC96"}},
            decreasing={"marker": {"color": "#EF553B"}},
            totals={"marker": {"color": "#636EFA"}}
        ))

        fig.update_layout(
            title=title,
            yaxis_title="收益率 (%)",
            width=800,
            height=500,
            **self.default_layout
        )

        return fig

    def create_correlation_heatmap(self, corr_matrix, title='相关性热力图'):
        """
        创建相关性热力图

        X/Y轴：股票代码
        颜色：相关系数（-1到1）
        """
        if corr_matrix is None or corr_matrix.empty:
            return self._empty_chart('暂无相关性数据')

        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns.tolist(),
            y=corr_matrix.index.tolist(),
            colorscale='RdBu_r',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=np.round(corr_matrix.values, 2),
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False,
            colorbar=dict(title='相关系数')
        ))

        fig.update_layout(
            title=title,
            width=700,
            height=600,
            xaxis_title='',
            yaxis_title='',
            **self.default_layout
        )

        return fig

    def create_bubble_chart(self, holdings, risk_return_data, title='风险收益气泡图'):
        """
        创建气泡图

        X轴：波动率（风险）
        Y轴：收益率
        气泡大小：持仓金额
        """
        if holdings.empty or not risk_return_data:
            return self._empty_chart('暂无数据')

        symbols = []
        x_vals = []  # 风险（波动率）
        y_vals = []  # 收益
        sizes = []   # 持仓金额

        for _, holding in holdings.iterrows():
            symbol = holding['股票代码']
            if symbol in risk_return_data:
                symbols.append(symbol)
                x_vals.append(risk_return_data[symbol].get('volatility', 0) * 100)
                y_vals.append(risk_return_data[symbol].get('return', 0) * 100)
                sizes.append(holding['总投入'])

        if not symbols:
            return self._empty_chart('暂无数据')

        # 标准化气泡大小
        max_size = max(sizes) if sizes else 1
        normalized_sizes = [s / max_size * 50 + 10 for s in sizes]

        fig = go.Figure(data=go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+text',
            marker=dict(
                size=normalized_sizes,
                color=y_vals,
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title='收益率%')
            ),
            text=symbols,
            textposition='top center',
            hovertemplate='<b>%{text}</b><br>风险: %{x:.1f}%<br>收益: %{y:.1f}%<extra></extra>'
        ))

        fig.update_layout(
            title=title,
            xaxis_title='波动率 (%)',
            yaxis_title='收益率 (%)',
            width=800,
            height=600,
            **self.default_layout
        )

        return fig

    def create_area_chart(self, position_history, title='仓位变化趋势'):
        """
        创建面积图

        堆叠展示各股票仓位变化
        """
        if position_history.empty:
            return self._empty_chart('暂无仓位历史数据')

        fig = go.Figure()

        # 假设position_history有date列和各股票列
        if 'date' not in position_history.columns:
            return self._empty_chart('数据格式不正确')

        stock_columns = [col for col in position_history.columns if col != 'date']

        for col in stock_columns:
            fig.add_trace(go.Scatter(
                x=position_history['date'],
                y=position_history[col],
                mode='lines',
                stackgroup='one',
                name=col,
                hovertemplate='%{y:,.0f}<extra>%{fullData.name}</extra>'
            ))

        fig.update_layout(
            title=title,
            xaxis_title='日期',
            yaxis_title='持仓金额 ($)',
            width=900,
            height=500,
            hovermode='x unified',
            **self.default_layout
        )

        return fig

    def create_pie_chart(self, data, labels, values, title='饼图'):
        """创建饼图"""
        fig = go.Figure(data=go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=px.colors.qualitative.Set3)
        ))

        fig.update_layout(
            title=title,
            width=500,
            height=500,
            **self.default_layout
        )

        return fig

    def create_bar_chart(self, x, y, title='柱状图', orientation='v', color=None):
        """创建柱状图"""
        if orientation == 'v':
            fig = go.Figure(data=go.Bar(
                x=x,
                y=y,
                marker_color=color or '#636EFA',
                text=[f'{v:,.0f}' for v in y],
                textposition='outside'
            ))
            fig.update_layout(yaxis_title='金额 ($)')
        else:
            fig = go.Figure(data=go.Bar(
                x=y,
                y=x,
                orientation='h',
                marker_color=color or '#636EFA',
                text=[f'{v:,.0f}' for v in y],
                textposition='outside'
            ))
            fig.update_layout(xaxis_title='金额 ($)')

        fig.update_layout(
            title=title,
            width=700,
            height=400,
            **self.default_layout
        )

        return fig

    def create_line_chart(self, data, x_col, y_cols, title='折线图'):
        """创建折线图"""
        fig = go.Figure()

        if isinstance(y_cols, str):
            y_cols = [y_cols]

        colors = px.colors.qualitative.Set1

        for i, col in enumerate(y_cols):
            fig.add_trace(go.Scatter(
                x=data[x_col],
                y=data[col],
                mode='lines+markers',
                name=col,
                line=dict(color=colors[i % len(colors)])
            ))

        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            width=800,
            height=400,
            hovermode='x unified',
            **self.default_layout
        )

        return fig

    def create_gauge_chart(self, value, title='仪表盘', max_value=100):
        """创建仪表盘图"""
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': max_value / 2},
            gauge={
                'axis': {'range': [None, max_value]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, max_value * 0.3], 'color': 'lightgreen'},
                    {'range': [max_value * 0.3, max_value * 0.7], 'color': 'yellow'},
                    {'range': [max_value * 0.7, max_value], 'color': 'salmon'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': max_value * 0.9
                }
            }
        ))

        fig.update_layout(
            width=400,
            height=300,
            **self.default_layout
        )

        return fig

    def create_treemap(self, holdings, title='持仓树图'):
        """创建树图"""
        if holdings.empty:
            return self._empty_chart('暂无持仓数据')

        labels = []
        parents = []
        values = []

        # 根节点
        labels.append('投资组合')
        parents.append('')
        values.append(0)

        # 各股票
        for _, row in holdings.iterrows():
            labels.append(row['股票代码'])
            parents.append('投资组合')
            values.append(row['总投入'])

        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            textinfo='label+value+percent entry',
            marker=dict(colorscale='Blues'),
        ))

        fig.update_layout(
            title=title,
            width=700,
            height=500,
            **self.default_layout
        )

        return fig

    def _empty_chart(self, message='暂无数据'):
        """创建空白图表"""
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            text=message,
            showarrow=False,
            font=dict(size=16, color='gray'),
            xref='paper', yref='paper'
        )
        fig.update_layout(
            width=400,
            height=300,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            **self.default_layout
        )
        return fig
