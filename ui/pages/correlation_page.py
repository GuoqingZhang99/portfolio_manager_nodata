"""
相关性分析页面
"""

import streamlit as st
from utils.constants import ACCOUNT_NAMES


def render(components):
    """渲染相关性分析页面"""
    st.title("相关性分析")

    correlation = components['correlation']
    calc = components['calc']
    chart_builder = components['chart_builder']

    tab1, tab2 = st.tabs(["运行分析", "历史记录"])

    with tab1:
        render_run_correlation(correlation, calc, chart_builder)

    with tab2:
        render_correlation_history(correlation)


def render_run_correlation(correlation, calc, chart_builder):
    """渲染运行相关性分析"""
    st.subheader("运行相关性分析")

    col1, col2 = st.columns(2)

    with col1:
        account = st.selectbox("账户", ["全部"] + ACCOUNT_NAMES, key="corr_account")

    with col2:
        lookback = st.number_input("回溯天数", min_value=30, max_value=365, value=90)

    # 获取持仓
    account_filter = None if account == "全部" else account
    stocks = calc.calculate_stock_summary(account=account_filter)

    if stocks.empty:
        st.warning("暂无持仓，无法进行相关性分析")
        return

    holdings = stocks['股票代码'].tolist()

    st.info(f"当前持仓: {', '.join(holdings)}")

    if st.button("运行相关性分析", type="primary", width='stretch'):
        with st.spinner("正在计算相关性..."):
            corr_matrix, stats = correlation.calculate_correlation_matrix(
                holdings=holdings,
                lookback_days=lookback
            )

        if corr_matrix is None:
            st.error("无法计算相关性，可能是数据不足")
            return

        # 显示统计
        st.markdown("---")
        st.subheader("相关性统计")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("最高相关性", f"{stats.get('max_correlation', 0):.2f}")

        with col2:
            st.metric("最低相关性", f"{stats.get('min_correlation', 0):.2f}")

        with col3:
            st.metric("平均相关性", f"{stats.get('avg_correlation', 0):.2f}")

        # 相关性热力图
        st.markdown("### 相关性热力图")

        fig = chart_builder.create_correlation_heatmap(corr_matrix)
        st.plotly_chart(fig, width='stretch')

        # 高相关性股票对
        st.markdown("### 高相关性股票对")

        high_corr_pairs = correlation.get_high_correlation_pairs(corr_matrix, threshold=0.7)

        if high_corr_pairs:
            for pair in high_corr_pairs:
                color = "red" if pair['correlation'] > 0.8 else "orange"
                st.markdown(
                    f"- {pair['symbol1']} - {pair['symbol2']}: "
                    f":{color}[{pair['correlation']:.2f}]"
                )
        else:
            st.success("没有高度相关的股票对（阈值: 0.7）")

        # 高相关集群
        st.markdown("### 高相关集群")

        clusters = correlation.identify_correlation_clusters(corr_matrix, threshold=0.7)

        if clusters:
            for i, cluster in enumerate(clusters):
                st.markdown(
                    f"**集群 {i+1}**: {', '.join(cluster['symbols'])} "
                    f"(平均相关性: {cluster['avg_correlation']:.2f})"
                )
        else:
            st.success("没有发现高相关集群")

        # 分散化评分
        st.markdown("---")
        st.subheader("分散化评分")

        # 获取板块信息
        sector_data = {}  # 可以从stock_settings获取

        score_result = correlation.calculate_diversification_score(
            holdings=holdings,
            corr_matrix=corr_matrix,
            sector_data=sector_data
        )

        col1, col2 = st.columns(2)

        with col1:
            score = score_result.get('score', 0)
            rating = score_result.get('rating', '未知')

            if score >= 80:
                color = "green"
            elif score >= 60:
                color = "orange"
            else:
                color = "red"

            st.markdown(f"### 总分: :{color}[{score}/100]")
            st.markdown(f"**评级**: {rating}")

        with col2:
            details = score_result.get('details', {})
            st.markdown("**评分细项:**")
            st.markdown(f"- 持股数量分: {details.get('count_score', 0)}/25")
            st.markdown(f"- 相关性分: {details.get('corr_score', 0)}/35")
            st.markdown(f"- 有效持股分: {details.get('effective_score', 0)}/20")
            st.markdown(f"- 板块分散分: {details.get('sector_score', 0)}/20")

        # 改进建议
        recommendations = score_result.get('recommendations', [])
        if recommendations:
            st.markdown("### 改进建议")
            for rec in recommendations:
                st.warning(rec)

        # 保存分析结果
        correlation.save_correlation_analysis(account, corr_matrix, stats)
        st.success("分析结果已保存")


def render_correlation_history(correlation):
    """渲染历史记录"""
    st.subheader("历史相关性分析")

    history = correlation.get_correlation_history()

    if history.empty:
        st.info("暂无历史相关性分析记录")
        return

    display_df = history[[
        'created_at', 'account_name', 'calculation_date',
        'lookback_period', 'max_correlation', 'min_correlation', 'avg_correlation'
    ]].copy()

    for col in ['max_correlation', 'min_correlation', 'avg_correlation']:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if x else "N/A")

    st.dataframe(
        display_df,
        column_config={
            'created_at': '分析时间',
            'account_name': '账户',
            'calculation_date': '计算日期',
            'lookback_period': '回溯天数',
            'max_correlation': '最高相关',
            'min_correlation': '最低相关',
            'avg_correlation': '平均相关'
        },
        width='stretch',
        hide_index=True
    )
