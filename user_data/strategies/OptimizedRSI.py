from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class OptimizedRSI(IStrategy):
    """
    优化的RSI策略 - 用于Hyperopt调参
    """
    
    # 策略参数范围（供Hyperopt优化）
    buy_rsi_fast = 30
    buy_rsi = 35
    
    sell_rsi = 70
    sell_rsi_fast = 80
    
    buy_ma_offset = 97
    sell_ma_offset = 100
    
    buy_ma_time = 3
    sell_ma_time = 3
    
    buy_rsi_time = 4
    sell_rsi_time = 4
    
    stoploss = -0.10
    trailing_stop = False
    timeframe = '1h'
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI计算
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.buy_rsi_time)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=self.buy_rsi_time // 2)
        
        # 移动平均线
        dataframe['ma{}'.format(self.buy_ma_time)] = ta.SMA(dataframe, timeperiod=self.buy_ma_time)
        dataframe['ma{}'.format(self.sell_ma_time)] = ta.SMA(dataframe, timeperiod=self.sell_ma_time)
        
        return dataframe
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < self.buy_rsi) &
                (dataframe['rsi_fast'] < self.buy_rsi_fast) &
                (dataframe['close'] < dataframe['ma{}'.format(self.buy_ma_time)] * (self.buy_ma_offset / 100))
            ),
            'buy'] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > self.sell_rsi) &
                (dataframe['rsi_fast'] > self.sell_rsi_fast) &
                (dataframe['close'] > dataframe['ma{}'.format(self.sell_ma_time)] * (self.sell_ma_offset / 100))
            ),
            'sell'] = 1
        
        return dataframe
