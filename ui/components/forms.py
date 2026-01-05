"""
表单组件
"""

import streamlit as st
from datetime import datetime
from utils.constants import TRANSACTION_TYPES, OPTION_TYPES, ACCOUNT_NAMES, EMOTIONAL_STATES


def create_transaction_form(on_submit=None):
    """
    创建交易表单

    Args:
        on_submit: 提交回调函数

    Returns:
        dict: 表单数据（如果提交）
    """
    with st.form("transaction_form"):
        st.subheader("基本信息")

        col1, col2 = st.columns(2)

        with col1:
            trans_date = st.date_input("交易日期", datetime.now())
            account = st.selectbox("账户", ACCOUNT_NAMES)
            symbol = st.text_input("股票代码", placeholder="例如: NVDA").upper()
            trans_type = st.selectbox("交易类型", TRANSACTION_TYPES)

        with col2:
            price = st.number_input("价格 ($)", min_value=0.01, format="%.2f")
            shares = st.number_input("股数", min_value=1, step=1)
            commission = st.number_input("佣金 ($)", min_value=0.0, value=0.0, format="%.2f")
            notes = st.text_area("备注", placeholder="可选", height=68)

        submitted = st.form_submit_button("提交交易", type="primary")

        if submitted:
            data = {
                'date': trans_date,
                'account': account,
                'symbol': symbol,
                'type': trans_type,
                'price': price,
                'shares': shares,
                'commission': commission,
                'notes': notes
            }

            if on_submit:
                on_submit(data)

            return data

    return None


def create_option_form(on_submit=None):
    """
    创建期权表单

    Args:
        on_submit: 提交回调函数

    Returns:
        dict: 表单数据（如果提交）
    """
    with st.form("option_form"):
        st.subheader("期权交易信息")

        col1, col2 = st.columns(2)

        with col1:
            account = st.selectbox("账户", ACCOUNT_NAMES)
            symbol = st.text_input("股票代码", placeholder="例如: NVDA").upper()
            option_type = st.selectbox("期权类型", OPTION_TYPES)
            strike_price = st.number_input("行权价 ($)", min_value=0.01, format="%.2f")
            expiration = st.date_input("到期日")

        with col2:
            premium = st.number_input("权利金/股 ($)", min_value=0.01, format="%.2f")
            contracts = st.number_input("合约数量", min_value=1, step=1)
            open_date = st.date_input("开仓日期", datetime.now())
            opening_fee = st.number_input("开仓费用 ($)", min_value=0.0, value=0.0, format="%.2f")

        st.subheader("Greeks（可选）")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            delta = st.number_input("Delta", min_value=-1.0, max_value=1.0, value=0.0, format="%.3f")

        with col2:
            gamma = st.number_input("Gamma", min_value=0.0, value=0.0, format="%.4f")

        with col3:
            theta = st.number_input("Theta", value=0.0, format="%.3f")

        with col4:
            vega = st.number_input("Vega", min_value=0.0, value=0.0, format="%.3f")

        col1, col2 = st.columns(2)
        with col1:
            iv = st.number_input("隐含波动率 (%)", min_value=0.0, value=0.0, format="%.2f")
        with col2:
            iv_percentile = st.number_input("IV百分位", min_value=0, max_value=100, value=50)

        notes = st.text_area("备注", placeholder="可选")

        submitted = st.form_submit_button("提交期权交易", type="primary")

        if submitted:
            data = {
                'account': account,
                'symbol': symbol,
                'option_type': option_type,
                'strike_price': strike_price,
                'expiration_date': expiration,
                'premium_per_share': premium,
                'contracts': contracts,
                'open_date': open_date,
                'opening_fee': opening_fee,
                'delta': delta if delta != 0 else None,
                'gamma': gamma if gamma != 0 else None,
                'theta': theta if theta != 0 else None,
                'vega': vega if vega != 0 else None,
                'implied_volatility': iv / 100 if iv != 0 else None,
                'iv_percentile': iv_percentile,
                'notes': notes
            }

            if on_submit:
                on_submit(data)

            return data

    return None


def create_journal_form(symbol=None, trade_type=None, on_submit=None):
    """
    创建交易日志表单

    Args:
        symbol: 预填股票代码
        trade_type: 预填交易类型
        on_submit: 提交回调函数

    Returns:
        dict: 表单数据
    """
    st.subheader("交易日志（建议填写）")

    reason = st.text_area(
        "为什么现在交易？ *",
        placeholder="例如：技术突破、财报超预期、止损触发等",
        help="记录决策原因，便于日后复盘"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        target_price = st.number_input("目标价 ($)", min_value=0.0, format="%.2f")

    with col2:
        stop_loss = st.number_input("止损位 ($)", min_value=0.0, format="%.2f")

    with col3:
        confidence = st.slider("信心等级", 1, 10, 5)

    col1, col2 = st.columns(2)

    with col1:
        expected_period = st.selectbox(
            "预期持有期",
            ["短期(1周内)", "中期(1-4周)", "长期(1月以上)", "不确定"]
        )

    with col2:
        emotional_state = st.selectbox("当前情绪状态", EMOTIONAL_STATES)

    main_risks = st.text_area(
        "主要风险",
        placeholder="列出你认为的主要风险因素",
        height=68
    )

    return {
        'reason': reason,
        'target_price': target_price if target_price > 0 else None,
        'stop_loss': stop_loss if stop_loss > 0 else None,
        'confidence_level': confidence,
        'expected_holding_period': expected_period,
        'emotional_state': emotional_state,
        'main_risks': main_risks
    }


def create_alert_form(on_submit=None):
    """
    创建价格预警表单

    Args:
        on_submit: 提交回调函数

    Returns:
        dict: 表单数据
    """
    with st.form("alert_form"):
        st.subheader("添加价格预警")

        col1, col2 = st.columns(2)

        with col1:
            symbol = st.text_input("股票代码", placeholder="例如: NVDA").upper()
            alert_type = st.selectbox("预警类型", ["高于", "低于", "穿越"])
            target_price = st.number_input("目标价格 ($)", min_value=0.01, format="%.2f")

        with col2:
            notification = st.selectbox("通知方式", ["邮件", "桌面"])
            email = st.text_input("邮箱地址", placeholder="如选择邮件通知")
            planned_action = st.selectbox("预设操作", ["无", "买入", "卖出"])

        if planned_action != "无":
            planned_shares = st.number_input("预设股数", min_value=1, step=1)
            planned_notes = st.text_area("操作备注", height=68)
        else:
            planned_shares = None
            planned_notes = None

        submitted = st.form_submit_button("添加预警", type="primary")

        if submitted and symbol and target_price > 0:
            data = {
                'stock_symbol': symbol,
                'alert_type': alert_type,
                'target_price': target_price,
                'notification_method': notification,
                'email_address': email if notification == '邮件' else None,
                'planned_action': planned_action if planned_action != "无" else None,
                'planned_shares': planned_shares,
                'planned_notes': planned_notes
            }

            if on_submit:
                on_submit(data)

            return data

    return None
