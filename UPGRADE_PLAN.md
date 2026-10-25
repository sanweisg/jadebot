# JadeBot 升级计划 - 基于HyperGrok架构

## 已验证能力
1. ✅ Agnes看图能力正常工作 (agnes-2.5-flash)
2. ✅ FreqUI面板运行正常
3. ✅ 模拟交易已启动但未产生交易信号

## 关键发现：HyperGrok架构

### 7 Agent角色
| Agent | 职责 | 对应JadeBot现有 |
|-------|------|----------------|
| Desk Lead | 协调所有Agent，生成每日简报 | multi_agent.py |
| Market Analyst | 实时价格、深度、资金费率 | 无 |
| Research Analyst | 新闻、基本面、链上数据 | 无 |
| Strategist | 策略研发、回测、样本外验证 | SimpleStableRSI |
| Risk Manager | 风控、仓位计算、stressed stop | multi_agent.py简单实现 |
| Execution Trader | 下单执行、对账 | freqtrade |
| Trade Reviewer | 交易复盘、记录 | 无 |

### 核心机制
1. **Ticket系统**：每笔交易有唯一ID (HG-YYYYMMDD-XX)
2. **人工审批**：Risk Manager出票 → 用户批准 → Execution Trader执行
3. **Stressed Sizing**：考虑滑点和手续费计算止损距离
4. **Out-of-Sample**：保留20%数据做样本外验证
5. **每日简报**：统一状态汇总

## 升级步骤

### Phase 1: 添加Market Analyst (1小时)
- 获取实时BTC/ETH/SOL价格
- 监控资金费率和持仓量
- 检测异常波动

### Phase 2: 添加Research Analyst (2小时)
- 获取加密货币新闻
- Twitter/X情绪分析
- 链上数据监控

### Phase 3: 增强Risk Manager (30分钟)
- 实现stressed stop sizing
- 添加每日亏损停止机制
- 仓位上限控制

### Phase 4: 添加Trade Reviewer (1小时)
- 自动记录每笔交易
- 生成交易报告
- 策略表现分析

### Phase 5: 集成Agnes看图 (30分钟)
- 定时截图面板
- Agnes分析图表
- 自动识别交易信号

## 立即行动
1. 先升级multi_agent.py，添加Market Analyst和Research Analyst
2. 测试Agnes看图功能
3. 运行完整的7 Agent模拟
