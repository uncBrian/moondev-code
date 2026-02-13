'''
this is an alternate backtest of the elliot wave strategy.  
'''

import pandas as pd 
from backtesting import Backtest, Strategy
from backtesting.lib import crossover 

def indentify_waves(data):

    waves = [] 

    # dummy exapes
    for i in range(0, len(data) -1, 5):
        wave_start = i 
        wave_end = i + 4 
        waves.append((wave_start, wave_end))

    return waves

class ElliotWaveStrategy(Strategy):
    def init(self):
        self.waves = indentify_waves(self.data.Close)
        self.current_wave = 0 

    def next(self):
        current_index = len(self.data.Close) - 1

        for wave_start, wave_end in self.waves:
            if current_index == wave_end:
                self.current_wave += 1 

                # buy at the end ofwave 2 

                if self.current_wave % 5 ==2:
                    self.buy()
                
                # sell at the end of wave 5 
                if self.current_wave % 5 ==0:
                    self.sell()

data = pd.read_csv('/Users/tc/Dropbox/**HMV/*ATC/Weekly Code - ATC/BTC-USD-5m-2015-2-02T00:00.csv', index_col=0, parse_dates=True)
data.columns = [column.capitalize() for column in data.columns]

bt = Backtest(data, ElliotWaveStrategy, cash=1000000, commission=.002)

stats = bt.run()
print(stats)
bt.plot()