"""
现金流分析页面
"""

import streamlit as st
from datetime import datetime, timedelta
from utils.constants import ACCOUNT_NAMES, FLOW_TYPES


def render(components):
    """渲染现金流分析页面"""
    st.title("现金流分析")

    cash_flow = components['cash_flow']
    chart_builder = components['chart_builder']
    db = components['db']

    tab1, tab2, tab3 = st.tabs(["现金流量表", "添加现金流", "详细记录"])

    with tab1:
        render_cash_flow_statement(cash_flow, chart_builder)

    with tab2:
        render_add_cash_flow(cash_flow)

    with tab3:
        render_cash_flow_details(db)


def render_cash_flow_statement(cash_flow, chart_builder):
    """渲染现金流量表"""
    st.subheader("现金流量表")

    col1, col2, col3 = st.columns(3)

    with col1:
        account = st.selectbox("账户", ["全部"] + ACCOUNT_NAMES, key="cf_account")

    with col2:
        start_date = st.date_input(
            "开始日期",
            datetime.now().replace(day=1) - timedelta(days=30),
            key="cf_start"
        )

    with col3:
        end_date = st.date_input("结束日期", datetime.now(), key="cf_end")

    # 获取现金流量表
    account_filter = None if account == "全部" else account
    statement = cash_flow.get_cash_flow_statement(
        account=account_filter,
        start_date=start_date,
        end_date=end_date
    )

    # 经营活动
    st.markdown("### 经营活动现金流")
    operating = statement.get('经营活动现金流', {})

    if operating.get('明细'):
        for flow_type, amount in operating['明细'].items():
            color = "green" if amount >= 0 else "red"
            st.markdown(f"- {flow_type}: :{color}[${abs(amount):,.2f}]")

    operating_total = operating.get('小计', 0)
    st.markdown(f"**小计: ${operating_total:,.2f}**")

    # 投资活动
    st.markdown("### 投资活动现金流")
    investing = statement.get('投资活动现金流', {})

    if investing.get('明细'):
        for flow_type, amount in investing['明细'].items():
            color = "green" if amount >= 0 else "red"
            st.markdown(f"- {flow_type}: :{color}[${abs(amount):,.2f}]")

    investing_total = investing.get('小计', 0)
    st.markdown(f"**小计: ${investing_total:,.2f}**")

    # 融资活动
    st.markdown("### 融资活动现金流")
    financing = statement.get('融资活动现金流', {})

    if financing.get('明细'):
        for flow_type, amount in financing['明细'].items():
            color = "green" if amount >= 0 else "red"
            st.markdown(f"- {flow_type}: :{color}[${abs(amount):,.2f}]")

    financing_total = financing.get('小计', 0)
    st.markdown(f"**小计: ${financing_total:,.2f}**")

    # 佣金
    commission = statement.get('佣金支出', 0)
    st.markdown(f"### 佣金支出: :red[${abs(commission):,.2f}]")

    # 净现金流
    st.markdown("---")
    net_cash = statement.get('净现金流', 0)
    color = "green" if net_cash >= 0 else "red"
    st.markdown(f"## 净现金流: :{color}[${net_cash:,.2f}]")

    # 已实现盈亏
    st.markdown("---")
    st.subheader("已实现 vs 未实现")

    realized = cash_flow.calculate_realized_vs_unrealized(account_filter)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("期权已实现盈亏", f"${realized.get('期权盈亏', 0):,.2f}")

    with col2:
        st.metric("分红收入", f"${realized.get('分红收入', 0):,.2f}")

    with col3:
        st.metric("总已实现盈亏", f"${realized.get('总已实现盈亏', 0):,.2f}")


def render_add_cash_flow(cash_flow):
    """渲染添加现金流"""
    st.subheader("手动添加现金流")

    with st.form("manual_cash_flow"):
        col1, col2 = st.columns(2)

        with col1:
            flow_date = st.date_input("日期", datetime.now())
            account = st.selectbox("账户", ACCOUNT_NAMES)
            flow_type = st.selectbox("类型", ['存入', '取出', '利息', '其他'])

        with col2:
            amount = st.number_input("金额 ($)", format="%.2f")
            description = st.text_input("描述")
            notes = st.text_area("备注", height=68)

        submitted = st.form_submit_button("添加", type="primary", width='stretch')

        if submitted:
            if amount == 0:
                st.error("请输入金额")
            else:
                try:
                    # 存入为正，取出为负
                    actual_amount = amount if flow_type in ['存入', '利息'] else -abs(amount)

                    cash_flow.add_manual_cash_flow(
                        flow_date=flow_date,
                        account=account,
                        flow_type=flow_type,
                        amount=actual_amount,
                        description=description,
                        notes=notes
                    )

                    st.success(f"成功添加现金流: {flow_type} ${abs(amount):,.2f}")
                    st.rerun()

                except Exception as e:
                    st.error(f"添加失败: {str(e)}")


def render_cash_flow_details(db):
    """渲染详细记录"""
    st.subheader("现金流详细记录")

    col1, col2 = st.columns(2)

    with col1:
        account = st.selectbox("账户筛选", ["全部"] + ACCOUNT_NAMES, key="detail_account")

    with col2:
        flow_type = st.selectbox("类型筛选", ["全部"] + FLOW_TYPES, key="detail_type")

    flows = db.get_cash_flows(
        account=None if account == "全部" else account,
        flow_type=None if flow_type == "全部" else flow_type
    )

    if flows.empty:
        st.info("暂无现金流记录")
        return

    # 格式化显示
    display_df = flows[[
        'flow_date', 'account_name', 'flow_type',
        'stock_symbol', 'amount', 'description', 'auto_generated'
    ]].copy()

    display_df['amount'] = display_df['amount'].apply(
        lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"
    )
    display_df['auto_generated'] = display_df['auto_generated'].apply(
        lambda x: '自动' if x else '手动'
    )

    st.dataframe(
        display_df,
        column_config={
            'flow_date': '日期',
            'account_name': '账户',
            'flow_type': '类型',
            'stock_symbol': '股票',
            'amount': '金额',
            'description': '描述',
            'auto_generated': '来源'
        },
        width='stretch',
        hide_index=True
    )

    # 月度汇总
    st.markdown("---")
    st.subheader("月度汇总")

    account_filter = None if account == "全部" else account

    # 创建 CashFlowManager 实例
    from core.cash_flow import CashFlowManager
    cash_flow_mgr = CashFlowManager(db)
    monthly = cash_flow_mgr.get_monthly_summary(account=account_filter)

    if not monthly.empty:
        st.dataframe(monthly, width='stretch', hide_index=True)
