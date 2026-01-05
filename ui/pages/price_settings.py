"""
价格数据源设置页面
"""

import streamlit as st
from utils.price_sources import get_price_manager, batch_get_prices_multi_source


def render(components):
    """渲染价格设置页面"""
    st.title("价格数据源设置")

    calc = components['calc']
    price_manager = get_price_manager()

    tab1, tab2, tab3 = st.tabs(["手动输入价格", "API 数据源", "测试数据源"])

    with tab1:
        render_manual_prices(calc, price_manager)

    with tab2:
        render_api_settings()

    with tab3:
        render_test_sources(calc)


def render_manual_prices(calc, price_manager):
    """渲染手动输入价格"""
    st.subheader("手动输入股票价格")

    st.info("💡 如果自动获取价格失败，可以手动输入当前价格作为临时方案")

    # 获取所有持仓股票
    stocks = calc.calculate_stock_summary()

    if stocks.empty:
        st.warning("暂无持仓股票")
        return

    symbols = stocks['股票代码'].unique().tolist()

    st.markdown("### 批量输入")

    # 显示当前手动价格
    manual_prices = price_manager.get_manual_prices()
    if manual_prices:
        st.success(f"已设置 {len(manual_prices)} 个手动价格")
        for symbol, price in manual_prices.items():
            st.caption(f"{symbol}: ${price:.2f}")

    with st.form("batch_manual_prices"):
        st.markdown("**为所有持仓股票输入价格：**")

        prices_input = {}
        cols_per_row = 3
        rows = (len(symbols) + cols_per_row - 1) // cols_per_row

        for row in range(rows):
            cols = st.columns(cols_per_row)
            for i, col in enumerate(cols):
                idx = row * cols_per_row + i
                if idx < len(symbols):
                    symbol = symbols[idx]
                    current_price = manual_prices.get(symbol, 0.0)
                    with col:
                        prices_input[symbol] = st.number_input(
                            symbol,
                            min_value=0.01,
                            value=float(current_price) if current_price else 100.0,
                            format="%.2f",
                            key=f"price_{symbol}"
                        )

        submitted = st.form_submit_button("保存所有价格", type="primary", width='stretch')

        if submitted:
            count = 0
            for symbol, price in prices_input.items():
                if price > 0:
                    price_manager.set_manual_price(symbol, price)
                    count += 1

            st.success(f"✅ 已保存 {count} 个股票的手动价格")
            st.rerun()

    # 清除手动价格
    if manual_prices:
        st.markdown("---")
        if st.button("🗑️ 清除所有手动价格", width='stretch'):
            price_manager.clear_manual_prices()
            st.success("已清除所有手动价格")
            st.rerun()


