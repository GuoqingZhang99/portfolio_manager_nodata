"""
辅助工具函数
"""

from datetime import datetime


def format_currency(amount, symbol='$'):
    """
    格式化货币

    Args:
        amount: 金额
        symbol: 货币符号

    Returns:
        str: 格式化后的字符串
    """
    if amount is None:
        return f"{symbol}0.00"

    if amount >= 0:
        return f"{symbol}{amount:,.2f}"
    else:
        return f"-{symbol}{abs(amount):,.2f}"


def format_percentage(value, decimal_places=2):
    """
    格式化百分比

    Args:
        value: 数值
        decimal_places: 小数位数

    Returns:
        str: 格式化后的字符串
    """
    if value is None:
        return "0.00%"

    return f"{value:.{decimal_places}f}%"


def calculate_days_between(start_date, end_date):
    """
    计算天数差

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        int: 天数差
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date[:10], '%Y-%m-%d').date()

    if hasattr(start_date, 'date'):
        start_date = start_date.date()
    if hasattr(end_date, 'date'):
        end_date = end_date.date()

    return (end_date - start_date).days


def safe_divide(numerator, denominator, default=0):
    """
    安全除法

    Args:
        numerator: 分子
        denominator: 分母
        default: 除数为0时的默认值

    Returns:
        float: 结果
    """
    if denominator == 0 or denominator is None:
        return default
    return numerator / denominator


def color_value(value, positive_color='green', negative_color='red', zero_color='gray'):
    """
    根据值返回颜色

    Args:
        value: 数值
        positive_color: 正数颜色
        negative_color: 负数颜色
        zero_color: 零值颜色

    Returns:
        str: 颜色名称
    """
    if value is None or value == 0:
        return zero_color
    elif value > 0:
        return positive_color
    else:
        return negative_color


def format_pnl(value):
    """
    格式化盈亏

    Args:
        value: 盈亏金额

    Returns:
        str: 带颜色标记的字符串（用于Streamlit）
    """
    if value is None:
        return "$0.00"

    if value >= 0:
        return f":green[+${value:,.2f}]"
    else:
        return f":red[-${abs(value):,.2f}]"


def format_pnl_percent(value):
    """
    格式化盈亏百分比

    Args:
        value: 盈亏百分比

    Returns:
        str: 带颜色标记的字符串
    """
    if value is None:
        return "0.00%"

    if value >= 0:
        return f":green[+{value:.2f}%]"
    else:
        return f":red[{value:.2f}%]"


def validate_stock_symbol(symbol):
    """
    验证股票代码

    Args:
        symbol: 股票代码

    Returns:
        tuple: (is_valid, cleaned_symbol)
    """
    if not symbol:
        return False, ""

    cleaned = symbol.strip().upper()

    # 基本验证：1-5个字母
    if not cleaned.isalpha() or len(cleaned) > 5:
        return False, ""

    return True, cleaned


def parse_date(date_input):
    """
    解析日期

    Args:
        date_input: 日期输入（字符串、date、datetime）

    Returns:
        date: 日期对象
    """
    if date_input is None:
        return None

    if isinstance(date_input, datetime):
        return date_input.date()

    if hasattr(date_input, 'date'):
        return date_input

    # 尝试多种格式
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y']

    for fmt in formats:
        try:
            return datetime.strptime(str(date_input)[:10], fmt).date()
        except ValueError:
            continue

    return None


def calculate_annualized_return(total_return, days):
    """
    计算年化收益率

    Args:
        total_return: 总收益率
        days: 持有天数

    Returns:
        float: 年化收益率
    """
    if days <= 0:
        return 0

    return total_return * (365 / days)


def truncate_string(s, max_length=50, suffix='...'):
    """
    截断字符串

    Args:
        s: 原始字符串
        max_length: 最大长度
        suffix: 后缀

    Returns:
        str: 截断后的字符串
    """
    if not s:
        return ""

    if len(s) <= max_length:
        return s

    return s[:max_length - len(suffix)] + suffix


def merge_dicts(*dicts):
    """
    合并多个字典

    Args:
        *dicts: 多个字典

    Returns:
        dict: 合并后的字典
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def get_fiscal_quarter(date):
    """
    获取财季

    Args:
        date: 日期

    Returns:
        tuple: (year, quarter)
    """
    if isinstance(date, str):
        date = parse_date(date)

    if date is None:
        return None, None

    quarter = (date.month - 1) // 3 + 1
    return date.year, quarter


def format_large_number(value):
    """
    格式化大数字

    Args:
        value: 数值

    Returns:
        str: 格式化后的字符串（如 1.5M, 2.3B）
    """
    if value is None:
        return "0"

    abs_value = abs(value)
    sign = "" if value >= 0 else "-"

    if abs_value >= 1e12:
        return f"{sign}{abs_value/1e12:.1f}T"
    elif abs_value >= 1e9:
        return f"{sign}{abs_value/1e9:.1f}B"
    elif abs_value >= 1e6:
        return f"{sign}{abs_value/1e6:.1f}M"
    elif abs_value >= 1e3:
        return f"{sign}{abs_value/1e3:.1f}K"
    else:
        return f"{sign}{abs_value:.0f}"
