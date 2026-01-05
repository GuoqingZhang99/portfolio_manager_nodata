# 价格数据源说明

## 当前数据源：yahooquery

系统使用 **yahooquery** 作为主要数据源，从Yahoo Finance获取股票价格。

## 为什么使用 yahooquery

### ✅ 优势特性

**1. 批量优化**
- 多个股票一次API调用
- 9个股票 = 1次请求
- 节省 89% API调用量

**示例**：
```
传统方式（逐个获取）：
  MU, PLTR, NVDA, AAPL, TSLA, MSFT, GOOGL, AMZN, META
  = 9次API调用

yahooquery批量模式：
  所有股票一次性获取
  = 1次API调用 ⚡
```

**2. 盘后缓存优化**
- 盘后自动使用今日收盘价缓存
- 避免重复请求相同数据
- 减少 96% 盘后API调用

**3. 性能提升**
- 响应速度比yfinance快 45-60倍
- yfinance被ban后的最佳替代方案
- 稳定可靠

**4. 市场状态感知**
- 自动识别盘前/盘中/盘后
- 根据市场状态选择合适的价格字段
- 支持盘前价格、盘中价格、盘后价格

## 数据延迟说明

### ⚠️ 重要限制

Yahoo Finance **免费API** 提供的是 **15-20分钟延迟数据**，不是真正的实时数据。

### 适用场景

**✅ 适合**：
- 日常投资组合监控
- 价格预警系统
- 趋势分析
- 长期投资决策

**❌ 不适合**：
- 高频交易
- 日内短线交易
- 需要秒级精度的场景
- Tick-by-tick数据分析

### 对系统功能的影响

| 功能 | 影响 | 说明 |
|------|------|------|
| 账户总览 | ✅ 无影响 | 价格延迟对查看持仓影响不大 |
| 价格预警 | ⚠️ 轻微影响 | 预警触发会有15-20分钟延迟 |
| 仓位管理 | ✅ 无影响 | 长期持仓管理不需要实时价格 |
| 再平衡 | ✅ 无影响 | 再平衡是长期策略 |

## 系统配置

### 当前配置（config.py）

```python
# 预警监控配置
ALERT_MONITORING_CONFIG = {
    'check_interval': 30,  # 30秒检查间隔
    'enable_dynamic_interval': False,  # 禁用动态间隔
}
```

### 批量获取工作原理

```python
# utils/data_fetcher.py
from yahooquery import Ticker

def batch_get_prices(symbols):
    """批量获取多个股票价格"""
    # 一次性获取所有股票
    tickers = Ticker(symbols)  # 只发送1次API请求
    prices_data = tickers.price

    # 解析价格
    for symbol in symbols:
        # 根据市场状态选择价格
        if market_state == 'REGULAR':
            price = data['regularMarketPrice']
        elif market_state == 'POST':
            price = data['postMarketPrice']
        # ...
```

## 备用方案：手动输入价格

如果yahooquery API无法访问（网络问题、API限制等），可以手动输入价格。

### 使用步骤

1. **准备价格数据**
   - 从券商平台查看实时价格
   - 或访问 finance.yahoo.com 查看

2. **创建或编辑手动价格文件**

   编辑文件：`data/manual_prices.json`

   ```json
   {
       "NVDA": 140.25,
       "AAPL": 195.42,
       "MU": 98.50
   }
   ```

3. **系统自动使用**
   - 系统会优先使用手动价格
   - 手动价格会覆盖API获取的价格
   - Dashboard会显示 "(手动)" 标记

### 手动价格优先级

```
价格获取优先级：
1. 手动价格 (data/manual_prices.json)  ⭐ 最高优先级
2. yahooquery批量获取
3. yahooquery单个获取（降级方案）
```

## 获取真正实时数据的方法

如果你需要真正的实时数据（无延迟），需要使用付费服务：

### 付费数据源选项

| 数据源 | 延迟 | 费用 | 适用场景 |
|--------|------|------|----------|
| **IEX Cloud** | 实时 | $9-499/月 | 个人投资者 |
| **Polygon.io** | 实时 | $29-399/月 | 日内交易 |
| **Alpha Vantage Premium** | 实时 | $49-249/月 | 专业投资者 |
| **券商API** | 实时 | 免费（需要券商账户） | 自动化交易 |

### 券商API集成（推荐）

如果你有以下券商账户，可以使用其API获取实时数据：

**支持的券商**：
- **TD Ameritrade**：免费API，实时数据
- **Interactive Brokers**：免费API，全球市场
- **Alpaca**：免费API，美股实时数据

