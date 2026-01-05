"""
提醒督促系统
"""

from datetime import datetime, timedelta
import threading
import time


class ReminderSystem:
    """提醒管理器"""

    REMINDER_TYPES = {
        'weekly_review': {
            'trigger': 'every Sunday 20:00',
            'description': '周度复盘提醒'
        },
        'monthly_summary': {
            'trigger': 'last day of month',
            'description': '月度总结提醒'
        },
        'journal_reminder': {
            'trigger': '24 hours after trade',
            'description': '交易日志提醒'
        },
        'option_expiry': {
            'trigger': '3 days before expiration',
            'description': '期权到期提醒'
        }
    }

    def __init__(self, db, journal=None, summary_gen=None):
        """初始化提醒系统"""
        self.db = db
        self.journal = journal
        self.summary_gen = summary_gen
        self.running = False
        self.reminder_thread = None

    def check_weekly_review(self):
        """
        检查周度复盘

        每周日检查是否有未复盘交易
        """
        today = datetime.now().date()

        # 检查是否是周日
        if today.weekday() != 6:  # 0=Monday, 6=Sunday
            return None

        # 计算本周范围
        week_start = today - timedelta(days=6)

        # 检查本周交易
        transactions = self.db.get_transactions(
            start_date=week_start,
            end_date=today
        )

        if transactions.empty:
            return None

        # 检查是否有未复盘的日志
        if self.journal:
            unreviewed = self.journal.get_unreviewed_entries()
            this_week_unreviewed = unreviewed[
                unreviewed['trade_date'].apply(
                    lambda x: datetime.strptime(str(x)[:10], '%Y-%m-%d').date() >= week_start
                )
            ] if not unreviewed.empty else pd.DataFrame()

            if not this_week_unreviewed.empty:
                return {
                    'type': 'weekly_review',
                    'message': f'本周有 {len(this_week_unreviewed)} 笔交易未复盘',
                    'details': this_week_unreviewed.to_dict('records')
                }

        return None

    def check_monthly_summary(self):
        """
        检查月度总结

        每月末检查是否有未完成的总结
        """
        today = datetime.now().date()

        # 检查是否是月末（简化：检查明天是否是下个月）
        tomorrow = today + timedelta(days=1)
        if today.month == tomorrow.month:
            return None

        # 检查本月是否有已完成的总结
        month_str = today.strftime('%Y年%m月')

        if self.summary_gen:
            summaries = self.db.get_summaries(
                summary_type='账户',
                status='已完成'
            )

            # 检查是否有本月的总结
            has_monthly_summary = False
            if not summaries.empty:
                for _, s in summaries.iterrows():
                    if month_str in (s.get('subject', '') or ''):
                        has_monthly_summary = True
                        break

            if not has_monthly_summary:
                return {
                    'type': 'monthly_summary',
                    'message': f'{month_str}的月度总结尚未完成',
                    'action': '请完成本月的账户总结'
                }

        return None

    def check_journal_completion(self, hours=24):
        """
        检查日志完成度

        交易后N小时未写日志则提醒
        """
        if not self.journal:
            return None

        missing = self.journal.get_trades_without_journal(days=3)

        if missing.empty:
            return None

        # 检查是否超过指定小时数
        now = datetime.now()
        alerts = []

        for _, trade in missing.iterrows():
            trade_time = datetime.strptime(str(trade['transaction_date'])[:10], '%Y-%m-%d')
            hours_since = (now - trade_time).total_seconds() / 3600

            if hours_since > hours:
                alerts.append({
                    'symbol': trade['stock_symbol'],
                    'type': trade['transaction_type'],
                    'date': trade['transaction_date'],
                    'hours_since': int(hours_since)
                })

        if alerts:
            return {
                'type': 'journal_reminder',
                'message': f'{len(alerts)} 笔交易尚未填写日志',
                'details': alerts
            }

        return None

    def check_option_expiry(self, days_before=3):
        """
        检查期权到期

        到期前N天提醒
        """
        options = self.db.get_options_trades(status='持仓中')

        if options.empty:
            return None

        today = datetime.now().date()
        expiring_soon = []

        for _, opt in options.iterrows():
            exp_date = datetime.strptime(str(opt['expiration_date'])[:10], '%Y-%m-%d').date()
            days_to_expiry = (exp_date - today).days

            if 0 <= days_to_expiry <= days_before:
                expiring_soon.append({
                    'symbol': opt['stock_symbol'],
                    'option_type': opt['option_type'],
                    'strike_price': opt['strike_price'],
                    'expiration_date': str(exp_date),
                    'days_to_expiry': days_to_expiry,
                    'contracts': opt['contracts']
                })

        if expiring_soon:
            return {
                'type': 'option_expiry',
                'message': f'{len(expiring_soon)} 个期权即将到期',
                'details': expiring_soon
            }

        return None

    def check_milestone_achievements(self):
        """
        里程碑检查

        - 第100笔交易
        - 账户盈利突破10%
        - 连续7天写日志
        """
        milestones = []

        # 检查交易数量里程碑
        transactions = self.db.get_transactions()
        trade_count = len(transactions)

        milestone_numbers = [10, 50, 100, 200, 500, 1000]
        for milestone in milestone_numbers:
            if trade_count >= milestone and trade_count < milestone + 5:
                milestones.append({
                    'type': 'trade_count',
                    'message': f'恭喜完成第 {milestone} 笔交易！'
                })

        # 检查日志连续天数
        if self.journal:
            journals = self.journal.get_journal_entries()
            if not journals.empty:
                journals['trade_date'] = pd.to_datetime(journals['trade_date'])
                dates = journals['trade_date'].dt.date.unique()
                dates = sorted(dates, reverse=True)

                consecutive = 1
                for i in range(1, len(dates)):
                    if (dates[i-1] - dates[i]).days == 1:
                        consecutive += 1
                    else:
                        break

                if consecutive >= 7:
                    milestones.append({
                        'type': 'journal_streak',
                        'message': f'已连续 {consecutive} 天记录交易日志！'
                    })

        return milestones if milestones else None

    def get_all_reminders(self):
        """获取所有待处理提醒"""
        reminders = []

        # 检查各类提醒
        weekly = self.check_weekly_review()
        if weekly:
            reminders.append(weekly)

        monthly = self.check_monthly_summary()
        if monthly:
            reminders.append(monthly)

        journal = self.check_journal_completion()
        if journal:
            reminders.append(journal)

        expiry = self.check_option_expiry()
        if expiry:
            reminders.append(expiry)

        milestones = self.check_milestone_achievements()
        if milestones:
            for m in milestones:
                reminders.append(m)

        return reminders

    def send_reminder(self, reminder_type, data, notification_method='console'):
        """
        发送提醒

        Args:
            reminder_type: 提醒类型
            data: 提醒数据
            notification_method: 通知方式（console/email/desktop）
        """
        if notification_method == 'console':
            print(f"\n=== 提醒: {self.REMINDER_TYPES.get(reminder_type, {}).get('description', reminder_type)} ===")
            print(data.get('message', ''))
            if data.get('details'):
                print(f"详情: {data['details']}")
            print("=" * 50)

        # 可以扩展其他通知方式

    def start_background_check(self, interval=3600):
        """
        启动后台检查

        Args:
            interval: 检查间隔（秒），默认1小时
        """
        if self.running:
            print("提醒系统已在运行")
            return

        self.running = True

        def check_loop():
            while self.running:
                try:
                    reminders = self.get_all_reminders()
                    for reminder in reminders:
                        self.send_reminder(reminder.get('type', 'general'), reminder)

                except Exception as e:
                    print(f"提醒检查错误: {e}")

                time.sleep(interval)

        self.reminder_thread = threading.Thread(target=check_loop, daemon=True)
        self.reminder_thread.start()
        print(f"提醒系统已启动，检查间隔 {interval} 秒")

    def stop_background_check(self):
        """停止后台检查"""
        self.running = False
        if self.reminder_thread:
            self.reminder_thread = None
        print("提醒系统已停止")


# 需要导入pandas用于日期处理
import pandas as pd
