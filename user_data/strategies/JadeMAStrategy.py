#!/usr/bin/env python3
"""
JadeBot - MA Crossover Strategy (简单均线策略)
基于双均线交叉的经典策略，适合初学者理解
"""
import numpy as np
import pandas as pd
from pandas import DataFrame
from typing import Dict, Optional

from freqtrade.strategy import IStrategy
from freqtrade.strategy import IntParameter
import talib.abstract as ta
from technical import qtpylib


class JadeMAStrategy(IStrategy):
    """
    JadeBot 简单均线交叉策略
    
    买入条件：
    - 短期均线(快线)上穿长期均线(慢线) = 金叉
    
    卖出条件：
    - 短期均线下穿长期均线 = 死叉
    - 或达到止盈/止损目标
    
    风险提示：
    - 本策略仅供参考学习，不构成投资建议
    - 加密货币市场波动极大，请务必做好风险管理
    - 建议先在模拟环境充分测试后再考虑实盘
    """
    
    INTERFACE_VERSION = 3
    
    # 时间框架（5分钟K线）
    timeframe = '5m'
    
    # 不允许做空
    can_short: bool = False
    
    # 最小投资回报率（ROI）
    # 0分钟涨4%，30分钟涨2%，60分钟涨1%
    minimal_roi = {
        "0": 0.04,
        "30": 0.02,
        "60": 0.01
    }
    
    # 止损（-10%）
    stoploss = -0.10
    
    # 启用追踪止损
    trailing_stop = True
    trailing_stop_positive = 0.02      # 盈利2%后启用追踪
    trailing_stop_positive_offset = 0.04  # 偏移4%
    trailing_only_offset_is_reached = True
    
    # 只在有新K线时运行
    process_only_new_candles = True
    
    # 启动所需K线数
    startup_candle_count = 50
    
    # 是否使用退出信号
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # 可优化参数
    fast_length = IntParameter(5, 20, default=9, space='buy')
    slow_length = IntParameter(20, 50, default=21, space='buy')
    
    # 订单类型
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False
    }
    
    # 订单时间类型
    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC"
    }
    
    # 绘图配置
    @property
    def plot_config(self):
        return {
            "main_plot": {
                "sma_fast": {"color": "#00ff88"},
                "sma_slow": {"color": "#ff6b6b"},
            },
            "subplots": {
                "MACD": {
                    "macd": {"color": "blue"},
                    "macdsignal": {"color": "orange"},
                }
            }
        }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算技术指标
        """
        # 快速移动平均线
        dataframe['sma_fast'] = ta.SMA(dataframe, timeperiod=self.fast_length.value)
        
        # 慢速移动平均线
        dataframe['sma_slow'] = ta.SMA(dataframe, timeperiod=self.slow_length.value)
        
        # MACD（用于辅助判断）
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # RSI（相对强弱指标）
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 成交量
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        定义买入信号
        """
        dataframe.loc[
            (
                # 快线上穿慢线（金叉）
                qtpylib.crossed_above(dataframe['sma_fast'], dataframe['sma_slow']) &
                # MACD为正值（趋势向上）
                (dataframe['macd'] > 0) &
                # RSI不过热（避免追高）
                (dataframe['rsi'] < 70) &
                # 成交量大于平均值（确认趋势）
                (dataframe['volume'] > dataframe['volume_mean']) &
                # 确保有成交量
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        定义卖出信号
        """
        dataframe.loc[
            (
                # 快线下穿慢线（死叉）
                qtpylib.crossed_below(dataframe['sma_fast'], dataframe['sma_slow']) &
                # MACD为负值（趋势向下）
                (dataframe['macd'] < 0) &
                # 确保有成交量
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1
        
        return dataframe


# 策略说明文档
STRATEGY_DOC = """
# JadeBot 交易策略说明

## 策略名称
MA Crossover (均线交叉策略)

## 策略逻辑
这是一个经典的双均线交叉策略，适用于趋势跟踪：

### 买入条件（做多）
1. 快速均线(9周期)上穿慢速均线(21周期) = 金叉
2. MACD > 0（确认上升趋势）
3. RSI < 70（避免在高点买入）
4. 成交量 > 20周期均值（确认趋势有效性）

### 卖出条件（平仓）
1. 快速均线下穿慢速均线 = 死叉
2. 达到止盈目标（4%/2%/1%）
3. 触发止损（-10%）
4. 启用追踪止损（盈利2%后保护利润）

## 风险参数
- 单笔最大风险：10%（止损）
- 最大持仓时间：约60分钟（根据ROI配置）
- 建议仓位：不超过总资金的20%

## 适用市场
- 趋势明显的市场（牛市/熊市中期）
- 不适合横盘震荡市场

## 风险提示
⚠️ **本策略仅供参考学习，不构成投资建议**

1. 加密货币市场波动极大，可能产生巨额亏损
2. 历史回测结果不代表未来表现
3. 建议先用模拟账户充分测试
4. 切勿投入无法承受损失的资金
5. 本策略未经充分实盘验证

## 下一步优化方向
1. 添加更多技术指标（布林带、KDJ等）
2. 使用机器学习和FreqAI优化参数
3. 多时间框架分析（同时查看1h和4h趋势）
4. 结合链上数据和市场情绪
5. 实施更严格的风险管理

## 回测命令
```bash
# 回测最近30天
freqtrade backtesting -c config_dryrun.json --strategy JadeMAStrategy --timerange 20250901-20251025

# 查看结果
freqtrade backtesting-show -c config_dryrun.json
```
"""

if __name__ == '__main__':
    print(STRATEGY_DOC)
