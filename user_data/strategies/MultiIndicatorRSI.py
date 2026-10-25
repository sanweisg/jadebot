from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib
from freqtrade.strategy import IntParameter, CategoricalParameter


class MultiIndicatorRSI(IStrategy):
    """
    多指标RSI策略 - 增强版
    - RSI + MACD + 布林带 + ATR
    - 多条件确认，提高信号质量
    - 动态止损（基于ATR）
    """
    
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    
    # ROI配置
    minimal_roi = {
        "0": 0.15,      # 任何时刻保留15%利润
        "60": 0.08,     # 持有60分钟后保留8%
        "180": 0.03     # 持有180分钟后保留3%
    }
    
    # 参数定义
    buy_rsi = IntParameter(low=20, high=40, default=30, space='buy')
    sell_rsi = IntParameter(low=60, high=80, default=70, space='sell')
    
    # 止损配置（必须）
    stoploss = -0.05
    
    # 动态止损系数（基于ATR）
    atr_stop_multiplier = 2.0
    
    # 不使用trailing stop
    trailing_stop = False
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # 布林带
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lower'] = bollinger['lower']
        dataframe['bb_middle'] = bollinger['mid']
        dataframe['bb_upper'] = bollinger['upper']
        
        # ATR（用于动态止损）
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # 趋势过滤
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 买入条件：多个指标确认
        dataframe.loc[
            (
                # RSI超卖
                (dataframe['rsi'] < self.buy_rsi.value) &
                # 价格在布林带下轨附近（超卖区域）
                (dataframe['close'] < dataframe['bb_lower'] * 1.02) &
                # MACD金叉或即将金叉
                (dataframe['macd'] > dataframe['macdsignal']) &
                # 上升趋势
                (dataframe['close'] > dataframe['ema_200']) &
                # 成交量正常
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 卖出条件：多个指标确认
        dataframe.loc[
            (
                # RSI超买
                (dataframe['rsi'] > self.sell_rsi.value) &
                # MACD死叉
                (dataframe['macd'] < dataframe['macdsignal']) &
                # 价格在布林带上轨附近
                (dataframe['close'] > dataframe['bb_upper'] * 0.98)
            ),
            'exit_long'] = 1
        
        return dataframe
    
    def custom_stoploss(self, pair: str, trade: 'Trade', current_time, current_rate, current_profit, **kwargs) -> float:
        """动态止损：基于ATR"""
        # 获取最近的ATR值
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1]
        
        if last_candle is None:
            return self.stoploss
        
        atr = last_candle['atr']
        if atr == 0:
            return self.stoploss
        
        # 动态止损距离
        dynamic_stop = self.atr_stop_multiplier * atr / current_rate
        
        # 取保守的止损
        return min(abs(self.stoploss), dynamic_stop)
