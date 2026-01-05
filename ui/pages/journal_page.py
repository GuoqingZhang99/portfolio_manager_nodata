"""
交易日志页面
"""

import streamlit as st
from datetime import datetime
from utils.constants import ACCOUNT_NAMES, EMOTIONAL_STATES


def render(components):
    """渲染交易日志页面"""
    st.title("交易日志")

    journal = components['journal']
    db = components['db']

    tab1, tab2, tab3 = st.tabs(["日志列表", "添加日志", "复盘"])

    with tab1:
        render_journal_list(journal)

    with tab2:
        render_add_journal(journal, db)

    with tab3:
        render_review(journal)


def render_journal_list(journal):
    """渲染日志列表"""
    st.subheader("交易日志列表")

    # 筛选
    col1, col2, col3 = st.columns(3)

    with col1:
        account = st.selectbox("账户", ["全部"] + ACCOUNT_NAMES, key="journal_account")

    with col2:
        symbol = st.text_input("股票代码", placeholder="输入筛选", key="journal_symbol")

    with col3:
        show_unreviewed = st.checkbox("仅显示未复盘")

    # 获取日志
    journals = journal.get_journal_entries(
        account=None if account == "全部" else account,
        symbol=symbol.upper() if symbol else None
    )

    if show_unreviewed and not journals.empty:
        journals = journals[journals['reviewed_at'].isna()]

    if journals.empty:
        st.info("暂无日志记录")
        return

    # 完成率
    col1, col2 = st.columns(2)

    with col1:
        rate = journal.get_completion_rate(
            account=None if account == "全部" else account
        )
        st.metric(
            "30天日志完成率",
            f"{rate['completion_rate']:.0f}%",
            f"{rate['journal_count']}/{rate['total_trades']} 笔交易"
        )

    with col2:
        unreviewed = journal.get_unreviewed_entries(
            account=None if account == "全部" else account
        )
        st.metric("待复盘", f"{len(unreviewed)} 条")

    # 日志列表
    st.markdown("---")

    for _, entry in journals.head(20).iterrows():
        with st.expander(
            f"{entry['trade_date']} | {entry['stock_symbol']} | {entry['trade_type']}"
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**账户**: {entry['account_name']}")
                st.markdown(f"**决策原因**: {entry['reason'] or '未填写'}")
                st.markdown(f"**目标价**: ${entry['target_price']:.2f}" if entry['target_price'] else "**目标价**: 未设置")
                st.markdown(f"**止损位**: ${entry['stop_loss']:.2f}" if entry['stop_loss'] else "**止损位**: 未设置")

            with col2:
                st.markdown(f"**信心等级**: {entry['confidence_level']}/10" if entry['confidence_level'] else "")
                st.markdown(f"**情绪状态**: {entry['emotional_state'] or '未填写'}")
                st.markdown(f"**主要风险**: {entry['main_risks'] or '未填写'}")

            if entry['reviewed_at']:
                st.success("已复盘")
                st.markdown(f"**是否达标**: {'是' if entry['met_expectation'] else '否'}")
                if entry['lessons_learned']:
                    st.markdown(f"**经验教训**: {entry['lessons_learned']}")
            else:
                st.warning("待复盘")


def render_add_journal(journal, db):
    """渲染添加日志"""
    st.subheader("手动添加日志")

    # 获取最近没有日志的交易
    missing = journal.get_trades_without_journal()

    if not missing.empty:
        st.warning(f"有 {len(missing)} 笔交易尚未填写日志")

        selected_trade = st.selectbox(
            "选择要补充日志的交易",
            missing['transaction_id'].tolist(),
            format_func=lambda x: f"{missing[missing['transaction_id']==x].iloc[0]['transaction_date']} - "
                                 f"{missing[missing['transaction_id']==x].iloc[0]['stock_symbol']} "
                                 f"{missing[missing['transaction_id']==x].iloc[0]['transaction_type']}"
        )

        trade_info = missing[missing['transaction_id'] == selected_trade].iloc[0]

        st.markdown(f"""
        **交易详情:**
        - 日期: {trade_info['transaction_date']}
        - 股票: {trade_info['stock_symbol']}
        - 类型: {trade_info['transaction_type']}
        - 价格: ${trade_info['price']:.2f}
        - 股数: {trade_info['shares']}
        """)

    with st.form("manual_journal"):
        if missing.empty:
            symbol = st.text_input("股票代码")
            trade_type = st.selectbox("交易类型", ["股票买入", "股票卖出", "期权开仓", "期权平仓"])
            trade_date = st.date_input("交易日期")
            account = st.selectbox("账户", ACCOUNT_NAMES)
        else:
            symbol = trade_info['stock_symbol']
            trade_type = f"股票{trade_info['transaction_type']}"
            trade_date = trade_info['transaction_date']
            account = trade_info['account_name']

        reason = st.text_area("为什么现在交易？", placeholder="记录决策原因")

        col1, col2, col3 = st.columns(3)

        with col1:
            target_price = st.number_input("目标价 ($)", min_value=0.0, format="%.2f")

        with col2:
            stop_loss = st.number_input("止损位 ($)", min_value=0.0, format="%.2f")

        with col3:
            confidence = st.slider("信心等级", 1, 10, 5)

        col1, col2 = st.columns(2)

        with col1:
            emotional_state = st.selectbox("情绪状态", EMOTIONAL_STATES)

        with col2:
            main_risks = st.text_input("主要风险")

        submitted = st.form_submit_button("保存日志", type="primary", width='stretch')

        if submitted:
            if not reason:
                st.error("请填写决策原因")
            else:
                try:
                    journal.add_journal_entry({
                        'transaction_id': selected_trade if not missing.empty else None,
                        'stock_symbol': symbol,
                        'trade_type': trade_type,
                        'trade_date': trade_date,
                        'account_name': account,
                        'reason': reason,
                        'target_price': target_price if target_price > 0 else None,
                        'stop_loss': stop_loss if stop_loss > 0 else None,
                        'confidence_level': confidence,
                        'emotional_state': emotional_state,
                        'main_risks': main_risks if main_risks else None
                    })

                    st.success("日志已保存")
                    st.rerun()

                except Exception as e:
                    st.error(f"保存失败: {str(e)}")


def render_review(journal):
    """渲染复盘"""
    st.subheader("交易复盘")

    # 获取未复盘的日志
    unreviewed = journal.get_unreviewed_entries()

    if unreviewed.empty:
        st.success("所有日志都已复盘！")
        return

    st.info(f"有 {len(unreviewed)} 条日志待复盘")

    # 选择要复盘的日志
    selected_id = st.selectbox(
        "选择要复盘的日志",
        unreviewed['journal_id'].tolist(),
        format_func=lambda x: f"{unreviewed[unreviewed['journal_id']==x].iloc[0]['trade_date']} - "
                             f"{unreviewed[unreviewed['journal_id']==x].iloc[0]['stock_symbol']} "
                             f"{unreviewed[unreviewed['journal_id']==x].iloc[0]['trade_type']}"
    )

    entry = unreviewed[unreviewed['journal_id'] == selected_id].iloc[0]

    # 显示原始日志
    st.markdown("### 原始日志")
    st.markdown(f"**决策原因**: {entry['reason'] or '未填写'}")
    st.markdown(f"**目标价**: ${entry['target_price']:.2f}" if entry['target_price'] else "**目标价**: 未设置")
    st.markdown(f"**止损位**: ${entry['stop_loss']:.2f}" if entry['stop_loss'] else "**止损位**: 未设置")
    st.markdown(f"**信心等级**: {entry['confidence_level']}/10" if entry['confidence_level'] else "")

    # 复盘表单
    st.markdown("---")
    st.markdown("### 填写复盘")

    with st.form("review_form"):
        met_expectation = st.radio("是否达到预期？", ["是", "否"])

        deviation_reason = st.text_area(
            "偏离原因（如有）",
            placeholder="如果没有达到预期，分析原因"
        )

        lessons_learned = st.text_area(
            "经验教训",
            placeholder="从这次交易中学到什么？"
        )

        improvements = st.text_area(
            "改进建议",
            placeholder="下次如何做得更好？"
        )

        submitted = st.form_submit_button("保存复盘", type="primary", width='stretch')

        if submitted:
            try:
                journal.add_review(
                    journal_id=selected_id,
                    review_data={
                        'met_expectation': met_expectation == "是",
                        'deviation_reason': deviation_reason if deviation_reason else None,
                        'lessons_learned': lessons_learned if lessons_learned else None,
                        'improvements': improvements if improvements else None
                    }
                )

                st.success("复盘已保存")
                st.rerun()

            except Exception as e:
                st.error(f"保存失败: {str(e)}")
