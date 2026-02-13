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
limit = 20 #amount of candles to check
symbol = 'ETHUSD'
size = 1
tp_percent = .3 #set percent of take profit
sl_percent = .25 #set percent of take loss
params = {'timeInForce': 'PostOnly','takeProfit':0,'stopLoss':0} #set default tp and sl, will be changed when an order is about to be placed

# used to only trade in times of little movement. This value is the percent deviance from price of the true range,
# meaning that if the true range is within x percent away from the price it is considered consolidation
consolidation_percent = .7



def bot():

    position_info,in_position,long = get_position(phemex,symbol) #get your current position in the market
    candles = get_candle_df(phemex,symbol,timeframe,limit) #get the last 55 candle data for the timeframe
    tr = calc_tr(candles) #get the true range

    tr_deviance = (tr/candles.close.iloc[-1])*100 #get the percent deviation of the true range from the price

    
    #only look to create an order if we are not in a position already
    if not in_position:

        if tr_deviance < consolidation_percent:
            price = phemex.fetch_ticker(symbol)['bid'] #get the current bid
            low,high = get_extreme_of_consolidation(candles,consolidation_percent) #get the lowest and highest prices in the current consolidation

            #buy if price is in the lower 1/3 of the consolidation range
            if price <= ((high-low)/3)+low:
                params['stopLoss'] = price * (1-(sl_percent/100)) #set stop loss price
                params['takeProfit'] = price * (1+(tp_percent/100)) #set take profit price
                order = phemex.create_limit_buy_order(symbol, size, price=price, params=params)

            #sell if price is in the upper 1/3 of the consolidation range
            if price >= high-((high-low)/3):
                params['stopLoss'] = price * (1+(sl_percent/100)) #set stop loss price
                params['takeProfit'] = price * (1-(tp_percent/100)) #set take profit price
                order = phemex.create_limit_sell_order(symbol, size, price=price, params=params)


#run the bot every 20 seconds
schedule.every(20).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
        time.sleep(30)