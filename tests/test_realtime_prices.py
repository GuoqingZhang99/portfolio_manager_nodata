"""
测试实时价格功能
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils.market_hours import get_market_status
from utils.price_sources import get_price_manager
from utils.data_fetcher import batch_get_prices
from datetime import datetime
import pytz

print("=" * 70)
print("实时价格功能测试")
print("=" * 70)

# 1. 测试市场状态
print("\n1. 市场状态检测")
print("-" * 70)
status = get_market_status()
print(f"  市场开盘: {'是' if status['is_open'] else '否'}")
print(f"  状态说明: {status['status']}")
print(f"  美东时间: {status['current_time_et']}")
print(f"  本地时间: {status['current_time_local']}")
if 'next_open' in status:
    print(f"  下次开盘: {status['next_open']}")

# 2. 测试价格管理器
print("\n2. 价格管理器测试")
print("-" * 70)
manager = get_price_manager()

# 检查已有价格
manual_prices = manager.get_manual_prices()
print(f"  手动价格数量: {len(manual_prices)}")
if manual_prices:
    for symbol, price in manual_prices.items():
        timestamp = manager.get_timestamp(symbol)
        if timestamp:
            local_time = timestamp.astimezone(pytz.timezone('Asia/Shanghai'))
            time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = "无记录"
        print(f"    {symbol}: ${price:.2f} (更新时间: {time_str})")

# 最后更新时间
last_update = manager.get_last_update_time()
if last_update:
    local_time = last_update.astimezone(pytz.timezone('Asia/Shanghai'))
    print(f"\n  最后更新时间: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    print(f"\n  最后更新时间: 无")

# 3. 测试批量获取价格
print("\n3. 批量获取价格测试")
print("-" * 70)
test_symbols = ['NVDA', 'TSLA']
print(f"  测试股票: {', '.join(test_symbols)}")
print()

prices = batch_get_prices(test_symbols, use_batch=False)

print(f"\n  获取结果:")
for symbol in test_symbols:
    if symbol in prices:
        print(f"    ✓ {symbol}: ${prices[symbol]:.2f}")
    else:
        print(f"    ✗ {symbol}: 获取失败")

# 4. 显示更新后的时间戳
print("\n4. 更新后的时间戳")
print("-" * 70)
manager = get_price_manager()  # 重新获取以刷新数据
for symbol in test_symbols:
    timestamp = manager.get_timestamp(symbol)
    if timestamp:
        local_time = timestamp.astimezone(pytz.timezone('Asia/Shanghai'))
        time_str = local_time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {symbol}: {time_str}")
    else:
        print(f"  {symbol}: 无时间戳")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
