'''
this is a backtest of the liquidity grab strategy
you can edit things in the strat file

1st run - 10 sl,10 tp == 10% in 2022
2nd run - 5 sl,10 tp == .52%  
3rd run - 10 sl, 20 tp == 10%

now testing the 15min from 2020

'''


from backtesting import Backtest

from strat import *
from dataset import get_candles_since_date
from datetime import datetime,timedelta


def run_backtest(stratName,symbol,start_time,timeframe,plot=True,save_data=True):

    candles = get_candles_since_date(symbol,timeframe=timeframe,start_time=start_time,save_data=save_data) #get the historical candles data
    candles = candles.loc[:datetime.now().replace(hour=0,minute=0,second=0,microsecond=0) - timedelta(seconds=1)]
    candles.columns = ['Open', 'High', 'Low', 'Close','Volume'] #reset the column names to fit format for backtrading

    
    bt = Backtest(candles, eval(stratName),
                cash=5000000, commission=.001) #create a backtest object

    output = bt.run() #run the backtest and store the results as a variable
    print(output) #print the results

    if plot:
        bt.plot(resample=False) #resample = False to show all original candles instead of merging to a higher timeframe


run_backtest('LiquidityGrab','ETH-USD',start_time=datetime(year=2021,month=1,day=4,hour=0,minute=0,second=0),timeframe='15m',plot=True,save_data=False)