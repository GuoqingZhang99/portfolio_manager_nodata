"""
仓位管理页面
"""

import streamlit as st
import pandas as pd
from utils.constants import ACCOUNT_NAMES, TARGET_TYPES


def calculate_option_pnl(row):
    """计算期权盈亏"""
    try:
        # 开仓权利金总额
        open_premium = row['premium_per_share'] * row['contracts'] * 100
        # 平仓成本（如果有）
        close_cost = 0
        if pd.notna(row.get('close_price_per_share')):
            close_cost = row['close_price_per_share'] * row['contracts'] * 100

        # 费用
        total_fees = (row.get('opening_fee', 0) or 0) + (row.get('closing_fee', 0) or 0)

        # 卖期权：收入 - 平仓成本 - 费用
        if row['option_type'] in ['卖Call', '卖Put']:
            pnl = open_premium - close_cost - total_fees
        else:
            # 买期权：平仓收入 - 成本 - 费用
            pnl = close_cost - open_premium - total_fees

        return pnl
    except:
        return None


def render(components):
    """渲染仓位管理页面"""
    st.title("仓位管理")

    position_mgr = components['position_mgr']
    calc = components['calc']
    db = components['db']

    tab1, tab2, tab3 = st.tabs(["仓位分析", "设置目标", "再平衡计划"])

    with tab1:
        render_position_analysis(position_mgr, calc)

    with tab2:
        render_set_target(position_mgr, db)

    with tab3:
        render_rebalance_plan(position_mgr)


