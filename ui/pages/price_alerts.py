"""
价格预警页面
"""

import streamlit as st
from utils.constants import ALERT_TYPES


def render(components):
    """渲染价格预警页面"""
    st.title("价格预警")

    alert_system = components['alert_system']
    db = components['db']

    tab1, tab2, tab3 = st.tabs(["添加预警", "激活预警", "历史预警"])

    with tab1:
        render_add_alert(alert_system)

    with tab2:
        render_active_alerts(alert_system, db)

    with tab3:
        render_triggered_alerts(alert_system)


def render_add_alert(alert_system):
    """渲染添加预警表单"""
    st.subheader("添加价格预警")

    with st.form("alert_form"):
        col1, col2 = st.columns(2)

        with col1:
            symbol = st.text_input("股票代码", placeholder="例如: NVDA")
            alert_type = st.selectbox("预警类型", ALERT_TYPES)
            target_price = st.number_input("目标价格 ($)", min_value=0.01, format="%.2f")

        with col2:
            notification = st.selectbox("通知方式", ["桌面", "邮件"])
            planned_action = st.selectbox("预设操作", ["无", "买入", "卖出"])
            email = st.text_input(
                "邮箱地址（邮件通知）",
                placeholder="留空使用默认邮箱",
                help="仅当选择邮件通知时需要"
            )

        # 预设操作详情
        st.markdown("**预设操作详情** _(选择买入或卖出时填写)_")
        col1, col2 = st.columns(2)
        with col1:
            planned_shares = st.number_input(
                "预设股数",
                min_value=1,
                step=1,
                value=1,
                help="当预设操作为买入或卖出时，此字段才会被保存"
            )
        with col2:
            planned_notes = st.text_input(
                "操作备注",
                help="当预设操作为买入或卖出时，此字段才会被保存"
            )

        submitted = st.form_submit_button("添加预警", type="primary", width='stretch')

        if submitted:
            if not symbol:
                st.error("请输入股票代码")
            elif target_price <= 0:
                st.error("请输入有效目标价格")
            else:
                try:
                    alert_data = {
                        'stock_symbol': symbol.upper(),
                        'alert_type': alert_type,
                        'target_price': target_price,
                        'notification_method': notification,
                        'email_address': email if notification == '邮件' else None,
                        'planned_action': planned_action if planned_action != "无" else None,
                        'planned_shares': planned_shares,
                        'planned_notes': planned_notes
                    }

                    alert_system.add_alert(alert_data)
                    st.success(f"成功添加预警：{symbol.upper()} {alert_type} ${target_price:.2f}")
                    st.rerun()

                except Exception as e:
                    st.error(f"添加失败: {str(e)}")


def render_edit_alert_form(alert_system, alert):
    """渲染编辑预警表单"""
    alert_id = alert['alert_id']

    st.markdown("---")
    st.markdown(f"**编辑预警: {alert['stock_symbol']}**")

    with st.form(f"edit_form_{alert_id}"):
        col1, col2 = st.columns(2)

        with col1:
            alert_type = st.selectbox(
                "预警类型",
                ALERT_TYPES,
                index=ALERT_TYPES.index(alert['alert_type'])
            )
            target_price = st.number_input(
                "目标价格 ($)",
                min_value=0.01,
                value=float(alert['target_price']),
                format="%.2f"
            )

        with col2:
            notification = st.selectbox(
                "通知方式",
                ["桌面", "邮件"],
                index=0 if alert['notification_method'] == '桌面' else 1
            )
            email = st.text_input(
                "邮箱地址",
                value=alert['email_address'] or '',
                placeholder="如选择邮件通知，留空使用默认邮箱"
            )

        # 预设操作
        planned_action_options = ["无", "买入", "卖出"]
        current_action = alert['planned_action'] or '无'
        planned_action = st.selectbox(
            "预设操作",
            planned_action_options,
            index=planned_action_options.index(current_action)
        )

        st.markdown("**预设操作详情** _(选择买入或卖出时填写)_")
        col1, col2 = st.columns(2)
        with col1:
            planned_shares = st.number_input(
                "预设股数",
                min_value=1,
                step=1,
                value=int(alert['planned_shares'] or 1),
                help="当预设操作为买入或卖出时，此字段才会被保存"
            )
        with col2:
            planned_notes = st.text_input(
                "操作备注",
                value=alert['planned_notes'] or '',
                help="当预设操作为买入或卖出时，此字段才会被保存"
            )

        col1, col2 = st.columns(2)
        with col1:
            save_button = st.form_submit_button("💾 保存", type="primary", width='stretch')
        with col2:
            cancel_button = st.form_submit_button("❌ 取消", width='stretch')

        if save_button:
            try:
                update_data = {
                    'alert_type': alert_type,
                    'target_price': target_price,
                    'notification_method': notification,
                    'email_address': email if notification == '邮件' else None,
                    'planned_action': planned_action if planned_action != "无" else None,
                    'planned_shares': planned_shares if planned_action != "无" else None,
                    'planned_notes': planned_notes if planned_action != "无" else None,
                }

                alert_system.update_alert(alert_id, update_data)
                st.success("预警已更新")
                # 清除编辑状态
                del st.session_state[f"editing_{alert_id}"]
                st.rerun()

            except Exception as e:
                st.error(f"更新失败: {str(e)}")

        if cancel_button:
            # 取消编辑
            del st.session_state[f"editing_{alert_id}"]
            st.rerun()


