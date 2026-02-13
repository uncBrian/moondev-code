'''
consolidation_pop 

as always, this will be long and short. i will explain the long case and we will 
just create the opposite for the short entries. essentially, we want to build a 
strategy that looks for consolidation (price moving sideways for a bit) on short 
time frames (1m, 3m, 5, 15, 1h) and it will buy the lows of that range with the 
expectation that it will Pop through the resistance at some point. 

most traders will be shorting the resistance, and we will be doing the opposite, 
longing the lows of the consolidation near resistance for a quick profit with 
the thought that price will atleast briefly crack resistance. 

the bid to buy in the lower 1/3rd of the consolidation and take profit 
at .3% and stop loss at .25%.

how long of consolidation are we looking for? please make this a variable and 
we can use 10 bars for now
'''

import ccxt, config, time, schedule 
from functions import *


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

# used to only trade in times of little movement. 
# This value is the percent deviance from price of the true range,
# meaning that if the true range is within x percent away 
# from the price it is considered consolidation
consolidation_percent = .7 # if tr is .7% of the price its considered consolidation


def bot():

    position_info,in_position,long = get_position(phemex,symbol) #get your current position in the market
    candles = get_candle_df(phemex,symbol,timeframe,limit) #get the last 55 candle data for the timeframe
    tr = calc_tr(candles) #get the true range

    # calc the deviance % from tr of lcose
    tr_deviance = (tr/candles.close.iloc[-1])*100 #get the percent deviation of the true range from the price

    #only look to create an order if we are not in a position already
    if not in_position:
        
        # if the tr_dev is smaller than our wanted one then we do the bot
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