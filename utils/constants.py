"""
常量定义
"""

# 交易类型
TRANSACTION_TYPES = ['买入', '卖出']

# 期权类型
OPTION_TYPES = ['卖Call', '卖Put', '买Call', '买Put']

# 现金流类型
FLOW_TYPES = [
    '股票买入',
    '股票卖出',
    '期权权利金收入',
    '期权权利金支出',
    '期权平仓',
    '分红',
    '存入',
    '取出',
    '利息',
    '佣金',
]

# 期权状态
OPTION_STATUS = ['持仓中', '已平仓', '被行权', '到期作废']

# 股票状态
STOCK_STATUS = ['持仓中', '观察中', '等待回调', '已清仓']

# 账户名称
ACCOUNT_NAMES = ['长期账户', '波段账户']

# 其他现金流类型（手动录入）
OTHER_CASH_FLOW_TYPES = ['利息', '存入', '取出']

# 情绪状态
EMOTIONAL_STATES = ['理性', '焦虑', '贪婪', '恐惧', '兴奋', '沮丧', '犹豫', '自信']

# 总结类型
SUMMARY_TYPES = ['单股', '账户', '策略', '月度', '季度', '年度']

# 预警类型
ALERT_TYPES = ['高于', '低于', '穿越']

# 通知方式
NOTIFICATION_METHODS = ['邮件', '桌面', '短信']

# 仓位目标类型
TARGET_TYPES = ['百分比', '金额', '股数']

# 板块分类
SECTORS = [
    '科技',
    '金融',
    '医疗健康',
    '消费品',
    '工业',
    '能源',
    '材料',
    '公用事业',
    '房地产',
    '通信服务',
    '其他'
]

# 市场状况
MARKET_CONDITIONS = [
    '牛市',
    '熊市',
    '震荡市',
    '突破中',
    '调整中',
    '底部区域',
    '顶部区域'
]

# 信心等级说明
CONFIDENCE_LEVELS = {
    1: '非常低 - 几乎没有把握',
    2: '很低 - 不太确定',
    3: '较低 - 有些怀疑',
    4: '偏低 - 略有担忧',
    5: '中等 - 一半一半',
    6: '偏高 - 较有信心',
    7: '较高 - 相当确定',
    8: '高 - 很有把握',
    9: '很高 - 非常确定',
    10: '极高 - 完全确信'
}

# 决策质量说明
DECISION_QUALITY_LEVELS = {
    1: '极差 - 冲动交易',
    2: '很差 - 缺乏分析',
    3: '较差 - 分析不足',
    4: '偏差 - 有些草率',
    5: '一般 - 基本合理',
    6: '偏好 - 考虑周全',
    7: '较好 - 分析充分',
    8: '好 - 计划周密',
    9: '很好 - 全面分析',
    10: '极好 - 完美执行'
}

# 默认值
DEFAULTS = {
    'rebalance_threshold': 10,  # 再平衡阈值 %
    'max_single_stock_pct': 15,  # 单股最大仓位 %
    'max_sector_pct': 50,  # 单板块最大仓位 %
    'correlation_lookback_days': 90,  # 相关性计算回溯天数
    'high_correlation_threshold': 0.7,  # 高相关性阈值
}

# 颜色配置
COLORS = {
    'positive': '#00CC96',
    'negative': '#EF553B',
    'neutral': '#636EFA',
    'warning': '#FFA15A',
    'info': '#19D3F3',
}

# 图表配置
CHART_CONFIG = {
    'default_width': 700,
    'default_height': 400,
    'color_scheme': 'Set3',
}
