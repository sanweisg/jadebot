from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib
from freqtrade.strategy import IntParameter


class SimpleStableRSI(IStrategy):
    """
    简单稳定型RSI策略
    - 极少参数，减少过拟合
    - 明确的趋势过滤
    - 保守的止损止盈
    """
    
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    
    # 保守的ROI和止损
    minimal_roi = {
        "0": 0.10,      # 任何时刻都保留10%利润
        "60": 0.05,     # 持有60分钟后保留5%
        "180": 0.02     # 持有180分钟后保留2%
    }
    
    stoploss = -0.05  # 止损5%（更保守）
    
    # 只有1个可优化参数
    buy_rsi = IntParameter(low=20, high=40, default=30, space='buy')
    
    trailing_stop = False
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 只计算RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # 趋势过滤 - 价格在200EMA上方才是上升趋势
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 买入条件：RSI低于阈值 + 上升趋势
        dataframe.loc[
            (
                (dataframe['rsi'] < self.buy_rsi.value) &
                (dataframe['close'] > dataframe['ema_200']) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 卖出条件：触发ROI或手动设置
        return dataframe
