"""
投资组合管理系统配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库配置
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'portfolio.db')
BACKUP_DIR = os.path.join(BASE_DIR, 'data', 'backups')

# 账户默认配置
DEFAULT_ACCOUNTS = {
    '长期账户': {
        'total_capital': 150000,
        'cash_reserve': 50000,
        'conditional_reserve': 40000,
        'target_min': 40,
        'target_max': 50
    },
    '波段账户': {
        'total_capital': 50000,
        'cash_reserve': 20000,
        'conditional_reserve': 15000,
        'target_min': 30,
        'target_max': 40
    }
}

# 仓位限制
POSITION_LIMITS = {
    'max_single_stock_pct': 15,
    'max_sector_pct': 50,
}

# 相关性分析配置
CORRELATION_CONFIG = {
    'lookback_days': 90,
    'high_correlation_threshold': 0.7,
}

# 归因分析配置
ATTRIBUTION_CONFIG = {
    'default_benchmark': 'SPY',
    'min_data_points': 30,
}

# 邮件通知配置（从环境变量读取，更安全）
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', '587')),
    'sender_email': os.getenv('SENDER_EMAIL', 'your_email@gmail.com'),
    'sender_password': os.getenv('SENDER_PASSWORD', 'your_app_password'),
    'default_recipient': os.getenv('DEFAULT_RECIPIENT_EMAIL', ''),
}

# 通知配置
NOTIFICATION_CONFIG = {
    'default_method': os.getenv('DEFAULT_NOTIFICATION_METHOD', '桌面'),  # 默认使用桌面通知
}

# 预警监控配置
ALERT_MONITORING_CONFIG = {
    'auto_start': os.getenv('AUTO_START_MONITORING', 'True').lower() == 'true',  # 启动时自动开始监控
    'check_interval': int(os.getenv('ALERT_CHECK_INTERVAL', '30')),  # 检查间隔（秒），默认30秒（使用yahooquery批量获取）

    # 动态间隔调整配置（使用 yahooquery 数据源，批量获取）
    # 注意：yahooquery批量获取所有股票只算1次API调用，所以可以更频繁地检查
    'enable_dynamic_interval': os.getenv('ENABLE_DYNAMIC_INTERVAL', 'False').lower() == 'true',  # 禁用动态间隔（使用固定30秒）
    'target_requests_per_hour': int(os.getenv('TARGET_REQUESTS_PER_HOUR', '120')),  # 目标每小时API调用次数（30秒=120次/小时）
    'min_check_interval': int(os.getenv('MIN_CHECK_INTERVAL', '30')),  # 最小检查间隔（秒），30秒
    'max_check_interval': int(os.getenv('MAX_CHECK_INTERVAL', '300')),  # 最大检查间隔（秒），5分钟
}


def calculate_dynamic_interval(stock_count):
    """
    根据监控的股票数量动态计算检查间隔

    Args:
        stock_count: 监控的股票数量

    Returns:
        int: 建议的检查间隔（秒）
    """
    if not ALERT_MONITORING_CONFIG['enable_dynamic_interval'] or stock_count == 0:
        return ALERT_MONITORING_CONFIG['check_interval']

    target_per_hour = ALERT_MONITORING_CONFIG['target_requests_per_hour']
    min_interval = ALERT_MONITORING_CONFIG['min_check_interval']
    max_interval = ALERT_MONITORING_CONFIG['max_check_interval']

    # 计算公式：interval = 3600 / (target_requests_per_hour / stock_count)
    # 即：interval = 3600 * stock_count / target_requests_per_hour
    calculated_interval = int((3600 * stock_count) / target_per_hour)

    # 限制在最小和最大间隔之间
    interval = max(min_interval, min(calculated_interval, max_interval))

    return interval

# Streamlit配置
STREAMLIT_CONFIG = {
    'page_title': '投资组合管理系统',
    'page_icon': '📊',
    'layout': 'wide',
}
