# this is a moving average crossover strategy backtest

import pandas as pd 
import numpy as np 
import talib
from backtesting import Backtest, Strategy

data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/BTC-USD-5m-2022-2-02T00:00.csv')
data.columns = [column.capitalize() for column in data.columns]

# define the MOving average cross over strategy
class MovingAverageCrossStrategy(Strategy): 
    n1 = 5 # short moving average
    n2 = 20 # long moving average

    def init(self):
        self.short_mavg = self.I(talib.SMA, self.data.Close, self.n1)
        self.long_mavg = self.I(talib.SMA, self.data.Close, self.n2)

    def next(self):
        if self.short_mavg[-1] > self.long_mavg[-1] and self.short_mavg[-2] <= self.long_mavg[-2]:
            self.buy()
        elif self.short_mavg[-1] < self.long_mavg[-1] and self.short_mavg[-2] >= self.long_mavg[-2]:
            self.sell()

# initialize the backtest
bt = Backtest(data, MovingAverageCrossStrategy, cash=10000, commission=.002)
output = bt.run()
print(output)

# plot the backtest
bt.plot()

