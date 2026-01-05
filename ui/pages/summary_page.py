"""
总结中心页面
"""

import streamlit as st
from utils.constants import ACCOUNT_NAMES, SUMMARY_TYPES


def render(components):
    """渲染总结中心页面"""
    st.title("总结中心")

    summary_gen = components['summary_gen']
    db = components['db']

    tab1, tab2, tab3 = st.tabs(["生成总结", "待完成", "历史总结"])

    with tab1:
        render_generate_summary(summary_gen)

    with tab2:
        render_pending_summaries(summary_gen)

    with tab3:
        render_summary_history(summary_gen)


def render_generate_summary(summary_gen):
    """渲染生成总结"""
    st.subheader("生成新总结")

    summary_type = st.selectbox("总结类型", ["单股", "账户", "策略"])

    if summary_type == "单股":
        symbol = st.text_input("股票代码")
        account = st.selectbox("账户（可选）", ["全部"] + ACCOUNT_NAMES)
        period = st.number_input("分析周期（天）", min_value=30, max_value=365, value=90)

        if st.button("生成单股总结", type="primary"):
            if not symbol:
                st.error("请输入股票代码")
            else:
                result = summary_gen.generate_stock_summary(
                    symbol=symbol.upper(),
                    account=None if account == "全部" else account,
                    period_days=period
                )

                st.success(f"已生成 {symbol.upper()} 的总结模板")
                display_summary_template(result)

    elif summary_type == "账户":
        account = st.selectbox("账户", ACCOUNT_NAMES, key="acc_summary")
        period = st.selectbox("周期", ["monthly", "quarterly", "yearly"])

        if st.button("生成账户总结", type="primary"):
            result = summary_gen.generate_account_summary(
                account=account,
                period=period
            )

            st.success(f"已生成 {account} 的{period}总结模板")
            display_summary_template(result)

    elif summary_type == "策略":
        period = st.number_input("分析周期（天）", min_value=30, max_value=365, value=90, key="strategy_period")

        if st.button("生成策略总结", type="primary"):
            result = summary_gen.generate_strategy_summary(period_days=period)

            st.success("已生成策略总结模板")
            display_summary_template(result)


def display_summary_template(result):
    """显示总结模板"""
    st.markdown("---")
    st.markdown("### 自动生成的数据")

    auto_data = result.get('auto_data', {})

    for key, value in auto_data.items():
        if isinstance(value, dict):
            st.markdown(f"**{key}:**")
            for k, v in value.items():
                st.markdown(f"  - {k}: {v}")
        else:
            st.markdown(f"**{key}**: {value}")

    st.markdown("---")
    st.markdown("### 需要填写的内容")

    user_fields = result.get('user_fields', {})

    for field, placeholder in user_fields.items():
        st.text_area(field, placeholder=placeholder, key=f"field_{field}")

    st.info(f"总结ID: {result.get('summary_id')} - 请前往'待完成'标签页完成填写")


def render_pending_summaries(summary_gen):
    """渲染待完成的总结"""
    st.subheader("待完成的总结")

    pending = summary_gen.get_pending_summaries()

    if pending.empty:
        st.success("没有待完成的总结！")
        return

    for _, summary in pending.iterrows():
        with st.expander(
            f"{summary['summary_type']} - {summary['subject']} "
            f"({summary['created_at'][:10]})"
        ):
            st.markdown(f"**创建时间**: {summary['created_at']}")
            st.markdown(f"**周期**: {summary['period_start']} 至 {summary['period_end']}")

            # 自动生成的数据
            if summary['auto_generated_data']:
                st.markdown("**自动数据**: (已生成)")

            # 填写表单
            with st.form(f"complete_{summary['summary_id']}"):
                what_worked = st.text_area("成功之处 / 做对的事", key=f"ww_{summary['summary_id']}")
                what_failed = st.text_area("失败之处 / 犯的错误", key=f"wf_{summary['summary_id']}")
                market_obs = st.text_area("市场观察", key=f"mo_{summary['summary_id']}")
                future_plans = st.text_area("未来计划", key=f"fp_{summary['summary_id']}")
                lessons = st.text_area("经验教训", key=f"ll_{summary['summary_id']}")
                methodology = st.text_area("方法论更新", key=f"mu_{summary['summary_id']}")

                if st.form_submit_button("保存并完成"):
                    summary_gen.complete_summary(
                        summary_id=summary['summary_id'],
                        user_data={
                            'what_worked': what_worked,
                            'what_failed': what_failed,
                            'market_observations': market_obs,
                            'future_plans': future_plans,
                            'lessons_learned': lessons,
                            'methodology_updates': methodology
                        }
                    )
                    st.success("总结已完成！")
                    st.rerun()


def render_summary_history(summary_gen):
    """渲染历史总结"""
    st.subheader("历史总结")

    # 筛选
    col1, col2 = st.columns(2)

    with col1:
        type_filter = st.selectbox("类型筛选", ["全部"] + SUMMARY_TYPES)

    with col2:
        status_filter = st.selectbox("状态筛选", ["全部", "已完成", "草稿"])

    # 获取总结
    summaries = summary_gen.db.get_summaries(
        summary_type=None if type_filter == "全部" else type_filter,
        status=None if status_filter == "全部" else status_filter
    )

    if summaries.empty:
        st.info("暂无历史总结")
        return

    # 显示列表
    for _, summary in summaries.iterrows():
        status_icon = "✅" if summary['completion_status'] == '已完成' else "📝"

        with st.expander(
            f"{status_icon} {summary['summary_type']} - {summary['subject']} "
            f"({summary['created_at'][:10]})"
        ):
            st.markdown(f"**状态**: {summary['completion_status']}")
            st.markdown(f"**周期**: {summary['period_start']} 至 {summary['period_end']}")

            if summary['what_worked']:
                st.markdown(f"**成功之处**: {summary['what_worked']}")

            if summary['what_failed']:
                st.markdown(f"**失败之处**: {summary['what_failed']}")

            if summary['lessons_learned']:
                st.markdown(f"**经验教训**: {summary['lessons_learned']}")

            if summary['future_plans']:
                st.markdown(f"**未来计划**: {summary['future_plans']}")

    # 经验教训汇总
    st.markdown("---")
    st.subheader("经验教训汇总")

    lessons = summary_gen.get_all_lessons_learned(limit=10)

    if lessons:
        for i, lesson in enumerate(lessons, 1):
            st.markdown(f"{i}. {lesson}")
    else:
        st.info("暂无经验教训记录")
