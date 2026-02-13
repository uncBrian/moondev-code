'''
EMA + Bollinger Band Backtest
Start                                     0.0                                                                      
End                                   30775.0
Duration                              30775.0
Exposure Time [%]                   85.131271
Equity Final [$]                 9440694.8155
Equity Peak [$]                  11328562.348
Return [%]                         844.069482
Buy & Hold Return [%]              908.245604
Return (Ann.) [%]                         0.0
Volatility (Ann.) [%]                     NaN
Sharpe Ratio                              NaN
Sortino Ratio                             NaN
Calmar Ratio                              0.0
Max. Drawdown [%]                  -65.204123
Avg. Drawdown [%]                    -3.57187
Max. Drawdown Duration                15234.0
Avg. Drawdown Duration             158.505208
# Trades                               2882.0
Win Rate [%]                        57.078418
Best Trade [%]                      10.116798
Worst Trade [%]                    -14.813377
Avg. Trade [%]                       0.834167
Max. Trade Duration                    1123.0
Avg. Trade Duration                108.292505
Profit Factor                        1.555826
Expectancy [%]                       0.975947
SQN                                  1.254341
'''

import numpy as np 
import backtesting 
import talib 
import pandas as pd 
from backtesting.lib import crossover 

class BBANDS_EMA_STRATEGY(backtesting.Strategy):
    timeperiod = 20 
    ema_period = 20 
    def init(self):
        self.upper_band, self.middle_band, self.lower_band = self.I(talib.BBANDS, self.data.Close, timeperiod=self.timeperiod, nbdevup=2, nbdevdn=2)
        self.ema = self.I(talib.EMA, self.data.Close, timeperiod = self.timeperiod)

    def next(self):# 5002862.9
        if crossover(self.data.Close, self.upper_band) or crossover(self.ema, self.data.Close):
            self.buy(tp=self.data.Close*1.1, sl=self.data.Close*0.95)

        elif crossover(self.data.Close, self.ema):
            self.sell(size=2)
            pass 

data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/ETH-USD-1h-2020-2-02T00:00.csv')
data.columns = [column.capitalize() for column in data.columns]
data = data.dropna()

bt = backtesting.Backtest(data, BBANDS_EMA_STRATEGY, cash=1000000, commission=.006)

stats = bt.optimize(maximize='Equity Final [$]', timeperiod=range(20, 60, 5))

print(stats)

bt.plot()