"""
数据库操作基类，提供所有CRUD操作
"""

import sqlite3
import os
import shutil
from datetime import datetime
import pandas as pd


class Database:
    """数据库管理类"""

    def __init__(self, db_path):
        """初始化数据库连接"""
        self.db_path = db_path

        # 确保数据目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

        # 初始化数据库
        self.init_database()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """创建所有表和索引"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. 账户配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL UNIQUE,
                total_capital DECIMAL(12, 2) NOT NULL,
                cash_reserve DECIMAL(12, 2) DEFAULT 0,
                conditional_reserve DECIMAL(12, 2) DEFAULT 0,
                target_position_min DECIMAL(5, 2),
                target_position_max DECIMAL(5, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. 交易记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date DATE NOT NULL,
                account_name TEXT NOT NULL,
                stock_symbol TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                shares INTEGER NOT NULL,
                commission DECIMAL(8, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_name) REFERENCES accounts(account_name)
            )
        ''')

        # 3. 期权交易表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options_trades (
                option_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                stock_symbol TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strike_price DECIMAL(10, 2) NOT NULL,
                expiration_date DATE NOT NULL,
                premium_per_share DECIMAL(8, 2) NOT NULL,
                contracts INTEGER NOT NULL,
                delta DECIMAL(4, 3),
                gamma DECIMAL(6, 4),
                theta DECIMAL(6, 3),
                vega DECIMAL(6, 3),
                implied_volatility DECIMAL(6, 4),
                iv_percentile INTEGER,
                open_date DATE NOT NULL,
                close_date DATE,
                close_price_per_share DECIMAL(8, 2),
                opening_fee DECIMAL(8, 2) DEFAULT 0,
                closing_fee DECIMAL(8, 2) DEFAULT 0,
                status TEXT DEFAULT '持仓中',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_name) REFERENCES accounts(account_name)
            )
        ''')

        # 4. 股票配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_settings (
                stock_symbol TEXT PRIMARY KEY,
                account_name TEXT,
                category TEXT,
                sector TEXT,
                target_investment DECIMAL(12, 2),
                stop_loss_pct DECIMAL(5, 2),
                take_profit_pct DECIMAL(5, 2),
                cc_eligible BOOLEAN DEFAULT 0,
                investment_thesis TEXT,
                status TEXT DEFAULT '观察中',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 5. 仓位目标配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS position_targets (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                account_name TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_percentage DECIMAL(5, 2),
                target_amount DECIMAL(12, 2),
                max_percentage DECIMAL(5, 2),
                max_amount DECIMAL(12, 2),
                priority INTEGER DEFAULT 5,
                rebalance_threshold DECIMAL(5, 2) DEFAULT 10,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_symbol, account_name)
            )
        ''')

        # 6. 现金流记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_flows (
                flow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_date DATE NOT NULL,
                account_name TEXT NOT NULL,
                flow_type TEXT NOT NULL,
                related_transaction_id INTEGER,
                related_option_id INTEGER,
                stock_symbol TEXT,
                amount DECIMAL(12, 2) NOT NULL,
                is_realized BOOLEAN DEFAULT 1,
                description TEXT,
                notes TEXT,
                auto_generated BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_transaction_id) REFERENCES transactions(transaction_id),
                FOREIGN KEY (related_option_id) REFERENCES options_trades(option_id)
            )
        ''')

        # 7. 分红记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dividends (
                dividend_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                account_name TEXT NOT NULL,
                ex_dividend_date DATE NOT NULL,
                payment_date DATE,
                dividend_per_share DECIMAL(8, 4) NOT NULL,
                shares_held INTEGER NOT NULL,
                total_dividend DECIMAL(12, 2) NOT NULL,
                dividend_type TEXT DEFAULT '普通',
                reinvested BOOLEAN DEFAULT 0,
                tax_withheld DECIMAL(10, 2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 8. 价格预警表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                target_price DECIMAL(10, 2) NOT NULL,
                current_price DECIMAL(10, 2),
                notification_method TEXT DEFAULT '邮件',
                email_address TEXT,
                planned_action TEXT,
                planned_shares INTEGER,
                planned_notes TEXT,
                status TEXT DEFAULT '激活',
                triggered_at TIMESTAMP,
                triggered_price DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 9. 期权策略规则表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_strategy_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                option_type TEXT NOT NULL,
                description TEXT,
                min_delta DECIMAL(4, 3),
                max_delta DECIMAL(4, 3),
                min_theta DECIMAL(6, 3),
                max_theta DECIMAL(6, 3),
                min_vega DECIMAL(6, 3),
                max_vega DECIMAL(6, 3),
                min_iv_percentile INTEGER,
                max_iv_percentile INTEGER,
                min_annualized_return DECIMAL(5, 2),
                min_dte INTEGER,
                max_dte INTEGER,
                recommendation_score INTEGER,
                recommendation_text TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 10. 期权评估记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_evaluations (
                eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strike_price DECIMAL(10, 2),
                expiration_date DATE,
                current_stock_price DECIMAL(10, 2),
                option_premium DECIMAL(8, 2),
                delta DECIMAL(4, 3),
                gamma DECIMAL(6, 4),
                theta DECIMAL(6, 3),
                vega DECIMAL(6, 3),
                implied_volatility DECIMAL(6, 4),
                iv_percentile INTEGER,
                days_to_expiration INTEGER,
                annualized_return DECIMAL(6, 2),
                breakeven_price DECIMAL(10, 2),
                matched_rules TEXT,
                recommendation_score INTEGER,
                recommendation TEXT,
                evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                execution_date TIMESTAMP
            )
        ''')

        # 11. 交易日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_journal (
                journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                option_id INTEGER,
                stock_symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                trade_date DATE NOT NULL,
                account_name TEXT NOT NULL,
                reason TEXT,
                target_price DECIMAL(10, 2),
                expected_holding_period TEXT,
                expected_return DECIMAL(6, 2),
                stop_loss DECIMAL(10, 2),
                stop_profit DECIMAL(10, 2),
                max_acceptable_loss DECIMAL(12, 2),
                main_risks TEXT,
                market_condition TEXT,
                vix_level DECIMAL(6, 2),
                confidence_level INTEGER,
                emotional_state TEXT,
                decision_quality INTEGER,
                tags TEXT,
                met_expectation BOOLEAN,
                deviation_reason TEXT,
                lessons_learned TEXT,
                improvements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
                FOREIGN KEY (option_id) REFERENCES options_trades(option_id)
            )
        ''')

        # 12. 总结记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                period_start DATE,
                period_end DATE,
                auto_generated_data TEXT,
                what_worked TEXT,
                what_failed TEXT,
                market_observations TEXT,
                future_plans TEXT,
                lessons_learned TEXT,
                methodology_updates TEXT,
                completion_status TEXT DEFAULT '草稿',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        # 13. 股价历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_price_history (
                price_id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL,
                price_date DATE NOT NULL,
                close_price DECIMAL(10, 2) NOT NULL,
                daily_return DECIMAL(8, 4),
                volume BIGINT,
                UNIQUE(stock_symbol, price_date)
            )
        ''')

        # 14. 基准指数历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS benchmark_prices (
                price_id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_symbol TEXT NOT NULL,
                price_date DATE NOT NULL,
                close_price DECIMAL(10, 2) NOT NULL,
                daily_return DECIMAL(8, 4),
                UNIQUE(benchmark_symbol, price_date)
            )
        ''')

        # 15. 相关性矩阵表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correlation_matrix (
                matrix_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT,
                calculation_date DATE NOT NULL,
                lookback_period INTEGER DEFAULT 90,
                correlation_data TEXT,
                max_correlation DECIMAL(6, 4),
                min_correlation DECIMAL(6, 4),
                avg_correlation DECIMAL(6, 4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 16. 归因分析结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attribution_analysis (
                analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                analysis_period TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_return DECIMAL(8, 4),
                benchmark_return DECIMAL(8, 4),
                excess_return DECIMAL(8, 4),
                portfolio_beta DECIMAL(6, 4),
                beta_contribution DECIMAL(8, 4),
                total_alpha DECIMAL(8, 4),
                selection_alpha DECIMAL(8, 4),
                timing_alpha DECIMAL(8, 4),
                strategy_alpha DECIMAL(8, 4),
                allocation_alpha DECIMAL(8, 4),
                detailed_breakdown TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions(stock_symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_symbol ON options_trades(stock_symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_status ON options_trades(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_options_expiration ON options_trades(expiration_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_flows_date ON cash_flows(flow_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_flows_account ON cash_flows(account_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_flows_type ON cash_flows(flow_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dividends_symbol ON dividends(stock_symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dividends_date ON dividends(ex_dividend_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON price_alerts(stock_symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON price_alerts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal_symbol ON trading_journal(stock_symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal_date ON trading_journal(trade_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summaries_type ON summaries(summary_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summaries_subject ON summaries(subject)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON stock_price_history(stock_symbol, price_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_benchmark_symbol_date ON benchmark_prices(benchmark_symbol, price_date)')

        # 插入默认账户数据
        cursor.execute('SELECT COUNT(*) FROM accounts')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO accounts (account_name, total_capital, cash_reserve, conditional_reserve, target_position_min, target_position_max)
                VALUES
                    ('长期账户', 150000, 50000, 40000, 40, 50),
                    ('波段账户', 50000, 20000, 15000, 30, 40)
            ''')

        conn.commit()
        conn.close()

    # ==================== 交易记录 CRUD ====================

    def add_transaction(self, date, account, symbol, trans_type, price, shares, commission=0, notes=None):
        """添加交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO transactions (transaction_date, account_name, stock_symbol, transaction_type, price, shares, commission, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (date, account, symbol.upper(), trans_type, price, shares, commission, notes))

        trans_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return trans_id

    def get_transactions(self, account=None, symbol=None, start_date=None, end_date=None):
        """获取交易记录"""
        conn = self.get_connection()

        query = 'SELECT * FROM transactions WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)
        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol.upper())
        if start_date:
            query += ' AND transaction_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND transaction_date <= ?'
            params.append(end_date)

        query += ' ORDER BY transaction_date DESC, transaction_id DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def update_transaction(self, transaction_id, date=None, account=None, symbol=None,
                          trans_type=None, price=None, shares=None, commission=None, notes=None):
        """更新交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if date is not None:
            updates.append('transaction_date = ?')
            params.append(date)
        if account is not None:
            updates.append('account_name = ?')
            params.append(account)
        if symbol is not None:
            updates.append('stock_symbol = ?')
            params.append(symbol.upper())
        if trans_type is not None:
            updates.append('transaction_type = ?')
            params.append(trans_type)
        if price is not None:
            updates.append('price = ?')
            params.append(price)
        if shares is not None:
            updates.append('shares = ?')
            params.append(shares)
        if commission is not None:
            updates.append('commission = ?')
            params.append(commission)
        if notes is not None:
            updates.append('notes = ?')
            params.append(notes)

        if updates:
            query = f'UPDATE transactions SET {", ".join(updates)} WHERE transaction_id = ?'
            params.append(transaction_id)
            cursor.execute(query, params)

        conn.commit()
        conn.close()

    def delete_transaction(self, transaction_id):
        """删除交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM transactions WHERE transaction_id = ?', (transaction_id,))

        conn.commit()
        conn.close()

    # ==================== 期权交易 CRUD ====================

    def add_option_trade(self, account, symbol, option_type, strike_price, expiration_date,
                        premium_per_share, contracts, open_date, delta=None, gamma=None,
                        theta=None, vega=None, implied_volatility=None, iv_percentile=None,
                        opening_fee=0, notes=None):
        """添加期权交易"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO options_trades (account_name, stock_symbol, option_type, strike_price,
                expiration_date, premium_per_share, contracts, open_date, delta, gamma, theta,
                vega, implied_volatility, iv_percentile, opening_fee, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account, symbol.upper(), option_type, strike_price, expiration_date,
              premium_per_share, contracts, open_date, delta, gamma, theta, vega,
              implied_volatility, iv_percentile, opening_fee, notes))

        option_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return option_id

    def get_options_trades(self, account=None, symbol=None, status=None):
        """获取期权交易记录"""
        conn = self.get_connection()

        query = 'SELECT * FROM options_trades WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)
        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol.upper())
        if status:
            query += ' AND status = ?'
            params.append(status)

        query += ' ORDER BY open_date DESC, option_id DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def update_option_close(self, option_id, close_date, close_price_per_share, closing_fee=0, status='已平仓'):
        """更新期权平仓"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE options_trades
            SET close_date = ?, close_price_per_share = ?, closing_fee = ?, status = ?
            WHERE option_id = ?
        ''', (close_date, close_price_per_share, closing_fee, status, option_id))

        conn.commit()
        conn.close()

    def update_option_trade(self, option_id, account=None, symbol=None, option_type=None,
                           strike_price=None, expiration_date=None, premium_per_share=None,
                           contracts=None, open_date=None, delta=None, gamma=None, theta=None,
                           vega=None, implied_volatility=None, iv_percentile=None,
                           opening_fee=None, notes=None):
        """更新期权交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if account is not None:
            updates.append('account_name = ?')
            params.append(account)
        if symbol is not None:
            updates.append('stock_symbol = ?')
            params.append(symbol.upper())
        if option_type is not None:
            updates.append('option_type = ?')
            params.append(option_type)
        if strike_price is not None:
            updates.append('strike_price = ?')
            params.append(strike_price)
        if expiration_date is not None:
            updates.append('expiration_date = ?')
            params.append(expiration_date)
        if premium_per_share is not None:
            updates.append('premium_per_share = ?')
            params.append(premium_per_share)
        if contracts is not None:
            updates.append('contracts = ?')
            params.append(contracts)
        if open_date is not None:
            updates.append('open_date = ?')
            params.append(open_date)
        if delta is not None:
            updates.append('delta = ?')
            params.append(delta)
        if gamma is not None:
            updates.append('gamma = ?')
            params.append(gamma)
        if theta is not None:
            updates.append('theta = ?')
            params.append(theta)
        if vega is not None:
            updates.append('vega = ?')
            params.append(vega)
        if implied_volatility is not None:
            updates.append('implied_volatility = ?')
            params.append(implied_volatility)
        if iv_percentile is not None:
            updates.append('iv_percentile = ?')
            params.append(iv_percentile)
        if opening_fee is not None:
            updates.append('opening_fee = ?')
            params.append(opening_fee)
        if notes is not None:
            updates.append('notes = ?')
            params.append(notes)

        if updates:
            query = f'UPDATE options_trades SET {", ".join(updates)} WHERE option_id = ?'
            params.append(option_id)
            cursor.execute(query, params)

        conn.commit()
        conn.close()

    def delete_option_trade(self, option_id):
        """删除期权交易记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM options_trades WHERE option_id = ?', (option_id,))

        conn.commit()
        conn.close()

    # ==================== 账户 CRUD ====================

    def get_accounts(self):
        """获取所有账户"""
        conn = self.get_connection()
        df = pd.read_sql_query('SELECT * FROM accounts', conn)
        conn.close()
        return df

    def update_account(self, account_name, total_capital=None, cash_reserve=None,
                      conditional_reserve=None, target_min=None, target_max=None):
        """更新账户配置"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if total_capital is not None:
            updates.append('total_capital = ?')
            params.append(total_capital)
        if cash_reserve is not None:
            updates.append('cash_reserve = ?')
            params.append(cash_reserve)
        if conditional_reserve is not None:
            updates.append('conditional_reserve = ?')
            params.append(conditional_reserve)
        if target_min is not None:
            updates.append('target_position_min = ?')
            params.append(target_min)
        if target_max is not None:
            updates.append('target_position_max = ?')
            params.append(target_max)

        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            query = f'UPDATE accounts SET {", ".join(updates)} WHERE account_name = ?'
            params.append(account_name)
            cursor.execute(query, params)

        conn.commit()
        conn.close()

    # ==================== 分红 CRUD ====================

    def add_dividend(self, symbol, account, ex_date, dividend_per_share, shares_held,
                    payment_date=None, dividend_type='普通', reinvested=False,
                    tax_withheld=0, notes=None):
        """添加分红记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        total_dividend = dividend_per_share * shares_held

        cursor.execute('''
            INSERT INTO dividends (stock_symbol, account_name, ex_dividend_date, payment_date,
                dividend_per_share, shares_held, total_dividend, dividend_type, reinvested,
                tax_withheld, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol.upper(), account, ex_date, payment_date, dividend_per_share, shares_held,
              total_dividend, dividend_type, reinvested, tax_withheld, notes))

        dividend_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return dividend_id

    def get_dividends(self, account=None, symbol=None, start_date=None, end_date=None):
        """获取分红记录"""
        conn = self.get_connection()

        query = 'SELECT * FROM dividends WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)
        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol.upper())
        if start_date:
            query += ' AND ex_dividend_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND ex_dividend_date <= ?'
            params.append(end_date)

        query += ' ORDER BY ex_dividend_date DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    # ==================== 现金流 CRUD ====================

    def add_cash_flow(self, flow_date, account, flow_type, amount, stock_symbol=None,
                     related_transaction_id=None, related_option_id=None,
                     is_realized=True, description=None, notes=None, auto_generated=False):
        """添加现金流记录"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO cash_flows (flow_date, account_name, flow_type, amount, stock_symbol,
                related_transaction_id, related_option_id, is_realized, description, notes, auto_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (flow_date, account, flow_type, amount, stock_symbol, related_transaction_id,
              related_option_id, is_realized, description, notes, auto_generated))

        flow_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return flow_id

    def get_cash_flows(self, account=None, flow_type=None, start_date=None, end_date=None):
        """获取现金流记录"""
        conn = self.get_connection()

        query = 'SELECT * FROM cash_flows WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)
        if flow_type:
            query += ' AND flow_type = ?'
            params.append(flow_type)
        if start_date:
            query += ' AND flow_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND flow_date <= ?'
            params.append(end_date)

        query += ' ORDER BY flow_date DESC, flow_id DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    # ==================== 价格预警 CRUD ====================

    def add_price_alert(self, symbol, alert_type, target_price, current_price=None,
                       notification_method='邮件', email_address=None, planned_action=None,
                       planned_shares=None, planned_notes=None):
        """添加价格预警"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO price_alerts (stock_symbol, alert_type, target_price, current_price,
                notification_method, email_address, planned_action, planned_shares, planned_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol.upper(), alert_type, target_price, current_price, notification_method,
              email_address, planned_action, planned_shares, planned_notes))

        alert_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return alert_id

    def get_price_alerts(self, symbol=None, status=None):
        """获取价格预警"""
        conn = self.get_connection()

        query = 'SELECT * FROM price_alerts WHERE 1=1'
        params = []

        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol.upper())
        if status:
            query += ' AND status = ?'
            params.append(status)

        query += ' ORDER BY created_at DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def update_alert_triggered(self, alert_id, triggered_price):
        """更新预警已触发"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE price_alerts
            SET status = '已触发', triggered_at = CURRENT_TIMESTAMP, triggered_price = ?
            WHERE alert_id = ?
        ''', (triggered_price, alert_id))

        conn.commit()
        conn.close()

    def delete_price_alert(self, alert_id):
        """删除价格预警"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM price_alerts WHERE alert_id = ?', (alert_id,))

        conn.commit()
        conn.close()

    # ==================== 交易日志 CRUD ====================

    def add_journal_entry(self, data):
        """添加交易日志"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO trading_journal (transaction_id, option_id, stock_symbol, trade_type,
                trade_date, account_name, reason, target_price, expected_holding_period,
                expected_return, stop_loss, stop_profit, max_acceptable_loss, main_risks,
                market_condition, vix_level, confidence_level, emotional_state, decision_quality, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('transaction_id'), data.get('option_id'), data.get('stock_symbol'),
            data.get('trade_type'), data.get('trade_date'), data.get('account_name'),
            data.get('reason'), data.get('target_price'), data.get('expected_holding_period'),
            data.get('expected_return'), data.get('stop_loss'), data.get('stop_profit'),
            data.get('max_acceptable_loss'), data.get('main_risks'), data.get('market_condition'),
            data.get('vix_level'), data.get('confidence_level'), data.get('emotional_state'),
            data.get('decision_quality'), data.get('tags')
        ))

        journal_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return journal_id

    def get_journal_entries(self, account=None, symbol=None, start_date=None, end_date=None):
        """获取交易日志"""
        conn = self.get_connection()

        query = 'SELECT * FROM trading_journal WHERE 1=1'
        params = []

        if account:
            query += ' AND account_name = ?'
            params.append(account)
        if symbol:
            query += ' AND stock_symbol = ?'
            params.append(symbol.upper())
        if start_date:
            query += ' AND trade_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND trade_date <= ?'
            params.append(end_date)

        query += ' ORDER BY trade_date DESC, journal_id DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def update_journal_review(self, journal_id, met_expectation, deviation_reason=None,
                             lessons_learned=None, improvements=None):
        """更新日志复盘"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE trading_journal
            SET met_expectation = ?, deviation_reason = ?, lessons_learned = ?,
                improvements = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE journal_id = ?
        ''', (met_expectation, deviation_reason, lessons_learned, improvements, journal_id))

        conn.commit()
        conn.close()

    # ==================== 总结 CRUD ====================

    def add_summary(self, summary_type, subject, period_start=None, period_end=None,
                   auto_generated_data=None):
        """添加总结"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO summaries (summary_type, subject, period_start, period_end, auto_generated_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (summary_type, subject, period_start, period_end, auto_generated_data))

        summary_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return summary_id

    def get_summaries(self, summary_type=None, subject=None, status=None):
        """获取总结"""
        conn = self.get_connection()

        query = 'SELECT * FROM summaries WHERE 1=1'
        params = []

        if summary_type:
            query += ' AND summary_type = ?'
            params.append(summary_type)
        if subject:
            query += ' AND subject = ?'
            params.append(subject)
        if status:
            query += ' AND completion_status = ?'
            params.append(status)

        query += ' ORDER BY created_at DESC'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    def update_summary(self, summary_id, what_worked=None, what_failed=None,
                      market_observations=None, future_plans=None, lessons_learned=None,
                      methodology_updates=None, status=None):
        """更新总结"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if what_worked is not None:
            updates.append('what_worked = ?')
            params.append(what_worked)
        if what_failed is not None:
            updates.append('what_failed = ?')
            params.append(what_failed)
        if market_observations is not None:
            updates.append('market_observations = ?')
            params.append(market_observations)
        if future_plans is not None:
            updates.append('future_plans = ?')
            params.append(future_plans)
        if lessons_learned is not None:
            updates.append('lessons_learned = ?')
            params.append(lessons_learned)
        if methodology_updates is not None:
            updates.append('methodology_updates = ?')
            params.append(methodology_updates)
        if status is not None:
            updates.append('completion_status = ?')
            params.append(status)
            if status == '已完成':
                updates.append('completed_at = CURRENT_TIMESTAMP')

        if updates:
            query = f'UPDATE summaries SET {", ".join(updates)} WHERE summary_id = ?'
            params.append(summary_id)
            cursor.execute(query, params)

        conn.commit()
        conn.close()

    # ==================== 股价历史 CRUD ====================

    def add_price_history(self, symbol, price_date, close_price, daily_return=None, volume=None):
        """添加股价历史"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO stock_price_history (stock_symbol, price_date, close_price, daily_return, volume)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol.upper(), price_date, close_price, daily_return, volume))

        conn.commit()
        conn.close()

    def get_price_history(self, symbol, start_date=None, end_date=None):
        """获取股价历史"""
        conn = self.get_connection()

        query = 'SELECT * FROM stock_price_history WHERE stock_symbol = ?'
        params = [symbol.upper()]

        if start_date:
            query += ' AND price_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND price_date <= ?'
            params.append(end_date)

        query += ' ORDER BY price_date'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    # ==================== 仓位目标 CRUD ====================

    def set_position_target(self, symbol, account, target_type, target_percentage=None,
                           target_amount=None, target_shares=None, max_percentage=None,
                           max_amount=None, max_shares=None, priority=5,
                           rebalance_threshold=10, notes=None):
        """设置仓位目标"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO position_targets (stock_symbol, account_name, target_type,
                target_percentage, target_amount, target_shares, max_percentage, max_amount,
                max_shares, priority, rebalance_threshold, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (symbol.upper(), account, target_type, target_percentage, target_amount,
              target_shares, max_percentage, max_amount, max_shares, priority,
              rebalance_threshold, notes))

        conn.commit()
        conn.close()

    def get_position_targets(self, account=None, is_active=True):
        """获取仓位目标"""
        conn = self.get_connection()

        query = 'SELECT * FROM position_targets WHERE is_active = ?'
        params = [is_active]

        if account:
            query += ' AND account_name = ?'
            params.append(account)

        query += ' ORDER BY priority, stock_symbol'

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    # ==================== 期权策略规则 CRUD ====================

    def add_strategy_rule(self, rule_name, option_type, description=None, min_delta=None,
                         max_delta=None, min_theta=None, max_theta=None, min_vega=None,
                         max_vega=None, min_iv_percentile=None, max_iv_percentile=None,
                         min_annualized_return=None, min_dte=None, max_dte=None,
                         recommendation_score=None, recommendation_text=None):
        """添加策略规则"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO option_strategy_rules (rule_name, option_type, description, min_delta,
                max_delta, min_theta, max_theta, min_vega, max_vega, min_iv_percentile,
                max_iv_percentile, min_annualized_return, min_dte, max_dte,
                recommendation_score, recommendation_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (rule_name, option_type, description, min_delta, max_delta, min_theta,
              max_theta, min_vega, max_vega, min_iv_percentile, max_iv_percentile,
              min_annualized_return, min_dte, max_dte, recommendation_score, recommendation_text))

        rule_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return rule_id

    def get_strategy_rules(self, option_type=None, is_active=True):
        """获取策略规则"""
        conn = self.get_connection()

        query = 'SELECT * FROM option_strategy_rules WHERE is_active = ?'
        params = [is_active]

        if option_type:
            query += ' AND option_type = ?'
            params.append(option_type)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()

        return df

    # ==================== 期权评估记录 CRUD ====================

    def save_option_evaluation(self, data):
        """保存期权评估"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO option_evaluations (stock_symbol, option_type, strike_price,
                expiration_date, current_stock_price, option_premium, delta, gamma, theta,
                vega, implied_volatility, iv_percentile, days_to_expiration, annualized_return,
                breakeven_price, matched_rules, recommendation_score, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('stock_symbol'), data.get('option_type'), data.get('strike_price'),
            data.get('expiration_date'), data.get('current_stock_price'), data.get('option_premium'),
            data.get('delta'), data.get('gamma'), data.get('theta'), data.get('vega'),
            data.get('implied_volatility'), data.get('iv_percentile'), data.get('days_to_expiration'),
            data.get('annualized_return'), data.get('breakeven_price'), data.get('matched_rules'),
            data.get('recommendation_score'), data.get('recommendation')
        ))

        eval_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return eval_id

    # ==================== 备份 ====================

    def backup_database(self, backup_dir=None):
        """备份数据库"""
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'portfolio_backup_{timestamp}.db')

        shutil.copy2(self.db_path, backup_path)

        return backup_path

    def restore_database(self, backup_path):
        """恢复数据库"""
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, self.db_path)
            return True
        return False

    def get_backups(self, backup_dir=None):
        """获取备份文件列表"""
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')

        if not os.path.exists(backup_dir):
            return []

        backups = []
        for f in os.listdir(backup_dir):
            if f.endswith('.db'):
                path = os.path.join(backup_dir, f)
                backups.append({
                    'filename': f,
                    'path': path,
                    'size': os.path.getsize(path),
                    'modified': datetime.fromtimestamp(os.path.getmtime(path))
                })

        return sorted(backups, key=lambda x: x['modified'], reverse=True)
