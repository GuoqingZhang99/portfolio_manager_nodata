"""
业绩归因分析，分解收益来源
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


class PerformanceAttribution:
    """归因分析器"""

    def __init__(self, db):
        """初始化归因分析器"""
        self.db = db

    def calculate_beta(self, portfolio_returns, benchmark_returns):
        """
        计算Beta值

        公式: Beta = Cov(组合, 基准) / Var(基准)
        """
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 1.0

        # 确保长度一致
        min_len = min(len(portfolio_returns), len(benchmark_returns))
        p_ret = portfolio_returns[-min_len:]
        b_ret = benchmark_returns[-min_len:]

        covariance = np.cov(p_ret, b_ret)[0][1]
        variance = np.var(b_ret)

        if variance == 0:
            return 1.0

        return covariance / variance

    def calculate_alpha(self, portfolio_return, benchmark_return, beta, risk_free_rate=0.02):
        """
        计算Alpha（Jensen's Alpha）

        公式: Alpha = 组合收益 - (无风险利率 + Beta * (基准收益 - 无风险利率))
        """
        expected_return = risk_free_rate + beta * (benchmark_return - risk_free_rate)
        return portfolio_return - expected_return

    def _get_benchmark_returns(self, symbol, start_date, end_date):
        """获取基准收益率数据"""
        conn = self.db.get_connection()

        df = pd.read_sql_query('''
            SELECT price_date, daily_return
            FROM benchmark_prices
            WHERE benchmark_symbol = ?
              AND price_date BETWEEN ? AND ?
            ORDER BY price_date
        ''', conn, params=[symbol, start_date, end_date])

        conn.close()

        if df.empty:
            return None, None

        # 计算累计收益
        df['cumulative'] = (1 + df['daily_return'].fillna(0)).cumprod() - 1
        total_return = df['cumulative'].iloc[-1] if len(df) > 0 else 0

        return df['daily_return'].fillna(0).values, total_return

    def _get_portfolio_returns(self, account, start_date, end_date):
        """获取组合收益率数据"""
        # 从现金流和持仓变化计算组合收益
        # 简化实现：使用股价历史数据

        conn = self.db.get_connection()

        # 获取持仓股票
        holdings_query = '''
            SELECT DISTINCT stock_symbol
            FROM transactions
            WHERE account_name = ?
        '''
        holdings = pd.read_sql_query(holdings_query, conn, params=[account])

        if holdings.empty:
            conn.close()
            return None, None

        symbols = holdings['stock_symbol'].tolist()

        # 获取各股票收益率
        all_returns = []
        for symbol in symbols:
            df = pd.read_sql_query('''
                SELECT price_date, daily_return
                FROM stock_price_history
                WHERE stock_symbol = ?
                  AND price_date BETWEEN ? AND ?
                ORDER BY price_date
            ''', conn, params=[symbol, start_date, end_date])

            if not df.empty:
                all_returns.append(df.set_index('price_date')['daily_return'])

        conn.close()

        if not all_returns:
            return None, None

        # 简单平均（实际应该按权重计算）
        combined = pd.concat(all_returns, axis=1)
        portfolio_daily = combined.mean(axis=1).fillna(0)

        # 累计收益
        cumulative = (1 + portfolio_daily).cumprod() - 1
        total_return = cumulative.iloc[-1] if len(cumulative) > 0 else 0

        return portfolio_daily.values, total_return

    def attribute_returns(self, account, start_date, end_date, benchmark='SPY'):
        """
        主归因函数

        Returns:
            dict: 归因分析结果
        """
        # 获取组合收益
        portfolio_daily, portfolio_total = self._get_portfolio_returns(account, start_date, end_date)

        # 获取基准收益
        benchmark_daily, benchmark_total = self._get_benchmark_returns(benchmark, start_date, end_date)

        if portfolio_daily is None or benchmark_daily is None:
            return {
                'error': '数据不足，无法进行归因分析',
                'total_return': 0,
                'benchmark_return': 0,
            }

        # 计算Beta
        beta = self.calculate_beta(portfolio_daily, benchmark_daily)

        # Beta贡献
        beta_contribution = benchmark_total * beta

        # 总Alpha
        total_alpha = portfolio_total - beta_contribution

        # Alpha细分（简化方法）
        # 实际应该基于更复杂的因子模型
        selection_alpha = total_alpha * 0.4  # 选股贡献
        timing_alpha = total_alpha * 0.2     # 择时贡献
        strategy_alpha = self._calculate_strategy_alpha(account, start_date, end_date)
        allocation_alpha = total_alpha - selection_alpha - timing_alpha - strategy_alpha

        result = {
            'account_name': account,
            'analysis_period': f"{start_date} 至 {end_date}",
            'start_date': start_date,
            'end_date': end_date,
            'total_return': portfolio_total,
            'benchmark_return': benchmark_total,
            'excess_return': portfolio_total - benchmark_total,
            'portfolio_beta': beta,
            'beta_contribution': beta_contribution,
            'total_alpha': total_alpha,
            'selection_alpha': selection_alpha,
            'timing_alpha': timing_alpha,
            'strategy_alpha': strategy_alpha,
            'allocation_alpha': allocation_alpha,
        }

        # 保存分析结果
        self._save_attribution_result(result)

        return result

    def _calculate_strategy_alpha(self, account, start_date, end_date):
        """计算策略Alpha（期权策略贡献）"""
        # 获取期间内的期权盈亏
        options = self.db.get_options_trades(account=account)

        if options.empty:
            return 0

        # 筛选期间内平仓的期权
        closed = options[
            (options['status'] != '持仓中') &
            (options['close_date'] >= str(start_date)) &
            (options['close_date'] <= str(end_date))
        ]

        if closed.empty:
            return 0

        # 计算期权盈亏
        total_pnl = 0
        for _, opt in closed.iterrows():
            premium = opt['premium_per_share'] * opt['contracts'] * 100
            close_amount = (opt['close_price_per_share'] or 0) * opt['contracts'] * 100
            fees = opt['opening_fee'] + opt['closing_fee']

            if opt['option_type'] in ['卖Call', '卖Put']:
                pnl = premium - close_amount - fees
            else:
                pnl = close_amount - premium - fees

            total_pnl += pnl

        # 获取账户总资金
        accounts = self.db.get_accounts()
        account_info = accounts[accounts['account_name'] == account]

        if account_info.empty:
            return 0

        total_capital = float(account_info.iloc[0]['total_capital'])

        # 转换为收益率
        return total_pnl / total_capital if total_capital > 0 else 0

    def _save_attribution_result(self, result):
        """保存归因分析结果"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO attribution_analysis (
                account_name, analysis_period, start_date, end_date,
                total_return, benchmark_return, excess_return,
                portfolio_beta, beta_contribution, total_alpha,
                selection_alpha, timing_alpha, strategy_alpha, allocation_alpha,
                detailed_breakdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['account_name'], result['analysis_period'],
            result['start_date'], result['end_date'],
            result['total_return'], result['benchmark_return'],
            result['excess_return'], result['portfolio_beta'],
            result['beta_contribution'], result['total_alpha'],
            result['selection_alpha'], result['timing_alpha'],
            result['strategy_alpha'], result['allocation_alpha'],
            json.dumps(result)
        ))

        conn.commit()
        conn.close()

    def get_attribution_history(self, account=None):
        """获取历史归因分析"""
        conn = self.db.get_connection()

        query = 'SELECT * FROM attribution_analysis WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)

        query += ' ORDER BY created_at DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def get_stock_contribution(self, account, start_date, end_date):
        """获取各股票贡献度"""
        conn = self.db.get_connection()

        # 获取持仓
        stocks_query = '''
            SELECT
                t.stock_symbol,
                SUM(CASE WHEN t.transaction_type = '买入' THEN t.shares * t.price
                         WHEN t.transaction_type = '卖出' THEN -t.shares * t.price
                         ELSE 0 END) as cost_basis
            FROM transactions t
            WHERE t.account_name = ?
              AND t.transaction_date <= ?
            GROUP BY t.stock_symbol
            HAVING cost_basis > 0
        '''

        stocks = pd.read_sql_query(stocks_query, conn, params=[account, end_date])

        if stocks.empty:
            conn.close()
            return pd.DataFrame()

        contributions = []
        for _, row in stocks.iterrows():
            symbol = row['stock_symbol']

            # 获取期间收益率
            prices = pd.read_sql_query('''
                SELECT close_price
                FROM stock_price_history
                WHERE stock_symbol = ?
                  AND price_date BETWEEN ? AND ?
                ORDER BY price_date
            ''', conn, params=[symbol, start_date, end_date])

            if len(prices) >= 2:
                start_price = prices.iloc[0]['close_price']
                end_price = prices.iloc[-1]['close_price']
                stock_return = (end_price - start_price) / start_price
            else:
                stock_return = 0

            contributions.append({
                'stock_symbol': symbol,
                'cost_basis': row['cost_basis'],
                'return': stock_return,
                'contribution': row['cost_basis'] * stock_return
            })

        conn.close()

        df = pd.DataFrame(contributions)

        if not df.empty:
            total_contribution = df['contribution'].sum()
            df['contribution_pct'] = df['contribution'] / abs(total_contribution) * 100 if total_contribution != 0 else 0

        return df
