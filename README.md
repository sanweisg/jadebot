# JadeBot - 加密货币智能交易系统

基于Freqtrade + 多Agent架构的智能交易机器人

## 快速开始

### 1. 启动多Agent系统
```bash
cd ~/jadebot && source venv/bin/activate && python multi_agent.py
```

### 2. 启动可视化面板
```bash
# FreqUI面板
freqtrade webserver --config config_final.json
# 浏览器打开: http://localhost:8080

# Streamlit面板
streamlit run dashboard.py
# 浏览器打开: http://localhost:8501
```

### 3. 运行模拟交易
```bash
# 后台运行24小时
freqtrade trade --strategy SimpleStableRSI --config config_final.json > user_data/logs/trade.log 2>&1 &

# 查看实时日志
tail -f user_data/logs/trade.log

# 停止
pkill -f "freqtrade trade"
```

## 项目结构
```
~/jadebot/
├── user_data/
│   ├── strategies/          # 策略代码
│   │   ├── SimpleStableRSI.py  # 最终推荐策略
│   │   └── SimpleRSI.py
│   ├── data/binance/        # 历史数据
│   ├── logs/                # 运行日志
│   └── tradesv3.dryrun.sqlite  # 模拟交易数据库
├── config_final.json        # 主配置
├── multi_agent.py           # 多Agent系统
├── dashboard.py             # Streamlit面板
├── README.md
└── ...
```

## 策略说明
- **SimpleStableRSI**: RSI超卖买入 + EMA趋势过滤
- 止损: -5%
- 止盈: 分阶段 10%/5%/2%
- 连续亏损2次自动停手

## 文件位置
- 所有文件都在: `/home/jace/jadebot/`
- 备份已推送到GitHub: sanweisg/jadebot
