# opening range breakout backtest 

import pandas as pd 
import numpy as np 
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class OpeningRangeStrategy(Strategy):
    opening_range_minutes = 30 
    breakout = True 

    def init(self):
        self.high = self.I(lambda x: pd.Series(x).rolling(self.opening_range_minutes).max(), self.data.High)
        self.low = self.I(lambda x: pd.Series(x).rolling(self.opening_range_minutes).min(), self.data.Low)

    def next(self):
        if len(self.data) < self.opening_range_minutes:
            return

        if self.breakout:
            # vreakout startegy
            if self.data.Close[-1] > self.high[-2]:
                self.buy()
            elif self.data.Close[-1] < self.low[-2]:
                self.sell()

        else:
            # reversal strategy
            if self.data.Close[-1] < self.low[-2] and crossover(self.data.Close, self.high[-2]):
                self.buy()
            elif self.data.Close[-1] > self.high[-2] and crossover(self.high[-2], self.data.Close):
                self.sell()


data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/BTC-USD-5m-2022-2-02T00:00.csv')
data.columns = [column.capitalize() for column in data.columns]
print(data)

bt = Backtest(data, OpeningRangeStrategy, cash=1000000, commission=.002)

# run the backtest with breakout
stats_breakout = bt.run()
print(stats_breakout)
range_minutes = range(10, 61, 5)

# optimixe the strat by finding the best opening range min values
optimize_results = bt.optimize(opening_range_minutes=range_minutes, maximize='Sharpe Ratio')

# runthe reversal strat
bt._strategy.breakout = False
#stats_reversal = bt.run()
#print(stats_reversal)
# plot results
bt.plot()