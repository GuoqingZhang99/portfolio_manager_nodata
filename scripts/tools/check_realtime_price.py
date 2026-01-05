"""
检查实时价格数据
"""

import sys
import io
import os
from datetime import datetime
import pytz

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
import requests
import yfinance as yf

load_dotenv()

# 获取当前时间
now_utc = datetime.now(pytz.UTC)
now_et = now_utc.astimezone(pytz.timezone('America/New_York'))

print(f"当前时间（美东）: {now_et.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"当前时间（本地）: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 测试 Alpha Vantage - GLOBAL_QUOTE
print("=" * 60)
print("测试 1: Alpha Vantage - GLOBAL_QUOTE")
print("=" * 60)

api_key = os.getenv('ALPHAVANTAGE_API_KEY')
symbol = 'NVDA'

url = "https://www.alphavantage.co/query"
params = {
    'function': 'GLOBAL_QUOTE',
    'symbol': symbol,
    'apikey': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    if 'Global Quote' in data:
        quote = data['Global Quote']
        print(f"股票代码: {quote.get('01. symbol', 'N/A')}")
        print(f"价格: ${quote.get('05. price', 'N/A')}")
        print(f"交易日期: {quote.get('07. latest trading day', 'N/A')}")
        print(f"前收盘价: ${quote.get('08. previous close', 'N/A')}")
        print(f"涨跌: ${quote.get('09. change', 'N/A')}")
        print(f"涨跌幅: {quote.get('10. change percent', 'N/A')}")
    else:
        print(f"返回数据: {data}")
except Exception as e:
    print(f"错误: {e}")

print()

# 测试 Alpha Vantage - INTRADAY (1分钟)
print("=" * 60)
print("测试 2: Alpha Vantage - TIME_SERIES_INTRADAY (1分钟)")
print("=" * 60)

params = {
    'function': 'TIME_SERIES_INTRADAY',
    'symbol': symbol,
    'interval': '1min',
    'apikey': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    if 'Time Series (1min)' in data:
        time_series = data['Time Series (1min)']
        latest_time = list(time_series.keys())[0]
        latest_data = time_series[latest_time]

        print(f"最新时间: {latest_time}")
        print(f"开盘: ${latest_data['1. open']}")
        print(f"最高: ${latest_data['2. high']}")
        print(f"最低: ${latest_data['3. low']}")
        print(f"收盘: ${latest_data['4. close']}")
        print(f"成交量: {latest_data['5. volume']}")
    else:
        print(f"返回数据: {data}")
except Exception as e:
    print(f"错误: {e}")

print()

# 测试 yfinance
print("=" * 60)
print("测试 3: yfinance - 实时数据")
print("=" * 60)

try:
    ticker = yf.Ticker(symbol)

    # 获取最新信息
    info = ticker.info

    print(f"股票代码: {info.get('symbol', 'N/A')}")
    print(f"当前价格: ${info.get('currentPrice', 'N/A')}")
    print(f"常规市场价格: ${info.get('regularMarketPrice', 'N/A')}")
    print(f"前收盘价: ${info.get('previousClose', 'N/A')}")
    print(f"开盘价: ${info.get('open', 'N/A')}")
    print(f"今日最高: ${info.get('dayHigh', 'N/A')}")
    print(f"今日最低: ${info.get('dayLow', 'N/A')}")
    print(f"市场状态: {info.get('marketState', 'N/A')}")

except Exception as e:
    print(f"错误: {e}")

print()
print("=" * 60)
