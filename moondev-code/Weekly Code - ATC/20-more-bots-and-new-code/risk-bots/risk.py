'''
RISK FILE - will continue to add to over time but essentially is 
different functions to help monitor my trades

as always, use at your own risk* 

'''

import ccxt 
import pandas as pd
#import dontshare_config 
import xconfig
import time, schedule
from datetime import datetime 
import warnings
warnings.filterwarnings("ignore")

############### INPUTS #####################
symbol = 'uBTCUSD'
### INPUTS ###
target = 59
max_loss = -39 # if needed can increase this
#############################################

# JM ACCOUNT
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '',
    'secret': '', 
})




def last_trade_check(symbol=symbol): # PASS IN SYMBOL
    '''
    this will look at the last trade close and if it is in a timeframe
    that we dont want to trade, then it wont trade that symbol
    ex. if input is 30 mins, we can use function to look at the sym
    for the last 30 mins and if it shows a closed trade in time
    dont trade
    '''

    no_trade_time = 30 # 30 minutes from last close, no trade
    no_trade_secs = no_trade_time * 60 

    # get time 
    now = datetime.now()
    dt_string = now.strftime('%m/%d/%Y %H:%M:%S')
    #print(dt_string)
    comptime = int(time.time())
    comptime = comptime 
    print(comptime)

    closed = phemex.fetch_closed_orders(symbol)
    closed_df = pd.DataFrame.from_dict(closed)
    closed_df = closed_df[['filled', 'lastTradeTimestamp']]
    #print(closed_df)

    last_close_time_df = closed_df.loc[closed_df['filled']>0, 'lastTradeTimestamp']
    last_close_list = last_close_time_df.tolist()
    #print(last_close_list)

    last_close_time = last_close_list[-1]
    #print(f'this is the last closed time for {symbol} {last_close_time}')

    last_close_time = int(last_close_time/1000)
    print(last_close_time)

    comp_minus_notradesecs = comptime - no_trade_secs
    print(comp_minus_notradesecs)

    if comp_minus_notradesecs < last_close_time:
        print(f'we should not open a new order cause we closed an order in last {no_trade_time} mins')
        no_trade_time = True
    else:
        print(f'continue with placing orders bc the last trade was more than {no_trade_time} mins')
        no_trade_time = False


    # look at eth then look at btc... 
    # check pnl close... will close if target hit or DD
    # implement into all bots: last_trade_check(symbol)
        # itll loop thru and return t/f
        # implement if no_trade_time = True, just continue to kill loop
            # if false, continue 

 
    return no_trade_time # this will return a t/f

def pos_info(symbol=symbol):

    '''
    this function gets the position info we need to trade. for some reason it switches between
    position 0 and 1 on the output
    '''

    params = {'type':'swap', 'code':'USD'}

    balance = phemex.fetch_balance(params=params)
    open_positions = balance['info']['data']['positions']

    pos_df = pd.DataFrame.from_dict(open_positions)



    pos_cost = pos_df.loc[pos_df['symbol']==symbol, 'posCost'].values[0]
    side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]
    pos_cost = float(pos_cost)
    pos_size = pos_df.loc[pos_df['symbol']==symbol, 'size'].values[0]
    size = float(pos_size)
    entryPrice = pos_df.loc[pos_df['symbol']==symbol, 'avgEntryPrice'].values[0]
    entry_price = float(entryPrice)
    leverage = pos_df.loc[pos_df['symbol']==symbol, 'leverage'].values[0]
    leverage = float(leverage)




    print(f'symbol: {symbol} side: {side} lev: {leverage} size: {size} entry: {entry_price}')

    return pos_cost, side, size, entry_price, leverage # pos_info() pos_cost, side, size, entry_price, leverage


def open_positions(symbol=symbol):

    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    open_positions = phe_bal['info']['data']['positions']
    #print(open_positions)

    balance = phemex.fetch_balance(params)
    open_positions = balance['info']['data']['positions']

    pos_df = pd.DataFrame.from_dict(open_positions)
    
## THIS GETS DATA FROM POS DICT DF
    side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]
    #  side = pos_df.loc[pos_df['symbol']==symbol, 'side'][0]
    leverage = pos_df.loc[pos_df['symbol']==symbol, 'leverage'].values[0]
    leverage = float(leverage)
    size = pos_df.loc[pos_df['symbol']==symbol, 'size'].values[0]
    size = float(size)
    entryPrice = pos_df.loc[pos_df['symbol']==symbol, 'avgEntryPrice'].values[0]
    entry_price = float(entryPrice)

    if side == ('Buy'):
        openpos_bool = True 
        long = True 
    elif side == ('Sell'):
        openpos_bool = True
        long = False
    else:
        openpos_bool = False
        long = None 

    print(f'open_positions... | openpos_bool {openpos_bool} | openpos_size {size} | long {long}')

    return open_positions, openpos_bool, size, long,  phe_bal
    

