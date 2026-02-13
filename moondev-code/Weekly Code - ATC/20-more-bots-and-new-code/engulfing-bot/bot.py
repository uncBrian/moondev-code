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
size = 1
tp_percent = .3 #set percent of take profit
params = {'timeInForce': 'PostOnly','takeProfit':0,'stopLoss':0} #set default tp and sl, will be changed when an order is about to be placed


def bot():

        position_info,in_position,long = get_position(phemex,symbol) #get your current position in the market
        candles = get_candle_df(phemex,symbol,timeframe,limit=40) #get the last 55 candle data for the timeframe
        sma = calc_sma(candles,length=20) #add sma column to candles df
        engulfing_pos,engulfing_neg = calc_engulfing(candles) #add engulfing columns to candles df
        bid = phemex.fetch_ticker(symbol)['bid'] #get the current bid


        #only look to create an order if we are not in a position already
        if not in_position:
            if bid > sma and engulfing_pos:
                openPrice = candles.iloc[-1]['open']
                params['stopLoss'] = candles.iloc[-2]['low']
                params['takeProfit'] = bid * (1+(tp_percent/100))
                order = phemex.create_limit_buy_order(symbol, size, price=openPrice, params=params)

            elif bid < sma and engulfing_neg:
                openPrice = candles.iloc[-1]['open']
                params['stopLoss'] = candles.iloc[-2]['high']
                params['takeProfit'] = bid * (1-(tp_percent/100))
                order = phemex.create_limit_sell_order(symbol, size, price=openPrice, params=params)


#run the bot every 20 seconds
schedule.every(20).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
        time.sleep(30)