'''
Today we are backting a Flag Pattern Breakout strategy. This strategy is a simple breakout strategy that looks for a flag pattern to form, and then breaks out of the pattern. The strategy is based on the following assumptions:
 
NOTE- must have data imported on the line that says data = pd.read_csv(....)
'''

# get data on the 15min timeframe

from backtesting import Backtest 
from datetime import datetime 
import warnings
warnings.filterwarnings('ignore')
import pandas as pd 
from strats_26 import *

def run_backtest(stratName, symbol, timeframe, start_time, plot=True, save_data=True):

    data = pd.read_csv('BTC-USD-5m-2015-2-02T00:00.csv', index_col='datetime', parse_dates=True)

    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    # run the backtest
    bt = Backtest(data, eval(stratName), cash=10000, commission=.001, exclusive_orders=True)

    # get the results
    output = bt.run()
    #print(output)

    # plot the results
    if plot:
        bt.plot()


run_backtest('FlagCont', 'ETH-USD', timeframe='1h', start_time=datetime(2022, 1, 1, 12,0, 0), plot=True, save_data=False)

# # look at data and see where missing data is
# data = pd.read_csv('feb23/BTC-USD-15m.csv', index_col='datetime', parse_dates=True)
# # print columns where there is missing data
# # show where there is missing data 

# # fill in missing data with previous data
# data = data.fillna(method='ffill')
# # save the new data as datafilled
# data.to_csv('feb23/BTC-USD-15m_filled.csv')

'''
run_backtest('FlagCont', 'ETH-USD', timeframe='1h', start_time=datetime(2022, 1, 1, 12,0, 0), plot=True, save_data=False)
tp_perc = 29
sl_perc = 7
==
Return [%]                          43.980268
Buy & Hold Return [%]              -56.152373


test 2
run_backtest('FlagCont', 'ETH-USD', timeframe='1h', start_time=datetime(2020, 1, 1, 12,0, 0), plot=True, save_data=False)


** remember to put in bootcamp folder
'''