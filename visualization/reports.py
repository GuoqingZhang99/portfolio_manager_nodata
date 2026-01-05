"""
报告生成器
"""

import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO


class ReportGenerator:
    """报告生成器"""

    def __init__(self, db, calculator=None, chart_builder=None):
        """初始化报告生成器"""
        self.db = db
        self.calculator = calculator
        self.chart_builder = chart_builder

    def generate_weekly_report(self, account, week_start=None):
        """
        生成周报

        - 本周交易汇总
        - 盈亏统计
        - 持仓变化
        """
        if week_start is None:
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        # 获取本周交易
        transactions = self.db.get_transactions(
            account=account,
            start_date=week_start,
            end_date=week_end
        )

        # 获取本周期权交易
        options = self.db.get_options_trades(account=account)
        week_options = pd.DataFrame()
        if not options.empty:
            week_options = options[
                (options['open_date'] >= str(week_start)) &
                (options['open_date'] <= str(week_end))
            ]

        # 统计
        report = {
            'header': {
                'account': account,
                'period': f"{week_start} 至 {week_end}",
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'summary': {
                'total_stock_trades': len(transactions),
                'total_option_trades': len(week_options),
                'buy_trades': len(transactions[transactions['transaction_type'] == '买入']) if not transactions.empty else 0,
                'sell_trades': len(transactions[transactions['transaction_type'] == '卖出']) if not transactions.empty else 0,
            },
            'transactions': transactions.to_dict('records') if not transactions.empty else [],
            'options': week_options.to_dict('records') if not week_options.empty else []
        }

        # 计算本周买入/卖出金额
        if not transactions.empty:
            buy_amount = transactions[transactions['transaction_type'] == '买入'].apply(
                lambda x: x['price'] * x['shares'], axis=1
            ).sum()
            sell_amount = transactions[transactions['transaction_type'] == '卖出'].apply(
                lambda x: x['price'] * x['shares'], axis=1
            ).sum()
            report['summary']['buy_amount'] = buy_amount
            report['summary']['sell_amount'] = sell_amount
            report['summary']['net_flow'] = sell_amount - buy_amount
        else:
            report['summary']['buy_amount'] = 0
            report['summary']['sell_amount'] = 0
            report['summary']['net_flow'] = 0

        return report

    def generate_monthly_report(self, account, year=None, month=None):
        """
        生成月报

        - 月度业绩
        - 交易分析
        - 目标达成情况
        - 期权策略统计
        """
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        month_start = datetime(year, month, 1).date()
        if month == 12:
            month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

        # 获取交易数据
        transactions = self.db.get_transactions(
            account=account,
            start_date=month_start,
            end_date=month_end
        )

        # 获取期权数据
        options = self.db.get_options_trades(account=account)

        # 本月开仓期权
        month_options = pd.DataFrame()
        if not options.empty:
            month_options = options[
                (options['open_date'] >= str(month_start)) &
                (options['open_date'] <= str(month_end))
            ]

        # 本月平仓期权
        closed_options = pd.DataFrame()
        if not options.empty:
            closed_options = options[
                (options['close_date'] >= str(month_start)) &
                (options['close_date'] <= str(month_end)) &
                (options['status'] != '持仓中')
            ]

        # 计算期权盈亏
        option_pnl = 0
        winning_trades = 0
        losing_trades = 0
        if not closed_options.empty:
            for _, opt in closed_options.iterrows():
                premium = opt['premium_per_share'] * opt['contracts'] * 100
                close_amount = (opt['close_price_per_share'] or 0) * opt['contracts'] * 100

                if opt['option_type'] in ['卖Call', '卖Put']:
                    pnl = premium - close_amount
                else:
                    pnl = close_amount - premium

                option_pnl += pnl
                if pnl > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1

        # 生成报告
        report = {
            'header': {
                'account': account,
                'period': f"{year}年{month}月",
                'period_start': str(month_start),
                'period_end': str(month_end),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'performance': {
                'option_pnl': option_pnl,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': winning_trades / (winning_trades + losing_trades) if (winning_trades + losing_trades) > 0 else 0
            },
            'trades': {
                'stock_trades': len(transactions),
                'option_opened': len(month_options),
                'option_closed': len(closed_options)
            },
            'transactions': transactions.to_dict('records') if not transactions.empty else [],
            'options_opened': month_options.to_dict('records') if not month_options.empty else [],
            'options_closed': closed_options.to_dict('records') if not closed_options.empty else []
        }

        # 添加账户当前状态
        if self.calculator:
            overview = self.calculator.calculate_account_overview(account)
            report['current_status'] = overview

        return report

    def generate_quarterly_report(self, account, year=None, quarter=None):
        """
        生成季报

        - 季度业绩
        - 策略回顾
        - 归因分析
        - 相关性分析
        """
        if year is None:
            year = datetime.now().year
        if quarter is None:
            quarter = (datetime.now().month - 1) // 3 + 1

        quarter_start_month = (quarter - 1) * 3 + 1
        quarter_start = datetime(year, quarter_start_month, 1).date()

        if quarter == 4:
            quarter_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            quarter_end = datetime(year, quarter_start_month + 3, 1).date() - timedelta(days=1)

        # 生成各月报告并汇总
        monthly_reports = []
        for m in range(3):
            month = quarter_start_month + m
            monthly_reports.append(self.generate_monthly_report(account, year, month))

        # 汇总统计
        total_option_pnl = sum(r['performance']['option_pnl'] for r in monthly_reports)
        total_winning = sum(r['performance']['winning_trades'] for r in monthly_reports)
        total_losing = sum(r['performance']['losing_trades'] for r in monthly_reports)
        total_stock_trades = sum(r['trades']['stock_trades'] for r in monthly_reports)

        report = {
            'header': {
                'account': account,
                'period': f"{year}年Q{quarter}",
                'period_start': str(quarter_start),
                'period_end': str(quarter_end),
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'performance': {
                'total_option_pnl': total_option_pnl,
                'total_winning_trades': total_winning,
                'total_losing_trades': total_losing,
                'overall_win_rate': total_winning / (total_winning + total_losing) if (total_winning + total_losing) > 0 else 0,
                'total_stock_trades': total_stock_trades
            },
            'monthly_breakdown': monthly_reports
        }

        return report

    def export_to_excel(self, data, filename):
        """
        导出到Excel

        多sheet格式
        """
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 汇总表
            summary_df = pd.DataFrame([data.get('header', {})])
            summary_df.to_excel(writer, sheet_name='汇总', index=False)

            # 业绩表
            if 'performance' in data:
                perf_df = pd.DataFrame([data['performance']])
                perf_df.to_excel(writer, sheet_name='业绩', index=False)

            # 交易记录
            if 'transactions' in data and data['transactions']:
                trans_df = pd.DataFrame(data['transactions'])
                trans_df.to_excel(writer, sheet_name='股票交易', index=False)

            # 期权记录
            if 'options_opened' in data and data['options_opened']:
                opt_df = pd.DataFrame(data['options_opened'])
                opt_df.to_excel(writer, sheet_name='期权开仓', index=False)

            if 'options_closed' in data and data['options_closed']:
                opt_df = pd.DataFrame(data['options_closed'])
                opt_df.to_excel(writer, sheet_name='期权平仓', index=False)

        output.seek(0)

        # 保存到文件
        with open(filename, 'wb') as f:
            f.write(output.getvalue())

        return filename

    def export_to_csv(self, data, filename):
        """导出到CSV"""
        if 'transactions' in data and data['transactions']:
            df = pd.DataFrame(data['transactions'])
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return filename
        return None

    def generate_holdings_report(self, account=None):
        """生成持仓报告"""
        if not self.calculator:
            return {'error': '需要计算器组件'}

        stocks = self.calculator.calculate_stock_summary(account=account)
        options = self.calculator.calculate_options_summary(account=account)

        open_options = options[options['status'] == '持仓中'] if not options.empty else pd.DataFrame()

        report = {
            'header': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'account': account or '全部账户'
            },
            'stocks': {
                'count': len(stocks),
                'total_investment': stocks['总投入'].sum() if not stocks.empty else 0,
                'holdings': stocks.to_dict('records') if not stocks.empty else []
            },
            'options': {
                'count': len(open_options),
                'holdings': open_options.to_dict('records') if not open_options.empty else []
            }
        }

        return report

    def get_report_templates(self):
        """获取可用的报告模板"""
        return [
            {'id': 'weekly', 'name': '周报', 'description': '每周交易汇总和分析'},
            {'id': 'monthly', 'name': '月报', 'description': '月度业绩和交易分析'},
            {'id': 'quarterly', 'name': '季报', 'description': '季度策略回顾和归因分析'},
            {'id': 'holdings', 'name': '持仓报告', 'description': '当前持仓详情'}
        ]
