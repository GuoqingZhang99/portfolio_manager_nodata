"""
灵活仓位管理和再平衡
"""

import pandas as pd
from datetime import datetime


class PositionManager:
    """仓位管理器"""

    def __init__(self, db, calculator):
        """初始化仓位管理器"""
        self.db = db
        self.calculator = calculator

    def set_position_target(self, target_data):
        """
        设置仓位目标

        Args:
            target_data: dict
                - stock_symbol: 股票代码
                - account_name: 账户名称
                - target_type: 目标类型（百分比/金额/股数）
                - target_percentage: 目标百分比
                - target_amount: 目标金额
                - target_shares: 目标股数
                - max_percentage: 最大百分比
                - max_amount: 最大金额
                - max_shares: 最大股数
                - priority: 优先级（1-10）
                - rebalance_threshold: 再平衡阈值（%）
                - notes: 备注
        """
        return self.db.set_position_target(
            symbol=target_data['stock_symbol'],
            account=target_data['account_name'],
            target_type=target_data['target_type'],
            target_percentage=target_data.get('target_percentage'),
            target_amount=target_data.get('target_amount'),
            target_shares=target_data.get('target_shares'),
            max_percentage=target_data.get('max_percentage'),
            max_amount=target_data.get('max_amount'),
            max_shares=target_data.get('max_shares'),
            priority=target_data.get('priority', 5),
            rebalance_threshold=target_data.get('rebalance_threshold', 10),
            notes=target_data.get('notes')
        )

    def get_position_analysis(self, account, current_prices=None):
        """
        仓位分析

        Args:
            account: 账户名称
            current_prices: dict {symbol: price}

        Returns:
            DataFrame: 仓位分析结果
        """
        # 获取账户信息
        accounts = self.db.get_accounts()
        account_info = accounts[accounts['account_name'] == account]

        if account_info.empty:
            return pd.DataFrame()

        total_capital = float(account_info.iloc[0]['total_capital'])

        # 获取当前持仓
        stocks = self.calculator.calculate_stock_summary(account=account)

        # 获取仓位目标（需要提前获取，以便获取所有相关股票的价格）
        targets = self.db.get_position_targets(account=account)

        # 获取当前价格（如果没有提供）
        if current_prices is None:
            from utils.data_fetcher import batch_get_prices

            # 获取需要查询价格的股票（持仓股票 + 目标股票）
            symbols = []
            if not stocks.empty:
                symbols.extend(stocks['股票代码'].unique().tolist())

            # 也获取已设置目标但未持仓的股票价格
            if not targets.empty:
                target_symbols = targets['stock_symbol'].unique().tolist()
                symbols.extend([s for s in target_symbols if s not in symbols])

            if symbols:
                current_prices = batch_get_prices(symbols)
            else:
                current_prices = {}

        # 添加当前价格和盈亏信息（如果有持仓）
        if not stocks.empty:
            stocks['当前价格'] = stocks['股票代码'].apply(
                lambda x: current_prices.get(x) if current_prices else None
            )
            stocks['当前市值'] = stocks.apply(
                lambda x: x['当前价格'] * x['当前股数'] if x['当前价格'] else None,
                axis=1
            )
            stocks['盈亏金额'] = stocks.apply(
                lambda x: x['当前市值'] - x['总投入'] if x['当前市值'] else None,
                axis=1
            )
            stocks['盈亏%'] = stocks.apply(
                lambda x: (x['盈亏金额'] / x['总投入'] * 100) if x['总投入'] and x['盈亏金额'] is not None else None,
                axis=1
            )

        # 检查是否有仓位目标
        if targets.empty:
            # 如果没有设定目标，返回当前持仓分析（添加空列保持一致性）
            if not stocks.empty:
                stocks['目标金额'] = None
                stocks['偏离金额'] = None
                stocks['偏离%'] = None
                stocks['需要再平衡'] = False
                stocks['建议操作'] = None
                stocks['建议股数'] = None
            return stocks

        analysis = []

        for _, target in targets.iterrows():
            symbol = target['stock_symbol']

            # 查找当前持仓
            current_holding = stocks[stocks['股票代码'] == symbol] if not stocks.empty else pd.DataFrame()

            if not current_holding.empty:
                current_amount = float(current_holding.iloc[0]['总投入'])
                current_shares = int(current_holding.iloc[0]['当前股数'])
                avg_cost = float(current_holding.iloc[0]['平均成本'])
            else:
                current_amount = 0
                current_shares = 0
                avg_cost = 0

            # 计算目标金额
            if target['target_type'] == '百分比':
                target_amount = total_capital * (target['target_percentage'] or 0) / 100
                max_amount = total_capital * (target['max_percentage'] or 100) / 100
            elif target['target_type'] == '股数':
                # 根据当前价格计算目标金额
                current_price = current_prices.get(symbol) if current_prices else avg_cost
                target_shares_value = target['target_shares'] or 0
                max_shares_value = target['max_shares'] or int(target_shares_value * 1.5)
                target_amount = target_shares_value * current_price if current_price else 0
                max_amount = max_shares_value * current_price if current_price else target_amount * 1.5
            else:  # 金额
                target_amount = target['target_amount'] or 0
                max_amount = target['max_amount'] or target_amount * 1.5

            # 计算偏离
            deviation_amount = current_amount - target_amount
            deviation_pct = ((current_amount / target_amount) - 1) * 100 if target_amount > 0 else 0

            # 判断是否需要再平衡
            threshold = target['rebalance_threshold'] or 10
            needs_rebalance = abs(deviation_pct) > threshold

            # 生成建议
            # 如果是股数目标，直接计算股数差异
            if target['target_type'] == '股数':
                target_shares_value = target['target_shares'] or 0
                shares_diff = current_shares - target_shares_value

                if shares_diff > 0:
                    action = '减仓'
                    action_shares = shares_diff
                elif shares_diff < 0:
                    # 如果当前没有持仓，标记为"开仓"
                    action = '开仓' if current_shares == 0 else '加仓'
                    action_shares = abs(shares_diff)
                else:
                    action = '持有'
                    action_shares = 0
            else:
                # 百分比和金额目标，通过金额计算
                if deviation_amount > 0:
                    action = '减仓'
                    action_shares = round(deviation_amount / avg_cost) if avg_cost > 0 else 0
                elif deviation_amount < 0:
                    # 如果当前没有持仓，标记为"开仓"
                    action = '开仓' if current_shares == 0 else '加仓'
                    # 如果有当前价格，用当前价格计算
                    if current_prices and symbol in current_prices:
                        action_shares = round(abs(deviation_amount) / current_prices[symbol])
                    else:
                        action_shares = round(abs(deviation_amount) / avg_cost) if avg_cost > 0 else 0
                else:
                    action = '持有'
                    action_shares = 0

            # 获取价格和盈亏信息（如果有持仓）
            if not current_holding.empty:
                current_price = current_holding.iloc[0].get('当前价格')
                current_market_value = current_holding.iloc[0].get('当前市值')
                pnl_amount = current_holding.iloc[0].get('盈亏金额')
                pnl_pct = current_holding.iloc[0].get('盈亏%')
            else:
                current_price = current_prices.get(symbol) if current_prices else None
                current_market_value = None
                pnl_amount = None
                pnl_pct = None

            analysis.append({
                '股票代码': symbol,
                '当前股数': current_shares,
                '当前金额': current_amount,
                '平均成本': avg_cost,
                '当前价格': current_price,
                '当前市值': current_market_value,
                '盈亏金额': pnl_amount,
                '盈亏%': pnl_pct,
                '目标类型': target['target_type'],
                '目标金额': target_amount,
                '最大限额': max_amount,
                '偏离金额': deviation_amount,
                '偏离%': deviation_pct,
                '再平衡阈值%': threshold,
                '需要再平衡': needs_rebalance,
                '建议操作': action,
                '建议股数': action_shares,
                '优先级': target['priority']
            })

        df = pd.DataFrame(analysis)

        # 添加没有设置目标的持仓股票
        if not stocks.empty:
            # 找出没有设置目标的股票
            target_symbols = set(target['stock_symbol'] for _, target in targets.iterrows())
            all_symbols = set(stocks['股票代码'].unique())
            stocks_without_targets = all_symbols - target_symbols

            if stocks_without_targets:
                # 为没有目标的股票添加记录
                for symbol in stocks_without_targets:
                    stock_data = stocks[stocks['股票代码'] == symbol].iloc[0]

                    # 添加到分析中，但标记为没有目标
                    analysis.append({
                        '股票代码': symbol,
                        '当前股数': int(stock_data['当前股数']),
                        '当前金额': float(stock_data['总投入']),
                        '平均成本': float(stock_data['平均成本']),
                        '当前价格': stock_data.get('当前价格'),
                        '当前市值': stock_data.get('当前市值'),
                        '盈亏金额': stock_data.get('盈亏金额'),
                        '盈亏%': stock_data.get('盈亏%'),
                        '目标类型': None,
                        '目标金额': None,
                        '最大限额': None,
                        '偏离金额': None,
                        '偏离%': None,
                        '再平衡阈值%': None,
                        '需要再平衡': False,
                        '建议操作': '未设置目标',
                        '建议股数': None,
                        '优先级': 999  # 低优先级
                    })

                # 重新创建DataFrame
                df = pd.DataFrame(analysis)

        # 按优先级排序
        if not df.empty:
            df = df.sort_values('优先级')

        return df

    def get_rebalance_plan(self, account, current_prices=None):
        """
        生成再平衡计划

        Returns:
            dict: 再平衡计划详情
        """
        analysis = self.get_position_analysis(account, current_prices)

        if analysis.empty:
            return {
                'needs_rebalance': [],
                'to_buy': [],
                'to_sell': [],
                'cash_needed': 0,
                'cash_freed': 0,
                'net_cash': 0
            }

        # 检查是否有必要的列（没有设置目标时不会有这些列）
        if '需要再平衡' not in analysis.columns or '建议操作' not in analysis.columns:
            return {
                'needs_rebalance': [],
                'to_buy': [],
                'to_sell': [],
                'cash_needed': 0,
                'cash_freed': 0,
                'net_cash': 0,
                'message': '请先为股票设置仓位目标'
            }

        # 筛选需要再平衡的
        needs_rebalance = analysis[analysis['需要再平衡'] == True]

        if needs_rebalance.empty:
            return {
                'needs_rebalance': [],
                'to_buy': [],
                'to_sell': [],
                'cash_needed': 0,
                'cash_freed': 0,
                'net_cash': 0,
                'message': '所有仓位在目标范围内，无需再平衡'
            }

        # 分类：需要买入和需要卖出
        to_buy = needs_rebalance[needs_rebalance['建议操作'] == '加仓'].copy()
        to_sell = needs_rebalance[needs_rebalance['建议操作'] == '减仓'].copy()

        # 计算资金需求
        if not to_buy.empty:
            to_buy['所需资金'] = to_buy.apply(
                lambda x: x['建议股数'] * (current_prices.get(x['股票代码'], x['平均成本'])
                                      if current_prices else x['平均成本']),
                axis=1
            )
            cash_needed = to_buy['所需资金'].sum()
        else:
            cash_needed = 0

        if not to_sell.empty:
            to_sell['释放资金'] = to_sell['建议股数'] * to_sell['平均成本']
            cash_freed = to_sell['释放资金'].sum()
        else:
            cash_freed = 0

        return {
            'needs_rebalance': needs_rebalance.to_dict('records'),
            'to_buy': to_buy.to_dict('records') if not to_buy.empty else [],
            'to_sell': to_sell.to_dict('records') if not to_sell.empty else [],
            'cash_needed': cash_needed,
            'cash_freed': cash_freed,
            'net_cash': cash_freed - cash_needed
        }

    def check_position_limits(self, account, symbol, additional_amount=0):
        """
        检查仓位限制

        Args:
            account: 账户名称
            symbol: 股票代码
            additional_amount: 计划增加的金额

        Returns:
            dict: 限制检查结果
        """
        from config import POSITION_LIMITS

        accounts = self.db.get_accounts()
        account_info = accounts[accounts['account_name'] == account]

        if account_info.empty:
            return {'ok': False, 'reason': '账户不存在'}

        total_capital = float(account_info.iloc[0]['total_capital'])

        # 获取当前持仓
        stocks = self.calculator.calculate_stock_summary(account=account)

        current_amount = 0
        if not stocks.empty:
            current_stock = stocks[stocks['股票代码'] == symbol.upper()]
            if not current_stock.empty:
                current_amount = float(current_stock.iloc[0]['总投入'])

        # 检查单股限制
        new_amount = current_amount + additional_amount
        new_pct = new_amount / total_capital * 100

        max_single_stock_pct = POSITION_LIMITS.get('max_single_stock_pct', 15)

        if new_pct > max_single_stock_pct:
            return {
                'ok': False,
                'reason': f'超过单股限制({max_single_stock_pct}%)',
                'current_pct': current_amount / total_capital * 100,
                'new_pct': new_pct,
                'max_allowed': total_capital * max_single_stock_pct / 100 - current_amount
            }

        # 获取仓位目标
        targets = self.db.get_position_targets(account=account)
        if not targets.empty:
            target = targets[targets['stock_symbol'] == symbol.upper()]
            if not target.empty:
                max_amount = target.iloc[0]['max_amount']
                max_pct = target.iloc[0]['max_percentage']

                if max_amount and new_amount > max_amount:
                    return {
                        'ok': False,
                        'reason': f'超过设定的最大金额限制(${max_amount:,.0f})',
                        'max_allowed': max_amount - current_amount
                    }

                if max_pct and new_pct > max_pct:
                    return {
                        'ok': False,
                        'reason': f'超过设定的最大比例限制({max_pct}%)',
                        'max_allowed': total_capital * max_pct / 100 - current_amount
                    }

        return {
            'ok': True,
            'current_pct': current_amount / total_capital * 100,
            'new_pct': new_pct,
            'remaining_capacity': total_capital * max_single_stock_pct / 100 - new_amount
        }

    def get_position_summary(self, account):
        """获取仓位汇总"""
        accounts = self.db.get_accounts()
        account_info = accounts[accounts['account_name'] == account]

        if account_info.empty:
            return {}

        total_capital = float(account_info.iloc[0]['total_capital'])
        target_min = float(account_info.iloc[0]['target_position_min'] or 0)
        target_max = float(account_info.iloc[0]['target_position_max'] or 100)

        # 获取账户概览
        overview = self.calculator.calculate_account_overview(account)

        current_position_pct = overview.get('股票仓位占比%', 0)

        # 判断仓位状态
        if current_position_pct < target_min:
            position_status = '偏低'
            suggestion = f'建议增加仓位至{target_min}%以上'
        elif current_position_pct > target_max:
            position_status = '偏高'
            suggestion = f'建议降低仓位至{target_max}%以下'
        else:
            position_status = '正常'
            suggestion = '仓位在目标范围内'

        return {
            '总资金': total_capital,
            '已投资金额': overview.get('已投入股票', 0),
            '当前仓位%': current_position_pct,
            '目标下限%': target_min,
            '目标上限%': target_max,
            '仓位状态': position_status,
            '建议': suggestion,
            '可用于投资': overview.get('可用投资额度', 0)
        }

    def calculate_portfolio_weight(self, account):
        """计算组合权重"""
        stocks = self.calculator.calculate_stock_summary(account=account)

        if stocks.empty:
            return pd.DataFrame()

        total_investment = stocks['总投入'].sum()

        stocks['权重%'] = stocks['总投入'] / total_investment * 100

        return stocks[['股票代码', '当前股数', '总投入', '权重%']]
