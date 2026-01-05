"""
价格预警和自动监控系统
"""

import threading
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os

# 导入配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NOTIFICATION_CONFIG, EMAIL_CONFIG


class PriceAlertSystem:
    """预警系统"""

    def __init__(self, db, email_config=None):
        """初始化预警系统"""
        self.db = db
        self.email_config = email_config
        self.monitoring = False
        self.monitor_thread = None
        self.current_interval = 60  # 当前检查间隔（秒）

    def add_alert(self, alert_data):
        """
        添加价格预警

        Args:
            alert_data: dict
                - stock_symbol: 股票代码
                - alert_type: 预警类型（高于/低于/穿越）
                - target_price: 目标价格
                - current_price: 当前价格（可选）
                - notification_method: 通知方式（邮件/桌面）
                - email_address: 邮箱地址
                - planned_action: 预设操作（买入/卖出）
                - planned_shares: 预设股数
                - planned_notes: 操作备注
        """
        # 使用默认通知方式（桌面通知）
        notification_method = alert_data.get('notification_method', NOTIFICATION_CONFIG['default_method'])

        # 使用默认接收邮箱（如果未指定且通知方式为邮件）
        email_address = alert_data.get('email_address')
        if not email_address and notification_method == '邮件':
            email_address = EMAIL_CONFIG.get('default_recipient', '')

        return self.db.add_price_alert(
            symbol=alert_data['stock_symbol'],
            alert_type=alert_data['alert_type'],
            target_price=alert_data['target_price'],
            current_price=alert_data.get('current_price'),
            notification_method=notification_method,
            email_address=email_address,
            planned_action=alert_data.get('planned_action'),
            planned_shares=alert_data.get('planned_shares'),
            planned_notes=alert_data.get('planned_notes')
        )

    def check_alerts(self, current_prices):
        """
        检查所有预警

        Args:
            current_prices: dict {symbol: price}

        Returns:
            list: 触发的预警列表
        """
        alerts = self.db.get_price_alerts(status='激活')
        triggered = []

        if alerts.empty:
            return triggered

        for _, alert in alerts.iterrows():
            symbol = alert['stock_symbol']

            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            target_price = alert['target_price']
            alert_type = alert['alert_type']

            is_triggered = False

            if alert_type == '高于' and current_price >= target_price:
                is_triggered = True
            elif alert_type == '低于' and current_price <= target_price:
                is_triggered = True
            elif alert_type == '穿越':
                # 穿越预警：价格接近目标价的0.2%范围内
                if abs(current_price - target_price) / target_price < 0.002:
                    is_triggered = True

            if is_triggered:
                # 更新预警状态
                self.db.update_alert_triggered(alert['alert_id'], current_price)

                # 发送通知
                self.send_notification(dict(alert), current_price)

                triggered.append({
                    'alert_id': alert['alert_id'],
                    'symbol': symbol,
                    'alert_type': alert_type,
                    'target_price': target_price,
                    'current_price': current_price,
                    'planned_action': alert['planned_action'],
                    'planned_shares': alert['planned_shares']
                })

        return triggered

    def send_notification(self, alert, current_price):
        """发送通知"""
        notification_method = alert.get('notification_method', '邮件')

        if notification_method == '邮件':
            self._send_email_notification(alert, current_price)
        elif notification_method == '桌面':
            self._send_desktop_notification(alert, current_price)

    def _send_email_notification(self, alert, current_price):
        """发送邮件通知"""
        if not self.email_config or not alert.get('email_address'):
            print(f"预警触发: {alert['stock_symbol']} {alert['alert_type']} ${alert['target_price']}")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = alert['email_address']
            msg['Subject'] = f"价格预警: {alert['stock_symbol']} 已触发"

            body = f"""
            股票代码: {alert['stock_symbol']}
            预警类型: {alert['alert_type']} ${alert['target_price']}
            当前价格: ${current_price}
            触发时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            预设操作: {alert.get('planned_action', '无')}
            预设股数: {alert.get('planned_shares', '无')}
            备注: {alert.get('planned_notes', '无')}
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            server.send_message(msg)
            server.quit()

            print(f"邮件通知已发送: {alert['stock_symbol']}")

        except Exception as e:
            print(f"发送邮件失败: {e}")

    def _send_desktop_notification(self, alert, current_price):
        """发送桌面通知"""
        # 使用系统通知（跨平台支持有限）
        try:
            import platform
            system = platform.system()

            title = f"价格预警: {alert['stock_symbol']}"
            message = f"{alert['alert_type']} ${alert['target_price']}, 当前 ${current_price}"

            if system == 'Darwin':  # macOS
                import subprocess
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{message}" with title "{title}"'
                ])
            elif system == 'Windows':
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            elif system == 'Linux':
                import subprocess
                subprocess.run(['notify-send', title, message])

        except Exception as e:
            print(f"桌面通知失败: {e}")
            print(f"预警: {alert['stock_symbol']} {alert['alert_type']} ${alert['target_price']}, 当前 ${current_price}")

    def start_monitoring(self, price_fetcher, interval=60):
        """
        启动后台监控

        Args:
            price_fetcher: 获取价格的函数，返回 {symbol: price}
            interval: 检查间隔（秒），如果启用动态间隔则此参数会被覆盖
        """
        if self.monitoring:
            print("监控已在运行")
            return

        self.monitoring = True
        self.current_interval = interval  # 保存当前间隔

        def monitor_loop():
            while self.monitoring:
                try:
                    # 获取所有需要监控的股票（包括预警和持仓）
                    alert_symbols = set()
                    alerts = self.db.get_price_alerts(status='激活')
                    if not alerts.empty:
                        alert_symbols = set(alerts['stock_symbol'].unique().tolist())

                    # 获取所有持仓股票
                    holding_symbols = set()
                    try:
                        conn = self.db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT DISTINCT stock_symbol
                            FROM transactions
                            GROUP BY stock_symbol
                            HAVING SUM(CASE WHEN transaction_type='买入' THEN shares
                                           WHEN transaction_type='卖出' THEN -shares
                                           ELSE 0 END) > 0
                        ''')
                        holding_symbols = set(row[0] for row in cursor.fetchall())
                        conn.close()
                    except Exception:
                        pass

                    # 合并预警和持仓股票
                    all_symbols = list(alert_symbols | holding_symbols)
                    stock_count = len(all_symbols)

                    if stock_count > 0:
                        # 动态计算间隔
                        from config import calculate_dynamic_interval, ALERT_MONITORING_CONFIG
                        if ALERT_MONITORING_CONFIG['enable_dynamic_interval']:
                            self.current_interval = calculate_dynamic_interval(stock_count)

                        # 获取所有股票的价格（同时更新缓存）
                        prices = price_fetcher(all_symbols)

                        # 只检查有预警的股票
                        if prices and alert_symbols:
                            triggered = self.check_alerts(prices)
                            if triggered:
                                print(f"触发了 {len(triggered)} 个预警")

                except Exception as e:
                    print(f"监控错误: {e}")

                time.sleep(self.current_interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

        # 打印启动信息
        from config import ALERT_MONITORING_CONFIG
        if ALERT_MONITORING_CONFIG['enable_dynamic_interval']:
            print(f"价格监控已启动（动态间隔模式）")
        else:
            print(f"价格监控已启动，间隔 {interval} 秒")

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread = None
        print("价格监控已停止")

    def get_active_alerts(self):
        """获取激活的预警"""
        return self.db.get_price_alerts(status='激活')

    def get_triggered_alerts(self):
        """获取已触发的预警"""
        return self.db.get_price_alerts(status='已触发')

    def delete_alert(self, alert_id):
        """删除预警"""
        self.db.delete_price_alert(alert_id)

    def reactivate_alert(self, alert_id):
        """重新激活预警"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE price_alerts
            SET status = '激活', triggered_at = NULL, triggered_price = NULL
            WHERE alert_id = ?
        ''', (alert_id,))

        conn.commit()
        conn.close()

    def update_alert(self, alert_id, alert_data):
        """
        更新预警

        Args:
            alert_id: 预警ID
            alert_data: dict 包含要更新的字段
                - alert_type: 预警类型（可选）
                - target_price: 目标价格（可选）
                - notification_method: 通知方式（可选）
                - email_address: 邮箱地址（可选）
                - planned_action: 预设操作（可选）
                - planned_shares: 预设股数（可选）
                - planned_notes: 操作备注（可选）
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # 构建更新语句
        update_fields = []
        values = []

        if 'alert_type' in alert_data:
            update_fields.append('alert_type = ?')
            values.append(alert_data['alert_type'])

        if 'target_price' in alert_data:
            update_fields.append('target_price = ?')
            values.append(alert_data['target_price'])

        if 'notification_method' in alert_data:
            update_fields.append('notification_method = ?')
            values.append(alert_data['notification_method'])

        if 'email_address' in alert_data:
            update_fields.append('email_address = ?')
            values.append(alert_data['email_address'])

        if 'planned_action' in alert_data:
            update_fields.append('planned_action = ?')
            values.append(alert_data['planned_action'])

        if 'planned_shares' in alert_data:
            update_fields.append('planned_shares = ?')
            values.append(alert_data['planned_shares'])

        if 'planned_notes' in alert_data:
            update_fields.append('planned_notes = ?')
            values.append(alert_data['planned_notes'])

        if update_fields:
            values.append(alert_id)
            sql = f'''
                UPDATE price_alerts
                SET {', '.join(update_fields)}
                WHERE alert_id = ?
            '''
            cursor.execute(sql, values)
            conn.commit()

        conn.close()

    def get_alerts_by_symbol(self, symbol):
        """获取指定股票的预警"""
        return self.db.get_price_alerts(symbol=symbol)

    def get_alert_summary(self):
        """获取预警汇总"""
        active = self.db.get_price_alerts(status='激活')
        triggered = self.db.get_price_alerts(status='已触发')

        return {
            'active_count': len(active),
            'triggered_count': len(triggered),
            'active_symbols': active['stock_symbol'].unique().tolist() if not active.empty else [],
            'recent_triggered': triggered.head(5).to_dict('records') if not triggered.empty else []
        }

    def get_monitoring_info(self):
        """
        获取监控信息

        Returns:
            dict: 包含监控状态、间隔、股票数量等信息
        """
        # 获取预警股票
        active_alerts = self.db.get_price_alerts(status='激活')
        alert_stock_count = len(active_alerts['stock_symbol'].unique()) if not active_alerts.empty else 0

        # 获取持仓股票
        holding_stock_count = 0
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(DISTINCT stock_symbol)
                FROM transactions
                GROUP BY stock_symbol
                HAVING SUM(CASE WHEN transaction_type='买入' THEN shares
                               WHEN transaction_type='卖出' THEN -shares
                               ELSE 0 END) > 0
            ''')
            result = cursor.fetchall()
            holding_stock_count = len(result)
            conn.close()
        except Exception:
            pass

        # 计算总股票数（去重）
        alert_symbols = set(active_alerts['stock_symbol'].unique()) if not active_alerts.empty else set()
        holding_symbols = set()
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT stock_symbol
                FROM transactions
                GROUP BY stock_symbol
                HAVING SUM(CASE WHEN transaction_type='买入' THEN shares
                               WHEN transaction_type='卖出' THEN -shares
                               ELSE 0 END) > 0
            ''')
            holding_symbols = set(row[0] for row in cursor.fetchall())
            conn.close()
        except Exception:
            pass

        total_stock_count = len(alert_symbols | holding_symbols)

        from config import calculate_dynamic_interval, ALERT_MONITORING_CONFIG

        info = {
            'is_monitoring': self.monitoring,
            'alert_stock_count': alert_stock_count,
            'holding_stock_count': holding_stock_count,
            'total_stock_count': total_stock_count,
            'stock_count': total_stock_count,  # 向后兼容
            'current_interval': self.current_interval,
            'dynamic_mode': ALERT_MONITORING_CONFIG['enable_dynamic_interval'],
        }

        # 如果是动态模式，计算建议间隔
        if ALERT_MONITORING_CONFIG['enable_dynamic_interval'] and total_stock_count > 0:
            info['calculated_interval'] = calculate_dynamic_interval(total_stock_count)
            info['requests_per_hour'] = int(3600 / info['calculated_interval']) * total_stock_count if info['calculated_interval'] > 0 else 0
        else:
            info['calculated_interval'] = self.current_interval
            info['requests_per_hour'] = int(3600 / self.current_interval) * total_stock_count if self.current_interval > 0 and total_stock_count > 0 else 0

        return info