**集成方法**（示例）：
```python
# 未来可能的集成方式
from td.client import TDClient

td_client = TDClient(
    client_id='YOUR_CLIENT_ID',
    redirect_uri='http://localhost',
    credentials_path='token.json'
)

# 获取实时报价
quote = td_client.get_quotes(instruments=['AAPL'])
price = quote['AAPL']['lastPrice']  # 真正的实时价格
```

## 性能优化建议

### 1. 使用批量获取

```python
# ❌ 不推荐：逐个获取
prices = {}
for symbol in ['NVDA', 'AAPL', 'MSFT']:
    prices[symbol] = get_current_price(symbol)  # 3次API调用

# ✅ 推荐：批量获取
prices = batch_get_prices(['NVDA', 'AAPL', 'MSFT'])  # 1次API调用
```

### 2. 利用盘后缓存

系统会自动优化盘后请求：
- 市场闭盘后，自动使用今日收盘价
- 避免重复请求相同数据
- 无需手动配置

### 3. 合理设置检查间隔

```python
# 价格预警监控建议间隔
ALERT_MONITORING_CONFIG = {
    'check_interval': 30,  # 30秒推荐
}

# 说明：
# - yahooquery批量获取，不受股票数量影响
# - 30秒足够频繁，同时避免过度请求
# - 数据本身有15-20分钟延迟，更短间隔意义不大
```

## 故障排除

### Yahoo Finance API无法访问

**症状**：
```
错误：获取价格失败
或：所有价格显示为 None
```

**可能原因**：
1. 网络连接问题
2. Yahoo Finance服务暂时不可用
3. 触发了API速率限制

**解决方法**：

**方法1：等待重试**
- 系统会自动重试（最多2次）
- 每次重试间隔1秒

**方法2：使用手动价格**
- 创建 `data/manual_prices.json`
- 输入当前价格
- 系统会自动使用手动价格

**方法3：检查网络**
```bash
# 测试网络连接
ping finance.yahoo.com

# 测试yahooquery
python -c "from yahooquery import Ticker; print(Ticker('AAPL').price)"
```

### 批量获取失败自动降级

系统有自动降级机制：

```
1. 尝试批量获取所有股票
   ↓ 失败
2. 自动降级到逐个获取
   ↓
3. 每个股票单独请求
   ↓ 仍失败
4. 返回None，使用缓存或手动价格
```

### 价格更新慢

**原因**：
- 数据延迟是Yahoo Finance免费API的固有限制
- 15-20分钟延迟是正常的

**解决**：
- 接受延迟（适合大多数场景）
- 或升级到付费实时数据源

## 数据文件位置

系统使用以下文件存储价格相关数据：

```
portfolio_manager/
└── data/
    ├── manual_prices.json      # 手动输入的价格
    └── price_timestamps.json   # 价格更新时间戳
```

**说明**：
- 这些文件由系统自动管理
- 通常不需要手动编辑
- 如需手动输入价格，编辑 `manual_prices.json`

## 未来改进方向

### 计划中的功能

- [ ] 支持更多数据源（IEX Cloud, Polygon.io）
- [ ] 券商API集成（TD Ameritrade, Interactive Brokers）
- [ ] WebSocket实时推送（需要付费数据源）
- [ ] 数据源自动切换（主数据源失败时切换到备用）
- [ ] 历史价格缓存（减少重复请求）

### 长期目标

- 提供插件式数据源架构
- 用户可自定义数据源优先级
- 支持混合数据源（不同股票使用不同数据源）

## 总结

### 核心要点

1. **主数据源**：yahooquery
   - 批量优化，性能优异
   - 15-20分钟延迟（免费API限制）

2. **适用场景**：
   - ✅ 日常监控、价格预警、长期投资
   - ❌ 高频交易、秒级精度需求

3. **备用方案**：
   - 手动输入价格（简单可靠）
   - 付费数据源（真正实时）

4. **性能优化**：
   - 使用批量获取
   - 利用盘后缓存
   - 合理设置检查间隔

### 快速参考

**正常使用**：
- 无需特殊配置
- yahooquery自动工作
- 30秒检查间隔

**遇到问题**：
- 检查网络连接
- 使用手动价格
- 查看故障排除章节

**需要实时数据**：
- 考虑付费数据源
- 或使用券商API

---

**最后更新**：2026-01-05
**相关文档**：
- [README.md](../README.md) - 系统总览
- [ALERT_MONITORING_GUIDE.md](ALERT_MONITORING_GUIDE.md) - 价格预警配置
