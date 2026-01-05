"""
获取真实的股票价格
"""

import os
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from config import DATABASE_PATH
from core.database import Database
from core.calculator import PortfolioCalculator
from utils.price_sources import PriceSourceManager
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化
db = Database(DATABASE_PATH)
calc = PortfolioCalculator(db)
manager = PriceSourceManager()

# 获取持仓股票
stocks = calc.calculate_stock_summary()

if stocks.empty:
    print("ERROR: 无持仓股票")
    sys.exit(1)

symbols = stocks['股票代码'].unique().tolist()
print(f">> 发现 {len(symbols)} 只持仓股票: {', '.join(symbols)}\n")

# 获取 API Key
api_key = os.getenv('ALPHAVANTAGE_API_KEY')

if not api_key:
    print("ERROR: 未找到 Alpha Vantage API Key")
    print("请在 .env 文件中设置 ALPHAVANTAGE_API_KEY")
    sys.exit(1)

print(f">> 使用 Alpha Vantage API Key: {api_key[:10]}...\n")

# 获取每只股票的价格
prices = {}
for i, symbol in enumerate(symbols, 1):
    print(f"[{i}/{len(symbols)}] 获取 {symbol} 的最新价格...", end=' ')

    price = manager._get_price_alphavantage(symbol, api_key)

    if price:
        prices[symbol] = price
        print(f"✅ ${price:.2f}")
        manager.set_manual_price(symbol, price)
    else:
        print(f"❌ 失败")

    # 等待避免超过 API 限制
    if i < len(symbols):
        import time
        print("   ⏳ 等待 12 秒...")
        time.sleep(12)

print(f"\n{'='*60}")
print("📋 价格汇总：")
print(f"{'='*60}")

if prices:
    for symbol, price in prices.items():
        print(f"  {symbol:10s} ${price:>10.2f}")

    print(f"\n✅ 成功获取 {len(prices)}/{len(symbols)} 个股票价格")
    print(f"\n💾 价格已保存到手动价格管理器")
    print(f"   现在刷新 Dashboard 即可看到这些价格")
else:
    print("❌ 未能获取任何价格")

print(f"{'='*60}")
