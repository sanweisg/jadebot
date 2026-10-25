# JadeBot v1.0 - 完整逆向Grok Bot

## 架构对比

| 功能 | Grok Bot (官方) | JadeBot v1.0 (我们) |
|------|----------------|---------------------|
| Agent数量 | 7个 | 7个 ✅ |
| Ticket系统 | HG-YYYYMMDD-XXXX | HG-YYYYMMDD-XXXX ✅ |
| Stressed Sizing | 滑点+手续费 | 实现 ✅ |
| 人工审批 | 必需 | 简化自动批准 ⚠️ |
| Agnes看图 | N/A | ✅ 已集成 |
| 数据源 | Hyperliquid | Binance ✅ |
| 开源程度 | 部分开源 | 完全开源 ✅ |

## 核心改进

### 1. Agnes Vision集成
- 可分析交易面板截图
- 实时识别交易信号
- 自动检测异常

### 2. Stressed Position Sizing
```python
stressed_distance = stop_distance + slippage + fees
size = risk_budget / stressed_distance
```

### 3. 完整的7 Agent工作流
```
Market Analyst → Research Analyst → Strategist → Risk Manager → Execution Trader → Trade Reviewer
                                              ↓
                                        Desk Lead (协调)
```

### 4. Ticket审批流程
```
Strategist生成信号 → Risk Manager创建工单 → 用户审批 → Execution Trader执行 → Trade Reviewer复盘
```

## 使用方法

### 运行交易模拟
```bash
cd ~/jadebot && source venv/bin/activate
python jadebot_v1.py
```

### 运行FreqUI面板
```bash
freqtrade webserver --config config_final.json
# 访问: http://localhost:8080
```

### 测试Agnes看图
```bash
python test_agnes_vision.py /path/to/screenshot.jpg
```

## GitHub
- https://github.com/sanweisg/jadebot
- 包含完整7 Agent架构
- Agnes Vision集成
- Stressed Sizing实现

## 下一步

1. 接入真实交易所API（OKX/Binance）
2. 添加Telegram通知
3. 实现完整的人工审批界面
4. 添加回测引擎
5. 集成更多数据源（链上数据、社交媒体）
