"""
录入股票交易页面
"""

import streamlit as st
from datetime import datetime
from utils.constants import TRANSACTION_TYPES, ACCOUNT_NAMES, EMOTIONAL_STATES, OTHER_CASH_FLOW_TYPES


def render(components):
    """渲染录入交易页面"""
    st.title("录入交易")

    db = components['db']
    cash_flow = components['cash_flow']
    journal = components['journal']

    # 创建tabs
    tab1, tab2 = st.tabs(["股票交易", "其他现金流"])

    # Tab 1: 股票交易
    with tab1:
        render_stock_transaction(db, cash_flow, journal)

    # Tab 2: 其他现金流
    with tab2:
        render_other_cash_flow(db, cash_flow)


def render_stock_transaction(db, cash_flow, journal):
    """渲染股票交易表单"""

    # 初始化session state用于编辑功能
    if 'editing_transaction_id' not in st.session_state:
        st.session_state.editing_transaction_id = None
    if 'editing_transaction_data' not in st.session_state:
        st.session_state.editing_transaction_data = None

    # 添加模拟影响功能
    with st.expander("📊 模拟交易影响", expanded=False):
        st.info("在提交交易前，先模拟查看这笔交易对您的投资组合的影响")

        col1, col2 = st.columns(2)

        with col1:
            sim_account = st.selectbox("账户", ACCOUNT_NAMES, key="sim_account")
            sim_symbol = st.text_input("股票代码", placeholder="例如: NVDA", key="sim_symbol")
            sim_type = st.selectbox("交易类型", TRANSACTION_TYPES, key="sim_type")

        with col2:
            sim_price = st.number_input("价格 ($)", min_value=0.01, format="%.2f", key="sim_price")
            sim_shares = st.number_input("股数", min_value=1, step=1, value=1, key="sim_shares")
            sim_commission = st.number_input("佣金 ($)", min_value=0.0, value=0.0, format="%.2f", key="sim_commission")

        if st.button("🔮 模拟影响", type="secondary", width='stretch'):
            if not sim_symbol:
                st.error("请输入股票代码")
            elif sim_price <= 0:
                st.error("请输入有效价格")
            elif sim_shares <= 0:
                st.error("请输入有效股数")
            else:
                # 调用模拟计算
                from core.calculator import PortfolioCalculator
                calc = PortfolioCalculator(db)

                result = calc.simulate_transaction_impact(
                    account=sim_account,
                    symbol=sim_symbol,
                    trans_type=sim_type,
                    price=sim_price,
                    shares=sim_shares,
                    commission=sim_commission
                )

                if result.get('error'):
                    st.error(result['error'])
                else:
                    # 显示模拟结果
                    st.markdown("---")
                    st.markdown("### 📈 模拟结果")

                    # 交易概览
                    st.markdown(f"**交易：** {result['交易类型']} {sim_symbol.upper()} {sim_shares}股 @ ${sim_price:.2f}")
                    st.markdown(f"**交易金额：** ${result['交易金额']:,.2f}")

                    # 当前状态 vs 交易后预测
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("#### 📋 当前状态")
                        current = result['当前状态']
                        st.metric("总资金", f"${current['总资金']:,.0f}")
                        st.metric("股票投资", f"${current['当前股票投资']:,.0f}")
                        st.metric("仓位占比", f"{current['当前仓位占比']:.1f}%")
                        st.metric("可用现金", f"${current['当前可用现金']:,.0f}")

                        symbol_key = f"{sim_symbol.upper()}当前投资"
                        if symbol_key in current:
                            st.metric(f"{sim_symbol.upper()} 投资", f"${current[symbol_key]:,.0f}")
                            st.metric(f"{sim_symbol.upper()} 占比",
                                     f"{current[f'{sim_symbol.upper()}当前占比']:.1f}%")

                    with col2:
                        st.markdown("#### 🎯 交易后预测")
                        predicted = result['交易后预测']
                        st.metric("股票投资", f"${predicted['新股票投资']:,.0f}")
                        st.metric("仓位占比", f"{predicted['新仓位占比']:.1f}%",
                                 delta=f"{predicted['仓位变化']:.1f}%")
                        st.metric("剩余现金", f"${predicted['剩余现金']:,.0f}",
                                 delta=f"{result['现金变化']:,.0f}")

                        symbol_key = f"{sim_symbol.upper()}新投资额"
                        if symbol_key in predicted:
                            st.metric(f"{sim_symbol.upper()} 投资", f"${predicted[symbol_key]:,.0f}")
                            st.metric(f"{sim_symbol.upper()} 占比", f"{predicted[f'{sim_symbol.upper()}新占比']:.1f}%")

                    # 目标范围
                    st.markdown("---")
                    st.markdown("#### 🎚️ 目标范围")
                    targets = result['目标范围']
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"总仓位下限: **{targets['总仓位下限']:.0f}%**")
                    with col2:
                        st.markdown(f"总仓位上限: **{targets['总仓位上限']:.0f}%**")
                    with col3:
                        st.markdown(f"现金储备要求: **${targets['现金储备要求']:,.0f}**")

                    # 警告和建议
                    if result['警告']:
                        st.markdown("---")
                        st.markdown("#### ⚠️ 警告")
                        for warning in result['警告']:
                            st.warning(warning)

                    if result['建议']:
                        st.markdown("---")
                        st.markdown("#### 💡 建议")
                        for suggestion in result['建议']:
                            if suggestion.startswith("✅"):
                                st.success(suggestion)
                            else:
                                st.info(suggestion)

    st.markdown("---")

    # 根据是否在编辑模式显示不同的标题
    if st.session_state.editing_transaction_id:
        st.info(f"正在编辑交易 ID: {st.session_state.editing_transaction_id}")
        if st.button("取消编辑", type="secondary"):
            st.session_state.editing_transaction_id = None
            st.session_state.editing_transaction_data = None
            st.rerun()

    # 获取编辑数据（如果有）
    edit_data = st.session_state.editing_transaction_data or {}

    with st.form("transaction_form"):
        st.subheader("基本信息")

        col1, col2 = st.columns(2)

        with col1:
            # 处理日期默认值
            if edit_data.get('transaction_date'):
                default_date = datetime.strptime(edit_data['transaction_date'], '%Y-%m-%d').date()
            else:
                default_date = datetime.now().date()

            trans_date = st.date_input("交易日期", default_date)

            # 账户默认值
            default_account_idx = ACCOUNT_NAMES.index(edit_data['account_name']) if edit_data.get('account_name') in ACCOUNT_NAMES else 0
            account = st.selectbox("账户", ACCOUNT_NAMES, index=default_account_idx)

            symbol = st.text_input("股票代码", value=edit_data.get('stock_symbol', ''), placeholder="例如: NVDA")

            # 交易类型默认值
            default_type_idx = TRANSACTION_TYPES.index(edit_data['transaction_type']) if edit_data.get('transaction_type') in TRANSACTION_TYPES else 0
            trans_type = st.selectbox("交易类型", TRANSACTION_TYPES, index=default_type_idx)

        with col2:
            price = st.number_input("价格 ($)", min_value=0.01, format="%.2f", value=float(edit_data.get('price', 0.01)))
            shares = st.number_input("股数", min_value=1, step=1, value=int(edit_data.get('shares', 1)))
            commission = st.number_input("佣金 ($)", min_value=0.0, value=float(edit_data.get('commission', 0.0)), format="%.2f")
            notes = st.text_area("备注", value=edit_data.get('notes', '') or '', placeholder="可选", height=68)

        st.markdown("---")
        st.subheader("交易日志（建议填写）")

        reason = st.text_area(
            "为什么现在交易？",
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
            emotional_state = st.selectbox("当前情绪状态", EMOTIONAL_STATES)

        with col2:
            main_risks = st.text_input("主要风险", placeholder="简述主要风险因素")

        # 根据是否在编辑模式显示不同的按钮
        submit_label = "更新交易" if st.session_state.editing_transaction_id else "提交交易"
        submitted = st.form_submit_button(submit_label, type="primary", width='stretch')

        if submitted:
            if not symbol:
                st.error("请输入股票代码")
            elif price <= 0:
                st.error("请输入有效价格")
            elif shares <= 0:
                st.error("请输入有效股数")
            else:
                try:
                    if st.session_state.editing_transaction_id:
                        # 更新现有交易
                        db.update_transaction(
                            transaction_id=st.session_state.editing_transaction_id,
                            date=trans_date,
                            account=account,
                            symbol=symbol.upper(),
                            trans_type=trans_type,
                            price=price,
                            shares=shares,
                            commission=commission,
                            notes=notes
                        )

                        # 计算交易金额
                        amount = price * shares

                        st.success(f"成功更新：{symbol.upper()} {trans_type} {shares}股 @ ${price:.2f} = ${amount:,.2f}")

                        # 清除编辑状态
                        st.session_state.editing_transaction_id = None
                        st.session_state.editing_transaction_data = None

                    else:
                        # 1. 添加交易记录
                        trans_id = db.add_transaction(
                            date=trans_date,
                            account=account,
                            symbol=symbol.upper(),
                            trans_type=trans_type,
                            price=price,
                            shares=shares,
                            commission=commission,
                            notes=notes
                        )

                        # 2. 自动生成现金流
                        cash_flow.auto_generate_from_transaction(trans_id)

                        # 3. 如果填写了日志，添加日志记录
                        if reason:
                            journal.add_journal_entry({
                                'transaction_id': trans_id,
                                'stock_symbol': symbol.upper(),
                                'trade_type': f'股票{trans_type}',
                                'trade_date': trans_date,
                                'account_name': account,
                                'reason': reason,
                                'target_price': target_price if target_price > 0 else None,
                                'stop_loss': stop_loss if stop_loss > 0 else None,
                                'confidence_level': confidence,
                                'emotional_state': emotional_state,
                                'main_risks': main_risks if main_risks else None
                            })

                        # 计算交易金额
                        amount = price * shares

                        st.success(f"成功记录：{symbol.upper()} {trans_type} {shares}股 @ ${price:.2f} = ${amount:,.2f}")

                        if not reason:
                            st.warning("建议补充交易日志，记录决策过程")

                    st.rerun()

                except Exception as e:
                    st.error(f"操作失败: {str(e)}")

    # 显示最近交易
    st.markdown("---")
    st.subheader("最近交易记录")

    recent = db.get_transactions().head(10)

    if not recent.empty:
        # 为每条交易添加编辑和删除按钮
        for idx, row in recent.iterrows():
            col1, col2, col3 = st.columns([5, 1, 1])

            with col1:
                # 显示交易信息
                amount = row['price'] * row['shares']
                st.text(
                    f"{row['transaction_date']} | {row['account_name']} | "
                    f"{row['stock_symbol']} | {row['transaction_type']} | "
                    f"{row['shares']}股 @ ${row['price']:.2f} = ${amount:,.2f}"
                )

            with col2:
                # 编辑按钮
                if st.button("编辑", key=f"edit_{row['transaction_id']}"):
                    # 将该交易的数据保存到session_state
                    st.session_state.editing_transaction_id = row['transaction_id']
                    st.session_state.editing_transaction_data = {
                        'transaction_date': row['transaction_date'],
                        'account_name': row['account_name'],
                        'stock_symbol': row['stock_symbol'],
                        'transaction_type': row['transaction_type'],
                        'price': row['price'],
                        'shares': row['shares'],
                        'commission': row['commission'],
                        'notes': row['notes']
                    }
                    st.rerun()

            with col3:
                # 删除按钮
                if st.button("删除", key=f"del_{row['transaction_id']}", type="secondary"):
                    st.session_state.confirm_delete_transaction_id = row['transaction_id']
                    st.session_state.confirm_delete_transaction_info = f"{row['stock_symbol']} {row['transaction_type']} {row['shares']}股"
                    st.rerun()

        # 删除确认对话框
        if 'confirm_delete_transaction_id' in st.session_state and st.session_state.confirm_delete_transaction_id:
            @st.dialog("⚠️ 确认删除交易")
            def confirm_delete():
                st.warning(f"确定要删除这笔交易吗？")
                st.info(f"**交易信息：** {st.session_state.confirm_delete_transaction_info}")
                st.error("**此操作无法撤销！**")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("确认删除", type="primary", width='stretch'):
                        try:
                            db.delete_transaction(st.session_state.confirm_delete_transaction_id)
                            st.success("交易已删除")
                            st.session_state.confirm_delete_transaction_id = None
                            st.session_state.confirm_delete_transaction_info = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"删除失败: {str(e)}")

                with col2:
                    if st.button("取消", width='stretch'):
                        st.session_state.confirm_delete_transaction_id = None
                        st.session_state.confirm_delete_transaction_info = None
                        st.rerun()

            confirm_delete()
    else:
        st.info("暂无交易记录")


