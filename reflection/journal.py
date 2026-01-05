"""
交易日志系统
"""

import pandas as pd
from datetime import datetime, timedelta


class TradingJournal:
    """日志管理器"""

    # 必填字段提示
    REQUIRED_FIELDS = {
        'reason': '为什么现在交易？',
        'target_price': '目标价位是多少？',
        'stop_loss': '止损位在哪里？',
        'confidence_level': '信心等级（1-10）',
    }

    def __init__(self, db):
        """初始化日志管理器"""
        self.db = db

    def add_journal_entry(self, journal_data):
        """
        添加日志条目

        Args:
            journal_data: dict 包含日志信息
                - transaction_id: 关联交易ID（可选）
                - option_id: 关联期权ID（可选）
                - stock_symbol: 股票代码
                - trade_type: 交易类型
                - trade_date: 交易日期
                - account_name: 账户名称
                - reason: 决策原因
                - target_price: 目标价
                - expected_holding_period: 预期持有期
                - expected_return: 预期收益率
                - stop_loss: 止损位
                - stop_profit: 止盈位
                - max_acceptable_loss: 最大可接受亏损
                - main_risks: 主要风险
                - market_condition: 市场状况
                - vix_level: VIX水平
                - confidence_level: 信心等级（1-10）
                - emotional_state: 情绪状态
                - decision_quality: 决策质量（1-10）
                - tags: 标签
        """
        return self.db.add_journal_entry(journal_data)

    def get_journal_entries(self, account=None, symbol=None, start_date=None, end_date=None):
        """获取日志条目"""
        return self.db.get_journal_entries(
            account=account,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

    def add_review(self, journal_id, review_data):
        """
        添加复盘

        Args:
            journal_id: 日志ID
            review_data: dict
                - met_expectation: 是否达标
                - deviation_reason: 偏离原因
                - lessons_learned: 经验教训
                - improvements: 改进建议
        """
        return self.db.update_journal_review(
            journal_id=journal_id,
            met_expectation=review_data.get('met_expectation'),
            deviation_reason=review_data.get('deviation_reason'),
            lessons_learned=review_data.get('lessons_learned'),
            improvements=review_data.get('improvements')
        )

    def get_completion_rate(self, account=None, period_days=30):
        """
        计算日志完成率

        统计交易数 vs 日志数
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)

        # 获取交易数
        transactions = self.db.get_transactions(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        # 获取期权交易数
        options = self.db.get_options_trades(account=account)
        if not options.empty:
            options = options[
                (options['open_date'] >= str(start_date)) &
                (options['open_date'] <= str(end_date))
            ]

        total_trades = len(transactions) + len(options)

        # 获取日志数
        journals = self.get_journal_entries(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        journal_count = len(journals)

        completion_rate = journal_count / total_trades * 100 if total_trades > 0 else 0

        return {
            'total_trades': total_trades,
            'journal_count': journal_count,
            'completion_rate': completion_rate,
            'missing_journals': total_trades - journal_count,
            'period_days': period_days
        }

    def get_unreviewed_entries(self, account=None):
        """获取未复盘的日志"""
        journals = self.get_journal_entries(account=account)

        if journals.empty:
            return pd.DataFrame()

        return journals[journals['reviewed_at'].isna()]

    def get_trades_without_journal(self, account=None, days=7):
        """获取没有日志的交易"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # 获取交易
        transactions = self.db.get_transactions(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        # 获取日志
        journals = self.get_journal_entries(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        if transactions.empty:
            return pd.DataFrame()

        # 找出没有日志的交易
        if journals.empty:
            return transactions

        journal_trans_ids = journals[journals['transaction_id'].notna()]['transaction_id'].tolist()

        missing = transactions[~transactions['transaction_id'].isin(journal_trans_ids)]

        return missing

    def get_journal_statistics(self, account=None, period_days=90):
        """获取日志统计"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)

        journals = self.get_journal_entries(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        if journals.empty:
            return {
                'total_entries': 0,
                'reviewed_count': 0,
                'avg_confidence': 0,
                'met_expectation_rate': 0,
                'common_reasons': [],
                'emotional_distribution': {}
            }

        # 统计
        total = len(journals)
        reviewed = journals['reviewed_at'].notna().sum()

        # 平均信心等级
        avg_confidence = journals['confidence_level'].mean() if 'confidence_level' in journals.columns else 0

        # 达标率
        met_expectations = journals[journals['met_expectation'] == True]
        met_rate = len(met_expectations) / reviewed * 100 if reviewed > 0 else 0

        # 常见原因（词频统计简化版）
        reasons = journals['reason'].dropna().tolist()
        common_reasons = reasons[:5] if reasons else []

        # 情绪分布
        emotional_dist = {}
        if 'emotional_state' in journals.columns:
            emotional_dist = journals['emotional_state'].value_counts().to_dict()

        return {
            'total_entries': total,
            'reviewed_count': reviewed,
            'review_rate': reviewed / total * 100 if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'met_expectation_rate': met_rate,
            'common_reasons': common_reasons,
            'emotional_distribution': emotional_dist
        }

    def search_journals(self, keyword, account=None):
        """搜索日志"""
        journals = self.get_journal_entries(account=account)

        if journals.empty:
            return pd.DataFrame()

        # 搜索原因、教训、改进等字段
        mask = (
            journals['reason'].str.contains(keyword, case=False, na=False) |
            journals['lessons_learned'].str.contains(keyword, case=False, na=False) |
            journals['improvements'].str.contains(keyword, case=False, na=False) |
            journals['main_risks'].str.contains(keyword, case=False, na=False)
        )

        return journals[mask]

    def get_lessons_by_stock(self, symbol):
        """获取特定股票的经验教训"""
        journals = self.get_journal_entries(symbol=symbol)

        if journals.empty:
            return []

        lessons = journals[journals['lessons_learned'].notna()]['lessons_learned'].tolist()

        return lessons

    def export_journal(self, account=None, format='dataframe'):
        """导出日志"""
        journals = self.get_journal_entries(account=account)

        if format == 'dataframe':
            return journals
        elif format == 'dict':
            return journals.to_dict('records')
        elif format == 'markdown':
            md_content = "# 交易日志\n\n"
            for _, j in journals.iterrows():
                md_content += f"## {j['trade_date']} - {j['stock_symbol']} {j['trade_type']}\n\n"
                md_content += f"**原因**: {j['reason']}\n\n"
                if j['target_price']:
                    md_content += f"**目标价**: ${j['target_price']}\n\n"
                if j['lessons_learned']:
                    md_content += f"**教训**: {j['lessons_learned']}\n\n"
                md_content += "---\n\n"
            return md_content

        return journals