def render_active_alerts(alert_system, db):
    """渲染激活的预警"""
    st.subheader("激活的预警")

    alerts = alert_system.get_active_alerts()

    if alerts.empty:
        st.info("暂无激活的预警")
        return

    # 显示预警列表
    for _, alert in alerts.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

            with col1:
                st.markdown(f"**{alert['stock_symbol']}**")
                st.caption(f"{alert['alert_type']} ${alert['target_price']:.2f}")

            with col2:
                if alert['planned_action']:
                    st.markdown(f"预设: {alert['planned_action']} {alert['planned_shares'] or ''}股")
                    if alert['planned_notes']:
                        st.caption(f"备注: {alert['planned_notes']}")
                else:
                    st.markdown("无预设操作")

            with col3:
                st.caption(f"通知: {alert['notification_method']}")
                if alert['email_address']:
                    st.caption(f"邮箱: {alert['email_address']}")
                st.caption(f"创建: {alert['created_at'][:10]}")

            with col4:
                # 编辑按钮
                if st.button("✏️", key=f"edit_{alert['alert_id']}", help="编辑预警"):
                    st.session_state[f"editing_{alert['alert_id']}"] = True
                    st.rerun()

                # 删除按钮
                if st.button("🗑️", key=f"del_{alert['alert_id']}", help="删除预警"):
                    alert_system.delete_alert(alert['alert_id'])
                    st.rerun()

            # 编辑表单（如果正在编辑）
            if st.session_state.get(f"editing_{alert['alert_id']}", False):
                render_edit_alert_form(alert_system, alert)

            st.divider()

    # 手动检查按钮
    st.markdown("---")

    if st.button("手动检查预警", width='stretch'):
        try:
            from utils.data_fetcher import batch_get_prices

            symbols = alerts['stock_symbol'].unique().tolist()
            prices = batch_get_prices(symbols)

            if prices:
                triggered = alert_system.check_alerts(prices)

                if triggered:
                    st.success(f"触发了 {len(triggered)} 个预警！")
                    for t in triggered:
                        st.warning(
                            f"{t['symbol']}: {t['alert_type']} ${t['target_price']:.2f} "
                            f"(当前: ${t['current_price']:.2f})"
                        )
                else:
                    st.info("没有触发的预警")

                # 显示当前价格
                st.subheader("当前价格")
                for symbol, price in prices.items():
                    st.markdown(f"- {symbol}: ${price:.2f}")
            else:
                st.warning("获取价格失败")

        except Exception as e:
            st.error(f"检查失败: {str(e)}")


def render_triggered_alerts(alert_system):
    """渲染已触发的预警"""
    st.subheader("已触发的预警")

    alerts = alert_system.get_triggered_alerts()

    if alerts.empty:
        st.info("暂无已触发的预警")
        return

    display_df = alerts[[
        'stock_symbol', 'alert_type', 'target_price',
        'triggered_price', 'triggered_at', 'planned_action', 'planned_shares'
    ]].copy()

    display_df['target_price'] = display_df['target_price'].apply(lambda x: f"${x:.2f}")
    display_df['triggered_price'] = display_df['triggered_price'].apply(
        lambda x: f"${x:.2f}" if x else "N/A"
    )

    st.dataframe(
        display_df,
        column_config={
            'stock_symbol': '股票',
            'alert_type': '类型',
            'target_price': '目标价',
            'triggered_price': '触发价',
            'triggered_at': '触发时间',
            'planned_action': '预设操作',
            'planned_shares': '预设股数'
        },
        width='stretch',
        hide_index=True
    )

    # 重新激活按钮
    st.markdown("---")

    alert_to_reactivate = st.selectbox(
        "选择要重新激活的预警",
        alerts['alert_id'].tolist(),
        format_func=lambda x: f"{alerts[alerts['alert_id']==x].iloc[0]['stock_symbol']} - ${alerts[alerts['alert_id']==x].iloc[0]['target_price']:.2f}"
    )

    if st.button("重新激活"):
        alert_system.reactivate_alert(alert_to_reactivate)
        st.success("预警已重新激活")
        st.rerun()
