"""
投资组合管理系统 - Streamlit主界面
"""

import streamlit as st
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import Database
from core.calculator import PortfolioCalculator
from core.cash_flow import CashFlowManager
from core.attribution import PerformanceAttribution
from core.correlation import CorrelationAnalyzer
from decision.option_strategy import OptionStrategyEngine
from decision.alert_system import PriceAlertSystem
from decision.position_manager import PositionManager
from reflection.journal import TradingJournal
from reflection.summary import SummaryGenerator
from visualization.charts import ChartBuilder
import config

# 页面配置
st.set_page_config(
    page_title=config.STREAMLIT_CONFIG['page_title'],
    page_icon=config.STREAMLIT_CONFIG['page_icon'],
    layout=config.STREAMLIT_CONFIG['layout']
)


# 初始化系统
@st.cache_resource
def init_system():
    """初始化所有组件"""
    db = Database(config.DATABASE_PATH)
    calc = PortfolioCalculator(db)
    cash_flow_mgr = CashFlowManager(db)
    attribution = PerformanceAttribution(db)
    correlation = CorrelationAnalyzer(db)
    option_engine = OptionStrategyEngine(db)
    alert_system = PriceAlertSystem(db, email_config=config.EMAIL_CONFIG)
    position_mgr = PositionManager(db, calc)
    journal = TradingJournal(db)
    summary_gen = SummaryGenerator(db, calc)
    chart_builder = ChartBuilder()

    return {
        'db': db,
        'calc': calc,
        'cash_flow': cash_flow_mgr,
        'attribution': attribution,
        'correlation': correlation,
        'option_engine': option_engine,
        'alert_system': alert_system,
        'position_mgr': position_mgr,
        'journal': journal,
        'summary_gen': summary_gen,
        'chart_builder': chart_builder,
    }


# 获取所有组件
components = init_system()

# 自动启动预警监控（如果配置启用）
if config.ALERT_MONITORING_CONFIG['auto_start']:
    if 'monitoring_auto_started' not in st.session_state:
        from utils.data_fetcher import batch_get_prices

        def price_fetcher(symbols):
            return batch_get_prices(symbols)

        if not components['alert_system'].monitoring:
            interval = config.ALERT_MONITORING_CONFIG['check_interval']
            components['alert_system'].start_monitoring(price_fetcher, interval=interval)
            st.session_state.monitoring_auto_started = True

# 侧边栏导航
st.sidebar.title("投资组合管理系统")
st.sidebar.markdown("---")

page = st.sidebar.selectbox(
    "选择功能",
    [
        "账户总览",
        "录入交易",
        "录入期权",
        "期权策略评估",
        "价格预警",
        "仓位管理",
        "现金流分析",
        "业绩归因",
        "相关性分析",
        "交易日志",
        "总结中心",
        "数据管理",
    ]
)

account_filter = st.sidebar.selectbox(
    "账户筛选",
    ["全部", "长期账户", "波段账户"]
)

st.sidebar.markdown("---")

# 价格预警监控控制
st.sidebar.subheader("📊 预警监控")

# 初始化监控状态
if 'monitoring_enabled' not in st.session_state:
    st.session_state.monitoring_enabled = False

# 检查监控状态
is_monitoring = components['alert_system'].monitoring

col1, col2 = st.sidebar.columns([3, 1])
with col1:
    if is_monitoring:
        st.sidebar.success("🟢 监控运行中")
    else:
        st.sidebar.info("⚪ 监控已停止")

with col2:
    if is_monitoring:
        if st.sidebar.button("⏸️", help="停止监控", key="stop_monitoring"):
            components['alert_system'].stop_monitoring()
            st.session_state.monitoring_enabled = False
            st.rerun()
    else:
        if st.sidebar.button("▶️", help="启动监控", key="start_monitoring"):
            from utils.data_fetcher import batch_get_prices

            def price_fetcher(symbols):
                return batch_get_prices(symbols)

            # 使用配置的检查间隔
            interval = config.ALERT_MONITORING_CONFIG['check_interval']
            components['alert_system'].start_monitoring(price_fetcher, interval=interval)
            st.session_state.monitoring_enabled = True
            st.rerun()

# 显示监控详细信息
monitoring_info = components['alert_system'].get_monitoring_info()
active_alerts = components['alert_system'].get_active_alerts()

if not active_alerts.empty:
    st.sidebar.caption(f"激活预警: {len(active_alerts)} 个")

# 显示监控股票统计
total_stocks = monitoring_info.get('total_stock_count', 0)
alert_stocks = monitoring_info.get('alert_stock_count', 0)
holding_stocks = monitoring_info.get('holding_stock_count', 0)

if total_stocks > 0:
    st.sidebar.caption(f"监控股票: {total_stocks} 个 (预警{alert_stocks} + 持仓{holding_stocks})")

if is_monitoring:
    interval_sec = monitoring_info['current_interval']
    interval_min = interval_sec / 60

    # 显示间隔信息
    if monitoring_info['dynamic_mode']:
        st.sidebar.caption(f"🔄 动态间隔: {interval_min:.1f} 分钟")
        # 显示预计API调用量
        calls_per_hour = monitoring_info.get('requests_per_hour', 0)
        st.sidebar.caption(f"预计: ~{calls_per_hour} 次/小时")
    else:
        st.sidebar.caption(f"检查间隔: {interval_min:.0f} 分钟")

st.sidebar.markdown("---")

# 显示提醒
reminders = []

# 检查未复盘的日志
unreviewed = components['journal'].get_unreviewed_entries()
if not unreviewed.empty:
    reminders.append(f"有 {len(unreviewed)} 条日志待复盘")

# 检查未完成的总结
pending = components['summary_gen'].get_pending_summaries()
if not pending.empty:
    reminders.append(f"有 {len(pending)} 个总结待完成")

# 检查已触发的预警
triggered_alerts = components['alert_system'].get_triggered_alerts()
if not triggered_alerts.empty:
    reminders.append(f"⚠️ 有 {len(triggered_alerts)} 个预警已触发")

if reminders:
    st.sidebar.warning("\n".join(reminders))
else:
    st.sidebar.success("所有任务已完成")

st.sidebar.markdown("---")
st.sidebar.info("提示：每次交易后记得填写日志")

# 主页面路由
if page == "账户总览":
    from ui.pages import dashboard_overview
    dashboard_overview.render(components, account_filter)

elif page == "录入交易":
    from ui.pages import input_transaction
    input_transaction.render(components)

elif page == "录入期权":
    from ui.pages import input_option
    input_option.render(components)

elif page == "期权策略评估":
    from ui.pages import option_evaluation
    option_evaluation.render(components)

elif page == "价格预警":
    from ui.pages import price_alerts
    price_alerts.render(components)

elif page == "仓位管理":
    from ui.pages import position_management
    position_management.render(components)

elif page == "现金流分析":
    from ui.pages import cash_flow_page
    cash_flow_page.render(components)

elif page == "业绩归因":
    from ui.pages import attribution_page
    attribution_page.render(components)

elif page == "相关性分析":
    from ui.pages import correlation_page
    correlation_page.render(components)

elif page == "交易日志":
    from ui.pages import journal_page
    journal_page.render(components)

elif page == "总结中心":
    from ui.pages import summary_page
    summary_page.render(components)

elif page == "数据管理":
    from ui.pages import data_management
    data_management.render(components)
