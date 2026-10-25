from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib
from freqtrade.strategy import IntParameter


class RobustRSI(IStrategy):
    """
    稳健型RSI策略 - 减少过拟合风险
    - 更少参数
    - 更宽松的买卖条件
    - 更合理的止损止盈
    """
    
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    
    # 简化的止损止盈
    minimal_roi = {
        "0": 0.05,      # 任何时候都保留5%利润
        "30": 0.03,     # 持有30分钟后保留3%
        "60": 0.01      # 持有60分钟后保留1%
    }
    
    stoploss = -0.08  # 止损8%（比默认的10%更紧）
    
    # Hyperopt可优化参数
    buy_rsi = IntParameter(low=20, high=45, default=35, space='buy')
    sell_rsi = IntParameter(low=55, high=80, default=65, space='sell')
    
    # 不使用trailing stop，避免过度优化
    trailing_stop = False
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 只计算必要的指标
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 添加简单的趋势过滤
        dataframe['sma_20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 买入条件：RSI低于阈值 + 价格在SMA20上方（上升趋势）
        dataframe.loc[
            (
                (dataframe['rsi'] < self.buy_rsi.value) &
                (dataframe['close'] > dataframe['sma_20']) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 卖出条件：RSI高于阈值 OR 触发止损
        dataframe.loc[
            (
                (dataframe['rsi'] > self.sell_rsi.value) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1
        
        return dataframe
