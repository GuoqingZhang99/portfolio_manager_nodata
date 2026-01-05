"""
录入期权交易页面
"""

import streamlit as st
from datetime import datetime
from utils.constants import OPTION_TYPES, ACCOUNT_NAMES


def render(components):
    """渲染录入期权页面"""
    st.title("录入期权交易")

    db = components['db']
    cash_flow = components['cash_flow']

    tab1, tab2 = st.tabs(["开仓", "平仓"])

    with tab1:
        render_open_option(components)

    with tab2:
        render_close_option(components)


def render_open_option(components):
    """渲染开仓表单"""
    db = components['db']
    cash_flow = components['cash_flow']

    # 初始化session state用于编辑功能
    if 'editing_option_id' not in st.session_state:
        st.session_state.editing_option_id = None
    if 'editing_option_data' not in st.session_state:
        st.session_state.editing_option_data = None

    # 根据是否在编辑模式显示不同的标题
    if st.session_state.editing_option_id:
        st.info(f"正在编辑期权 ID: {st.session_state.editing_option_id}")
        if st.button("取消编辑", type="secondary"):
            st.session_state.editing_option_id = None
            st.session_state.editing_option_data = None
            st.rerun()

    # 获取编辑数据（如果有）
    edit_data = st.session_state.editing_option_data or {}

    with st.form("option_open_form"):
        st.subheader("期权开仓")

        col1, col2 = st.columns(2)

        with col1:
            # 账户默认值
            default_account_idx = ACCOUNT_NAMES.index(edit_data['account_name']) if edit_data.get('account_name') in ACCOUNT_NAMES else 0
            account = st.selectbox("账户", ACCOUNT_NAMES, index=default_account_idx, key="open_account")

            symbol = st.text_input("股票代码", value=edit_data.get('stock_symbol', ''), placeholder="例如: NVDA", key="open_symbol")

            # 期权类型默认值
            default_type_idx = OPTION_TYPES.index(edit_data['option_type']) if edit_data.get('option_type') in OPTION_TYPES else 0
            option_type = st.selectbox("期权类型", OPTION_TYPES, index=default_type_idx, key="open_type")

            strike_price = st.number_input("行权价 ($)", min_value=0.01, format="%.2f", value=float(edit_data.get('strike_price', 0.01)), key="open_strike")

            # 处理到期日默认值
            if edit_data.get('expiration_date'):
                default_exp = datetime.strptime(edit_data['expiration_date'], '%Y-%m-%d').date()
            else:
                default_exp = datetime.now().date()
            expiration = st.date_input("到期日", value=default_exp, key="open_exp")

        with col2:
            premium = st.number_input("权利金/股 ($)", min_value=0.01, format="%.2f", value=float(edit_data.get('premium_per_share', 0.01)), key="open_premium")
            contracts = st.number_input("合约数量", min_value=1, step=1, value=int(edit_data.get('contracts', 1)), key="open_contracts")

            # 处理开仓日期默认值
            if edit_data.get('open_date'):
                default_open_date = datetime.strptime(edit_data['open_date'], '%Y-%m-%d').date()
            else:
                default_open_date = datetime.now().date()
            open_date = st.date_input("开仓日期", value=default_open_date, key="open_date")

            opening_fee = st.number_input("开仓费用 ($)", min_value=0.0, value=float(edit_data.get('opening_fee', 0.0)), format="%.2f", key="open_fee")

        st.subheader("Greeks（可选）")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            delta = st.number_input("Delta", min_value=-1.0, max_value=1.0, value=float(edit_data.get('delta', 0.0) or 0.0), format="%.3f")

        with col2:
            gamma = st.number_input("Gamma", min_value=0.0, value=float(edit_data.get('gamma', 0.0) or 0.0), format="%.4f")

        with col3:
            theta = st.number_input("Theta", value=float(edit_data.get('theta', 0.0) or 0.0), format="%.3f")

        with col4:
            vega = st.number_input("Vega", min_value=0.0, value=float(edit_data.get('vega', 0.0) or 0.0), format="%.3f")

        col1, col2 = st.columns(2)

        with col1:
            # 处理隐含波动率，数据库中存储的是小数，需要转换为百分比
            default_iv = float(edit_data.get('implied_volatility', 0.0) or 0.0) * 100
            iv = st.number_input("隐含波动率 (%)", min_value=0.0, value=default_iv, format="%.2f")

        with col2:
            iv_percentile = st.number_input("IV百分位", min_value=0, max_value=100, value=int(edit_data.get('iv_percentile', 50) or 50))

        notes = st.text_area("备注", value=edit_data.get('notes', '') or '', placeholder="可选", key="open_notes")

        # 根据是否在编辑模式显示不同的按钮
        submit_label = "更新期权" if st.session_state.editing_option_id else "提交开仓"
        submitted = st.form_submit_button(submit_label, type="primary", width='stretch')

        if submitted:
            if not symbol:
                st.error("请输入股票代码")
            elif strike_price <= 0:
                st.error("请输入有效行权价")
            elif premium <= 0:
                st.error("请输入有效权利金")
            else:
                try:
                    if st.session_state.editing_option_id:
                        # 更新现有期权
                        db.update_option_trade(
                            option_id=st.session_state.editing_option_id,
                            account=account,
                            symbol=symbol.upper(),
                            option_type=option_type,
                            strike_price=strike_price,
                            expiration_date=expiration,
                            premium_per_share=premium,
                            contracts=contracts,
                            open_date=open_date,
                            delta=delta if delta != 0 else None,
                            gamma=gamma if gamma != 0 else None,
                            theta=theta if theta != 0 else None,
                            vega=vega if vega != 0 else None,
                            implied_volatility=iv / 100 if iv > 0 else None,
                            iv_percentile=iv_percentile,
                            opening_fee=opening_fee,
                            notes=notes
                        )

                        total_premium = premium * contracts * 100

                        st.success(
                            f"成功更新：{symbol.upper()} {option_type} ${strike_price} "
                            f"x{contracts}张 = ${total_premium:,.2f}"
                        )

                        # 清除编辑状态
                        st.session_state.editing_option_id = None
                        st.session_state.editing_option_data = None

                    else:
                        # 添加新期权
                        option_id = db.add_option_trade(
                            account=account,
                            symbol=symbol.upper(),
                            option_type=option_type,
                            strike_price=strike_price,
                            expiration_date=expiration,
                            premium_per_share=premium,
                            contracts=contracts,
                            open_date=open_date,
                            delta=delta if delta != 0 else None,
                            gamma=gamma if gamma != 0 else None,
                            theta=theta if theta != 0 else None,
                            vega=vega if vega != 0 else None,
                            implied_volatility=iv / 100 if iv > 0 else None,
                            iv_percentile=iv_percentile,
                            opening_fee=opening_fee,
                            notes=notes
                        )

                        # 自动生成现金流
                        cash_flow.auto_generate_from_option(option_id)

                        total_premium = premium * contracts * 100

                        st.success(
                            f"成功开仓：{symbol.upper()} {option_type} ${strike_price} "
                            f"x{contracts}张 = ${total_premium:,.2f}"
                        )

                    st.rerun()

                except Exception as e:
                    st.error(f"操作失败: {str(e)}")

    # 显示最近期权记录
    st.markdown("---")
    st.subheader("最近期权记录")

    recent_options = db.get_options_trades()
    if hasattr(recent_options, 'head'):
        recent_options = recent_options.head(10)

    if not recent_options.empty:
        # 为每条期权添加编辑和删除按钮
        for idx, row in recent_options.iterrows():
            col1, col2, col3 = st.columns([5, 1, 1])

            with col1:
                # 显示期权信息
                total_premium = row['premium_per_share'] * row['contracts'] * 100
                status_str = f" ({row['status']})" if row.get('status') else ""
                st.text(
                    f"{row['open_date']} | {row['account_name']} | "
                    f"{row['stock_symbol']} {row['option_type']} ${row['strike_price']:.2f} | "
                    f"到期:{row['expiration_date']} | {row['contracts']}张 = ${total_premium:,.2f}{status_str}"
                )

            with col2:
                # 编辑按钮
                if st.button("编辑", key=f"edit_opt_{row['option_id']}"):
                    # 将该期权的数据保存到session_state
                    st.session_state.editing_option_id = row['option_id']
                    st.session_state.editing_option_data = {
                        'account_name': row['account_name'],
                        'stock_symbol': row['stock_symbol'],
                        'option_type': row['option_type'],
                        'strike_price': row['strike_price'],
                        'expiration_date': row['expiration_date'],
                        'premium_per_share': row['premium_per_share'],
                        'contracts': row['contracts'],
                        'open_date': row['open_date'],
                        'delta': row['delta'],
                        'gamma': row['gamma'],
                        'theta': row['theta'],
                        'vega': row['vega'],
                        'implied_volatility': row['implied_volatility'],
                        'iv_percentile': row['iv_percentile'],
                        'opening_fee': row['opening_fee'],
                        'notes': row['notes']
                    }
                    st.rerun()

            with col3:
                # 删除按钮
                if st.button("删除", key=f"del_opt_{row['option_id']}", type="secondary"):
                    st.session_state.confirm_delete_option_id = row['option_id']
                    st.session_state.confirm_delete_option_info = f"{row['stock_symbol']} {row['option_type']} ${row['strike_price']:.2f}"
                    st.rerun()

        # 删除确认对话框
        if 'confirm_delete_option_id' in st.session_state and st.session_state.confirm_delete_option_id:
            @st.dialog("⚠️ 确认删除期权")
            def confirm_delete():
                st.warning(f"确定要删除这个期权吗？")
                st.info(f"**期权信息：** {st.session_state.confirm_delete_option_info}")
                st.error("**此操作无法撤销！**")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("确认删除", type="primary", width='stretch'):
                        try:
                            db.delete_option_trade(st.session_state.confirm_delete_option_id)
                            st.success("期权已删除")
                            st.session_state.confirm_delete_option_id = None
                            st.session_state.confirm_delete_option_info = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败: {str(e)}")

                with col2:
                    if st.button("取消", width='stretch'):
                        st.session_state.confirm_delete_option_id = None
                        st.session_state.confirm_delete_option_info = None
                        st.rerun()

            confirm_delete()
    else:
        st.info("暂无期权记录")


