import ccxt, config, time, schedule, cbpro
from functions import *


coinbase = cbpro.PublicClient()
 
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '',
    'secret': ''
})



#config settings for bot
timeframe = 900 #tiemframe of candles in seconds (5min would be 300, 15min would be 900, etc.)
dataRange = 20 #amount of candles to get
sl_percent = .2 #percent to take loss on trades
tp_percent = .25 #percent to take profit on trades
size = 1 #set amount to buy
params = {'timeInForce': 'PostOnly','takeProfit':0,'stopLoss':0} #set default tp and sl, will be changed when an order is about to be placed
symbol = 'ETH-USD'
alt_coins = ['ADAUSD', 'DOTUSD', 'MANAUSD', 'XRPUSD', 'UNIUSD', 'SOLUSD']






def bot():
    price = float(coinbase.get_product_ticker(symbol)['bid']) #get the current bid
    candles = get_candle_df(coinbase,symbol,timeframe,dataRange) #get candles dataframe

    #calculate our signals
    trange = calc_tr(candles)
    support,resistance = calc_sup_res(candles,dataRange)



    #if price goes above the true range or resistance
    if price > candles.close.iloc[-1]+trange or price > resistance:
        #get the current prices for the alt coins
        coinData = {}
        for coin in alt_coins:
            cur_price = float(phemex.fetch_ticker(coin)['bid']) #get coins current price
            coinData[coin] = (abs(cur_price - candles.close.iloc[-1]) / candles.close.iloc[-1]) * 100.0 #get percentage change from last candle

        most_lagging = min(coinData, key=coinData.get) #get the coin with the min change
        
        params['stopLoss'] = price * (1-(sl_percent/100)) #set stop loss price
        params['takeProfit'] = price * (1+(tp_percent/100)) #set take profit price
        order = phemex.create_limit_buy_order(symbol, size, price=price, params=params) #place order




    #if price goes below the true range or support
    elif price < candles.close.iloc[-1]-trange or price < support:
        #get the current prices for the alt coins
        coinData = {}
        for coin in alt_coins:
            cur_price = float(phemex.fetch_ticker(coin)['bid']) #get coins current price
            coinData[coin] = (abs(cur_price - candles.close.iloc[-1]) / candles.close.iloc[-1]) * 100.0 #get percentage change from last candle

        most_lagging = min(coinData, key=coinData.get) #get the coin with the min change
        
        params['stopLoss'] = price * (1+(sl_percent/100)) #set stop loss price
        params['takeProfit'] = price * (1-(tp_percent/100)) #set take profit price
        order = phemex.create_limit_sell_order(symbol, size, price=price, params=params) #place order



#run the bot every 20 seconds
schedule.every(20).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
        time.sleep(30)