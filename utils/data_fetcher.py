"""
股价数据获取模块
"""

from yahooquery import Ticker
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import time
from functools import wraps
import logging
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# 设置 yfinance 日志级别为 CRITICAL，抑制警告
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


def get_current_price(symbol, max_retries=2, delay=1.0):
    """
    获取股票当前价格（使用 yahooquery）

    Args:
        symbol: 股票代码
        max_retries: 最大重试次数
        delay: 重试延迟（秒）

    Returns:
        float: 当前价格，失败返回None
    """
    for attempt in range(max_retries):
        try:
            stock = Ticker(symbol)
            price_data = stock.price

            if symbol in price_data and isinstance(price_data[symbol], dict):
                # 尝试获取当前价格（优先级：盘中价格 > 盘后价格 > 盘前价格）
                price = price_data[symbol].get('regularMarketPrice') or \
                        price_data[symbol].get('postMarketPrice') or \
                        price_data[symbol].get('preMarketPrice')

                if price and price > 0:
                    return round(price, 2)

            # 如果失败，重试
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue

    return None


# ============================================================================
# 备份实现（保留以防主要数据源失败）
# ============================================================================

def get_current_price_yfinance(symbol, max_retries=2, delay=2.0):
    """
    获取股票当前价格（使用 yfinance - 备用方案）
    已弃用：改用 yahooquery，此函数保留作为备份
    """
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(symbol)

            # 方法1: 使用最简单的 history(period='5d')
            try:
                hist = ticker.history(period='5d')
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
                    if price and price > 0:
                        return round(price, 2)
            except Exception:
                pass

            # 方法2: 尝试 fast_info
            try:
                if hasattr(ticker, 'fast_info'):
                    price = ticker.fast_info.get('lastPrice') or ticker.fast_info.get('regularMarketPrice')
                    if price and price > 0:
                        return round(price, 2)
            except Exception:
                pass

            # 如果所有方法都失败，重试
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            else:
                return None

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay * (attempt + 1))
                continue

    return None


# ============================================================================
# 以下是原 Alpha Vantage 实现（已弃用，保留作为备份）
# ============================================================================
def get_current_price_alphavantage(symbol, max_retries=3, delay=1.0):
    """
    获取股票最近收盘价（使用 Alpha Vantage API）
    已弃用：改用 yfinance，此函数保留作为备份
    """
    import random
    import requests
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')

    if not api_key:
        print(f"❌ {symbol}: 缺少 ALPHAVANTAGE_API_KEY")
        return None

    for attempt in range(max_retries):
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            # 检查响应
            if 'Global Quote' in data and '05. price' in data['Global Quote']:
                price = float(data['Global Quote']['05. price'])
                return round(price, 2)
            elif 'Note' in data:
                # API 速率限制
                if attempt == max_retries - 1:
                    print(f"⚠️ {symbol}: API 速率限制")
                    return None
            elif 'Information' in data:
                # 超过每日限额或需要等待
                if attempt == max_retries - 1:
                    print(f"⚠️ {symbol}: API 限额已用完")
                    return None
            else:
                if attempt == max_retries - 1:
                    print(f"❌ {symbol}: 无效响应")
                    return None

        except Exception as e:
            if attempt == max_retries - 1:
                msg = str(e)
                print(f"❌ {symbol}: {msg[:120]}")
                return None

        # 等待后重试（Alpha Vantage 限制：每秒1次）
        if attempt < max_retries - 1:
            time.sleep(delay * (attempt + 1) + random.uniform(0, 0.3))

    return None


