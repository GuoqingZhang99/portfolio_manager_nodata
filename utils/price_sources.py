"""
多数据源价格获取模块
支持多个数据源获取股票价格
"""

import requests
import json
import time
import pandas as pd
import os
from datetime import datetime
import pytz


class PriceSourceManager:
    """价格数据源管理器"""

    def __init__(self, prices_file='data/manual_prices.json', timestamps_file='data/price_timestamps.json'):
        self.sources = {
            'yfinance': self._get_price_yfinance,
            'alphavantage': self._get_price_alphavantage,
            'alphavantage_intraday': self._get_price_alphavantage_intraday,
            'finnhub': self._get_price_finnhub,
            'manual': self._get_price_manual
        }
        self.prices_file = prices_file
        self.timestamps_file = timestamps_file
        self.manual_prices = self._load_manual_prices()  # 从文件加载手动输入的价格
        self.price_timestamps = self._load_timestamps()  # 加载价格更新时间戳

    def get_price(self, symbol, source='auto', api_key=None):
        """
        获取股票价格

        Args:
            symbol: 股票代码
            source: 数据源 ('auto', 'yfinance', 'alphavantage', 'finnhub', 'manual')
            api_key: API密钥（某些数据源需要）

        Returns:
            dict: {'success': bool, 'price': float, 'source': str, 'error': str}
        """
        if source == 'auto':
            # 优先使用手动价格
            manual_result = self._get_price_manual(symbol, api_key)
            if manual_result['success']:
                return manual_result

            # 自动尝试多个数据源
            for source_name in ['yfinance', 'alphavantage', 'finnhub']:
                try:
                    result = self.sources[source_name](symbol, api_key)
                    if result['success']:
                        return result
                except Exception as e:
                    continue
            return {'success': False, 'error': '所有数据源均失败', 'source': 'auto'}
        else:
            source_func = self.sources.get(source, self._get_price_yfinance)
            return source_func(symbol, api_key)

    def _get_price_yfinance(self, symbol, api_key=None):
        """使用 yfinance 获取价格"""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            # 使用类似用户例子的方式，获取最近5天数据（更稳定）
            data = ticker.history(period='5d')

            if data is None or data.empty:
                return {
                    'success': False,
                    'error': '无数据',
                    'source': 'yfinance'
                }

            # 获取最后一个有效的收盘价
            price = data['Close'].iloc[-1]
            if pd.isna(price):
                return {
                    'success': False,
                    'error': '价格为 NaN',
                    'source': 'yfinance'
                }

            return {
                'success': True,
                'price': round(float(price), 2),
                'source': 'yfinance'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source': 'yfinance'
            }

    def _get_price_alphavantage(self, symbol, api_key=None):
        """
        使用 Alpha Vantage API 获取价格（每日收盘价）

        免费 API Key: https://www.alphavantage.co/support/#api-key
        每分钟 5 次请求，每天 500 次
        """
        if not api_key:
            # 尝试从环境变量获取
            import os
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('ALPHAVANTAGE_API_KEY')

        if not api_key:
            return {
                'success': False,
                'error': '缺少 API Key',
                'source': 'alphavantage'
            }

        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'Global Quote' in data and '05. price' in data['Global Quote']:
                price = float(data['Global Quote']['05. price'])
                return {
                    'success': True,
                    'price': round(price, 2),
                    'source': 'alphavantage'
                }
            elif 'Note' in data:
                # API 限制
                return {
                    'success': False,
                    'error': 'API 速率限制',
                    'source': 'alphavantage'
                }
            else:
                return {
                    'success': False,
                    'error': f'无效响应: {data}',
                    'source': 'alphavantage'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source': 'alphavantage'
            }

    def _get_price_alphavantage_intraday(self, symbol, api_key=None):
        """
        使用 Alpha Vantage API 获取盘中实时价格

        使用 TIME_SERIES_INTRADAY 获取最新的分钟级数据
        """
        if not api_key:
            # 尝试从环境变量获取
            import os
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv('ALPHAVANTAGE_API_KEY')

        if not api_key:
            return {
                'success': False,
                'error': '缺少 API Key',
                'source': 'alphavantage_intraday'
            }

        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'interval': '1min',
                'apikey': api_key
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'Time Series (1min)' in data:
                time_series = data['Time Series (1min)']
                # 获取最新时间点的数据
                latest_time = list(time_series.keys())[0]
                latest_data = time_series[latest_time]
                price = float(latest_data['4. close'])
                return {
                    'success': True,
                    'price': round(price, 2),
                    'source': 'alphavantage_intraday'
                }
            elif 'Note' in data:
                return {
                    'success': False,
                    'error': 'API 速率限制',
                    'source': 'alphavantage_intraday'
                }
            else:
                return {
                    'success': False,
                    'error': f'无效响应: {data}',
                    'source': 'alphavantage_intraday'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source': 'alphavantage_intraday'
            }

    def _get_price_finnhub(self, symbol, api_key=None):
        """
        使用 Finnhub API 获取价格

        免费 API Key: https://finnhub.io/register
        每分钟 60 次请求
        """
        if not api_key:
            return None

        try:
            url = f"https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol,
                'token': api_key
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if 'c' in data and data['c']:
                price = float(data['c'])  # c = current price
                return round(price, 2)
        except Exception as e:
            print(f"Finnhub 获取失败: {e}")

        return None

    def _get_price_manual(self, symbol, api_key=None):
        """获取手动输入的价格"""
        return self.manual_prices.get(symbol)

    def _load_manual_prices(self):
        """从文件加载手动价格"""
        if os.path.exists(self.prices_file):
            try:
                with open(self.prices_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载手动价格失败: {e}")
                return {}
        return {}

    def _save_manual_prices(self):
        """保存手动价格到文件"""
        try:
            with open(self.prices_file, 'w', encoding='utf-8') as f:
                json.dump(self.manual_prices, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存手动价格失败: {e}")

    def _load_timestamps(self):
        """从文件加载价格更新时间戳"""
        if os.path.exists(self.timestamps_file):
            try:
                with open(self.timestamps_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载时间戳失败: {e}")
                return {}
        return {}

    def _save_timestamps(self):
        """保存价格更新时间戳到文件"""
        try:
            with open(self.timestamps_file, 'w', encoding='utf-8') as f:
                json.dump(self.price_timestamps, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存时间戳失败: {e}")

    def set_manual_price(self, symbol, price, update_timestamp=True):
        """设置手动价格"""
        self.manual_prices[symbol] = round(float(price), 2)
        self._save_manual_prices()  # 立即保存到文件

        if update_timestamp:
            self.update_timestamp(symbol)

    def get_manual_prices(self):
        """获取所有手动价格"""
        return self.manual_prices.copy()

    def clear_manual_prices(self):
        """清除所有手动价格"""
        self.manual_prices.clear()
        self._save_manual_prices()  # 保存更改

    def update_timestamp(self, symbol):
        """更新价格的时间戳"""
        now = datetime.now(pytz.UTC)
        self.price_timestamps[symbol] = now.isoformat()
        self._save_timestamps()

    def get_timestamp(self, symbol):
        """获取价格的更新时间"""
        timestamp_str = self.price_timestamps.get(symbol)
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str)
            except:
                return None
        return None

    def get_all_timestamps(self):
        """获取所有价格的更新时间"""
        return self.price_timestamps.copy()

    def get_last_update_time(self):
        """获取最后一次价格更新的时间（所有股票中最新的）"""
        if not self.price_timestamps:
            return None

        try:
            timestamps = [datetime.fromisoformat(ts) for ts in self.price_timestamps.values()]
            return max(timestamps)
        except:
            return None


def batch_get_prices_multi_source(symbols, source='auto', api_key=None):
    """
    批量获取股票价格（支持多数据源）

    Args:
        symbols: 股票代码列表
        source: 数据源
        api_key: API密钥

    Returns:
        dict: {symbol: price}
    """
    manager = PriceSourceManager()
    prices = {}

    print(f"📊 正在获取 {len(symbols)} 个股票的价格 (数据源: {source})...")

    for i, symbol in enumerate(symbols, 1):
        print(f"  [{i}/{len(symbols)}] 获取 {symbol}...", end=' ')
        price = manager.get_price(symbol, source, api_key)

        if price:
            prices[symbol] = price
            print(f"✓ ${price:.2f}")
        else:
            print(f"✗ 失败")

        # Alpha Vantage 免费版限制：每分钟5次
        if source == 'alphavantage' and i < len(symbols):
            time.sleep(12)  # 等待12秒，确保不超过限制

    if prices:
        print(f"✅ 成功获取 {len(prices)} 个价格")
    else:
        print(f"⚠️ 未能获取任何价格")

    return prices


# 全局价格管理器实例
_price_manager = PriceSourceManager()

def get_price_manager():
    """获取全局价格管理器"""
    return _price_manager
