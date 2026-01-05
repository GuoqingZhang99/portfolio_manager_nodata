"""
数据管理页面
"""

import streamlit as st
from datetime import datetime
from utils.constants import ACCOUNT_NAMES


def render(components):
    """渲染数据管理页面"""
    st.title("数据管理")

    db = components['db']

    tab1, tab2, tab3, tab4 = st.tabs(["账户设置", "数据备份", "数据导入", "数据清理"])

    with tab1:
        render_account_settings(db)

    with tab2:
        render_backup(db)

    with tab3:
        render_import(db)

    with tab4:
        render_cleanup(db)


def render_account_settings(db):
    """渲染账户设置"""
    st.subheader("账户配置")

    accounts = db.get_accounts()

    if accounts.empty:
        st.warning("没有账户数据")
        return

    for _, account in accounts.iterrows():
        with st.expander(f"编辑: {account['account_name']}"):
            with st.form(f"account_{account['account_id']}"):
                col1, col2 = st.columns(2)

                with col1:
                    total_capital = st.number_input(
                        "总资金 ($)",
                        value=float(account['total_capital']),
                        format="%.2f",
                        key=f"tc_{account['account_id']}"
                    )

                    cash_reserve = st.number_input(
                        "现金储备 ($)",
                        value=float(account['cash_reserve'] or 0),
                        format="%.2f",
                        key=f"cr_{account['account_id']}"
                    )

                with col2:
                    conditional_reserve = st.number_input(
                        "条件性预留 ($)",
                        value=float(account['conditional_reserve'] or 0),
                        format="%.2f",
                        key=f"cdr_{account['account_id']}"
                    )

                    target_min = st.number_input(
                        "目标仓位下限 (%)",
                        value=float(account['target_position_min'] or 0),
                        format="%.1f",
                        key=f"tmin_{account['account_id']}"
                    )

                    target_max = st.number_input(
                        "目标仓位上限 (%)",
                        value=float(account['target_position_max'] or 100),
                        format="%.1f",
                        key=f"tmax_{account['account_id']}"
                    )

                if st.form_submit_button("保存更改"):
                    db.update_account(
                        account_name=account['account_name'],
                        total_capital=total_capital,
                        cash_reserve=cash_reserve,
                        conditional_reserve=conditional_reserve,
                        target_min=target_min,
                        target_max=target_max
                    )
                    st.success(f"已更新 {account['account_name']}")
                    st.rerun()


def render_backup(db):
    """渲染备份"""
    st.subheader("数据备份")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("立即备份", type="primary", width='stretch'):
            try:
                backup_path = db.backup_database()
                st.success(f"备份成功！\n文件: {backup_path}")
            except Exception as e:
                st.error(f"备份失败: {str(e)}")

    with col2:
        st.info("备份将保存到 data/backups/ 目录")

    # 显示现有备份
    st.markdown("---")
    st.subheader("现有备份")

    backups = db.get_backups()

    if not backups:
        st.info("暂无备份文件")
    else:
        for backup in backups:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"**{backup['filename']}**")

            with col2:
                st.caption(f"{backup['modified'].strftime('%Y-%m-%d %H:%M')}")
                st.caption(f"{backup['size'] / 1024:.1f} KB")

            with col3:
                if st.button("恢复", key=f"restore_{backup['filename']}"):
                    if st.session_state.get(f"confirm_restore_{backup['filename']}"):
                        db.restore_database(backup['path'])
                        st.success("恢复成功！请刷新页面")
                        del st.session_state[f"confirm_restore_{backup['filename']}"]
                    else:
                        st.session_state[f"confirm_restore_{backup['filename']}"] = True
                        st.warning("再次点击确认恢复")


def render_import(db):
    """渲染数据导入"""
    st.subheader("数据导入")

    st.warning("导入功能会覆盖现有数据，请先备份！")

    uploaded_file = st.file_uploader(
        "上传CSV文件",
        type=['csv'],
        help="支持导入交易记录、期权记录等"
    )

    if uploaded_file:
        import pandas as pd

        try:
            df = pd.read_csv(uploaded_file)
            st.markdown("### 文件预览")
            st.dataframe(df.head(10))

            import_type = st.selectbox(
                "选择导入类型",
                ["交易记录", "期权记录", "分红记录"]
            )

            if st.button("开始导入", type="primary"):
                st.info("导入功能开发中...")
                # TODO: 实现具体导入逻辑

        except Exception as e:
            st.error(f"读取文件失败: {str(e)}")


def render_cleanup(db):
    """渲染数据清理"""
    st.subheader("数据清理")

    st.error("警告：以下操作不可恢复，请谨慎操作！")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 清理旧数据")

        if st.button("清理90天前的股价历史"):
            st.info("清理功能开发中...")

    with col2:
        st.markdown("### 数据统计")

        # 统计各表数据量
        conn = db.get_connection()

        tables = [
            ('transactions', '交易记录'),
            ('options_trades', '期权记录'),
            ('cash_flows', '现金流记录'),
            ('trading_journal', '交易日志'),
            ('price_alerts', '价格预警'),
            ('summaries', '总结记录')
        ]

        for table, name in tables:
            try:
                cursor = conn.cursor()
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                count = cursor.fetchone()[0]
                st.markdown(f"- {name}: **{count}** 条")
            except:
                pass

        conn.close()

    # 数据库优化
    st.markdown("---")
    st.subheader("数据库优化")

    if st.button("优化数据库 (VACUUM)"):
        try:
            conn = db.get_connection()
            conn.execute('VACUUM')
            conn.close()
            st.success("数据库优化完成")
        except Exception as e:
            st.error(f"优化失败: {str(e)}")
