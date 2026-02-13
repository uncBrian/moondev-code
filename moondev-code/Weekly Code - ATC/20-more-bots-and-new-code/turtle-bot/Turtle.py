from os import openpty
import ccxt, config, time, schedule 
from functions import *


'''
create 'config.py' to store phemex_key and phemex_secret 
'''

#connect to the phemex exchange
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': config.phemex_key,
    'secret': config.phemex_secret
})


#config settings for bot
timeframe = '1m' #use m for minutes and h for hours, EX. 1m (1 minute) or 4h (4 hour)
symbol = 'ETHUSD'
size = 1
params = {'timeInForce': 'PostOnly'}
take_profit_percent = .2



def bot():

    if in_timeframe():

        position_info,in_position,long = get_position(phemex,symbol) #get your current position in the market
        candles = get_candle_df(phemex,symbol,timeframe) #get the last 55 candle data for the timeframe
        ticker = phemex.fetch_ticker(symbol) #get ticker data
        bid = ticker['bid']
        openPrice = ticker['open']


        if not in_position:

            #get the min and max prices over the 55 candle period
            minPrice = candles['low'].min()
            maxPrice = candles['high'].max()


            #if the 55 candle low is crossed under
            if bid <= minPrice and openPrice > minPrice :
                order = phemex.create_limit_sell_order(symbol, size, price=bid, params=params)

            #if the 55 candle high is crossed over
            elif bid >= maxPrice and openPrice < maxPrice:
                order = phemex.create_limit_buy_order(symbol, size, price=bid, params=params)



        elif in_position:

            #add the ATR to the candles dataframe (column named ATR)
            calc_atr(candles)
            
                
            #CALCULATE PRICES TO TAKE PROFIT AND LOSS AT
                #take profit formula: entry price * ( 1 + take_profit_percent(in decimal form) )  (would be - instead of + for a short)
                #stop loss formula: entry price - (ATR*2)  (would be + instead of - for a short)
            take_profit_price = float(position_info['avgEntryPrice']) * (1+(take_profit_percent/100))   if long else   float(position_info['avgEntryPrice']) * (1-(take_profit_percent/100))
            stop_loss_price = float(position_info['avgEntryPrice']) - (candles['ATR'].iloc[-1]*2)   if long else   float(position_info['avgEntryPrice']) + (candles['ATR'].iloc[-1]*2)
                
            #if the take profit or stop loss is reached close the position
            if hit_target(bid,take_profit_price,stop_loss_price,long):
                close_position(phemex,symbol)



    #if past 4pm est on a friday close all positions
    elif end_of_trading_week():
        close_position(phemex,symbol)



#run the bot every 60 seconds
schedule.every(20).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
        time.sleep(30)