def get_historical_prices(symbol, start_date, end_date):
    """
    获取历史价格

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        DataFrame: 包含日期、收盘价、成交量
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)

        if not data.empty:
            data['daily_return'] = data['Close'].pct_change()
            return data[['Close', 'Volume', 'daily_return']]
        return None
    except Exception as e:
        print(f"获取{symbol}历史数据失败: {e}")
        return None


def batch_get_prices(symbols, use_batch=True, force_refresh=False):
    """
    批量获取股价（使用 yahooquery，支持盘中/盘后智能切换）

    Args:
        symbols: 股票代码列表
        use_batch: 是否使用批量获取（推荐True，性能更好）
        force_refresh: 是否强制刷新价格（忽略缓存）

    Returns:
        dict: {symbol: price}
    """
    if not symbols:
        print("⚠️ 没有需要获取的股票代码")
        return {}

    prices = {}

    # 检测市场状态
    try:
        from utils.market_hours import get_market_status
        market_status = get_market_status()
        is_market_open = market_status['is_open']
        status_msg = market_status['status']
    except:
        is_market_open = True  # 默认假设开盘
        status_msg = "无法检测市场状态"

    # 盘后/周末：优先使用今日缓存，避免重复API调用
    if not is_market_open and not force_refresh:
        try:
            from utils.price_sources import get_price_manager
            from datetime import datetime, timedelta
            import pytz

            price_manager = get_price_manager()
            manual_prices = price_manager.get_manual_prices()
            timestamps = price_manager.get_all_timestamps()

            # 获取当前日期
            eastern = pytz.timezone('America/New_York')
            now_et = datetime.now(eastern)
            today_date = now_et.date()

            print(f"📊 市场状态: {status_msg}")
            print(f"💡 盘后策略: 优先使用今日收盘价缓存")

            # 检查缓存：只使用今日的缓存
            cached_today_count = 0
            need_fetch = []

            for symbol in symbols:
                has_today_cache = False

                if symbol in manual_prices:
                    # 检查时间戳是否是今天的
                    timestamp_str = timestamps.get(symbol)
                    if timestamp_str:
                        try:
                            cached_time = datetime.fromisoformat(timestamp_str)
                            cached_time_et = cached_time.astimezone(eastern)
                            cached_date = cached_time_et.date()

                            # 只使用今天的缓存
                            if cached_date == today_date:
                                prices[symbol] = manual_prices[symbol]
                                cached_today_count += 1
                                print(f"  ✓ {symbol}: ${prices[symbol]:.2f} (今日收盘价缓存)")
                                has_today_cache = True
                        except:
                            pass

                # 如果没有今日缓存，需要获取
                if not has_today_cache:
                    need_fetch.append(symbol)

            if not need_fetch:
                print(f"✅ 全部使用今日缓存（{cached_today_count} 个），无需调用API")
                return prices
            else:
                print(f"💡 {cached_today_count} 个使用今日缓存，{len(need_fetch)} 个需要获取收盘价")
                print(f"📥 首次获取收盘价: {', '.join(need_fetch)}")
                # 更新symbols为需要获取的
                symbols = need_fetch

        except ImportError:
            pass

    # 盘中或强制刷新：正常获取价格
    if force_refresh:
        print(f"🔄 强制刷新价格（忽略缓存）")
    else:
        print(f"📊 市场状态: {status_msg}")

    # 使用批量获取（yahooquery优势：一次性获取所有股票）
    if use_batch and len(symbols) > 0:
        print(f"📊 批量获取 {len(symbols)} 个股票的价格（yahooquery）...")
        try:
            tickers = Ticker(symbols)
            prices_data = tickers.price

            fetched_count = 0
            for symbol in symbols:
                if symbol in prices_data and isinstance(prices_data[symbol], dict):
                    price = prices_data[symbol].get('regularMarketPrice') or \
                            prices_data[symbol].get('postMarketPrice') or \
                            prices_data[symbol].get('preMarketPrice')

                    if price and price > 0:
                        prices[symbol] = round(price, 2)
                        fetched_count += 1
                        print(f"  ✓ {symbol}: ${prices[symbol]:.2f}")

                        # 保存到缓存管理器（供下次使用）
                        try:
                            from utils.price_sources import get_price_manager
                            price_manager = get_price_manager()
                            price_manager.set_manual_price(symbol, prices[symbol])
                        except:
                            pass

            if fetched_count > 0:
                print(f"✅ 批量获取成功 {fetched_count}/{len(symbols)} 个价格")
            else:
                print(f"⚠️ 批量获取失败，尝试逐个获取...")
                use_batch = False  # 降级到逐个获取

        except Exception as e:
            print(f"⚠️ 批量获取失败: {str(e)[:100]}，尝试逐个获取...")
            use_batch = False  # 降级到逐个获取

    # 逐个获取（作为降级方案）
    if not use_batch:
        print(f"📊 逐个获取 {len(symbols)} 个股票的价格...")
        for i, symbol in enumerate(symbols, 1):
            if symbol in prices:  # 已经获取过了
                continue

            print(f"  [{i}/{len(symbols)}] {symbol}...", end=' ')
            price = get_current_price(symbol)
            if price:
                prices[symbol] = price
                print(f"${price:.2f} ✅")

                # 保存到缓存管理器（供下次使用）
                try:
                    from utils.price_sources import get_price_manager
                    price_manager = get_price_manager()
                    price_manager.set_manual_price(symbol, price)
                except:
                    pass
            else:
                print(f"❌")

            # 间隔时间，避免速率限制
            if i < len(symbols):
                time.sleep(0.5)

    return prices


def get_stock_info(symbol):
    """
    获取股票基本信息

    Args:
        symbol: 股票代码

    Returns:
        dict: 股票信息
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return {
            'symbol': symbol,
            'name': info.get('shortName', ''),
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 1),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
        }
    except Exception as e:
        print(f"获取{symbol}信息失败: {e}")
        return None