#NOTE - i marked out 2 orders belwo and the cancel, need to unmark before live
# returns: kill_switch() nothing
# kill_switch: pass in (symbol) if no symbol just uses default
def kill_switch(symbol=symbol):

    print(f'starting the kill switch for {symbol}')
    openposi = open_positions(symbol)[1] # true or false
    long = open_positions(symbol)[3]# t or false
    kill_size = open_positions(symbol)[2] # size thats open  

    print(f'openposi {openposi}, long {long}, size {kill_size}')

    while openposi == True:

        print('starting kill switch loop til limit fil..')
        temp_df = pd.DataFrame()
        #print('just made a temp df')

        phemex.cancel_all_orders(symbol)
        openposi = open_positions(symbol)[1]
        long = open_positions(symbol)[3]#t or false
        kill_size = open_positions(symbol)[2]
        kill_size = int(kill_size)

        ob = phemex.fetch_order_book(symbol)
    #print(ob)

        bid = ob['bids'][0][0]
        ask = ob['asks'][0][0]

        params = {'timeInForce': 'PostOnly',}
        
        if long == False:
            #phemex.create_limit_buy_order(symbol, kill_size, bid, params)
            phemex.create_market_buy_order(symbol, kill_size)
            print(f'just made a BUY to CLOSE order of {kill_size} {symbol} at ${bid}')
            print('sleeping for 30 seconds to see if it fills..')
            time.sleep(30)
        elif long == True:
            #phemex.create_limit_sell_order(symbol, kill_size, ask,params )
            phemex.create_market_sell_order(symbol, kill_size)
            print(f'just made a SELL to CLOSE order of {kill_size} {symbol} at ${ask}')
            print('sleeping for 30 seconds to see if it fills..')
            time.sleep(30)
        else:
            print('++++++ SOMETHING I DIDNT EXCEPT IN KILL SWITCH FUNCTION')

        openposi = open_positions(symbol)[1]


def pnl_close(symbol=symbol):

    print(symbol)

    '''
    this is the first thing we check every loop of any algo 
    its gonna look for the DD max, and also the Winning %
    ex. if max dd is 5% and we hit that amount - it would clsose
    same for pnl if hits target if 10% close
    '''

    # pos_info() pos_cost, side, size, entry_price, leverage
    posinfo = pos_info(symbol)
    pos_cost = posinfo[0]
    side = posinfo[1]
    size = posinfo[2]
    entry_price = posinfo[3]
    leverage = posinfo[4]


# GET ASK BID
    ob = phemex.fetch_order_book(symbol)
    #print(ob)

    current_price = ob['bids'][0][0]

    print(f'this is the price for {symbol} {current_price}')

    if side == 'Buy':
        diff = current_price - entry_price
        long = True
    else: 
        diff = entry_price - current_price
        long = False

    #print(f'this is the diff {diff}')

# incase lev == 0 we dont multiply by lev cause it will * by 0 -> 0
    if leverage != 0:
        try: 
            perc = (diff/entry_price) * leverage
            #print('hiiiii')
        except:
            perc = 0
    else:
        try:
            perc = diff/entry_price
        except:
            perc = 0

    perc = 100*perc
    print(f'for {symbol} this is our PNL percentage: {(perc)}%')

    pnlclose = False 
    in_pos = False

### CHECKING TO SEE IF HIT TARGET OR ML 
    if perc > 0:
        in_pos = True
        print(f'for {symbol} we are in a winning postion')
        if perc > target:
            print(':) :) we are in profit & hit target.. checking volume to see if we should start kill switch')
            pnlclose = True
            kill_switch(symbol)
        else:
            print('we have not hit our target yet')

    elif perc < 0: # -10, -20, 
        
        in_pos = True

        if perc <= max_loss: # under -55 , -56
            print(f'we need to exit now down {perc}... so starting the kill switch.. max loss {max_loss}')
            kill_switch(symbol)
        else:
            print(f'we are in a losing position of {perc}.. but chillen cause max loss is {max_loss}')

    else:
        print('we are not in position')

    
    return pnlclose, in_pos, long 



def size_kill(symbol=symbol):

    '''
    max pos size should be 1000 so if ever over 1100 close position
    '''

    max_risk = 1100

    #print('starting size check...')

    # pos_info() pos_cost, side, size, entry_price, leverage
    posinfo = pos_info(symbol)
    pos_cost = posinfo[0]
    side = posinfo[1]
    size = posinfo[2]
    entry_price = posinfo[3]
    leverage = posinfo[4]
        

    if pos_cost > max_risk:

        print(f'_______EMERGENCY KILL SWITCH______ MAX RISK TO HIGH FOR {symbol} size: {pos_cost}')

        phemex.cancel_all_orders(symbol)
        phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
        print('just canceled all orders and conditional orders..')

        if side == 'Sell':
            phemex.create_market_buy_order(symbol, size, params={"reduceOnly":True})
            print('just closed order with a market buy cuz we were short.. sleeping 72 hours to see whatsup')
            time.sleep(260000)
        elif side == 'Buy':
            phemex.create_market_sell_order(symbol, size, params={"reduceOnly":True})
            print('just closed order with a market sell cuz we were long.. sleeping 72 hours to see whatsup')
            time.sleep(260000)
        else:
            print('*** No open order to market so nothing submitted')
    else:
        print(f'size kill check: current position {symbol} cost: {pos_cost} we are gucci')



def risk_bot():

    # get all open symbols
    params = {'type':'swap', 'code':'USD'}
    balance = phemex.fetch_balance(params)
    open_positions = balance['info']['data']['positions']
    pos_df = pd.DataFrame.from_dict(open_positions)

    # active_df = pos_df[pos_df.size != '0']
    active_df = pos_df[pos_df["size"] != '0']
    open_symbols = active_df['symbol'].tolist()
    print(f'these are the open symbols: {open_symbols}')

    # loop through each symbol
    for sym in open_symbols:

        # check pnl close
        pnl_close(sym)

        # check size kill 
        size_kill(sym)

        # check the account loss kill 

        print('')
        print('----')
        

# risk_bot()



schedule.every(15).seconds.do(risk_bot) 

# CONTINUOUSLY RUN THIS BOT 
while True:

    try:
        schedule.run_pending() 
        time.sleep(15)
    except:
        print('error... sleeping 30 and retrying')
        time.sleep(30)



