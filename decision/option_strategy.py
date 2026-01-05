"""
期权策略智能评估引擎
"""

import pandas as pd
from datetime import datetime
import json


class OptionStrategyEngine:
    """策略引擎"""

    def __init__(self, db):
        """初始化策略引擎"""
        self.db = db
        self.initialize_default_rules()

    def initialize_default_rules(self):
        """初始化默认策略规则"""
        rules = self.db.get_strategy_rules()

        if rules.empty:
            default_rules = [
                {
                    'rule_name': '保守型CC',
                    'option_type': '卖Call',
                    'description': '低Delta、高时间价值的Covered Call',
                    'min_delta': 0.15,
                    'max_delta': 0.30,
                    'min_dte': 21,
                    'max_dte': 45,
                    'min_annualized_return': 8,
                    'recommendation_score': 80,
                    'recommendation_text': '低风险CC策略，适合长期持股'
                },
                {
                    'rule_name': '激进型CC',
                    'option_type': '卖Call',
                    'description': '较高Delta、高权利金的Covered Call',
                    'min_delta': 0.30,
                    'max_delta': 0.45,
                    'min_dte': 14,
                    'max_dte': 30,
                    'min_annualized_return': 15,
                    'recommendation_score': 70,
                    'recommendation_text': '较高收益但有被行权风险'
                },
                {
                    'rule_name': '保守型CSP',
                    'option_type': '卖Put',
                    'description': '低Delta的Cash Secured Put',
                    'min_delta': 0.15,
                    'max_delta': 0.25,
                    'min_dte': 21,
                    'max_dte': 45,
                    'min_annualized_return': 8,
                    'recommendation_score': 80,
                    'recommendation_text': '安全的CSP策略，适合等待低价买入'
                },
                {
                    'rule_name': '高IV策略',
                    'option_type': '卖Call',
                    'description': '高IV环境下的期权策略',
                    'min_iv_percentile': 70,
                    'max_iv_percentile': 100,
                    'min_dte': 14,
                    'max_dte': 45,
                    'min_annualized_return': 20,
                    'recommendation_score': 85,
                    'recommendation_text': 'IV处于高位，卖出期权收益较好'
                },
                {
                    'rule_name': '高IV CSP',
                    'option_type': '卖Put',
                    'description': '高IV环境下的CSP策略',
                    'min_iv_percentile': 70,
                    'max_iv_percentile': 100,
                    'min_dte': 21,
                    'max_dte': 45,
                    'min_annualized_return': 15,
                    'recommendation_score': 85,
                    'recommendation_text': 'IV处于高位，CSP收益较好'
                }
            ]

            for rule in default_rules:
                self.add_strategy_rule(rule)

    def add_strategy_rule(self, rule_data):
        """添加策略规则"""
        return self.db.add_strategy_rule(
            rule_name=rule_data.get('rule_name'),
            option_type=rule_data.get('option_type'),
            description=rule_data.get('description'),
            min_delta=rule_data.get('min_delta'),
            max_delta=rule_data.get('max_delta'),
            min_theta=rule_data.get('min_theta'),
            max_theta=rule_data.get('max_theta'),
            min_vega=rule_data.get('min_vega'),
            max_vega=rule_data.get('max_vega'),
            min_iv_percentile=rule_data.get('min_iv_percentile'),
            max_iv_percentile=rule_data.get('max_iv_percentile'),
            min_annualized_return=rule_data.get('min_annualized_return'),
            min_dte=rule_data.get('min_dte'),
            max_dte=rule_data.get('max_dte'),
            recommendation_score=rule_data.get('recommendation_score'),
            recommendation_text=rule_data.get('recommendation_text')
        )

    def evaluate_option(self, option_data):
        """
        评估期权策略

        Args:
            option_data: dict 包含期权参数
                - stock_symbol: 股票代码
                - option_type: 期权类型（卖Call/卖Put/买Call/买Put）
                - strike_price: 行权价
                - expiration_date: 到期日
                - current_stock_price: 当前股价
                - option_premium: 期权价格
                - delta: Delta值
                - gamma: Gamma值
                - theta: Theta值
                - vega: Vega值
                - implied_volatility: 隐含波动率
                - iv_percentile: IV百分位

        Returns:
            dict: 评估结果
        """
        # 计算到期天数
        if isinstance(option_data['expiration_date'], str):
            exp_date = datetime.strptime(option_data['expiration_date'], '%Y-%m-%d')
        else:
            exp_date = option_data['expiration_date']

        dte = (exp_date - datetime.now()).days

        # 计算年化收益率
        stock_price = option_data['current_stock_price']
        premium = option_data['option_premium']
        strike = option_data['strike_price']
        option_type = option_data['option_type']

        # 根据期权类型计算年化收益率
        if option_type == '卖Call':
            # 基于股价的收益率
            single_return = premium / stock_price * 100
            base_price = stock_price
        elif option_type == '卖Put':
            # 基于行权价的收益率（因为需要准备这么多现金）
            single_return = premium / strike * 100
            base_price = strike
        elif option_type == '买Call':
            # 买Call的盈亏平衡
            single_return = 0  # 买方没有固定收益
            base_price = strike + premium
        else:  # 买Put
            single_return = 0
            base_price = strike - premium

        annualized_return = single_return * (365 / dte) if dte > 0 else 0

        # 计算盈亏平衡点
        if option_type == '卖Call':
            breakeven = stock_price + premium
        elif option_type == '卖Put':
            breakeven = strike - premium
        elif option_type == '买Call':
            breakeven = strike + premium
        else:
            breakeven = strike - premium

        # 匹配策略规则
        rules = self.db.get_strategy_rules(option_type=option_type)
        matched_rules = []
        max_score = 0
        best_recommendation = ''

        for _, rule in rules.iterrows():
            if self._match_rule(option_data, rule, dte, annualized_return):
                matched_rules.append(rule['rule_name'])
                if rule['recommendation_score'] > max_score:
                    max_score = rule['recommendation_score']
                    best_recommendation = rule['recommendation_text']

        # 风险评估
        risk_assessment = self._assess_risk(option_data, annualized_return)

        # 构建评估结果
        result = {
            'stock_symbol': option_data['stock_symbol'],
            'option_type': option_type,
            'strike_price': strike,
            'expiration_date': option_data['expiration_date'],
            'current_stock_price': stock_price,
            'option_premium': premium,
            'delta': option_data.get('delta'),
            'gamma': option_data.get('gamma'),
            'theta': option_data.get('theta'),
            'vega': option_data.get('vega'),
            'implied_volatility': option_data.get('implied_volatility'),
            'iv_percentile': option_data.get('iv_percentile'),
            'days_to_expiration': dte,
            'annualized_return': annualized_return,
            'breakeven_price': breakeven,
            'matched_rules': ','.join(matched_rules),
            'recommendation_score': max_score,
            'recommendation': best_recommendation if best_recommendation else '无匹配策略',
            'risk_assessment': risk_assessment
        }

        # 保存评估记录
        self.db.save_option_evaluation(result)

        return result

    def _match_rule(self, option_data, rule, dte, annualized_return):
        """检查期权是否匹配规则"""
        delta = abs(option_data.get('delta', 0) or 0)
        theta = abs(option_data.get('theta', 0) or 0)
        vega = option_data.get('vega', 0) or 0
        iv_percentile = option_data.get('iv_percentile')

        # 检查Delta范围
        if rule['min_delta'] is not None and delta < rule['min_delta']:
            return False
        if rule['max_delta'] is not None and delta > rule['max_delta']:
            return False

        # 检查Theta范围
        if rule['min_theta'] is not None and theta < rule['min_theta']:
            return False
        if rule['max_theta'] is not None and theta > rule['max_theta']:
            return False

        # 检查Vega范围
        if rule['min_vega'] is not None and vega < rule['min_vega']:
            return False
        if rule['max_vega'] is not None and vega > rule['max_vega']:
            return False

        # 检查IV百分位
        if iv_percentile is not None:
            if rule['min_iv_percentile'] is not None and iv_percentile < rule['min_iv_percentile']:
                return False
            if rule['max_iv_percentile'] is not None and iv_percentile > rule['max_iv_percentile']:
                return False

        # 检查年化收益率
        if rule['min_annualized_return'] is not None and annualized_return < rule['min_annualized_return']:
            return False

        # 检查到期天数
        if rule['min_dte'] is not None and dte < rule['min_dte']:
            return False
        if rule['max_dte'] is not None and dte > rule['max_dte']:
            return False

        return True

    def _assess_risk(self, option_data, annualized_return):
        """风险评估"""
        risks = []
        risk_level = '低'

        delta = abs(option_data.get('delta', 0) or 0)
        iv_percentile = option_data.get('iv_percentile')
        theta = abs(option_data.get('theta', 0) or 0)

        # Delta风险
        if delta > 0.4:
            risks.append(f'Delta较高({delta:.2f})，被行权风险较大')
            risk_level = '高'
        elif delta > 0.3:
            risks.append(f'Delta中等({delta:.2f})，有一定行权风险')
            risk_level = '中'

        # IV风险
        if iv_percentile is not None:
            if iv_percentile < 30:
                risks.append(f'IV百分位较低({iv_percentile})，权利金可能不够')
            elif iv_percentile > 80:
                risks.append(f'IV百分位很高({iv_percentile})，波动风险大')

        # 收益率评估
        if annualized_return < 8:
            risks.append(f'年化收益率较低({annualized_return:.1f}%)')
        elif annualized_return > 30:
            risks.append(f'年化收益率很高({annualized_return:.1f}%)，可能有隐含风险')

        # Theta评估
        if theta < 0.01:
            risks.append('Theta衰减较慢，时间价值不理想')

        return {
            'level': risk_level,
            'risks': risks
        }

    def get_evaluation_history(self, symbol=None, executed=None):
        """获取评估历史"""
        conn = self.db.get_connection()

        query = 'SELECT * FROM option_evaluations WHERE 1=1'
        params = []

        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol.upper())
        if executed is not None:
            query += ' AND executed = ?'
            params.append(executed)

        query += ' ORDER BY evaluation_date DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def mark_as_executed(self, eval_id):
        """标记评估已执行"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE option_evaluations
            SET executed = 1, execution_date = CURRENT_TIMESTAMP
            WHERE eval_id = ?
        ''', (eval_id,))

        conn.commit()
        conn.close()

    def get_quick_analysis(self, symbol, current_price, option_chain=None):
        """
        快速分析建议

        基于当前价格和期权链，推荐合适的期权策略
        """
        suggestions = []

        # 如果没有期权链数据，生成基本建议
        if option_chain is None:
            # 建议的CC行权价（OTM 5-10%）
            cc_strikes = [
                current_price * 1.05,
                current_price * 1.08,
                current_price * 1.10
            ]

            for strike in cc_strikes:
                suggestions.append({
                    'type': '卖Call',
                    'strike': round(strike, 2),
                    'reason': f'OTM {(strike/current_price - 1)*100:.1f}%，被行权风险较低'
                })

            # 建议的CSP行权价（OTM 5-10%）
            csp_strikes = [
                current_price * 0.95,
                current_price * 0.92,
                current_price * 0.90
            ]

            for strike in csp_strikes:
                suggestions.append({
                    'type': '卖Put',
                    'strike': round(strike, 2),
                    'reason': f'OTM {(1 - strike/current_price)*100:.1f}%，安全边际较好'
                })

        return {
            'symbol': symbol,
            'current_price': current_price,
            'suggestions': suggestions
        }