def render_position_analysis(position_mgr, calc):
    """渲染仓位分析"""
    st.subheader("当前仓位分析")

    account = st.selectbox("选择账户", ACCOUNT_NAMES, key="analysis_account")

    # 获取仓位汇总
    summary = position_mgr.get_position_summary(account)

    if not summary:
        st.warning("无法获取账户信息")
        return

    # 显示仓位指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("总资金", f"${summary['总资金']:,.0f}")

    with col2:
        st.metric("已投资", f"${summary['已投资金额']:,.0f}")

    with col3:
        st.metric(
            "当前仓位",
            f"{summary['当前仓位%']:.1f}%",
            f"目标: {summary['目标下限%']:.0f}%-{summary['目标上限%']:.0f}%"
        )

    with col4:
        status_color = "green" if summary['仓位状态'] == '正常' else "orange"
        st.metric("仓位状态", summary['仓位状态'])

    st.info(summary['建议'])

    # 获取详细仓位分析
    st.markdown("---")
    st.subheader("各股票仓位详情")

    analysis = position_mgr.get_position_analysis(account)

    # 检查是否有完整的分析数据（有设置目标）
    # 不仅要检查列是否存在，还要检查是否有实际的建议操作（不是None）
    has_targets = (not analysis.empty and
                   '建议操作' in analysis.columns and
                   '建议股数' in analysis.columns and
                   analysis['建议操作'].notna().any())

    # 如果没有分析数据，检查是否有持仓
    if analysis.empty:
        # 尝试直接获取持仓
        stocks = calc.calculate_stock_summary(account=account)
        if not stocks.empty:
            # 有持仓但没有目标，显示基本持仓信息
            st.warning("⚠️ 您有持仓但未设置仓位目标，建议设置目标以获得更好的仓位管理")

            # 获取当前价格并计算盈亏
            from utils.data_fetcher import batch_get_prices
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

            analysis = stocks
            has_targets = False
        else:
            st.info("暂无仓位和目标设置，请先添加交易或设置仓位目标")

    if not analysis.empty:

        # 不格式化数据，保留原始数值以便正确排序
        display_df = analysis.copy()

        # 只格式化布尔值列
        if '需要再平衡' in display_df.columns:
            display_df['需要再平衡'] = display_df['需要再平衡'].apply(lambda x: '是' if x else '否')

        # 根据是否有目标设置选择显示的列
        if has_targets:
            display_columns = [
                '股票代码', '当前股数', '平均成本', '当前价格', '盈亏金额', '盈亏%',
                '当前金额', '目标金额', '偏离金额', '偏离%', '需要再平衡', '建议操作', '建议股数'
            ]
        else:
            # 没有目标时，显示基本持仓信息和盈亏
            display_columns = ['股票代码', '当前股数', '平均成本']
            if '当前价格' in display_df.columns:
                display_columns.append('当前价格')
            if '盈亏金额' in display_df.columns:
                display_columns.append('盈亏金额')
            if '盈亏%' in display_df.columns:
                display_columns.append('盈亏%')
            if '总投入' in display_df.columns:
                display_columns.append('总投入')
            if '当前市值' in display_df.columns:
                display_columns.append('当前市值')

        # 只选择存在的列
        available_columns = [col for col in display_columns if col in display_df.columns]

        # 配置列显示（使用NumberColumn保证正确排序）
        column_config = {
            '股票代码': st.column_config.TextColumn('股票', width=60),
            '当前股数': st.column_config.NumberColumn('股数', width=55, format="%d"),
            '平均成本': st.column_config.NumberColumn('成本', width=70, format="$%.2f"),
            '当前价格': st.column_config.NumberColumn('现价', width=70, format="$%.2f"),
            '盈亏金额': st.column_config.NumberColumn('盈亏$', width=90, format="$%.0f"),
            '盈亏%': st.column_config.NumberColumn('盈亏%', width=70, format="%.2f%%"),
            '当前金额': st.column_config.NumberColumn('持仓$', width=90, format="$%.0f"),
            '当前市值': st.column_config.NumberColumn('市值$', width=90, format="$%.0f"),
            '总投入': st.column_config.NumberColumn('投入$', width=90, format="$%.0f"),
            '目标金额': st.column_config.NumberColumn('目标$', width=90, format="$%.0f"),
            '偏离金额': st.column_config.NumberColumn('偏离$', width=90, format="$%.0f"),
            '偏离%': st.column_config.NumberColumn('偏离%', width=70, format="%.2f%%"),
            '需要再平衡': st.column_config.TextColumn('再平衡', width=60),
            '建议操作': st.column_config.TextColumn('操作', width=80),
            '建议股数': st.column_config.NumberColumn('建议', width=55, format="%d"),
        }

        # 分离已持仓和待开仓的股票
        if has_targets and '建议操作' in display_df.columns:
            # 已持仓股票（包括加仓、减仓、持有）
            held_stocks = display_df[display_df['建议操作'].isin(['加仓', '减仓', '持有', '未设置目标'])]
            # 待开仓股票
            to_open_stocks = display_df[display_df['建议操作'] == '开仓']

            # 显示已持仓股票
            if not held_stocks.empty:
                st.markdown("#### 📊 已持仓股票")
                st.dataframe(
                    held_stocks[available_columns],
                    column_config=column_config,
                    hide_index=True
                )

            # 显示待开仓股票
            if not to_open_stocks.empty:
                st.markdown("---")  # 添加分隔线
                st.markdown("#### 🚀 待开仓股票")
                st.info("💡 以下股票已设置目标，但尚未持仓")
                st.dataframe(
                    to_open_stocks[available_columns],
                    column_config=column_config,
                    hide_index=True
                )

            # 如果两个都为空
            if held_stocks.empty and to_open_stocks.empty:
                st.info("暂无仓位数据")
        else:
            # 没有目标设置的情况，显示全部
            st.dataframe(
                display_df[available_columns],
                column_config=column_config,
                hide_index=True
            )

        if not has_targets:
            st.warning('⚠️ 部分股票未设置仓位目标，请在"设置目标"标签中进行配置')

    # 期权持仓详情
    st.markdown("---")
    st.subheader("期权持仓详情")

    # 获取该账户的所有期权记录
    all_options = calc.calculate_options_summary(account=account)

    if not all_options.empty:
        # 添加排序列：将持仓中的排在前面
        all_options['排序'] = all_options['status'].apply(lambda x: 0 if x == '持仓中' else 1)
        # 按排序列和开仓日期排序
        all_options = all_options.sort_values(['排序', 'open_date'], ascending=[True, False])
        all_options = all_options.drop('排序', axis=1)

        # 分离持仓中和已平仓的期权
        open_options = all_options[all_options['status'] == '持仓中']
        closed_options = all_options[all_options['status'] != '持仓中']

        # 显示持仓中的期权
        if not open_options.empty:
            st.markdown("#### 📊 持仓中期权")

            # 准备显示数据
            display_df = open_options.copy()
            display_df['行权价'] = display_df['strike_price'].apply(lambda x: f"${x:.2f}")
            display_df['权利金'] = display_df['总权利金'].apply(lambda x: f"${x:.2f}")
            display_df['开仓费'] = display_df['opening_fee'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00")

            display_cols = [
                'stock_symbol', 'option_type', '行权价', 'expiration_date',
                'contracts', '权利金', '开仓费', 'open_date', '剩余天数'
            ]

            column_config = {
                'stock_symbol': st.column_config.TextColumn('股票', width=60),
                'option_type': st.column_config.TextColumn('类型', width=70),
                '行权价': st.column_config.TextColumn('行权价', width=70),
                'expiration_date': st.column_config.TextColumn('到期日', width=90),
                'contracts': st.column_config.NumberColumn('合约数', width=60),
                '权利金': st.column_config.TextColumn('权利金', width=80),
                '开仓费': st.column_config.TextColumn('开仓费', width=70),
                'open_date': st.column_config.TextColumn('开仓日', width=90),
                '剩余天数': st.column_config.NumberColumn('剩余天数', width=70),
            }

            st.dataframe(
                display_df[display_cols],
                column_config=column_config,
                hide_index=True,
                width='stretch'
            )

        # 显示已平仓/到期的期权
        if not closed_options.empty:
            if not open_options.empty:
                st.markdown("---")
            st.markdown("#### 📜 已平仓/到期期权历史")

            # 准备显示数据
            display_df = closed_options.copy()
            display_df['行权价'] = display_df['strike_price'].apply(lambda x: f"${x:.2f}")
            display_df['权利金'] = display_df['总权利金'].apply(lambda x: f"${x:.2f}")
            display_df['开仓费'] = display_df['opening_fee'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00")

            # 添加平仓信息
            if 'close_price_per_share' in display_df.columns:
                display_df['平仓价'] = display_df['close_price_per_share'].apply(
                    lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"
                )
            if 'closing_fee' in display_df.columns:
                display_df['平仓费'] = display_df['closing_fee'].apply(
                    lambda x: f"${x:.2f}" if pd.notna(x) else "$0.00"
                )

            # 计算盈亏
            if 'close_price_per_share' in closed_options.columns:
                display_df['盈亏'] = closed_options.apply(
                    lambda row: calculate_option_pnl(row), axis=1
                )
                display_df['盈亏'] = display_df['盈亏'].apply(
                    lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A"
                )

            display_cols = [
                'stock_symbol', 'option_type', '行权价', 'expiration_date',
                'contracts', '权利金', '开仓费', 'open_date', 'close_date',
                'status'
            ]

            # 添加可选列
            if '平仓价' in display_df.columns:
                display_cols.append('平仓价')
            if '平仓费' in display_df.columns:
                display_cols.append('平仓费')
            if '盈亏' in display_df.columns:
                display_cols.append('盈亏')

            column_config = {
                'stock_symbol': st.column_config.TextColumn('股票', width=60),
                'option_type': st.column_config.TextColumn('类型', width=70),
                '行权价': st.column_config.TextColumn('行权价', width=70),
                'expiration_date': st.column_config.TextColumn('到期日', width=90),
                'contracts': st.column_config.NumberColumn('合约数', width=60),
                '权利金': st.column_config.TextColumn('权利金', width=80),
                '开仓费': st.column_config.TextColumn('开仓费', width=70),
                'open_date': st.column_config.TextColumn('开仓日', width=90),
                'close_date': st.column_config.TextColumn('平仓日', width=90),
                'status': st.column_config.TextColumn('状态', width=80),
                '平仓价': st.column_config.TextColumn('平仓价', width=70),
                '平仓费': st.column_config.TextColumn('平仓费', width=70),
                '盈亏': st.column_config.TextColumn('盈亏', width=90),
            }

            st.dataframe(
                display_df[display_cols],
                column_config=column_config,
                hide_index=True,
                width='stretch'
            )
    else:
        st.info("暂无期权记录")

    # 组合权重
    st.markdown("---")
    st.subheader("组合权重分布")

    weights = position_mgr.calculate_portfolio_weight(account)

    if not weights.empty:
        import plotly.express as px

        fig = px.pie(
            weights,
            values='权重%',
            names='股票代码',
            title='持仓权重分布'
        )

        st.plotly_chart(fig, width='stretch')
    else:
        st.info("暂无持仓")


def render_set_target(position_mgr, db):
    """渲染设置目标"""
    st.subheader("设置仓位目标")

    # 获取现有目标
    all_targets = db.get_position_targets()

    # 编辑模式选择
    edit_mode = st.radio(
        "操作模式",
        ["新建目标", "编辑现有目标"],
        horizontal=True,
        key="target_mode"
    )

    # 如果是编辑模式，显示目标选择器
    selected_target = None
    if edit_mode == "编辑现有目标":
        if all_targets.empty:
            st.warning("暂无目标可编辑，请先创建新目标")
            return

        # 创建目标选项列表
        target_options = []
        for _, target in all_targets.iterrows():
            label = f"{target['stock_symbol']} - {target['account_name']} ({target['target_type']})"
            target_options.append(label)

        selected_label = st.selectbox(
            "选择要编辑的目标",
            target_options,
            key="edit_target_select"
        )

        # 找到选中的目标
        selected_index = target_options.index(selected_label)
        selected_target = all_targets.iloc[selected_index]

        # 显示删除按钮
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🗑️ 删除此目标", type="secondary", width='stretch'):
                try:
                    db.delete_position_target(
                        selected_target['stock_symbol'],
                        selected_target['account_name']
                    )
                    st.success(f"已删除 {selected_target['stock_symbol']} 的目标")
                    st.rerun()
                except Exception as e:
                    st.error(f"删除失败: {e}")

    st.markdown("---")

    # 将目标类型选择移到表单外面，实现实时刷新
    if selected_target is not None:
        default_type = TARGET_TYPES.index(selected_target['target_type'])
        target_type = st.selectbox("目标类型", TARGET_TYPES, index=default_type, key="target_type_select")
    else:
        target_type = st.selectbox("目标类型", TARGET_TYPES, key="target_type_select")

    with st.form("target_form"):
        col1, col2 = st.columns(2)

        with col1:
            # Pre-populate symbol and account if editing
            if selected_target is not None:
                symbol = st.text_input("股票代码", value=selected_target['stock_symbol'], disabled=True)
                account_idx = ACCOUNT_NAMES.index(selected_target['account_name'])
                account = st.selectbox("账户", ACCOUNT_NAMES, index=account_idx, disabled=True)
            else:
                symbol = st.text_input("股票代码", placeholder="例如: NVDA")
                account = st.selectbox("账户", ACCOUNT_NAMES)

        with col2:
            if target_type == '百分比':
                # Pre-populate values if editing
                default_target = selected_target['target_percentage'] if selected_target is not None else 0.0
                default_max = selected_target['max_percentage'] if selected_target is not None and selected_target['max_percentage'] is not None else 0.0
                target_value = st.number_input("目标百分比 (%)", min_value=0.0, max_value=100.0, value=float(default_target), format="%.1f")
                max_value = st.number_input("最大百分比 (%)", min_value=0.0, max_value=100.0, value=float(default_max), format="%.1f")
            elif target_type == '股数':
                # Pre-populate values if editing
                default_target = selected_target['target_shares'] if selected_target is not None and selected_target['target_shares'] is not None else 0
                default_max = selected_target['max_shares'] if selected_target is not None and selected_target['max_shares'] is not None else 0
                target_value = st.number_input("目标股数", min_value=0, step=1, value=int(default_target), format="%d")
                max_value = st.number_input("最大股数", min_value=0, step=1, value=int(default_max), format="%d")

                # 显示预计占用金额
                if symbol and target_value > 0:
                    try:
                        from utils.data_fetcher import batch_get_prices
                        prices = batch_get_prices([symbol.upper()])
                        if symbol.upper() in prices:
                            current_price = prices[symbol.upper()]
                            estimated_amount = current_price * target_value
                            max_estimated = current_price * max_value if max_value > 0 else 0
                            st.info(f"💡 根据当前价格 ${current_price:.2f}:\n\n"
                                  f"- 目标金额: ${estimated_amount:,.2f}\n"
                                  f"- 最大金额: ${max_estimated:,.2f}" if max_value > 0 else f"- 预计占用: ${estimated_amount:,.2f}")
                    except Exception as e:
                        st.warning(f"无法获取价格: {e}")
            else:  # 金额
                # Pre-populate values if editing
                default_target = selected_target['target_amount'] if selected_target is not None and selected_target['target_amount'] is not None else 0.0
                default_max = selected_target['max_amount'] if selected_target is not None and selected_target['max_amount'] is not None else 0.0
                target_value = st.number_input("目标金额 ($)", min_value=0.0, value=float(default_target), format="%.0f")
                max_value = st.number_input("最大金额 ($)", min_value=0.0, value=float(default_max), format="%.0f")

        col1, col2 = st.columns(2)

        with col1:
            # Pre-populate priority if editing
            default_priority = int(selected_target['priority']) if selected_target is not None else 5
            priority = st.slider("优先级", 1, 10, default_priority)

        with col2:
            # Pre-populate threshold if editing
            default_threshold = float(selected_target['rebalance_threshold']) if selected_target is not None else 10.0
            threshold = st.number_input("再平衡阈值 (%)", min_value=1.0, max_value=50.0, value=default_threshold)

        # Pre-populate notes if editing
        default_notes = selected_target['notes'] if selected_target is not None and selected_target['notes'] is not None else ""
        notes = st.text_area("备注", value=default_notes, placeholder="可选")

        # Change button text based on mode
        button_text = "更新目标" if selected_target is not None else "保存目标"
        submitted = st.form_submit_button(button_text, type="primary", width='stretch')

        if submitted:
            if not symbol:
                st.error("请输入股票代码")
            elif target_value <= 0:
                st.error("请输入有效目标值")
            else:
                try:
                    target_data = {
                        'stock_symbol': symbol.upper(),
                        'account_name': account,
                        'target_type': target_type,
                        'target_percentage': target_value if target_type == '百分比' else None,
                        'target_amount': target_value if target_type == '金额' else None,
                        'target_shares': int(target_value) if target_type == '股数' else None,
                        'max_percentage': max_value if target_type == '百分比' else None,
                        'max_amount': max_value if target_type == '金额' else None,
                        'max_shares': int(max_value) if target_type == '股数' and max_value > 0 else None,
                        'priority': priority,
                        'rebalance_threshold': threshold,
                        'notes': notes
                    }

                    position_mgr.set_position_target(target_data)
                    action_text = "更新" if selected_target is not None else "设置"
                    st.success(f"成功{action_text} {symbol.upper()} 的仓位目标")
                    st.rerun()

                except Exception as e:
                    st.error(f"设置失败: {str(e)}")

    # 显示现有目标
    st.markdown("---")
    st.subheader("现有仓位目标")

    targets = db.get_position_targets()

    if not targets.empty:
        # 选择显示的列
        display_cols = ['stock_symbol', 'account_name', 'target_type',
                       'target_percentage', 'target_amount', 'target_shares',
                       'priority', 'rebalance_threshold']

        # 只选择存在的列
        available_cols = [col for col in display_cols if col in targets.columns]
        display_df = targets[available_cols].copy()

        # 配置列显示
        column_config = {
            'stock_symbol': '股票',
            'account_name': '账户',
            'target_type': '目标类型',
            'target_percentage': '目标%',
            'target_amount': '目标金额',
            'target_shares': '目标股数',
            'priority': '优先级',
            'rebalance_threshold': '阈值%'
        }

        st.dataframe(
            display_df,
            column_config=column_config,
            width='stretch',
            hide_index=True
        )
    else:
        st.info("暂无仓位目标设置")


def render_rebalance_plan(position_mgr):
    """渲染再平衡计划"""
    st.subheader("再平衡计划")

    account = st.selectbox("选择账户", ACCOUNT_NAMES, key="rebalance_account")

    if st.button("生成再平衡计划", width='stretch'):
        plan = position_mgr.get_rebalance_plan(account)

        if plan.get('message'):
            st.success(plan['message'])
            return

        needs_rebalance = plan.get('needs_rebalance', [])

        if not needs_rebalance:
            st.success("所有仓位在目标范围内，无需再平衡")
            return

        # 显示需要操作的股票
        st.markdown("### 需要再平衡的仓位")

        to_buy = plan.get('to_buy', [])
        to_sell = plan.get('to_sell', [])

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**需要加仓:**")
            if to_buy:
                for item in to_buy:
                    st.markdown(
                        f"- {item['股票代码']}: 买入 {item['建议股数']}股 "
                        f"(${item.get('所需资金', 0):,.0f})"
                    )
            else:
                st.info("无需加仓")

        with col2:
            st.markdown("**需要减仓:**")
            if to_sell:
                for item in to_sell:
                    st.markdown(
                        f"- {item['股票代码']}: 卖出 {item['建议股数']}股 "
                        f"(${item.get('释放资金', 0):,.0f})"
                    )
            else:
                st.info("无需减仓")

        # 资金汇总
        st.markdown("---")
        st.markdown("### 资金汇总")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("需要资金", f"${plan.get('cash_needed', 0):,.0f}")

        with col2:
            st.metric("释放资金", f"${plan.get('cash_freed', 0):,.0f}")

        with col3:
            net = plan.get('net_cash', 0)
            st.metric(
                "净资金流",
                f"${abs(net):,.0f}",
                "流入" if net > 0 else "流出" if net < 0 else "平衡"
            )
