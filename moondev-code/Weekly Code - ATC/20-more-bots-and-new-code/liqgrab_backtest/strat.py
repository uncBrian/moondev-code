import datetime
import pandas as pd
from indicators import *
from dataset import *
from backtesting import Strategy


class LiquidityGrab(Strategy):
    tp_percent = 20
    sl_percent = 10
    entry_window_percent = 30 #must be within x% of the min for a long or x% of the max for a short after given the signal for a trade

    looking_to_buy = False
    looking_to_sell = False
    enter_threshold = None



    def init(self):
        self.broke_structure_high = self.I(break_structure, self.data.df,'high')
        self.broke_structure_low = self.I(break_structure, self.data.df,'low')
        self.asian_range,self.asian_range_max,self.asian_range_min = self.I(asian_range, self.data.df)
        self.broke_asian_range_low = self.I(break_asian_range, self.data.df,'low')
        self.broke_asian_range_high = self.I(break_asian_range, self.data.df,'high')



    def next(self):

        '''if not in a position'''
        if not self.position:

            if not (self.looking_to_buy or self.looking_to_sell):

                '''check long'''
                broke_asian_low = True in self.broke_asian_range_low[len(self.data.asian_range) - list(self.data.asian_range)[::-1].index(True):]
                if self.broke_structure_high and broke_asian_low:
                    self.looking_to_buy = True
                    self.enter_threshold = self.asian_range_min[-1]+((self.asian_range_min[-1]-self.asian_range_min[-1])*(self.entry_window_percent/100))
                    
            
                '''check short'''
                broke_asian_high = True in self.broke_asian_range_high[len(self.data.asian_range) - list(self.data.asian_range)[::-1].index(True):]
                if self.broke_structure_low and broke_asian_high:
                    self.looking_to_sell = True
                    self.enter_threshold = self.asian_range_max[-1]-((self.asian_range_max[-1]-self.asian_range_min[-1])*(self.entry_window_percent/100))


                
                
            else:
                
                if self.looking_to_buy and self.data.Low[-1] <= self.enter_threshold:
                    self.buy(tp=self.asian_range_max[-1], sl=self.data.Close[-1]-(self.data.Close[-1]*(self.sl_percent/100)))
                    # self.buy(tp=self.data.Close[-1]+(self.data.Close[-1]*(self.tp_percent/100)), sl=self.data.Close[-1]-(self.data.Close[-1]*(self.sl_percent/100)))
                    self.looking_to_buy = False
                    self.enter_threshold = None
                
                elif self.looking_to_sell and self.data.High[-1] >= self.enter_threshold:
                    self.sell(tp=self.asian_range_min[-1], sl=self.data.Close[-1]+(self.data.Close[-1]*(self.sl_percent/100)))
                    # self.sell(tp=self.data.Close[-1]-(self.data.Close[-1]*(self.tp_percent/100)), sl=self.data.Close[-1]+(self.data.Close[-1]*(self.sl_percent/100)))
                    self.looking_to_sell = False
                    self.enter_threshold = None



        '''close a trade if open for at least a day'''
        # if self.position:
        #     entry_time = self.trades[-1].entry_time

        #     if (self.data.df.index.tolist()[-1] - entry_time).total_seconds()/(3600*24) >= 1:
        #         self.position.close()