def render_close_option(components):
    """渲染平仓表单"""
    db = components['db']
    cash_flow = components['cash_flow']

    st.subheader("期权平仓")

    # 获取持仓中的期权
    options = db.get_options_trades(status='持仓中')

    if options.empty:
        st.info("暂无持仓中的期权")
        return

    # 选择要平仓的期权
    option_choices = []
    for _, opt in options.iterrows():
        label = (
            f"{opt['stock_symbol']} {opt['option_type']} ${opt['strike_price']} "
            f"到期:{opt['expiration_date']} x{opt['contracts']}张"
        )
        option_choices.append(label)

    selected_idx = st.selectbox(
        "选择要平仓的期权",
        range(len(option_choices)),
        format_func=lambda x: option_choices[x]
    )

    selected_option = options.iloc[selected_idx]

    # 显示期权详情
    st.markdown(f"""
    **期权详情:**
    - 股票: {selected_option['stock_symbol']}
    - 类型: {selected_option['option_type']}
    - 行权价: ${selected_option['strike_price']:.2f}
    - 到期日: {selected_option['expiration_date']}
    - 合约数: {selected_option['contracts']}
    - 开仓权利金: ${selected_option['premium_per_share']:.2f}/股
    - 开仓日期: {selected_option['open_date']}
    """)

    with st.form("option_close_form"):
        col1, col2 = st.columns(2)

        with col1:
            close_date = st.date_input("平仓日期", datetime.now())
            close_price = st.number_input(
                "平仓价格/股 ($)",
                min_value=0.0,
                value=0.0,
                format="%.2f"
            )

        with col2:
            closing_fee = st.number_input(
                "平仓费用 ($)",
                min_value=0.0,
                value=0.0,
                format="%.2f"
            )
            status = st.selectbox(
                "平仓状态",
                ["已平仓", "被行权", "到期作废"]
            )

        submitted = st.form_submit_button("确认平仓", type="primary", width='stretch')

        if submitted:
            try:
                option_id = int(selected_option['option_id'])

                db.update_option_close(
                    option_id=option_id,
                    close_date=close_date,
                    close_price_per_share=close_price,
                    closing_fee=closing_fee,
                    status=status
                )

                # 生成平仓现金流
                cash_flow.auto_generate_from_option(option_id, is_close=True)

                # 计算盈亏
                open_premium = selected_option['premium_per_share'] * selected_option['contracts'] * 100
                close_amount = close_price * selected_option['contracts'] * 100
                total_fees = selected_option['opening_fee'] + closing_fee

                if selected_option['option_type'] in ['卖Call', '卖Put']:
                    pnl = open_premium - close_amount - total_fees
                else:
                    pnl = close_amount - open_premium - total_fees

                pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"

                st.success(f"成功平仓！盈亏: {pnl_str}")
                st.rerun()

            except Exception as e:
                st.error(f"平仓失败: {str(e)}")

    # 显示期权持仓列表
    st.markdown("---")
    st.subheader("当前期权持仓")

    display_df = options[[
        'stock_symbol', 'option_type', 'strike_price',
        'expiration_date', 'contracts', 'premium_per_share', 'open_date'
    ]].copy()

    display_df['总权利金'] = display_df['premium_per_share'] * display_df['contracts'] * 100
    display_df['strike_price'] = display_df['strike_price'].apply(lambda x: f"${x:.2f}")
    display_df['premium_per_share'] = display_df['premium_per_share'].apply(lambda x: f"${x:.2f}")
    display_df['总权利金'] = display_df['总权利金'].apply(lambda x: f"${x:,.2f}")

    st.dataframe(
        display_df,
        column_config={
            'stock_symbol': '股票',
            'option_type': '类型',
            'strike_price': '行权价',
            'expiration_date': '到期日',
            'contracts': '合约数',
            'premium_per_share': '权利金/股',
            '总权利金': '总权利金',
            'open_date': '开仓日期'
        },
        width='stretch',
        hide_index=True
    )
