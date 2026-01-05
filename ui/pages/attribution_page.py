"""
业绩归因分析页面
"""

import streamlit as st
from datetime import datetime, timedelta
from utils.constants import ACCOUNT_NAMES


def render(components):
    """渲染业绩归因页面"""
    st.title("业绩归因分析")

    attribution = components['attribution']
    chart_builder = components['chart_builder']

    tab1, tab2 = st.tabs(["运行归因", "历史分析"])

    with tab1:
        render_run_attribution(attribution, chart_builder)

    with tab2:
        render_attribution_history(attribution)


def render_run_attribution(attribution, chart_builder):
    """渲染运行归因分析"""
    st.subheader("运行业绩归因分析")

    col1, col2, col3 = st.columns(3)

    with col1:
        account = st.selectbox("账户", ACCOUNT_NAMES, key="attr_account")

    with col2:
        period = st.selectbox(
            "分析周期",
            ["最近30天", "最近90天", "最近180天", "本年至今", "自定义"]
        )

    with col3:
        benchmark = st.text_input("基准指数", value="SPY")

    # 确定日期范围
    end_date = datetime.now().date()

    if period == "最近30天":
        start_date = end_date - timedelta(days=30)
    elif period == "最近90天":
        start_date = end_date - timedelta(days=90)
    elif period == "最近180天":
        start_date = end_date - timedelta(days=180)
    elif period == "本年至今":
        start_date = end_date.replace(month=1, day=1)
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", end_date - timedelta(days=90))
        with col2:
            end_date = st.date_input("结束日期", end_date)

    if st.button("运行归因分析", type="primary", width='stretch'):
        with st.spinner("正在分析..."):
            result = attribution.attribute_returns(
                account=account,
                start_date=str(start_date),
                end_date=str(end_date),
                benchmark=benchmark
            )

        if result.get('error'):
            st.error(result['error'])
            return

        # 显示结果
        st.markdown("---")
        st.subheader("归因分析结果")

        # 主要指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_ret = result.get('total_return', 0) * 100
            st.metric("组合收益", f"{total_ret:.2f}%")

        with col2:
            bench_ret = result.get('benchmark_return', 0) * 100
            st.metric("基准收益", f"{bench_ret:.2f}%")

        with col3:
            excess = result.get('excess_return', 0) * 100
            st.metric("超额收益", f"{excess:.2f}%")

        with col4:
            beta = result.get('portfolio_beta', 1)
            st.metric("组合Beta", f"{beta:.2f}")

        # 收益分解
        st.markdown("### 收益分解")

        col1, col2 = st.columns(2)

        with col1:
            beta_contrib = result.get('beta_contribution', 0) * 100
            st.metric("Beta贡献", f"{beta_contrib:.2f}%")

        with col2:
            alpha = result.get('total_alpha', 0) * 100
            st.metric("总Alpha", f"{alpha:.2f}%")

        # Alpha细分
        st.markdown("### Alpha细分")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("选股Alpha", f"{result.get('selection_alpha', 0) * 100:.2f}%")

        with col2:
            st.metric("择时Alpha", f"{result.get('timing_alpha', 0) * 100:.2f}%")

        with col3:
            st.metric("策略Alpha", f"{result.get('strategy_alpha', 0) * 100:.2f}%")

        with col4:
            st.metric("配置Alpha", f"{result.get('allocation_alpha', 0) * 100:.2f}%")

        # 瀑布图
        st.markdown("### 收益归因瀑布图")

        fig = chart_builder.create_waterfall_chart(result)
        st.plotly_chart(fig, width='stretch')

        # 各股票贡献
        st.markdown("### 各股票贡献度")

        stock_contrib = attribution.get_stock_contribution(
            account=account,
            start_date=str(start_date),
            end_date=str(end_date)
        )

        if not stock_contrib.empty:
            display_df = stock_contrib.copy()
            display_df['cost_basis'] = display_df['cost_basis'].apply(lambda x: f"${x:,.0f}")
            display_df['return'] = display_df['return'].apply(lambda x: f"{x*100:.2f}%")
            display_df['contribution'] = display_df['contribution'].apply(lambda x: f"${x:,.0f}")
            display_df['contribution_pct'] = display_df['contribution_pct'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                display_df,
                column_config={
                    'stock_symbol': '股票',
                    'cost_basis': '投资金额',
                    'return': '收益率',
                    'contribution': '贡献金额',
                    'contribution_pct': '贡献占比'
                },
                width='stretch',
                hide_index=True
            )
        else:
            st.info("暂无股票贡献数据")


def render_attribution_history(attribution):
    """渲染历史分析"""
    st.subheader("历史归因分析")

    history = attribution.get_attribution_history()

    if history.empty:
        st.info("暂无历史归因分析记录")
        return

    # 筛选
    account_filter = st.selectbox(
        "账户筛选",
        ["全部"] + history['account_name'].unique().tolist()
    )

    if account_filter != "全部":
        history = history[history['account_name'] == account_filter]

    # 显示历史记录
    display_df = history[[
        'created_at', 'account_name', 'analysis_period',
        'total_return', 'benchmark_return', 'excess_return',
        'portfolio_beta', 'total_alpha'
    ]].copy()

    for col in ['total_return', 'benchmark_return', 'excess_return', 'total_alpha']:
        display_df[col] = display_df[col].apply(lambda x: f"{x*100:.2f}%" if x else "N/A")

    display_df['portfolio_beta'] = display_df['portfolio_beta'].apply(
        lambda x: f"{x:.2f}" if x else "N/A"
    )

    st.dataframe(
        display_df,
        column_config={
            'created_at': '分析时间',
            'account_name': '账户',
            'analysis_period': '分析周期',
            'total_return': '组合收益',
            'benchmark_return': '基准收益',
            'excess_return': '超额收益',
            'portfolio_beta': 'Beta',
            'total_alpha': 'Alpha'
        },
        width='stretch',
        hide_index=True
    )
