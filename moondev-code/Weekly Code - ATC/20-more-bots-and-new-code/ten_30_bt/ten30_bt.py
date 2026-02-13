# this counter trades the crowd at 1030 

import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover 
from datetime import datetime

class MyStrategy(Strategy):

    n1 = 9 # 9am 
    n2 = 10 # 10am 

    long_trend = False
    short_trend = False 

    def init(self):
        self.long_trend = self.data.Close[:self.n1].mean() > self.data.Close[:self.n2].mean()
        self.short_trend = self.data.Close[:self.n1].mean() < self.data.Close[:self.n2].mean() 

    def next(self):
        hora = str(self.data.index[-1].time())[:-3]
        diez_30 = f'{self.n2}:30'

        # si es las 1030am 
        if hora == diez_30:
            if self.short_trend:
                self.buy()
            elif self.long_trend:
                self.sell()

data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/BTC-USD.csv', index_col=0, parse_dates=True)

data.columns = [column.capitalize() for column in data.columns]
print(data)

bt = Backtest(data, MyStrategy, cash=1000000, commission=.002)

stats = bt.run()
print(stats)

bt.plot()