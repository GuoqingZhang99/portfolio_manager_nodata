"""
指标卡片组件
"""

import streamlit as st


def display_metric_card(label, value, delta=None, delta_color='normal'):
    """
    显示指标卡片

    Args:
        label: 标签
        value: 值
        delta: 变化值
        delta_color: 颜色（normal/inverse/off）
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color
    )


def display_metric_row(metrics):
    """
    显示一行指标

    Args:
        metrics: list of dicts [{'label': str, 'value': str, 'delta': str}]
    """
    cols = st.columns(len(metrics))

    for i, metric in enumerate(metrics):
        with cols[i]:
            display_metric_card(
                label=metric.get('label', ''),
                value=metric.get('value', ''),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal')
            )


def display_account_overview_cards(overview):
    """
    显示账户概览卡片

    Args:
        overview: dict 账户概览数据
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "总资金",
            f"${overview.get('总资金', 0):,.0f}"
        )

    with col2:
        stock_inv = overview.get('已投入股票', 0)
        stock_pct = overview.get('股票仓位占比%', 0)
        st.metric(
            "已投资",
            f"${stock_inv:,.0f}",
            f"{stock_pct:.1f}%"
        )

    with col3:
        st.metric(
            "可用现金",
            f"${overview.get('可用现金', 0):,.0f}"
        )

    with col4:
        st.metric(
            "持股数量",
            f"{overview.get('持股数量', 0)}"
        )


def display_pnl_card(label, amount, percentage=None):
    """
    显示盈亏卡片

    Args:
        label: 标签
        amount: 金额
        percentage: 百分比（可选）
    """
    color = "green" if amount >= 0 else "red"
    sign = "+" if amount >= 0 else ""

    st.markdown(f"""
    <div style="
        background-color: {'#d4edda' if amount >= 0 else '#f8d7da'};
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    ">
        <p style="color: gray; margin: 0; font-size: 14px;">{label}</p>
        <p style="color: {color}; margin: 5px 0; font-size: 24px; font-weight: bold;">
            {sign}${abs(amount):,.2f}
        </p>
        {f'<p style="color: {color}; margin: 0; font-size: 14px;">{sign}{percentage:.2f}%</p>' if percentage is not None else ''}
    </div>
    """, unsafe_allow_html=True)


def display_progress_bar(label, current, target, unit='%'):
    """
    显示进度条

    Args:
        label: 标签
        current: 当前值
        target: 目标值
        unit: 单位
    """
    progress = min(current / target, 1.0) if target > 0 else 0

    st.markdown(f"**{label}**: {current:.1f}{unit} / {target:.1f}{unit}")
    st.progress(progress)


def display_status_badge(status, status_type='info'):
    """
    显示状态徽章

    Args:
        status: 状态文本
        status_type: 类型（info/success/warning/error）
    """
    colors = {
        'info': '#17a2b8',
        'success': '#28a745',
        'warning': '#ffc107',
        'error': '#dc3545'
    }

    color = colors.get(status_type, colors['info'])

    st.markdown(f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 12px;
    ">{status}</span>
    """, unsafe_allow_html=True)
