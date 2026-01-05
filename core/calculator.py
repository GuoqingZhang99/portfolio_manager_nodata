"""
投资组合计算引擎
"""

import pandas as pd
import numpy as np
from datetime import datetime


class PortfolioCalculator:
    """核心计算器"""

    def __init__(self, db):
        """初始化计算器"""
        self.db = db

    def calculate_stock_summary(self, account=None):
        """
        计算股票汇总表

        Returns:
            DataFrame: 包含持仓、成本、盈亏的汇总表
        """
        transactions = self.db.get_transactions(account=account)

        if transactions.empty:
            return pd.DataFrame()

        # 计算带符号股数和金额
        transactions['signed_shares'] = transactions.apply(
            lambda x: x['shares'] if x['transaction_type'] == '买入' else -x['shares'],
            axis=1
        )

        transactions['signed_amount'] = transactions.apply(
            lambda x: -(x['price'] * x['shares'] + x['commission'])
            if x['transaction_type'] == '买入'
            else (x['price'] * x['shares'] - x['commission']),
            axis=1
        )

        # 按股票汇总
        summary = transactions.groupby(['stock_symbol', 'account_name']).agg({
            'signed_shares': 'sum',
            'signed_amount': 'sum',
            'shares': 'sum',
            'commission': 'sum'
        }).reset_index()

        summary.columns = ['股票代码', '账户', '当前股数', '净现金流', '总交易股数', '总佣金']

        # 过滤持仓大于0的
        summary = summary[summary['当前股数'] > 0].copy()

        if summary.empty:
            return summary

        # 计算平均成本
        summary['平均成本'] = summary.apply(
            lambda x: abs(x['净现金流']) / x['当前股数'] if x['当前股数'] > 0 else 0,
            axis=1
        )

        # 计算总投入
        summary['总投入'] = summary['平均成本'] * summary['当前股数']

        # 获取期权锁定的股票
        options = self.db.get_options_trades(status='持仓中')
        if not options.empty:
            # 计算卖Call锁定的股票
            cc_locked = options[options['option_type'] == '卖Call'].groupby(
                ['stock_symbol', 'account_name']
            )['contracts'].sum().reset_index()
            cc_locked['锁定股数'] = cc_locked['contracts'] * 100
            cc_locked = cc_locked.drop('contracts', axis=1)

            summary = summary.merge(
                cc_locked,
                left_on=['股票代码', '账户'],
                right_on=['stock_symbol', 'account_name'],
                how='left'
            )
            summary['锁定股数'] = summary['锁定股数'].fillna(0)

            # 删除合并产生的多余列
            if 'stock_symbol' in summary.columns:
                summary = summary.drop(['stock_symbol', 'account_name'], axis=1)
        else:
            summary['锁定股数'] = 0

        summary['可用股数'] = summary['当前股数'] - summary['锁定股数']

        return summary

    def calculate_options_summary(self, account=None):
        """
        计算期权汇总

        Returns:
            DataFrame: 包含期权盈亏、锁定资本的汇总表
        """
        options = self.db.get_options_trades(account=account)

        if options.empty:
            return pd.DataFrame()

        # 计算总权利金
        options['总权利金'] = options['premium_per_share'] * options['contracts'] * 100

        # 计算平仓支出/收入
        options['平仓金额'] = options.apply(
            lambda x: x['close_price_per_share'] * x['contracts'] * 100
            if pd.notna(x['close_price_per_share']) else 0,
            axis=1
        )

        # 计算净盈亏
        options['净盈亏'] = options.apply(
            lambda x: (x['总权利金'] - x['平仓金额'] - x['opening_fee'] - x['closing_fee'])
            if x['option_type'] in ['卖Call', '卖Put']
            else (x['平仓金额'] - x['总权利金'] - x['opening_fee'] - x['closing_fee']),
            axis=1
        )

        # 计算持仓天数
        options['持仓天数'] = options.apply(
            lambda x: (datetime.strptime(str(x['close_date'])[:10], '%Y-%m-%d') -
                      datetime.strptime(str(x['open_date'])[:10], '%Y-%m-%d')).days
            if pd.notna(x['close_date'])
            else (datetime.now() - datetime.strptime(str(x['open_date'])[:10], '%Y-%m-%d')).days,
            axis=1
        )

        # 计算锁定资本（CSP）
        options['锁定资本'] = options.apply(
            lambda x: x['strike_price'] * x['contracts'] * 100
            if x['option_type'] == '卖Put' and x['status'] == '持仓中'
            else 0,
            axis=1
        )

        # 计算剩余天数
        options['剩余天数'] = options.apply(
            lambda x: (datetime.strptime(str(x['expiration_date'])[:10], '%Y-%m-%d') -
                      datetime.now()).days
            if x['status'] == '持仓中' else None,
            axis=1
        )

        return options

    def calculate_account_overview(self, account_name):
        """
        计算账户总览

        Returns:
            dict: 包含所有关键指标的字典
        """
        # 获取账户配置
        accounts = self.db.get_accounts()
        account_info = accounts[accounts['account_name'] == account_name]

        if account_info.empty:
            return {}

        account_info = account_info.iloc[0]

        total_capital = float(account_info['total_capital'])
        cash_reserve = float(account_info['cash_reserve'])
        conditional_reserve = float(account_info['conditional_reserve'])

        # 计算股票持仓
        stocks = self.calculate_stock_summary(account=account_name)
        stock_investment = float(stocks['总投入'].sum()) if not stocks.empty else 0

        # 计算期权
        options = self.calculate_options_summary(account=account_name)
        open_options = options[options['status'] == '持仓中'] if not options.empty else pd.DataFrame()

        # 锁定的现金（CSP保证金）
        locked_cash = float(open_options['锁定资本'].sum()) if not open_options.empty else 0

        # 期权已收权利金
        option_premium_received = float(
            open_options[open_options['option_type'].isin(['卖Call', '卖Put'])]['总权利金'].sum()
        ) if not open_options.empty else 0

        # 计算可用现金
        used_capital = stock_investment + locked_cash
        available_cash = total_capital - used_capital

        # 可用于投资的资金（排除现金储备）
        investable_capital = total_capital - cash_reserve
        available_for_investment = investable_capital - used_capital

        # 股票仓位占比
        stock_position_pct = (stock_investment / total_capital * 100) if total_capital > 0 else 0

        # 期权锁定比例
        option_locked_pct = (locked_cash / total_capital * 100) if total_capital > 0 else 0

        # 总使用资金比例
        total_used_pct = ((stock_investment + locked_cash) / total_capital * 100) if total_capital > 0 else 0

        # 计算总盈亏
        # 1. 获取净现金流入（利息、存款、取出）
        cash_flows = self.db.get_cash_flows(account=account_name)
        net_cash_flow = 0
        if not cash_flows.empty:
            flow_types = ['利息', '存入', '取出']
            relevant_flows = cash_flows[cash_flows['flow_type'].isin(flow_types)]
            net_cash_flow = float(relevant_flows['amount'].sum()) if not relevant_flows.empty else 0

        # 2. 获取当前股票市值
        current_stock_value = 0
        if not stocks.empty:
            try:
                from utils.data_fetcher import batch_get_prices
                symbols = stocks['股票代码'].unique().tolist()
                current_prices = batch_get_prices(symbols)

                for _, stock in stocks.iterrows():
                    symbol = stock['股票代码']
                    if symbol in current_prices and current_prices[symbol]:
                        current_stock_value += current_prices[symbol] * stock['当前股数']
                    else:
                        # 如果没有当前价格，使用成本价
                        current_stock_value += stock['总投入']
            except:
                # 如果获取价格失败，使用成本价
                current_stock_value = stock_investment

        # 3. 计算当前总资产（股票市值 + 现金 + 期权锁定）
        current_total_assets = current_stock_value + available_cash + locked_cash

        # 4. 计算总盈亏 = 当前总资产 - 初始资金 - 净现金流入
        total_pnl = current_total_assets - total_capital - net_cash_flow

        # 5. 计算盈亏比
        base_capital = total_capital + net_cash_flow
        pnl_ratio = (total_pnl / base_capital * 100) if base_capital > 0 else 0

        return {
            '总资金': total_capital,
            '现金储备': cash_reserve,
            '条件性预留': conditional_reserve,
            '已投入股票': stock_investment,
            '期权锁定现金': locked_cash,
            '期权权利金收入': option_premium_received,
            '可用现金': available_cash,
            '可投资资金': investable_capital,
            '可用投资额度': available_for_investment,
            '股票仓位占比%': stock_position_pct,
            '期权锁定占比%': option_locked_pct,
            '总使用资金占比%': total_used_pct,
            '可用总资金': available_cash + conditional_reserve,
            '持股数量': len(stocks) if not stocks.empty else 0,
            '期权持仓数': len(open_options) if not open_options.empty else 0,
            # 新增盈亏指标
            '当前总资产': current_total_assets,
            '净现金流入': net_cash_flow,
            '总盈亏': total_pnl,
            '总盈亏比%': pnl_ratio,
        }

    def calculate_realized_pnl(self, account=None, symbol=None, start_date=None, end_date=None):
        """
        计算已实现盈亏

        Returns:
            dict: 已实现盈亏详情
        """
        # 获取已平仓的期权
        options = self.db.get_options_trades(account=account, symbol=symbol)
        if not options.empty:
            closed_options = options[options['status'] != '持仓中']
        else:
            closed_options = pd.DataFrame()

        # 过滤日期
        if start_date and not closed_options.empty:
            closed_options = closed_options[closed_options['close_date'] >= str(start_date)]
        if end_date and not closed_options.empty:
            closed_options = closed_options[closed_options['close_date'] <= str(end_date)]

        # 计算期权已实现盈亏
        option_realized = 0
        if not closed_options.empty:
            for _, opt in closed_options.iterrows():
                premium = opt['premium_per_share'] * opt['contracts'] * 100
                close_amount = (opt['close_price_per_share'] or 0) * opt['contracts'] * 100
                fees = opt['opening_fee'] + opt['closing_fee']

                if opt['option_type'] in ['卖Call', '卖Put']:
                    pnl = premium - close_amount - fees
                else:
                    pnl = close_amount - premium - fees

                option_realized += pnl

        # TODO: 计算股票已实现盈亏（需要先进先出或平均成本法）

        return {
            '期权已实现盈亏': option_realized,
            '股票已实现盈亏': 0,  # TODO
            '总已实现盈亏': option_realized,
        }

    def calculate_unrealized_pnl(self, account=None, current_prices=None):
        """
        计算未实现盈亏

        Args:
            account: 账户名称
            current_prices: dict {symbol: price} 当前价格

        Returns:
            DataFrame: 未实现盈亏详情
        """
        stocks = self.calculate_stock_summary(account=account)

        if stocks.empty or not current_prices:
            return pd.DataFrame()

        # 添加当前价格
        stocks['当前价格'] = stocks['股票代码'].map(current_prices)

        # 计算市值
        stocks['市值'] = stocks['当前股数'] * stocks['当前价格']

        # 计算未实现盈亏
        stocks['未实现盈亏'] = stocks['市值'] - stocks['总投入']
        stocks['未实现盈亏%'] = (stocks['市值'] / stocks['总投入'] - 1) * 100

        return stocks

    def get_portfolio_holdings(self, account=None):
        """获取投资组合持仓"""
        stocks = self.calculate_stock_summary(account=account)
        options = self.calculate_options_summary(account=account)

        return {
            'stocks': stocks,
            'options': options[options['status'] == '持仓中'] if not options.empty else pd.DataFrame()
        }

    def calculate_sector_allocation(self, account=None):
        """计算板块配置"""
        conn = self.db.get_connection()

        query = '''
            SELECT
                s.sector,
                SUM(
                    CASE WHEN t.transaction_type = '买入' THEN t.shares
                         WHEN t.transaction_type = '卖出' THEN -t.shares
                         ELSE 0 END
                ) as total_shares,
                AVG(t.price) as avg_price
            FROM transactions t
            LEFT JOIN stock_settings s ON t.stock_symbol = s.stock_symbol
            WHERE 1=1
        '''
        params = []

        if account:
            query += ' AND t.account_name = ?'
            params.append(account)

        query += ' GROUP BY s.sector HAVING total_shares > 0'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        if df.empty:
            return df

        df['market_value'] = df['total_shares'] * df['avg_price']
        df['percentage'] = df['market_value'] / df['market_value'].sum() * 100

        return df

    def simulate_transaction_impact(self, account, symbol, trans_type, price, shares, commission=0):
        """
        模拟交易影响（不保存数据）

        Args:
            account: 账户名称
            symbol: 股票代码
            trans_type: 交易类型（买入/卖出）
            price: 价格
            shares: 股数
            commission: 佣金

        Returns:
            dict: 包含模拟结果的字典
        """
        # 获取当前账户信息
        accounts = self.db.get_accounts()
        account_info = accounts[accounts['account_name'] == account]

        if account_info.empty:
            return {'error': '账户不存在'}

        account_info = account_info.iloc[0]
        total_capital = float(account_info['total_capital'])
        cash_reserve = float(account_info['cash_reserve'])
        target_min = float(account_info.get('target_position_min', 0))
        target_max = float(account_info.get('target_position_max', 100))

        # 获取当前持仓
        stocks = self.calculate_stock_summary(account=account)
        current_stock_investment = float(stocks['总投入'].sum()) if not stocks.empty else 0

        # 获取期权锁定资金
        options = self.calculate_options_summary(account=account)
        open_options = options[options['status'] == '持仓中'] if not options.empty else pd.DataFrame()
        locked_cash = float(open_options['锁定资本'].sum()) if not open_options.empty else 0

        # 计算当前可用现金
        current_used = current_stock_investment + locked_cash
        current_available_cash = total_capital - current_used

        # 计算交易金额
        transaction_amount = price * shares + commission

        # 模拟交易后的变化
        if trans_type == '买入':
            new_stock_investment = current_stock_investment + transaction_amount
            new_available_cash = current_available_cash - transaction_amount
            cash_change = -transaction_amount
        else:  # 卖出
            new_stock_investment = current_stock_investment - (price * shares - commission)
            new_available_cash = current_available_cash + (price * shares - commission)
            cash_change = price * shares - commission

        # 计算新仓位占比
        new_position_pct = (new_stock_investment / total_capital * 100) if total_capital > 0 else 0
        current_position_pct = (current_stock_investment / total_capital * 100) if total_capital > 0 else 0

        # 计算该股票在投资组合中的占比
        symbol_upper = symbol.upper()
        current_symbol_value = 0
        if not stocks.empty:
            symbol_stocks = stocks[stocks['股票代码'] == symbol_upper]
            if not symbol_stocks.empty:
                current_symbol_value = float(symbol_stocks['总投入'].iloc[0])

        # 模拟后该股票的价值
        if trans_type == '买入':
            new_symbol_value = current_symbol_value + transaction_amount
        else:
            new_symbol_value = max(0, current_symbol_value - (price * shares - commission))

        new_symbol_pct = (new_symbol_value / total_capital * 100) if total_capital > 0 else 0

        # 检查仓位目标限制
        targets = self.db.get_position_targets(account=account)
        target_info = None
        if not targets.empty:
            symbol_target = targets[targets['stock_symbol'] == symbol_upper]
            if not symbol_target.empty:
                target_info = symbol_target.iloc[0]

        # 生成警告和建议
        warnings = []
        suggestions = []

        # 检查现金是否足够
        if trans_type == '买入' and new_available_cash < 0:
            warnings.append(f"⚠️ 资金不足！缺少 ${abs(new_available_cash):,.2f}")
            suggestions.append(f"建议减少买入数量到 {int(current_available_cash / price)} 股")

        # 检查现金储备
        if new_available_cash < cash_reserve:
            warnings.append(f"⚠️ 可用现金将低于储备要求（${cash_reserve:,.2f}）")
            suggestions.append("建议保留足够的现金储备")

        # 检查总仓位
        if new_position_pct > target_max:
            warnings.append(f"⚠️ 总仓位将超过上限 {target_max}%")
            suggestions.append(f"建议减少投资或调整仓位上限")
        elif new_position_pct < target_min:
            warnings.append(f"⚠️ 总仓位将低于下限 {target_min}%")
            suggestions.append("建议增加投资或调整仓位下限")

        # 检查个股仓位限制
        if target_info is not None:
            if pd.notna(target_info.get('max_percentage')):
                max_pct = float(target_info['max_percentage'])
                if new_symbol_pct > max_pct:
                    warnings.append(f"⚠️ {symbol_upper} 占比将超过设定上限 {max_pct}%")
                    max_value = total_capital * max_pct / 100
                    suggestions.append(f"建议 {symbol_upper} 投资额不超过 ${max_value:,.2f}")

            if pd.notna(target_info.get('max_amount')):
                max_amt = float(target_info['max_amount'])
                if new_symbol_value > max_amt:
                    warnings.append(f"⚠️ {symbol_upper} 投资额将超过设定上限 ${max_amt:,.2f}")
                    suggestions.append(f"建议减少买入数量")

        # 如果没有警告，给予正面反馈
        if not warnings:
            if trans_type == '买入':
                suggestions.append("✅ 交易符合您的投资策略")
            else:
                suggestions.append("✅ 卖出操作正常")

        return {
            'success': True,
            '交易类型': trans_type,
            '交易金额': transaction_amount,
            '现金变化': cash_change,
            '当前状态': {
                '总资金': total_capital,
                '当前股票投资': current_stock_investment,
                '当前仓位占比': current_position_pct,
                '当前可用现金': current_available_cash,
                f'{symbol_upper}当前投资': current_symbol_value,
                f'{symbol_upper}当前占比': (current_symbol_value / total_capital * 100) if total_capital > 0 else 0
            },
            '交易后预测': {
                '新股票投资': new_stock_investment,
                '新仓位占比': new_position_pct,
                '剩余现金': new_available_cash,
                f'{symbol_upper}新投资额': new_symbol_value,
                f'{symbol_upper}新占比': new_symbol_pct,
                '仓位变化': new_position_pct - current_position_pct
            },
            '目标范围': {
                '总仓位下限': target_min,
                '总仓位上限': target_max,
                '现金储备要求': cash_reserve
            },
            '警告': warnings,
            '建议': suggestions
        }
