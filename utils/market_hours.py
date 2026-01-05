"""
美股市场交易时间检测模块
"""

from datetime import datetime, time
import pytz
from typing import Tuple


# 美国主要假期（固定日期）
FIXED_HOLIDAYS = [
    (1, 1),   # 新年
    (7, 4),   # 独立日
    (12, 25), # 圣诞节
]

# 美国主要假期（需要计算的）
# 简化版：仅包含常见的固定假期
# 完整版需要计算感恩节、复活节等浮动假期


def is_market_open(dt=None) -> Tuple[bool, str]:
    """
    检查美股市场是否开盘

    Args:
        dt: datetime对象，默认为当前时间（UTC）

    Returns:
        (is_open: bool, reason: str)
        is_open: 是否开盘
        reason: 状态说明
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)

    # 转换为美东时间
    eastern = pytz.timezone('America/New_York')
    et_time = dt.astimezone(eastern)

    # 检查是否为周末
    if et_time.weekday() >= 5:  # 5=周六, 6=周日
        return False, f"周末休市（{['周一','周二','周三','周四','周五','周六','周日'][et_time.weekday()]}）"

    # 检查是否为假期
    month_day = (et_time.month, et_time.day)
    if month_day in FIXED_HOLIDAYS:
        holiday_names = {
            (1, 1): "新年",
            (7, 4): "独立日",
            (12, 25): "圣诞节"
        }
        return False, f"假期休市（{holiday_names.get(month_day, '假期')}）"

    # 检查是否在交易时间内（9:30 AM - 4:00 PM ET）
    market_open = time(9, 30)
    market_close = time(16, 0)
    current_time = et_time.time()

    if current_time < market_open:
        return False, f"盘前（开盘时间：9:30 AM ET，当前：{et_time.strftime('%H:%M:%S')} ET）"
    elif current_time >= market_close:
        return False, f"盘后（收盘时间：4:00 PM ET，当前：{et_time.strftime('%H:%M:%S')} ET）"
    else:
        return True, f"开盘中（{et_time.strftime('%H:%M:%S')} ET）"


def get_market_status() -> dict:
    """
    获取详细的市场状态信息

    Returns:
        dict: {
            'is_open': bool,
            'status': str,
            'current_time_et': str,
            'current_time_local': str,
            'next_open': str (如果闭市)
        }
    """
    now_utc = datetime.now(pytz.UTC)
    eastern = pytz.timezone('America/New_York')
    et_time = now_utc.astimezone(eastern)
    local_time = datetime.now()

    is_open, reason = is_market_open(now_utc)

    status = {
        'is_open': is_open,
        'status': reason,
        'current_time_et': et_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'current_time_local': local_time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    # 如果闭市，计算下次开盘时间（简化版）
    if not is_open:
        if et_time.weekday() >= 5:  # 周末
            # 计算到下周一
            days_until_monday = (7 - et_time.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 1
            status['next_open'] = f"{days_until_monday}天后（周一 9:30 AM ET）"
        elif et_time.time() >= time(16, 0):  # 盘后
            status['next_open'] = "明日 9:30 AM ET"
        else:  # 盘前
            status['next_open'] = "今日 9:30 AM ET"

    return status


def should_use_realtime_prices() -> bool:
    """
    判断当前是否应该使用实时价格

    Returns:
        bool: True表示应该使用实时价格，False表示使用收盘价
    """
    is_open, _ = is_market_open()
    return is_open


if __name__ == '__main__':
    # 测试
    import sys
    import io

    # Fix encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    status = get_market_status()

    print("=" * 60)
    print("美股市场状态")
    print("=" * 60)
    print(f"是否开盘: {'✅ 是' if status['is_open'] else '❌ 否'}")
    print(f"状态说明: {status['status']}")
    print(f"美东时间: {status['current_time_et']}")
    print(f"本地时间: {status['current_time_local']}")
    if 'next_open' in status:
        print(f"下次开盘: {status['next_open']}")
    print(f"使用实时价格: {'是' if should_use_realtime_prices() else '否（使用收盘价）'}")
    print("=" * 60)
