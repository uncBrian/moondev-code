from backtesting import Strategy 
from indicators_26 import * 

# flag continuation class
class FlagCont(Strategy):
    tp_perc = 29
    sl_perc = 7
    # look for flag pattern wiht this length
    length = 30 

    def init(self):
        self.trend = trend_lines(self.data.df) # in indicators file

    def next(self):
        index = len(self.data.Close)-1 

        ''' if not in position '''
        if not self.position:
            touched_times = self.trend['touched_top'].iloc[index-self.length:index].sum() + self.trend['touched_bot'].iloc[index-30:index].sum()
            slope = self.trend['high_trend'].iloc[index] - self.trend['high_trend'].iloc[index-1]
            print(touched_times)

            if touched_times == 3:
                '''check long'''
                if slope > 0:
                    self.buy(tp=self.data.Close+(self.data.Close*(self.tp_perc/100)), sl=self.data.Close-(self.data.Close*(self.sl_perc/100)))

                '''check short'''
                if slope < 0:
                    self.sell(tp=self.data.Close-(self.data.Close*(self.tp_perc/100)), sl=self.data.Close+(self.data.Close*(self.sl_perc/100)))