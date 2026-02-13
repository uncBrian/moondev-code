import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover


class DipBuyingStrategy(Strategy):
    buy_dips = [0.95, 0.90] # 5% dips an 10% dips 
    profit_target = 1.03 # 3% profit target  

    def init(self):
        self.buy_levels = [self.data.Close * dip for dip in self.buy_dips]
        self.sell_levels = self.data.Close * self.profit_target

    def next(self):
        if not self.position:
            for buy_level in self.buy_levels:
                if self.data.Close[-1] <= buy_level[-1]:
                    self.buy()
                    break

        else:
            if self.data.Close[-1] >= self.sell_levels[-1]:
                self.position.close()

data = pd.read_csv('20_more_bots_and_weekly_new_code/dipbuying_backtest/BTC-USD-6h-2020-12-02T00:00.csv', index_col=0, parse_dates=True)

data.columns = [column.capitalize() for column in data.columns]

bt = Backtest(data, DipBuyingStrategy, cash=1000000, commission=.002)

stats = bt.run()
print(stats)

bt.plot()