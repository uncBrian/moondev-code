'''
this is a backtest of the elliot wave strategy. 
'''

import pandas as pd 
import talib 
from backtesting import Backtest, Strategy

def moving_average_cross(price_data, short_period, long_period):
    short_ma = talib.SMA(price_data, timeperiod=short_period)
    long_ma = talib.SMA(price_data, timeperiod=long_period)
    cross_above = short_ma > long_ma 
    cross_below = short_ma < long_ma
    return cross_above, cross_below

def ElliotWaveStrategy(Strategy):
    def init(self):
        self.price = self.data.Close 
        self.cross_above, self.cross_below = moving_average_cross(self.price, 20, 50)
        self.in_position = False 

    def next(self):
        current_index = len(self.price)-1

        # enter a oong when short ma cross above long MA
        if self.cross_above[current_index] and not self.in_position:
            self.buy()
            self.in_position = True

        # exit a long position when short MA cross below long MA
        elif self.cross_below[current_index] and self.in_position:
            self.sell()
            self.in_position = False

data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/BTC-USD-5m-2015-2-02T00:00.csv', index_col=0, parse_dates=True)
data.columns = [column.capitalize() for column in data.columns]
bt = Backtest(data, ElliotWaveStrategy, cash=10000, commission=.002)
stats = bt.run()
print(stats)