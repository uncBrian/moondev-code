############### Coding Algo Orders 2024

# connect to exchange.

import ccxt
import key_file as k
import time , schedule 

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': k.xP_KEY,
    'secret': k.xP_SECRET
})

bal = phemex.fetch_balance()

symbol = 'uBTCUSD'
size = 1 
bid = 29000
params = {'timeInForce': 'PostOnly',}

# making an order
# order = phemex.create_limit_buy_order(symbol, size, bid, params )
# print(order)

# cancel order
#phemex.cancel_all_orders(symbol)

# phemex.create_limit_buy_order(symbol, size, bid, params )

# # sleep 10 seconds
# print('just made the order now sleeping for 10s.. ')
# time.sleep(10)

# # cancel that order
# phemex.cancel_all_orders(symbol)

def bot():

    phemex.create_limit_buy_order(symbol, size, bid, params )

    time.sleep(5)

    phemex.cancel_all_orders(symbol)


schedule.every(2).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ MAYBE AN INTERNET PROB OR SOMETHING')
        time.sleep(30)

