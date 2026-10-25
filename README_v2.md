# 🤖 JadeBot v0.2 - 系统化交易框架

> **基于Grok Bot交易台架构 + 真实风控逻辑**

## 核心设计理念

### 1. 多策略引擎（而非单一策略）
参考Grok Bot的"8-agent交易台"模式，我们实现了：
- **MA Crossover**：趋势跟踪，适合单边行情
- **Bollinger Reversion**：均值回归，适合震荡市场
- **ATR Breakout**：突破策略，捕捉大行情

### 2. 严格风控系统（基于实战经验）
从Grok Bot交易台的教训中提取：
- 单笔风险 ≤ 1.5%（防止单次错误致命）
- 日亏损熔断 5%（防止连续亏损吞噬本金）
- 总仓位 ≤ 25%（保留80%现金应对极端行情）
- 止损后冷却30分钟（防止情绪化复亏）

### 3. 完整的交易记录
类似Grok Bot的trading_log.md：
- SQLite数据库记录每笔交易
- 包含入场原因、止损止盈位、平仓原因
- 日报自动生成（扫描数/清除数/执行数/PnL）

---

## 快速开始

### 安装依赖
```bash
cd ~/jadebot
source venv/bin/activate
pip install ccxt python-telegram-bot pandas numpy
```

### 配置
编辑 `user_data/configs/jadebot_config.json`：
```json
{
  "telegram_token": "你的BotToken",
  "dry_run": true,
  "strategy": "ma_crossover"
}
```

### 运行
```bash
python jadebot_v2.py
```

---

## 风控参数详解

| 参数 | 值 | 说明 |
|------|-----|------|
| MAX_RISK_PER_TRADE | 1.5% | 单笔最大风险 |
| MAX_DAILY_LOSS | 5% | 日亏损熔断阈值 |
| MAX_TOTAL_EXPOSURE | 25% | 总持仓上限 |
| MAX_POSITION_PER_PAIR | 10% | 单币种仓位限制 |
| STOP_LOSS_ATR_MULTIPLIER | 2.0 | 止损距离(ATR倍数) |
| HARD_STOP_LOSS | 8% | 硬止损底线 |
| TRAILING_STOP_TRIGGER | 2% | 追踪止损触发点 |
| TRAILING_STOP_DISTANCE | 1.5% | 追踪距离 |

---

## 策略说明

### 策略1: MA Crossover（均线交叉）
- **买入条件**：快线上穿慢线 + RSI < 70
- **卖出条件**：快线下穿慢线 OR RSI > 75
- **适用市场**：趋势明显的行情
- **预期胜率**：45-55%
- **盈亏比**：1:2~1:3

### 策略2: Bollinger Reversion（布林带回归）
- **买入条件**：价格触及下轨 + RSI < 30
- **卖出条件**：价格触及上轨 + RSI > 70
- **适用市场**：震荡横盘
- **预期胜率**：55-65%
- **盈亏比**：1:1.5

### 策略3: ATR Breakout（突破策略）
- **买入条件**：突破20日高点 + ATR确认
- **卖出条件**：跌破20日低点
- **适用市场**：波动率放大阶段
- **预期胜率**：40-50%
- **盈亏比**：1:3+

---

## Telegram命令

| 命令 | 功能 |
|------|------|
| /start | 显示菜单 |
| /status | 运行状态 |
| /balance | 钱包余额 |
| /positions | 当前持仓 |
| /risk | 风控状态 |
| /stop | 紧急停止 |
| /help | 帮助信息 |

---

## 数据库结构

```sql
-- 交易记录表
trades (
    id, timestamp, pair, direction, 
    entry_price, exit_price, quantity,
    entry_reason, exit_reason,
    profit_usdt, profit_percent,
    status, stop_loss, take_profit_1/2/3
)

-- 持仓监控表
position_watch (
    trade_id, timestamp, price,
    unrealized_pnl, stop_distance,
    volume_trend, notes
)

-- 日报表
daily_report (
    date, scanned_count, cleared_count,
    executed_count, pnl_usdt, win_rate,
    best_trade, worst_trade, risk_status
)
```

---

## 风险提示

⚠️ **重要声明**

1. 本项目仅供学习研究，不构成投资建议
2. 加密货币交易风险极高，可能导致全部本金损失
3. 历史回测结果不代表未来表现
4. 建议先用模拟账户充分测试
5. 切勿投入无法承受损失的资金

---

## 下一步开发

- [ ] 接入OKX API（实盘）
- [ ] FreqAI机器学习优化
- [ ] 多交易所支持（Binance等）
- [ ] Web Dashboard可视化
- [ ] 社交信号整合（X/Twitter sentiment）
- [ ] 手机App控制（iOS/Android）

---

**记住：先活下来，再赚钱。**
