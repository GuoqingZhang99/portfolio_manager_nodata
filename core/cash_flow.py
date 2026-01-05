"""
现金流自动追踪和分析
"""

import pandas as pd
from datetime import datetime


class CashFlowManager:
    """现金流管理器"""

    def __init__(self, db):
        """初始化现金流管理器"""
        self.db = db

    def auto_generate_from_transaction(self, transaction_id):
        """
        从交易记录自动生成现金流

        买入 → 现金流出（负数）
        卖出 → 现金流入（正数）
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM transactions WHERE transaction_id = ?',
            (transaction_id,)
        )
        trans = cursor.fetchone()
        conn.close()

        if not trans:
            return None

        trans = dict(trans)

        # 计算金额
        total_amount = trans['price'] * trans['shares']

        if trans['transaction_type'] == '买入':
            flow_type = '股票买入'
            amount = -(total_amount + trans['commission'])
            description = f"买入 {trans['stock_symbol']} {trans['shares']}股 @ ${trans['price']}"
        else:
            flow_type = '股票卖出'
            amount = total_amount - trans['commission']
            description = f"卖出 {trans['stock_symbol']} {trans['shares']}股 @ ${trans['price']}"

        # 添加现金流记录
        flow_id = self.db.add_cash_flow(
            flow_date=trans['transaction_date'],
            account=trans['account_name'],
            flow_type=flow_type,
            amount=amount,
            stock_symbol=trans['stock_symbol'],
            related_transaction_id=transaction_id,
            is_realized=True,
            description=description,
            auto_generated=True
        )

        # 如果有佣金，单独记录
        if trans['commission'] > 0:
            self.db.add_cash_flow(
                flow_date=trans['transaction_date'],
                account=trans['account_name'],
                flow_type='佣金',
                amount=-trans['commission'],
                stock_symbol=trans['stock_symbol'],
                related_transaction_id=transaction_id,
                description=f"{trans['stock_symbol']} 交易佣金",
                auto_generated=True
            )

        return flow_id

    def auto_generate_from_option(self, option_id, is_close=False):
        """
        从期权交易自动生成现金流

        开仓：
        - 卖Call/Put → 权利金流入
        - 买Call/Put → 权利金流出

        平仓：反向流动
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM options_trades WHERE option_id = ?',
            (option_id,)
        )
        option = cursor.fetchone()
        conn.close()

        if not option:
            return None

        option = dict(option)

        contracts = option['contracts']
        premium = option['premium_per_share'] * contracts * 100

        if not is_close:
            # 开仓
            if option['option_type'] in ['卖Call', '卖Put']:
                flow_type = '期权权利金收入'
                amount = premium - option['opening_fee']
                description = f"卖出 {option['stock_symbol']} {option['option_type']} " \
                             f"${option['strike_price']} {contracts}张"
            else:
                flow_type = '期权权利金支出'
                amount = -(premium + option['opening_fee'])
                description = f"买入 {option['stock_symbol']} {option['option_type']} " \
                             f"${option['strike_price']} {contracts}张"

            flow_date = option['open_date']
        else:
            # 平仓
            close_premium = (option['close_price_per_share'] or 0) * contracts * 100

            if option['option_type'] in ['卖Call', '卖Put']:
                flow_type = '期权平仓'
                amount = -(close_premium + option['closing_fee'])
                description = f"平仓 {option['stock_symbol']} {option['option_type']} " \
                             f"${option['strike_price']} {contracts}张"
            else:
                flow_type = '期权平仓'
                amount = close_premium - option['closing_fee']
                description = f"平仓 {option['stock_symbol']} {option['option_type']} " \
                             f"${option['strike_price']} {contracts}张"

            flow_date = option['close_date']

        # 添加现金流记录
        flow_id = self.db.add_cash_flow(
            flow_date=flow_date,
            account=option['account_name'],
            flow_type=flow_type,
            amount=amount,
            stock_symbol=option['stock_symbol'],
            related_option_id=option_id,
            is_realized=True,
            description=description,
            auto_generated=True
        )

        return flow_id

    def auto_generate_from_dividend(self, dividend_id):
        """从分红记录自动生成现金流"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM dividends WHERE dividend_id = ?',
            (dividend_id,)
        )
        dividend = cursor.fetchone()
        conn.close()

        if not dividend:
            return None

        dividend = dict(dividend)

        # 净分红（扣税后）
        net_dividend = dividend['total_dividend'] - dividend['tax_withheld']

        description = f"{dividend['stock_symbol']} 分红 " \
                     f"${dividend['dividend_per_share']}/股 x {dividend['shares_held']}股"

        flow_id = self.db.add_cash_flow(
            flow_date=dividend['payment_date'] or dividend['ex_dividend_date'],
            account=dividend['account_name'],
            flow_type='分红',
            amount=net_dividend,
            stock_symbol=dividend['stock_symbol'],
            is_realized=True,
            description=description,
            auto_generated=True
        )

        return flow_id

    def get_cash_flow_statement(self, account=None, start_date=None, end_date=None):
        """
        生成现金流量表

        Returns:
            dict: 现金流量表，分为经营、投资、融资三类
        """
        flows = self.db.get_cash_flows(
            account=account,
            start_date=start_date,
            end_date=end_date
        )

        if flows.empty:
            return {
                '经营活动现金流': {},
                '投资活动现金流': {},
                '融资活动现金流': {},
                '净现金流': 0
            }

        # 分类现金流
        operating_types = ['分红', '期权权利金收入', '期权权利金支出', '期权平仓', '利息']
        investing_types = ['股票买入', '股票卖出']
        financing_types = ['存入', '取出']

        # 经营活动
        operating = flows[flows['flow_type'].isin(operating_types)]
        operating_summary = operating.groupby('flow_type')['amount'].sum().to_dict()
        operating_total = operating['amount'].sum()

        # 投资活动
        investing = flows[flows['flow_type'].isin(investing_types)]
        investing_summary = investing.groupby('flow_type')['amount'].sum().to_dict()
        investing_total = investing['amount'].sum()

        # 融资活动
        financing = flows[flows['flow_type'].isin(financing_types)]
        financing_summary = financing.groupby('flow_type')['amount'].sum().to_dict()
        financing_total = financing['amount'].sum()

        # 佣金单独列出
        commissions = flows[flows['flow_type'] == '佣金']
        commission_total = commissions['amount'].sum()

        return {
            '经营活动现金流': {
                '明细': operating_summary,
                '小计': operating_total
            },
            '投资活动现金流': {
                '明细': investing_summary,
                '小计': investing_total
            },
            '融资活动现金流': {
                '明细': financing_summary,
                '小计': financing_total
            },
            '佣金支出': commission_total,
            '净现金流': operating_total + investing_total + financing_total + commission_total
        }

    def calculate_realized_vs_unrealized(self, account=None):
        """
        计算已实现 vs 未实现盈亏

        Returns:
            dict: 盈亏分解
        """
        # 已实现盈亏来自现金流
        flows = self.db.get_cash_flows(account=account)

        realized = {
            '期权盈亏': 0,
            '分红收入': 0,
            '利息收入': 0,
        }

        if not flows.empty:
            # 期权相关
            option_flows = flows[flows['flow_type'].isin([
                '期权权利金收入', '期权权利金支出', '期权平仓'
            ])]
            realized['期权盈亏'] = option_flows['amount'].sum()

            # 分红
            dividend_flows = flows[flows['flow_type'] == '分红']
            realized['分红收入'] = dividend_flows['amount'].sum()

            # 利息
            interest_flows = flows[flows['flow_type'] == '利息']
            realized['利息收入'] = interest_flows['amount'].sum()

        realized['总已实现盈亏'] = sum(realized.values())

        return realized

    def get_cash_flow_by_stock(self, symbol, account=None):
        """获取单只股票的现金流"""
        flows = self.db.get_cash_flows(account=account)

        if flows.empty:
            return pd.DataFrame()

        stock_flows = flows[flows['stock_symbol'] == symbol.upper()]

        return stock_flows

    def get_monthly_summary(self, account=None, year=None, month=None):
        """获取月度现金流汇总"""
        flows = self.db.get_cash_flows(account=account)

        if flows.empty:
            return pd.DataFrame()

        flows['flow_date'] = pd.to_datetime(flows['flow_date'])
        flows['year'] = flows['flow_date'].dt.year
        flows['month'] = flows['flow_date'].dt.month

        if year:
            flows = flows[flows['year'] == year]
        if month:
            flows = flows[flows['month'] == month]

        summary = flows.groupby(['year', 'month', 'flow_type']).agg({
            'amount': 'sum',
            'flow_id': 'count'
        }).reset_index()

        summary.columns = ['年', '月', '类型', '金额', '笔数']

        return summary

    def add_manual_cash_flow(self, flow_date, account, flow_type, amount,
                            description=None, notes=None):
        """手动添加现金流（存取款等）"""
        return self.db.add_cash_flow(
            flow_date=flow_date,
            account=account,
            flow_type=flow_type,
            amount=amount,
            description=description,
            notes=notes,
            auto_generated=False
        )