def render_api_settings():
    """渲染 API 设置"""
    st.subheader("配置 API 数据源")

    st.markdown("""
    如果 Yahoo Finance 无法访问，可以使用以下免费 API 服务：
    """)

    # Alpha Vantage
    with st.expander("📈 Alpha Vantage (推荐)", expanded=True):
        st.markdown("""
        **优点**：
        - 免费，数据可靠
        - 支持美股、全球股市

        **限制**：
        - 每分钟 5 次请求
        - 每天 500 次请求

        **注册地址**：
        [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
        """)

        alphavantage_key = st.text_input(
            "Alpha Vantage API Key",
            type="password",
            placeholder="输入您的 API Key",
            key="alphavantage_key"
        )

        if alphavantage_key:
            if st.button("测试 Alpha Vantage"):
                from utils.price_sources import PriceSourceManager
                manager = PriceSourceManager()
                price = manager._get_price_alphavantage('AAPL', alphavantage_key)
                if price:
                    st.success(f"✅ 测试成功！AAPL 价格: ${price:.2f}")
                else:
                    st.error("❌ 测试失败，请检查 API Key")

            # 保存到 session state
            st.session_state['alphavantage_api_key'] = alphavantage_key

    # Finnhub
    with st.expander("📊 Finnhub"):
        st.markdown("""
        **优点**：
        - 免费，实时数据
        - 每分钟 60 次请求

        **限制**：
        - 免费版功能有限

        **注册地址**：
        [https://finnhub.io/register](https://finnhub.io/register)
        """)

        finnhub_key = st.text_input(
            "Finnhub API Key",
            type="password",
            placeholder="输入您的 API Key",
            key="finnhub_key"
        )

        if finnhub_key:
            if st.button("测试 Finnhub"):
                from utils.price_sources import PriceSourceManager
                manager = PriceSourceManager()
                price = manager._get_price_finnhub('AAPL', finnhub_key)
                if price:
                    st.success(f"✅ 测试成功！AAPL 价格: ${price:.2f}")
                else:
                    st.error("❌ 测试失败，请检查 API Key")

            st.session_state['finnhub_api_key'] = finnhub_key

    # 数据源优先级
    st.markdown("---")
    st.subheader("数据源优先级")

    source_priority = st.multiselect(
        "选择数据源顺序（从上到下尝试）",
        ['manual', 'yfinance', 'alphavantage', 'finnhub'],
        default=['manual', 'yfinance', 'alphavantage'],
        help="系统会按顺序尝试获取价格，直到成功"
    )

    if source_priority:
        st.session_state['price_source_priority'] = source_priority
        st.success(f"✅ 数据源优先级: {' → '.join(source_priority)}")


def render_test_sources(calc):
    """测试数据源"""
    st.subheader("测试数据源")

    # 获取持仓股票
    stocks = calc.calculate_stock_summary()

    if stocks.empty:
        st.warning("暂无持仓股票")
        return

    symbols = stocks['股票代码'].unique().tolist()[:3]  # 只测试前3个

    st.markdown(f"将测试获取以下股票的价格: {', '.join(symbols)}")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🧪 测试 Yahoo Finance", width='stretch'):
            test_yfinance(symbols)

    with col2:
        if st.button("🧪 测试 Alpha Vantage", width='stretch'):
            api_key = st.session_state.get('alphavantage_api_key')
            if api_key:
                test_alphavantage(symbols, api_key)
            else:
                st.error("请先在 API 数据源标签中配置 Alpha Vantage API Key")

    # 测试手动价格
    if st.button("🧪 测试手动价格", width='stretch'):
        price_manager = get_price_manager()
        manual_prices = price_manager.get_manual_prices()

        if not manual_prices:
            st.warning("尚未设置手动价格")
        else:
            st.success(f"已设置 {len(manual_prices)} 个手动价格：")
            for symbol in symbols:
                if symbol in manual_prices:
                    st.write(f"✓ {symbol}: ${manual_prices[symbol]:.2f}")
                else:
                    st.write(f"✗ {symbol}: 未设置")


def test_yfinance(symbols):
    """测试 yfinance"""
    from utils.data_fetcher import batch_get_prices

    with st.spinner("正在测试 Yahoo Finance..."):
        prices = batch_get_prices(symbols)

    if prices:
        st.success(f"✅ 成功获取 {len(prices)}/{len(symbols)} 个价格")
        for symbol, price in prices.items():
            st.write(f"✓ {symbol}: ${price:.2f}")
    else:
        st.error("❌ Yahoo Finance 获取失败")


def test_alphavantage(symbols, api_key):
    """测试 Alpha Vantage"""
    with st.spinner("正在测试 Alpha Vantage..."):
        prices = batch_get_prices_multi_source(
            symbols[:1],  # Alpha Vantage 免费版慢，只测试1个
            source='alphavantage',
            api_key=api_key
        )

    if prices:
        st.success(f"✅ Alpha Vantage 可用")
        for symbol, price in prices.items():
            st.write(f"✓ {symbol}: ${price:.2f}")
    else:
        st.error("❌ Alpha Vantage 获取失败，请检查 API Key")
