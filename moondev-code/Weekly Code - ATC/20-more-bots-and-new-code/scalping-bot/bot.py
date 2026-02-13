import ccxt, config, time, schedule 
from functions import *


'''
create 'config.py' to store phemex_key and phemex_secret variables 
'''

#connect to the phemex exchange
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': config.phemex_key,
    'secret': config.phemex_secret
})



#config settings for bot
timeframe = '5m' #use m for minutes and h for hours, EX. 1m (1 minute) or 4h (4 hour)
symbol = 'ETHUSD'
size = 1 #set amount to buy
vwma_percent = .04 #set the percentage deviance from vwma to buy/sell
sl_percent = .08 #percent to take loss on trades
tp_percent = .1 #percent to take profit on trades
params = {'timeInForce': 'PostOnly','takeProfit':0,'stopLoss':0} #set default tp and sl, will be changed when an order is about to be placed


#enable/disable close conditions
tr_close = input('would you like to close if price has drop 2n from the entry price (2 x ATR)? (y or n)\n')
tr_close = True if tr_close == 'y' else False
candle_extreme_close = input('would you like to close if a new low/high has been made? (y or n)\n')
candle_extreme_close = True if candle_extreme_close == 'y' else False

#choose side
side = input('would you like to buy or sell? (input b or s)\n')




def bot():
    position_info,in_position,long = get_position(phemex,symbol) #get your current position in the market
    candles = get_candle_df(phemex,symbol,timeframe) #get the candle data for the timeframe


    #run open conditions
    if not in_position:
        vwma = calc_vwma(candles) #calculate the vwma

        #create an order to buy vwma_percent below the current vwma with sl and tp
        if side == 'b':
            target_price = vwma-(vwma*(vwma_percent/100))
            params['stopLoss'] = target_price * (1-(sl_percent/100)) #set stop loss price
            params['takeProfit'] = target_price * (1+(tp_percent/100)) #set take profit price
            order = phemex.create_limit_buy_order(symbol, size, price=target_price, params=params)


        #create an order to sell vwma_percent above the current vwma with sl and tp
        elif side == 's':
            target_price = vwma+(vwma*(vwma_percent/100))
            params['stopLoss'] = target_price * (1+(sl_percent/100)) #set stop loss price
            params['takeProfit'] = target_price * (1-(tp_percent/100)) #set take profit price
            order = phemex.create_limit_sell_order(symbol, size, price=target_price, params=params)

    

    #run close conditions
    elif in_position:

        #run if true range close is on
            #close if price has dropped 2n from the entry price (2 x ATR)
        if tr_close:
            tr = calc_tr(candles) #calculate the true range
            entry_price = float(position_info['price']) #get the entry price of the position
            price = phemex.fetch_ticker(symbol)['bid'] #get the current bid

            if long:
                if (entry_price - (2*tr)) <= price:
                    close_position(phemex,symbol)

            else:
                if (entry_price + (2*tr)) >= price:
                    close_position(phemex,symbol)


        #run if candle extreme close is on
            #close if a new low in the last 10 bar period, if we are long. or a new high if shorting.
        if candle_extreme_close:
            end_df = candles.tail(11) #get last 10 candle range along with latest

            if long:
                if end_df.high.min() == end_df.high.iloc[-1]:
                    close_position(phemex,symbol)

            else:
                if end_df.high.max() == end_df.high.iloc[-1]:
                    close_position(phemex,symbol)




#run the bot every 20 seconds
schedule.every(20).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
        time.sleep(30)