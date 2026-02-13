############## Coding SMA Indicator 2024

################### Coding Risk Management

import ccxt
import key_file as k
import time , schedule 
import pandas as pd 

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': k.xP_KEY,
    'secret': k.xP_SECRET
})

symbol = 'uBTCUSD'
size = 1 
bid = 29000
params = {'timeInForce': 'PostOnly',}

# open positions
def open_positions(symbol=symbol):

    # what is the position index for that symbol?
    if symbol == 'uBTCUSD':
        index_pos = 4
    elif symbol == 'APEUSD':
        index_pos = 2
    elif symbol == 'ETHUSD':
        index_pos = 3
    elif symbol == 'DOGEUSD':
        index_pos = 1
    elif symbol == 'u100000SHIBUSD':
        index_pos = 0
    else:
        index_pos = None 

    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    open_positions = phe_bal['info']['data']['positions']
    #print(open_positions)

# dictionaries 
    openpos_side = open_positions[index_pos]['side'] # btc [3] [0] = doge, [1] ape
    openpos_size = open_positions[index_pos]['size']
    #print(open_positions)

# if statements 
    if openpos_side == ('Buy'):
        openpos_bool = True 
        long = True 
    elif openpos_side == ('Sell'):
        openpos_bool = True
        long = False
    else:
        openpos_bool = False
        long = None 

    print(f'open_positions... | openpos_bool {openpos_bool} | openpos_size {openpos_size} | long {long} | index_pos {index_pos}')

# returning
    return open_positions, openpos_bool, openpos_size, long, index_pos
   
# ask_bid 
def ask_bid(symbol=symbol):

    ob = phemex.fetch_order_book(symbol)
    #print(ob)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

# f literal
    print(f'this is the ask for {symbol} {ask}')

    return ask, bid # ask_bid()[0] = ask , [1] = bid

# kill switch

def kill_switch(symbol=symbol):

    print(f'starting the kill switch for {symbol}')
    openposi = open_positions(symbol)[1] # true or false
    long = open_positions(symbol)[3]# t or false
    kill_size = open_positions(symbol)[2] # size thats open  

    print(f'openposi {openposi}, long {long}, size {kill_size}')

    while openposi == True:

        print('starting kill switch loop til limit fil..')
        temp_df = pd.DataFrame()
        print('just made a temp df')

        phemex.cancel_all_orders(symbol)
        openposi = open_positions(symbol)[1]
        long = open_positions(symbol)[3]#t or false
        kill_size = open_positions(symbol)[2]
        kill_size = int(kill_size)
        
        ask = ask_bid(symbol)[0]
        bid = ask_bid(symbol)[1]

        if long == False:
            phemex.create_limit_buy_order(symbol, kill_size, bid, params)
            print(f'just made a BUY to CLOSE order of {kill_size} {symbol} at ${bid}')
            print('sleeping for 30 seconds to see if it fills..')
            time.sleep(30)
        elif long == True:
            phemex.create_limit_sell_order(symbol, kill_size, ask,params )
            print(f'just made a SELL to CLOSE order of {kill_size} {symbol} at ${ask}')
            print('sleeping for 30 seconds to see if it fills..')
            time.sleep(30)

        else:
            print('++++++ SOMETHING I DIDNT EXCEPT IN KILL SWITCH FUNCTION')

        openposi = open_positions(symbol)[1]

target = 9 
max_loss = -8
# pnl close
# pnl_close() [0] pnlclose and [1] in_pos [2]size [3]long TF
def pnl_close(symbol=symbol, target=target, max_loss=max_loss):

    print(f'checking to see if its time to exit for {symbol}... ')

    params = {'type':"swap", 'code':'USD'}
    pos_dict = phemex.fetch_positions(params=params)
    #print(pos_dict)

    index_pos = open_positions(symbol)[4]
    pos_dict = pos_dict[index_pos] # btc [3] [0] = doge, [1] ape
    side = pos_dict['side']
    size = pos_dict['contracts']
    entry_price = float(pos_dict['entryPrice'])
    leverage = float(pos_dict['leverage'])
# 34.38, int 893
    current_price = ask_bid(symbol)[1]

    print(f'side: {side} | entry_price: {entry_price} | lev: {leverage}')
    # short or long

    if side == 'long':
        diff = current_price - entry_price
        long = True
    else: 
        diff = entry_price - current_price
        long = False

# try /except 
    try: 
        perc = round(((diff/entry_price) * leverage), 10)
    except:
        perc = 0

    perc = 100*perc
    print(f'for {symbol} this is our PNL percentage: {(perc)}%')

    pnlclose = False 
    in_pos = False

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

        if perc <= max_loss: # under -55 , -5
            print(f'we need to exit now down {perc}... so starting the kill switch.. max loss {max_loss}')
            kill_switch(symbol)
        else:
            print(f'we are in a losing position of {perc}.. but chillen cause max loss is {max_loss}')

    else:
        print('we are not in position')

    print(f' for {symbol} just finished checking PNL close..')

    return pnlclose, in_pos, size, long


# size kill 
def size_kill():

    max_risk = 1000

    params = {'type':"swap", "code": "USD"}
    all_phe_balance = phemex.fetch_balance(params=params)
    open_positions = all_phe_balance['info']['data']['positions']
    #print(open_positions)

    try:
        pos_cost = open_positions[0]['posCost']
        pos_cost = float(pos_cost)
        openpos_side = open_positions[0]['side']
        openpos_size = open_positions[0]['size']
    except:
        pos_cost = 0
        openpos_side = 0
        openpos_size = 0
    print(f'position cost: {pos_cost}')
    print(f'openpos_side : {openpos_side}')

    if pos_cost > max_risk:

        print(f'EMERGENCY KILL SWITCH ACTIVATED DUE TO CURRENT POSITION SIZE OF {pos_cost} OVER MAX RISK OF: {max_risk}')
        kill_switch(symbol) # just calling the kill switch cause the code below is long
        time.sleep(30000)
    else:
        print(f'size kill check: current position cost is: {pos_cost} we are gucci')

timeframe = '15m'
limit = 100
sma = 20 

def df_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):

    print('starting indis...')

    bars = phemex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    #print(bars)
# pandas
    df_sma = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_sma['timestamp'] = pd.to_datetime(df_sma['timestamp'], unit='ms')

    # DAILY SMA - 20 day
    df_sma[f'sma{sma}_{timeframe}'] = df_sma.close.rolling(sma).mean()

    # if bid < the 20 day sma then = BEARISH, if bid > 20 day sma = BULLISH
    bid = ask_bid(symbol)[1]
    
    # if sma > bid = SELL, if sma < bid = BUY
    df_sma.loc[df_sma[f'sma{sma}_{timeframe}']>bid, 'sig'] = 'SELL'
    df_sma.loc[df_sma[f'sma{sma}_{timeframe}']<bid, 'sig'] = 'BUY'

    df_sma['support'] = df_sma[:-1]['close'].min()
    df_sma['resis'] = df_sma[:-1]['close'].max()

    print(df_sma)

    return df_sma

df_sma()