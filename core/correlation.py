"""
持仓相关性分析和分散化评估
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json


class CorrelationAnalyzer:
    """相关性分析器"""

    def __init__(self, db):
        """初始化相关性分析器"""
        self.db = db

    def calculate_correlation_matrix(self, holdings, lookback_days=90):
        """
        计算相关性矩阵

        Args:
            holdings: list of stock symbols
            lookback_days: 回溯天数

        Returns:
            tuple: (correlation_matrix, statistics)
        """
        if not holdings or len(holdings) < 2:
            return None, None

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=lookback_days)

        conn = self.db.get_connection()

        # 获取各股票收益率
        returns_data = {}
        for symbol in holdings:
            df = pd.read_sql_query('''
                SELECT price_date, daily_return
                FROM stock_price_history
                WHERE stock_symbol = ?
                  AND price_date BETWEEN ? AND ?
                ORDER BY price_date
            ''', conn, params=[symbol, start_date, end_date])

            if not df.empty:
                returns_data[symbol] = df.set_index('price_date')['daily_return']

        conn.close()

        if len(returns_data) < 2:
            return None, None

        # 合并收益率数据
        returns_df = pd.DataFrame(returns_data)
        returns_df = returns_df.dropna()

        if len(returns_df) < 10:  # 最少需要10个数据点
            return None, None

        # 计算相关性矩阵
        corr_matrix = returns_df.corr()

        # 计算统计指标
        # 排除对角线（自相关=1）
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        upper_triangle = corr_matrix.where(mask)

        stats = {
            'max_correlation': float(upper_triangle.max().max()),
            'min_correlation': float(upper_triangle.min().min()),
            'avg_correlation': float(upper_triangle.mean().mean()),
            'lookback_period': lookback_days,
            'calculation_date': datetime.now().strftime('%Y-%m-%d'),
            'symbols': holdings
        }

        return corr_matrix, stats

    def identify_correlation_clusters(self, corr_matrix, threshold=0.7):
        """
        识别高相关集群

        Args:
            corr_matrix: 相关性矩阵
            threshold: 相关性阈值

        Returns:
            list: 高相关股票组
        """
        if corr_matrix is None:
            return []

        clusters = []
        symbols = corr_matrix.columns.tolist()
        visited = set()

        for i, sym1 in enumerate(symbols):
            if sym1 in visited:
                continue

            cluster = [sym1]
            visited.add(sym1)

            for j, sym2 in enumerate(symbols):
                if i != j and sym2 not in visited:
                    if abs(corr_matrix.loc[sym1, sym2]) >= threshold:
                        cluster.append(sym2)
                        visited.add(sym2)

            if len(cluster) > 1:
                # 获取集群内平均相关性
                cluster_corr = corr_matrix.loc[cluster, cluster]
                mask = np.triu(np.ones_like(cluster_corr, dtype=bool), k=1)
                avg_corr = cluster_corr.where(mask).mean().mean()

                clusters.append({
                    'symbols': cluster,
                    'avg_correlation': float(avg_corr),
                    'size': len(cluster)
                })

        return clusters

    def calculate_effective_n(self, holdings, corr_matrix, weights=None):
        """
        计算有效持股数

        公式: N_eff = 1 / Σ(w_i²)
        考虑相关性调整

        Args:
            holdings: list of symbols
            corr_matrix: 相关性矩阵
            weights: dict {symbol: weight}，如果为None则等权重

        Returns:
            float: 有效持股数
        """
        n = len(holdings)
        if n == 0:
            return 0

        if weights is None:
            weights = {sym: 1/n for sym in holdings}

        # 基础有效持股数（HHI的倒数）
        hhi = sum(w**2 for w in weights.values())
        basic_effective_n = 1 / hhi if hhi > 0 else n

        # 相关性调整
        if corr_matrix is not None:
            # 计算加权平均相关性
            weighted_corr = 0
            total_weight = 0

            for i, sym1 in enumerate(holdings):
                for j, sym2 in enumerate(holdings):
                    if i < j:
                        w = weights.get(sym1, 0) * weights.get(sym2, 0)
                        weighted_corr += w * abs(corr_matrix.loc[sym1, sym2])
                        total_weight += w

            if total_weight > 0:
                avg_corr = weighted_corr / total_weight
                # 相关性越高，有效持股数越低
                adjusted_effective_n = basic_effective_n * (1 - avg_corr)
            else:
                adjusted_effective_n = basic_effective_n
        else:
            adjusted_effective_n = basic_effective_n

        return max(1, adjusted_effective_n)

    def calculate_diversification_score(self, holdings, corr_matrix, weights=None, sector_data=None):
        """
        计算分散化评分

        综合评分0-100，考虑：
        - 持股数量
        - 平均相关性
        - 有效持股数
        - 板块分散度

        Returns:
            dict: 分散化评分和详情
        """
        n = len(holdings)

        if n == 0:
            return {
                'score': 0,
                'rating': '无持仓',
                'details': {},
                'recommendations': ['添加投资标的']
            }

        # 1. 持股数量评分 (0-25)
        if n >= 15:
            count_score = 25
        elif n >= 10:
            count_score = 20
        elif n >= 5:
            count_score = 15
        elif n >= 3:
            count_score = 10
        else:
            count_score = 5

        # 2. 相关性评分 (0-35)
        corr_score = 35
        if corr_matrix is not None:
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
            avg_corr = corr_matrix.where(mask).mean().mean()

            if avg_corr >= 0.8:
                corr_score = 5
            elif avg_corr >= 0.6:
                corr_score = 15
            elif avg_corr >= 0.4:
                corr_score = 25
            else:
                corr_score = 35
        else:
            avg_corr = None

        # 3. 有效持股数评分 (0-20)
        effective_n = self.calculate_effective_n(holdings, corr_matrix, weights)
        effective_ratio = effective_n / n if n > 0 else 0

        if effective_ratio >= 0.8:
            effective_score = 20
        elif effective_ratio >= 0.6:
            effective_score = 15
        elif effective_ratio >= 0.4:
            effective_score = 10
        else:
            effective_score = 5

        # 4. 板块分散度评分 (0-20)
        sector_score = 10  # 默认中等
        unique_sectors = 0

        if sector_data:
            sectors = [sector_data.get(sym) for sym in holdings if sector_data.get(sym)]
            unique_sectors = len(set(sectors))

            if unique_sectors >= 5:
                sector_score = 20
            elif unique_sectors >= 3:
                sector_score = 15
            elif unique_sectors >= 2:
                sector_score = 10
            else:
                sector_score = 5

        # 总分
        total_score = count_score + corr_score + effective_score + sector_score

        # 评级
        if total_score >= 80:
            rating = '优秀'
        elif total_score >= 60:
            rating = '良好'
        elif total_score >= 40:
            rating = '一般'
        else:
            rating = '较差'

        # 生成建议
        recommendations = []

        if n < 5:
            recommendations.append('建议增加持股数量至5只以上')
        if avg_corr and avg_corr > 0.6:
            recommendations.append('持仓相关性较高，建议增加低相关性标的')
        if effective_ratio < 0.5:
            recommendations.append('有效持股数较低，可能存在过度集中')
        if unique_sectors < 3:
            recommendations.append('板块集中度较高，建议增加其他板块投资')

        return {
            'score': total_score,
            'rating': rating,
            'details': {
                'count_score': count_score,
                'corr_score': corr_score,
                'effective_score': effective_score,
                'sector_score': sector_score,
                'holding_count': n,
                'avg_correlation': avg_corr,
                'effective_n': effective_n,
                'unique_sectors': unique_sectors
            },
            'recommendations': recommendations
        }

    def save_correlation_analysis(self, account, corr_matrix, stats):
        """保存相关性分析结果"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # 将矩阵转为JSON
        corr_data = corr_matrix.to_json() if corr_matrix is not None else None

        cursor.execute('''
            INSERT INTO correlation_matrix (
                account_name, calculation_date, lookback_period,
                correlation_data, max_correlation, min_correlation, avg_correlation
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            account, stats.get('calculation_date'),
            stats.get('lookback_period'), corr_data,
            stats.get('max_correlation'), stats.get('min_correlation'),
            stats.get('avg_correlation')
        ))

        conn.commit()
        conn.close()

    def get_correlation_history(self, account=None):
        """获取历史相关性分析"""
        conn = self.db.get_connection()

        query = 'SELECT * FROM correlation_matrix WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)

        query += ' ORDER BY created_at DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def get_high_correlation_pairs(self, corr_matrix, threshold=0.7):
        """获取高相关性股票对"""
        if corr_matrix is None:
            return []

        pairs = []
        symbols = corr_matrix.columns.tolist()

        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    corr = corr_matrix.loc[sym1, sym2]
                    if abs(corr) >= threshold:
                        pairs.append({
                            'symbol1': sym1,
                            'symbol2': sym2,
                            'correlation': float(corr)
                        })

        return sorted(pairs, key=lambda x: abs(x['correlation']), reverse=True)

    def suggest_diversification(self, current_holdings, corr_matrix, potential_stocks):
        """
        建议分散化股票

        Args:
            current_holdings: 当前持仓
            corr_matrix: 相关性矩阵
            potential_stocks: 候选股票列表

        Returns:
            list: 推荐的低相关性股票
        """
        if not potential_stocks or corr_matrix is None:
            return []

        suggestions = []

        for stock in potential_stocks:
            if stock in current_holdings:
                continue

            # 计算与现有持仓的平均相关性
            correlations = []
            for holding in current_holdings:
                if holding in corr_matrix.columns and stock in corr_matrix.columns:
                    correlations.append(abs(corr_matrix.loc[holding, stock]))

            if correlations:
                avg_corr = np.mean(correlations)
                suggestions.append({
                    'symbol': stock,
                    'avg_correlation': float(avg_corr),
                    'diversification_benefit': 1 - avg_corr
                })

        # 按分散化收益排序
        return sorted(suggestions, key=lambda x: x['diversification_benefit'], reverse=True)
