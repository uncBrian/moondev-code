import ccxt, config, schedule 
from functions import *
import time 


'''
create 'config.py' to store phemex_key and phemex_secret variables

my notes- 
- bot in one file and functions in the other file
- uses the same functions as the turtle bot
- stoch rsi, nadarya are new here, is oversold, etc. 
... running this on the 1h time frame becayse in his video it showed 300%+
'''

#connect to the phemex exchange
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': config.xP_KEY,
    'secret': config.xP_SECRET
})


#config settings for bot
rsi_targets = [10,90] #set the overssold/overbought level in the stoch rsi
rsi_window = 14 #the n most recent amount of candles to check if stoch rsi suggest oversold/overbought
timeframe = '1h' #use m for minutes and h for hours, EX. 1m (1 minute) or 4h (4 hour)
symbol = 'ETHUSD'
size = 1000
params = {'timeInForce': 'PostOnly'}


def bot():

        position_info,in_position,long = get_position(phemex,symbol) #get your current position in the market
        candles = get_candle_df(phemex,symbol,timeframe) #get the last 55 candle data for the timeframe
        nadarya_buy_signal,nadarya_sell_signal = calc_nadarya(candles) #add the nadarya indicator to the candles dataframe, along with its buy and sell signal columns
        calc_stoch_rsi(candles) #add the stoch_rsi indicator as a column to the candles dataframe
        bid = phemex.fetch_ticker(symbol)['bid'] #get the current bid


        if not in_position:

            #place a long order if the nadarya indicator has said to buy OR if the stoch rsi indicator suggests it is oversold
            if nadarya_buy_signal or is_oversold(candles['stoch_rsi'],rsi_window,1,rsi_targets[0]):
                order = phemex.create_limit_buy_order(symbol, size, price=bid, params=params)

            #place a short order if the nadarya indicator has said to sell OR if the stoch rsi indicator suggests it is overbought
            elif nadarya_sell_signal or is_overbought(candles['stoch_rsi'],rsi_window,1,rsi_targets[1]):
                order = phemex.create_limit_sell_order(symbol, size, price=bid, params=params)
        


        elif in_position:

            # close the position if you are in a long and the nadarya indicator suggests a sell OR the stoch rsi has shown overbought twice already
            if long:
                if nadarya_sell_signal or is_overbought(candles['stoch_rsi'],rsi_window,times=2,target=rsi_targets[1]):
                    close_position(phemex,symbol)

            # close the position if you are in a short and the nadarya indicator suggests a buy OR the stoch rsi has shown oversold twice already
            else:
                if nadarya_buy_signal or is_oversold(candles['stoch_rsi'],rsi_window,times=2,target=rsi_targets[0]):
                    close_position(phemex,symbol)



#run the bot every 20 seconds
schedule.every(1).seconds.do(bot)

while True:
        try:
         schedule.run_pending()
     except:
         print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
         time.sleep(30)
