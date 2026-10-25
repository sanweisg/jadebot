# JadeBot v2.0 - 几十Agent系统

## 架构对比

| 版本 | Agent数 | Desk数 | 特点 |
|------|---------|--------|------|
| v0.5 | 4 | 1 | 简单多Agent |
| v0.6 | 7 | 1 | HyperGrok风格 |
| v1.0 | 7 | 1 | 完整Ticket系统 |
| **v2.0** | **68** | **11** | **仿GROKSTREET** |

## 核心架构（仿GROKSTREET）

### 3个Chief级别
- CFO: 财务管理
- CTO: 技术架构  
- COO: 运营协调

### 11个Desk
- Alpha, Beta, Gamma, Delta, Epsilon
- Zeta, Eta, Theta, Iota, Kappa, Lambda

### 68个Agent分配
- 3个Chief
- 11个Desk Manager
- 30个Trader（每个Desk 2-3个）
- 20个Analyst（市场/风险/研究/情绪/执行）
- 15个Automation

## 与Grok Bot的关系

### 能做到的
- ✅ 几十个Agent的架构
- ✅ 多Desk协作
- ✅ Ticket审批流程
- ✅ Agnes Vision集成
- ✅ 本地运行（免费）

### 做不到的
- ❌ 不能拿到xAI官方源码（商业机密）
- ❌ 不能得到Grok-4模型（需要订阅）
- ❌ 不能100%复制商业产品界面

## 使用方法

### 运行几十Agent系统
```bash
cd ~/jadebot && source venv/bin/activate
python jadebot_v2.py
```

### 运行FreqUI面板
```bash
freqtrade webserver --config config_final.json
# 访问: http://localhost:8080
```

## GitHub
https://github.com/sanweisg/jadebot

## 下次开机
说"继续JadeBot"即可恢复所有上下文
