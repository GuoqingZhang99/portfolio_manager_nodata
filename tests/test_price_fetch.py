"""
测试价格获取功能
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils.data_fetcher import batch_get_prices, get_current_price
from core.database import Database
from core.calculator import PortfolioCalculator
import config

def test_price_fetch():
    """测试价格获取"""
    print("=" * 60)
    print("测试价格获取功能")
    print("=" * 60)

    # 初始化数据库
    db = Database(config.DATABASE_PATH)
    calc = PortfolioCalculator(db)

    # 获取所有持仓股票
    stocks = calc.calculate_stock_summary()

    if stocks.empty:
        print("\n❌ 数据库中没有持仓股票！")
        print("   请先在系统中录入交易数据")
        return

    print(f"\n📊 找到 {len(stocks)} 只股票:")
    for _, stock in stocks.iterrows():
        print(f"   - {stock['股票代码']}: {stock['当前股数']} 股")

    symbols = stocks['股票代码'].unique().tolist()

    print(f"\n🔍 开始获取价格...")
    print("-" * 60)

    # 测试单个股票价格获取
    print("\n1️⃣ 测试单个股票价格获取:")
    test_symbol = symbols[0]
    price = get_current_price(test_symbol)
    if price:
        print(f"   ✅ {test_symbol}: ${price:.2f}")
    else:
        print(f"   ❌ {test_symbol}: 获取失败")

    # 测试批量获取
    print(f"\n2️⃣ 测试批量获取价格 ({len(symbols)} 个股票):")
    prices = batch_get_prices(symbols, force_refresh=True)

    print("\n📊 结果统计:")
    print(f"   总股票数: {len(symbols)}")
    print(f"   成功获取: {len(prices)}")
    print(f"   获取失败: {len(symbols) - len(prices)}")

    if prices:
        print("\n💰 获取到的价格:")
        for symbol, price in prices.items():
            print(f"   {symbol}: ${price:.2f}")

    if len(prices) < len(symbols):
        failed = [s for s in symbols if s not in prices]
        print("\n❌ 获取失败的股票:")
        for symbol in failed:
            print(f"   {symbol}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_price_fetch()
