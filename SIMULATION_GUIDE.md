# JadeBot 模拟交易测试指南

## 当前状态

### ✅ 已完成
- 策略开发：SimpleStableRSI（最终推荐版本）
- 回测验证：6个月训练集 + 6个月样本外
- 系统框架：Freqtrade + CCXT + 数据下载

### ⚠️ 配置问题
Freqtrade版本 2026.9 需要特定配置格式。下面提供两种启动方式：

---

## 方式一：使用简单配置（推荐）

创建 `config_simple.json`：

```json
{
    "stake_currency": "USDT",
    "stake_amount": 100,
    "dry_run": true,
    "dry_run_wallet": 1000,
    "exchange": {"name": "binance", "key": "", "secret": ""},
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "db_url": "sqlite:///tradesv3.dryrun.sqlite",
    "strategy": "SimpleStableRSI",
    "strategy_path": "user_data/strategies"
}
```

运行：
```bash
cd ~/jadebot
source venv/bin/activate
freqtrade trade --strategy SimpleStableRSI --config config_simple.json
```

---

## 方式二：使用命令行参数

```bash
cd ~/jadebot
source venv/bin/activate
freqtrade trade \
  --strategy SimpleStableRSI \
  --exchange binance \
  --pairs BTC/USDT ETH/USDT \
  --timeframe 1h \
  --dry-run \
  --max-open-trades 3 \
  --stake-amount 100
```

---

## 查看当前信号

策略逻辑：
```
买入条件：
1. RSI < 30（超卖）
2. 价格 > EMA200（上升趋势）

卖出条件：
1. 触发ROI（10%/5%/2%分阶段）
2. 触发止损（-5%）
```

检查当前RSI和趋势：
```bash
# 查看BTC当前价格
curl -s https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT

# 查看ETH当前价格
curl -s https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT
```

---

## 常见问题

### Q: 为什么没有产生交易信号？
A: 可能原因：
1. RSI > 30（不够超卖）
2. 价格 < EMA200（不是上升趋势）
3. 数据时间范围问题

### Q: 如何查看交易日志？
A: 日志保存在：`~/jadebot/user_data/logs/jadebot.log`

### Q: 如何停止模拟交易？
A: 按 `Ctrl+C` 终止进程

---

## 下一步

1. 运行模拟交易至少24小时
2. 观察信号是否符合预期
3. 确认系统稳定后，考虑接入OKX实盘

---

**重要提醒：** 这是模拟交易，不涉及真实资金。实盘前必须充分测试！
