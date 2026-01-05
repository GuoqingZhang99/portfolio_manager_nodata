"""
账户总览Dashboard
"""

import streamlit as st
import plotly.graph_objects as go


def render(components, account_filter):
    """渲染账户总览页面"""
    calc = components['calc']
    chart_builder = components['chart_builder']
    db = components['db']

    # 顶部：标题、市场状态和刷新按钮
    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        st.title("账户总览Dashboard")

    with col2:
        # 显示市场状态和价格更新时间
        try:
            from utils.market_hours import get_market_status
            from utils.price_sources import get_price_manager
            import pytz
            from datetime import datetime

            market_status = get_market_status()
            price_manager = get_price_manager()
            last_update = price_manager.get_last_update_time()

            # 市场状态
            if market_status['is_open']:
                st.success(f"🟢 {market_status['status']}")
            else:
                st.info(f"🔴 {market_status['status']}")

            # 价格更新时间
            if last_update:
                # 转换为本地时间
                local_time = last_update.astimezone(pytz.timezone('Asia/Shanghai'))
                time_str = local_time.strftime('%H:%M:%S')
                st.caption(f"价格更新: {time_str}")
            else:
                st.caption("价格未更新")

        except Exception as e:
            st.warning(f"无法获取市场状态: {e}")

    with col3:
        # 刷新价格按钮
        if st.button("🔄 刷新价格", key="refresh_prices_top"):
            with st.spinner("正在刷新价格..."):
                try:
                    from utils.data_fetcher import batch_get_prices

                    # 获取所有持仓股票
                    stocks = calc.calculate_stock_summary()
                    if not stocks.empty:
                        symbols = stocks['股票代码'].unique().tolist()
                        # 强制刷新价格
                        batch_get_prices(symbols, force_refresh=True)
                        st.success("价格刷新成功！")
                        st.rerun()
                    else:
                        st.info("暂无持仓股票")
                except Exception as e:
                    st.error(f"刷新失败: {e}")

    st.divider()

    # 确定要显示的账户
    if account_filter == '全部':
        accounts = ['长期账户', '波段账户']
    else:
        accounts = [account_filter]

    for account in accounts:
        st.header(f"{account}")

        # 获取账户数据
        overview = calc.calculate_account_overview(account)

        if not overview:
            st.warning(f"{account} 暂无数据")
            continue

        # 关键指标卡片
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总资金", f"${overview['总资金']:,.0f}")

        with col2:
            st.metric(
                "已投资",
                f"${overview['已投入股票']:,.0f}",
                f"{overview['股票仓位占比%']:.1f}%"
            )

        with col3:
            st.metric("可用现金", f"${overview['可用现金']:,.0f}")

        with col4:
            # 显示总盈亏和盈亏比
            pnl = overview['总盈亏']
            pnl_ratio = overview['总盈亏比%']
            pnl_color = "normal" if pnl >= 0 else "inverse"
            st.metric(
                "账户总盈亏",
                f"${abs(pnl):,.0f}" if pnl >= 0 else f"-${abs(pnl):,.0f}",
                f"{pnl_ratio:+.2f}%",
                delta_color=pnl_color
            )

        # 第二行指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("期权锁定", f"${overview['期权锁定现金']:,.0f}")

        with col2:
            st.metric("期权权利金收入", f"${overview['期权权利金收入']:,.0f}")

        with col3:
            st.metric("持股数量", f"{overview['持股数量']}")

        with col4:
            st.metric("期权持仓", f"{overview['期权持仓数']}")

        # 图表区域
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("资产配置")

            # 获取各股票持仓明细
            stocks = calc.calculate_stock_summary(account=account)

            labels = []
            values = []
            colors = []

            # 为每只股票生成颜色
            stock_colors = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
                          '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52']

            # 添加每只股票
            if not stocks.empty:
                for idx, (_, stock) in enumerate(stocks.iterrows()):
                    labels.append(stock['股票代码'])
                    values.append(stock['总投入'])
                    colors.append(stock_colors[idx % len(stock_colors)])

            # 添加期权锁定和可用现金
            if overview['期权锁定现金'] > 0:
                labels.append('期权锁定')
                values.append(overview['期权锁定现金'])
                colors.append('#FFCC00')

            if overview['可用现金'] > 0:
                labels.append('可用现金')
                values.append(overview['可用现金'])
                colors.append('#90EE90')

            # 创建饼图
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                textinfo='label+percent',
                marker=dict(colors=colors)
            )])

            fig.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=True,
                legend=dict(
                    orientation="v",
                    yanchor="middle",
                    y=0.5,
                    xanchor="left",
                    x=1.05
                )
            )

            st.plotly_chart(fig, width='stretch')

        with col2:
            st.subheader("持仓分布")

            stocks = calc.calculate_stock_summary(account=account)

            if not stocks.empty:
                fig = go.Figure(data=[go.Bar(
                    x=stocks['股票代码'],
                    y=stocks['总投入'],
                    marker_color='#636EFA',
                    text=[f"${v:,.0f}" for v in stocks['总投入']],
                    textposition='outside'
                )])

                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    yaxis_title='投资金额 ($)'
                )

                st.plotly_chart(fig, width='stretch')
            else:
                st.info("暂无股票持仓")

        # 持仓明细表
        st.subheader("股票持仓明细")
        stocks = calc.calculate_stock_summary(account=account)

        if not stocks.empty:
            # 获取当前价格和计算盈亏
            from utils.data_fetcher import batch_get_prices
            import pandas as pd

            symbols = stocks['股票代码'].unique().tolist()
            current_prices = batch_get_prices(symbols)

            # 添加当前价格和盈亏
            stocks['当前价格'] = stocks['股票代码'].apply(
                lambda x: current_prices.get(x) if current_prices else None
            )
            stocks['当前市值'] = stocks.apply(
                lambda x: x['当前价格'] * x['当前股数'] if x['当前价格'] else None,
                axis=1
            )
            stocks['盈亏金额'] = stocks.apply(
                lambda x: x['当前市值'] - x['总投入'] if x['当前市值'] else None,
                axis=1
            )
            stocks['盈亏%'] = stocks.apply(
                lambda x: (x['盈亏金额'] / x['总投入'] * 100) if x['总投入'] and x['盈亏金额'] is not None else None,
                axis=1
            )

            # 不格式化，使用column_config来控制显示
            display_df = stocks.copy()

            # 配置列显示格式（使用NumberColumn保证正确排序）
            column_config = {
                '股票代码': st.column_config.TextColumn('股票', width=60),
                '当前股数': st.column_config.NumberColumn('股数', width=55, format="%d"),
                '平均成本': st.column_config.NumberColumn('成本', width=70, format="$%.2f"),
                '当前价格': st.column_config.NumberColumn('现价', width=70, format="$%.2f"),
                '盈亏金额': st.column_config.NumberColumn('盈亏$', width=90, format="$%.0f"),
                '盈亏%': st.column_config.NumberColumn('盈亏%', width=70, format="%.2f%%"),
                '总投入': st.column_config.NumberColumn('投入$', width=90, format="$%.0f"),
                '当前市值': st.column_config.NumberColumn('市值$', width=90, format="$%.0f"),
                '可用股数': st.column_config.NumberColumn('可用', width=55, format="%d"),
                '锁定股数': st.column_config.NumberColumn('锁定', width=55, format="%d"),
            }

            st.dataframe(
                display_df[['股票代码', '当前股数', '平均成本', '当前价格', '盈亏金额', '盈亏%', '总投入', '当前市值', '可用股数', '锁定股数']],
                column_config=column_config,
                hide_index=True
            )
        else:
            st.info("暂无股票持仓")

        # 期权持仓
        st.subheader("期权持仓")
        options = calc.calculate_options_summary(account=account)

        if not options.empty:
            open_options = options[options['status'] == '持仓中']

            if not open_options.empty:
                display_cols = [
                    'stock_symbol', 'option_type', 'strike_price',
                    'expiration_date', 'contracts', '总权利金', '剩余天数'
                ]

                display_df = open_options[display_cols].copy()
                display_df.columns = ['股票', '类型', '行权价', '到期日', '合约数', '权利金', '剩余天数']
                display_df['行权价'] = display_df['行权价'].apply(lambda x: f"${x:.2f}")
                display_df['权利金'] = display_df['权利金'].apply(lambda x: f"${x:.2f}")

                st.dataframe(display_df, width='stretch', hide_index=True)
            else:
                st.info("暂无期权持仓")
        else:
            st.info("暂无期权持仓")

        st.divider()

    # 刷新按钮
    if st.button("刷新数据"):
        st.rerun()
