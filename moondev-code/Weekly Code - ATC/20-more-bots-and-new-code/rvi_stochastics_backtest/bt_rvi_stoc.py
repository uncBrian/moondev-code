'''
RVI STOCHASTICS BACKTEST
Start                                     0.0
End                                   30775.0
Duration                              30775.0
Exposure Time [%]                   99.951261
Equity Final [$]               16764900.83968
Equity Peak [$]                44407591.19968
Return [%]                        1576.490084 
Buy & Hold Return [%]              908.245604
Return (Ann.) [%]                         0.0
Volatility (Ann.) [%]                     NaN
Sharpe Ratio                              NaN
Sortino Ratio                             NaN
Calmar Ratio                              0.0
Max. Drawdown [%]                  -81.383173
Avg. Drawdown [%]                   -4.320725
Max. Drawdown Duration                15234.0
Avg. Drawdown Duration             140.233945
# Trades                                 14.0
Win Rate [%]                        92.857143
Best Trade [%]                    1251.230259
Worst Trade [%]                     -0.945364
Avg. Trade [%]                      71.057932
Max. Trade Duration                   29828.0
Avg. Trade Duration               4849.857143
Profit Factor                      2901.53944
Expectancy [%]                     195.861795
SQN                                  1.248716

'''


from backtesting import Backtest, Strategy 
from backtesting.lib import crossover 
import pandas as pd 
from talib import STOCH 


def calculate_rvi(data, period=14):
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)

    data['Close_diff'] = data['Close'].diff()

    data['Up_sum'] = data['Close_diff'].apply(lambda x: x if x > 0 else 0).rolling(period).sum()
    data['Down_sum'] = data['Close_diff'].apply(lambda x: abs(x) if x < 0 else 0).rolling(period).sum()

    data['RVI'] = data['Up_sum'] / (data['Up_sum'] + data['Down_sum'])

    return data['RVI']


class RVIStochastic(Strategy):
    stochastic_high = 80 
    stochastic_low = 30 
    def init(self):
        self.rvi = self.I(calculate_rvi, self.data.Close)
        self.k, self.d = self.I(STOCH, self.data.High, self.data.Low, self.data.Close)
    def next(self):
        stochastic_overbought = self.k[-1] > self.d[-1] or self.k[-1] > self.stochastic_high
        stochastic_oversold = self.k[-1] < self.stochastic_low
        rvi_overbought = self.rvi[-1] > 0.7
        rvi_oversold = self.rvi[-1] < 0.3
        if stochastic_oversold and rvi_oversold:
            self.buy()
        elif stochastic_overbought or rvi_overbought:
            self.sell()

data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/ETH-USD-1h-2020-2-02T00:00.csv')
data.columns = [column.capitalize() for column in data.columns]
data = data.dropna()

bt = Backtest(data, RVIStochastic, cash=1000000, commission=.006)

#@stats = bt.optimize(maximize='Equity Final [$]', timeperiod=range(20, 60, 5))
stats = bt.run()

print(stats)

bt.plot()