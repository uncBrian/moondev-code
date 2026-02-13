# adx backtest

import numpy as np 
import pandas as pd  
import talib as ta  
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class ADXTrendStrengthStrategy(Strategy):
    adx_period = 14 
    min_adx = 25 
    trailing_stop_pct = 0.02 

    def init(self):
        close = self.data.Close
        high = self.data.High
        low = self.data.Low

        self.adx = self.I(ta.ADX, high, low, close, timeperiod=self.adx_period)
        self.close_shifted = self.data.Close.to_series().shift(1)

    def next(self):
        if not self.position:
            if self.adx[-1] > self.min_adx:
                if crossover(self.data.Close, self.close_shifted):
                    self.buy()

        else:
            if crossover(self.close_shifted, self.data.Close):
                self.sell()

data = pd.read_csv('/Users/tc/Dropbox/dev/yt_vids/may23/BTC-USD-15m-2023-2-02T00:00.csv', index_col=0, parse_dates=True)
data.columns = [column.capitalize() for column in data.columns]

bt = Backtest(data, ADXTrendStrengthStrategy, cash=1000000, commission=.002)

stats = bt.run()
print(stats)
bt.plot()