def render_other_cash_flow(db, cash_flow):
    """渲染其他现金流表单"""
    with st.form("cash_flow_form"):
        st.subheader("录入其他现金流")

        col1, col2 = st.columns(2)

        with col1:
            flow_date = st.date_input("日期", datetime.now())
            account = st.selectbox("账户", ACCOUNT_NAMES)

        with col2:
            flow_type = st.selectbox("类型", OTHER_CASH_FLOW_TYPES)
            amount = st.number_input(
                "金额 ($)",
                format="%.2f",
                help="正数表示资金流入，负数表示资金流出"
            )

        notes = st.text_area("备注", placeholder="可选")

        submitted = st.form_submit_button("提交", type="primary", width='stretch')

        if submitted:
            if amount == 0:
                st.error("金额不能为0")
            else:
                try:
                    # 插入cash_flows表
                    conn = db.get_connection()
                    cursor = conn.cursor()

                    cursor.execute('''
                        INSERT INTO cash_flows (
                            flow_date, account_name, flow_type, amount,
                            description, notes, auto_generated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        flow_date,
                        account,
                        flow_type,
                        amount,
                        f"手动录入{flow_type}",
                        notes,
                        0  # 非自动生成
                    ))

                    conn.commit()
                    conn.close()

                    flow_direction = "流入" if amount > 0 else "流出"
                    st.success(f"成功记录：{flow_type} ${abs(amount):,.2f} ({flow_direction})")
                    st.rerun()

                except Exception as e:
                    st.error(f"记录失败: {str(e)}")

    # 显示最近的其他现金流记录
    st.markdown("---")
    st.subheader("最近的其他现金流记录")

    try:
        conn = db.get_connection()
        query = '''
            SELECT flow_date, account_name, flow_type, amount, notes
            FROM cash_flows
            WHERE flow_type IN ('利息', '存入', '取出')
            ORDER BY flow_date DESC, created_at DESC
            LIMIT 10
        '''
        import pandas as pd
        recent_flows = pd.read_sql_query(query, conn)
        conn.close()

        if not recent_flows.empty:
            display_df = recent_flows.copy()
            display_df['amount'] = display_df['amount'].apply(
                lambda x: f"${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"
            )

            st.dataframe(
                display_df,
                column_config={
                    'flow_date': '日期',
                    'account_name': '账户',
                    'flow_type': '类型',
                    'amount': '金额',
                    'notes': '备注'
                },
                width='stretch',
                hide_index=True
            )
        else:
            st.info("暂无其他现金流记录")
    except Exception as e:
        st.error(f"读取记录失败: {str(e)}")
