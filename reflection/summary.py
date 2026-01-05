"""
自动生成总结模板
"""

import pandas as pd
from datetime import datetime, timedelta
import json


class SummaryGenerator:
    """总结生成器"""

    def __init__(self, db, calculator=None):
        """初始化总结生成器"""
        self.db = db
        self.calculator = calculator

    def generate_stock_summary(self, symbol, account=None, period_days=90):
        """
        生成单股总结

        自动部分：
        - 持仓数据、交易历史、盈亏统计

        用户填写部分：
        - 成功之处、失败之处、投资逻辑验证、未来计划
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)

        # 获取交易记录
        transactions = self.db.get_transactions(
            symbol=symbol,
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        # 获取期权记录
        options = self.db.get_options_trades(symbol=symbol, account=account)

        # 计算统计数据
        auto_data = {
            'symbol': symbol,
            'period': f"{start_date} 至 {end_date}",
            'total_stock_trades': len(transactions),
            'buy_trades': len(transactions[transactions['transaction_type'] == '买入']) if not transactions.empty else 0,
            'sell_trades': len(transactions[transactions['transaction_type'] == '卖出']) if not transactions.empty else 0,
            'total_option_trades': len(options),
            'total_shares_bought': transactions[transactions['transaction_type'] == '买入']['shares'].sum() if not transactions.empty else 0,
            'total_shares_sold': transactions[transactions['transaction_type'] == '卖出']['shares'].sum() if not transactions.empty else 0,
            'avg_buy_price': transactions[transactions['transaction_type'] == '买入']['price'].mean() if not transactions.empty else 0,
            'avg_sell_price': transactions[transactions['transaction_type'] == '卖出']['price'].mean() if not transactions.empty else 0,
        }

        # 期权盈亏
        if not options.empty:
            closed_options = options[options['status'] != '持仓中']
            if not closed_options.empty:
                option_pnl = 0
                for _, opt in closed_options.iterrows():
                    premium = opt['premium_per_share'] * opt['contracts'] * 100
                    close_amount = (opt['close_price_per_share'] or 0) * opt['contracts'] * 100
                    if opt['option_type'] in ['卖Call', '卖Put']:
                        option_pnl += premium - close_amount
                    else:
                        option_pnl += close_amount - premium
                auto_data['option_pnl'] = option_pnl
            else:
                auto_data['option_pnl'] = 0
        else:
            auto_data['option_pnl'] = 0

        # 创建总结记录
        summary_id = self.db.add_summary(
            summary_type='单股',
            subject=symbol,
            period_start=start_date,
            period_end=end_date,
            auto_generated_data=json.dumps(auto_data, default=str)
        )

        return {
            'summary_id': summary_id,
            'auto_data': auto_data,
            'user_fields': {
                'what_worked': '成功之处...',
                'what_failed': '失败之处...',
                'investment_thesis_validation': '投资逻辑验证...',
                'future_plans': '未来计划...',
                'lessons_learned': '经验教训...'
            }
        }

    def generate_account_summary(self, account, period='monthly'):
        """
        生成账户总结

        自动部分：
        - 业绩数据、交易统计、目标达成、最佳/最差交易

        用户填写部分：
        - 做对的事、犯的错误、市场观察、下期计划
        """
        # 确定时间范围
        end_date = datetime.now().date()
        if period == 'monthly':
            start_date = end_date.replace(day=1)
            period_name = end_date.strftime('%Y年%m月')
        elif period == 'quarterly':
            quarter = (end_date.month - 1) // 3
            start_date = end_date.replace(month=quarter * 3 + 1, day=1)
            period_name = f"{end_date.year}年Q{quarter + 1}"
        elif period == 'yearly':
            start_date = end_date.replace(month=1, day=1)
            period_name = f"{end_date.year}年"
        else:
            start_date = end_date - timedelta(days=30)
            period_name = f"最近30天"

        # 获取交易记录
        transactions = self.db.get_transactions(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        # 获取期权记录
        options = self.db.get_options_trades(account=account)
        if not options.empty:
            period_options = options[
                (options['open_date'] >= str(start_date)) &
                (options['open_date'] <= str(end_date))
            ]
        else:
            period_options = pd.DataFrame()

        # 计算统计数据
        auto_data = {
            'account': account,
            'period': period_name,
            'period_start': str(start_date),
            'period_end': str(end_date),
            'total_trades': len(transactions) + len(period_options),
            'stock_trades': len(transactions),
            'option_trades': len(period_options),
        }

        # 胜率统计（简化版，基于期权）
        if not options.empty:
            closed_options = options[options['status'] != '持仓中']
            if not closed_options.empty:
                winning_trades = 0
                losing_trades = 0
                for _, opt in closed_options.iterrows():
                    premium = opt['premium_per_share'] * opt['contracts'] * 100
                    close_amount = (opt['close_price_per_share'] or 0) * opt['contracts'] * 100
                    if opt['option_type'] in ['卖Call', '卖Put']:
                        pnl = premium - close_amount
                    else:
                        pnl = close_amount - premium

                    if pnl > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1

                total_closed = winning_trades + losing_trades
                auto_data['winning_trades'] = winning_trades
                auto_data['losing_trades'] = losing_trades
                auto_data['win_rate'] = winning_trades / total_closed if total_closed > 0 else 0
            else:
                auto_data['winning_trades'] = 0
                auto_data['losing_trades'] = 0
                auto_data['win_rate'] = 0
        else:
            auto_data['winning_trades'] = 0
            auto_data['losing_trades'] = 0
            auto_data['win_rate'] = 0

        # 创建总结记录
        summary_id = self.db.add_summary(
            summary_type='账户',
            subject=account,
            period_start=start_date,
            period_end=end_date,
            auto_generated_data=json.dumps(auto_data, default=str)
        )

        return {
            'summary_id': summary_id,
            'auto_data': auto_data,
            'user_fields': {
                'what_worked': '做对的事...',
                'what_failed': '犯的错误...',
                'market_observations': '市场观察...',
                'future_plans': '下期计划...',
                'lessons_learned': '经验教训...',
                'methodology_updates': '方法论更新...'
            }
        }

    def generate_strategy_summary(self, period_days=90):
        """
        生成策略总结

        自动统计各策略使用次数、胜率、平均收益
        用户分析：策略评价、改进方向
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=period_days)

        # 获取所有期权
        options = self.db.get_options_trades()

        if options.empty:
            return {
                'auto_data': {'message': '没有期权交易记录'},
                'user_fields': {}
            }

        # 筛选时间范围内的
        period_options = options[
            (options['open_date'] >= str(start_date)) &
            (options['open_date'] <= str(end_date))
        ]

        # 按策略类型统计
        strategy_stats = {}
        for option_type in ['卖Call', '卖Put', '买Call', '买Put']:
            type_options = period_options[period_options['option_type'] == option_type]

            if type_options.empty:
                continue

            closed = type_options[type_options['status'] != '持仓中']

            total_count = len(type_options)
            closed_count = len(closed)

            # 计算盈亏
            winning = 0
            total_pnl = 0
            if not closed.empty:
                for _, opt in closed.iterrows():
                    premium = opt['premium_per_share'] * opt['contracts'] * 100
                    close_amount = (opt['close_price_per_share'] or 0) * opt['contracts'] * 100

                    if option_type in ['卖Call', '卖Put']:
                        pnl = premium - close_amount
                    else:
                        pnl = close_amount - premium

                    total_pnl += pnl
                    if pnl > 0:
                        winning += 1

            strategy_stats[option_type] = {
                'total_trades': total_count,
                'closed_trades': closed_count,
                'open_positions': total_count - closed_count,
                'winning_trades': winning,
                'win_rate': winning / closed_count if closed_count > 0 else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / closed_count if closed_count > 0 else 0
            }

        auto_data = {
            'period': f"{start_date} 至 {end_date}",
            'strategy_statistics': strategy_stats
        }

        # 创建总结记录
        summary_id = self.db.add_summary(
            summary_type='策略',
            subject='期权策略',
            period_start=start_date,
            period_end=end_date,
            auto_generated_data=json.dumps(auto_data, default=str)
        )

        return {
            'summary_id': summary_id,
            'auto_data': auto_data,
            'user_fields': {
                'strategy_evaluation': '策略评价...',
                'best_performing': '最佳策略...',
                'worst_performing': '最差策略...',
                'improvements': '改进方向...'
            }
        }

    def get_pending_summaries(self):
        """获取待完成的总结"""
        return self.db.get_summaries(status='草稿')

    def complete_summary(self, summary_id, user_data):
        """
        完成总结

        Args:
            summary_id: 总结ID
            user_data: dict 用户填写的内容
        """
        self.db.update_summary(
            summary_id=summary_id,
            what_worked=user_data.get('what_worked'),
            what_failed=user_data.get('what_failed'),
            market_observations=user_data.get('market_observations'),
            future_plans=user_data.get('future_plans'),
            lessons_learned=user_data.get('lessons_learned'),
            methodology_updates=user_data.get('methodology_updates'),
            status='已完成'
        )

    def get_summary_detail(self, summary_id):
        """获取总结详情"""
        summaries = self.db.get_summaries()

        if summaries.empty:
            return None

        summary = summaries[summaries['summary_id'] == summary_id]

        if summary.empty:
            return None

        return summary.iloc[0].to_dict()

    def get_all_lessons_learned(self, limit=20):
        """获取所有经验教训"""
        summaries = self.db.get_summaries(status='已完成')

        if summaries.empty:
            return []

        lessons = summaries[summaries['lessons_learned'].notna()]['lessons_learned'].tolist()

        return lessons[:limit]
