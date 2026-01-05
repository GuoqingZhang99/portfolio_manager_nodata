"""
期权策略评估页面
"""

import streamlit as st
from datetime import datetime, timedelta
from utils.constants import OPTION_TYPES


def render(components):
    """渲染期权评估页面"""
    st.title("期权策略评估")

    option_engine = components['option_engine']
    db = components['db']

    tab1, tab2 = st.tabs(["评估期权", "评估历史"])

    with tab1:
        render_evaluation_form(option_engine)

    with tab2:
        render_evaluation_history(option_engine)


def render_evaluation_form(option_engine):
    """渲染评估表单"""
    st.subheader("输入期权参数")

    col1, col2 = st.columns(2)

    with col1:
        symbol = st.text_input("股票代码", placeholder="例如: NVDA")
        current_price = st.number_input("当前股价 ($)", min_value=0.01, format="%.2f")
        option_type = st.selectbox("期权类型", OPTION_TYPES)
        strike_price = st.number_input("行权价 ($)", min_value=0.01, format="%.2f")

    with col2:
        expiration = st.date_input(
            "到期日",
            datetime.now() + timedelta(days=30)
        )
        premium = st.number_input("期权价格/股 ($)", min_value=0.01, format="%.2f")
        delta = st.number_input("Delta", min_value=-1.0, max_value=1.0, value=0.3, format="%.3f")
        iv_percentile = st.number_input("IV百分位", min_value=0, max_value=100, value=50)

    col1, col2 = st.columns(2)

    with col1:
        theta = st.number_input("Theta", value=-0.05, format="%.3f")

    with col2:
        iv = st.number_input("隐含波动率 (%)", min_value=0.0, value=30.0, format="%.2f")

    if st.button("评估策略", type="primary", width='stretch'):
        if not symbol or current_price <= 0 or strike_price <= 0 or premium <= 0:
            st.error("请填写所有必填字段")
        else:
            option_data = {
                'stock_symbol': symbol.upper(),
                'option_type': option_type,
                'strike_price': strike_price,
                'expiration_date': expiration.strftime('%Y-%m-%d'),
                'current_stock_price': current_price,
                'option_premium': premium,
                'delta': delta,
                'theta': theta,
                'implied_volatility': iv / 100,
                'iv_percentile': iv_percentile
            }

            result = option_engine.evaluate_option(option_data)

            # 显示评估结果
            st.markdown("---")
            st.subheader("评估结果")

            # 推荐分数
            score = result.get('recommendation_score', 0)

            if score >= 80:
                score_color = "green"
                score_label = "强烈推荐"
            elif score >= 60:
                score_color = "orange"
                score_label = "可以考虑"
            else:
                score_color = "red"
                score_label = "谨慎操作"

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("推荐评分", f"{score}/100")

            with col2:
                st.metric("年化收益率", f"{result.get('annualized_return', 0):.1f}%")

            with col3:
                st.metric("盈亏平衡点", f"${result.get('breakeven_price', 0):.2f}")

            # 推荐建议
            st.markdown(f"**评估**: :{score_color}[{score_label}]")

            recommendation = result.get('recommendation', '无匹配策略')
            st.info(f"**建议**: {recommendation}")

            # 匹配的策略规则
            matched_rules = result.get('matched_rules', '')
            if matched_rules:
                st.markdown(f"**匹配策略**: {matched_rules}")

            # 风险评估
            risk = result.get('risk_assessment', {})
            risk_level = risk.get('level', '未知')
            risk_items = risk.get('risks', [])

            st.markdown(f"**风险等级**: {risk_level}")

            if risk_items:
                st.markdown("**风险提示**:")
                for item in risk_items:
                    st.warning(item)

            # 详细数据
            with st.expander("查看详细数据"):
                st.json({
                    '到期天数': result.get('days_to_expiration'),
                    'Delta': result.get('delta'),
                    'Theta': result.get('theta'),
                    '隐含波动率': f"{result.get('implied_volatility', 0) * 100:.2f}%",
                    'IV百分位': result.get('iv_percentile'),
                    '年化收益率': f"{result.get('annualized_return', 0):.2f}%",
                    '盈亏平衡': f"${result.get('breakeven_price', 0):.2f}"
                })


def render_evaluation_history(option_engine):
    """渲染评估历史"""
    st.subheader("评估历史")

    history = option_engine.get_evaluation_history()

    if history.empty:
        st.info("暂无评估记录")
        return

    # 筛选
    col1, col2 = st.columns(2)

    with col1:
        symbols = ['全部'] + history['stock_symbol'].unique().tolist()
        filter_symbol = st.selectbox("股票筛选", symbols)

    with col2:
        executed_filter = st.selectbox("执行状态", ['全部', '已执行', '未执行'])

    # 应用筛选
    filtered = history.copy()

    if filter_symbol != '全部':
        filtered = filtered[filtered['stock_symbol'] == filter_symbol]

    if executed_filter == '已执行':
        filtered = filtered[filtered['executed'] == True]
    elif executed_filter == '未执行':
        filtered = filtered[filtered['executed'] == False]

    # 显示表格
    if not filtered.empty:
        display_df = filtered[[
            'evaluation_date', 'stock_symbol', 'option_type',
            'strike_price', 'expiration_date', 'annualized_return',
            'recommendation_score', 'executed'
        ]].copy()

        display_df['strike_price'] = display_df['strike_price'].apply(lambda x: f"${x:.2f}")
        display_df['annualized_return'] = display_df['annualized_return'].apply(lambda x: f"{x:.1f}%")
        display_df['executed'] = display_df['executed'].apply(lambda x: '是' if x else '否')

        st.dataframe(
            display_df,
            column_config={
                'evaluation_date': '评估时间',
                'stock_symbol': '股票',
                'option_type': '类型',
                'strike_price': '行权价',
                'expiration_date': '到期日',
                'annualized_return': '年化收益',
                'recommendation_score': '评分',
                'executed': '已执行'
            },
            width='stretch',
            hide_index=True
        )
    else:
        st.info("没有符合条件的记录")