def update_price_history(db, symbol, days=90):
    """
    更新股价历史到数据库

    Args:
        db: Database实例
        symbol: 股票代码
        days: 更新天数
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    hist = get_historical_prices(symbol, start_date, end_date)

    if hist is not None and not hist.empty:
        for date, row in hist.iterrows():
            db.add_price_history(
                symbol=symbol,
                price_date=date.date(),
                close_price=row['Close'],
                daily_return=row['daily_return'] if pd.notna(row['daily_return']) else None,
                volume=int(row['Volume']) if pd.notna(row['Volume']) else None
            )


def update_benchmark_history(db, symbol='SPY', days=90):
    """
    更新基准指数历史到数据库

    Args:
        db: Database实例
        symbol: 基准指数代码
        days: 更新天数
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    hist = get_historical_prices(symbol, start_date, end_date)

    if hist is not None and not hist.empty:
        conn = db.get_connection()
        cursor = conn.cursor()

        for date, row in hist.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO benchmark_prices
                (benchmark_symbol, price_date, close_price, daily_return)
                VALUES (?, ?, ?, ?)
            ''', (
                symbol,
                date.date(),
                row['Close'],
                row['daily_return'] if pd.notna(row['daily_return']) else None
            ))

        conn.commit()
        conn.close()


def get_dividend_history(symbol, years=2):
    """
    获取分红历史

    Args:
        symbol: 股票代码
        years: 查询年数

    Returns:
        DataFrame: 分红记录
    """
    try:
        ticker = yf.Ticker(symbol)
        dividends = ticker.dividends

        if dividends.empty:
            return pd.DataFrame()

        # 筛选时间范围
        cutoff_date = datetime.now() - timedelta(days=years * 365)
        dividends = dividends[dividends.index >= cutoff_date]

        df = dividends.reset_index()
        df.columns = ['date', 'dividend']

        return df
    except Exception as e:
        print(f"获取{symbol}分红历史失败: {e}")
        return pd.DataFrame()


def get_options_chain(symbol, expiration_date=None):
    """
    获取期权链

    Args:
        symbol: 股票代码
        expiration_date: 到期日（可选）

    Returns:
        dict: 包含calls和puts的期权链
    """
    try:
        ticker = yf.Ticker(symbol)

        # 获取可用到期日
        expirations = ticker.options

        if not expirations:
            return None

        if expiration_date is None:
            expiration_date = expirations[0]

        opt_chain = ticker.option_chain(expiration_date)

        return {
            'expiration': expiration_date,
            'calls': opt_chain.calls.to_dict('records'),
            'puts': opt_chain.puts.to_dict('records')
        }
    except Exception as e:
        print(f"获取{symbol}期权链失败: {e}")
        return None


def calculate_volatility(symbol, days=30):
    """
    计算历史波动率

    Args:
        symbol: 股票代码
        days: 计算天数

    Returns:
        float: 年化波动率
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)  # 多获取一些数据

        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_date, end=end_date)

        if len(data) < days:
            return None

        # 计算日收益率
        returns = data['Close'].pct_change().dropna()

        # 取最近N天
        returns = returns.tail(days)

        # 计算年化波动率
        volatility = returns.std() * (252 ** 0.5)

        return round(volatility, 4)
    except Exception as e:
        print(f"计算{symbol}波动率失败: {e}")
        return None


def get_risk_return_data(symbols, days=90):
    """
    获取风险收益数据

    Args:
        symbols: 股票代码列表
        days: 计算天数

    Returns:
        dict: {symbol: {'volatility': float, 'return': float}}
    """
    result = {}

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    for symbol in symbols:
        try:
            hist = get_historical_prices(symbol, start_date, end_date)

            if hist is not None and len(hist) > 10:
                returns = hist['daily_return'].dropna()
                volatility = returns.std() * (252 ** 0.5)
                total_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1

                result[symbol] = {
                    'volatility': volatility,
                    'return': total_return
                }
        except Exception as e:
            print(f"获取{symbol}风险收益数据失败: {e}")
            continue

    return result
