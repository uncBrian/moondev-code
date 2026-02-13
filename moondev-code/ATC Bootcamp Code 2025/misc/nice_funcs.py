# a bunch of nice functions to have in 2024


import ccxt
import json 
import pandas as pd 
import numpy as np
import dontshare_config as ds 
from datetime import date, datetime, timezone, tzinfo
import time, schedule

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '', 
    'secret': ''})

symbol = 'APEUSD'
index_pos = 1 # CHANGE BASED ON WHAT ASSET

# the time between trades
pause_time = 60

# for volume calc Vol_repeat * vol_time == TIME of volume collection
vol_repeat=11
vol_time=5

pos_size = 100 # 125, 75, 
params = {'timeInForce': 'PostOnly',}
target = 35
max_loss = -55
vol_decimal = .4

# for df 
timeframe = '4h'
limit = 100
sma = 20

# ask_bid()[0] = ask , [1] = bid
# ask_bid(symbol) if none given then its default
def ask_bid(symbol=symbol):

    ob = phemex.fetch_order_book(symbol)
    #print(ob)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

    print(f'this is the ask for {symbol} {ask}')

    return ask, bid # ask_bid()[0] = ask , [1] = bid

# returns: df_sma with sma (can customize with below)
# call: df_sma(symbol, timeframe, limit, sma) # if not passed, uses default
def df_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):

    print('starting indis...')

    bars = phemex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    #print(bars)
    df_sma = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_sma['timestamp'] = pd.to_datetime(df_sma['timestamp'], unit='ms')

    # DAILY SMA - 20 day
    df_sma[f'sma{sma}_{timeframe}'] = df_sma.close.rolling(sma).mean()

    # if bid < the 20 day sma then = BEARISH, if bid > 20 day sma = BULLISH
    bid = ask_bid(symbol)[1]
    
    # if sma > bid = SELL, if sma < bid = BUY
    df_sma.loc[df_sma[f'sma{sma}_{timeframe}']>bid, 'sig'] = 'SELL'
    df_sma.loc[df_sma[f'sma{sma}_{timeframe}']<bid, 'sig'] = 'BUY'

    df_sma['support'] = df_sma[:-2]['close'].min()
    df_sma['resis'] = df_sma[:-2]['close'].max()

    
    df_sma['PC'] = df_sma['close'].shift(1)


    # last close Bigger than Previous close
    # going to add this to order to ensure we only open
    # order on reversal confirmation
    df_sma.loc[df_sma['close']>df_sma['PC'], 'lcBpc'] = True
                # 2.981       > 2.966 == True
    df_sma.loc[df_sma['close']<df_sma['PC'], 'lcBpc'] = False
                # 2.980       < 2.981 == False
                # 2.966       < 2.967 == False



    return df_sma

    

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
        index_pos = None # just break it... 

    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    open_positions = phe_bal['info']['data']['positions']
    #print(open_positions)

    openpos_side = open_positions[index_pos]['side'] # btc [3] [0] = doge, [1] ape
    openpos_size = open_positions[index_pos]['size']
    #print(open_positions)

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

    return open_positions, openpos_bool, openpos_size, long, index_pos, phe_bal
    
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

# returns nothin 
# sleep_on_close(symbol=symbol, pause_time=pause_time) # pause in mins
def sleep_on_close(symbol=symbol, pause_time=pause_time):

    '''
    this func pulls closed orders, then if last close was in last 59min
    then it sleeps for 1m
    sincelasttrade = mintutes since last trade
    '''

    closed_orders = phemex.fetch_closed_orders(symbol)
    #print(closed_orders)

    for ord in closed_orders[-1::-1]:

        sincelasttrade = pause_time - 1 # how long we pause

        filled = False 

        status = ord['info']['ordStatus']
        txttime = ord['info']['transactTimeNs']
        txttime = int(txttime)
        txttime = round((txttime/1000000000)) # bc in nanoseconds
        print(f'for {symbol} is the status of the order {status} with epoch {txttime}')
        print('next iteration...')
        print('------')

        if status == 'Filled':
            print('FOUND the order with last fill..')
            print(f'for {symbol} this is the time {txttime} this is the orderstatus {status}')
            orderbook = phemex.fetch_order_book(symbol)
            ex_timestamp = orderbook['timestamp'] # in ms 
            ex_timestamp = int(ex_timestamp/1000)
            print('---- below is the transaction time then exchange epoch time')
            #print(txttime)
            #print(ex_timestamp)

            time_spread = (ex_timestamp - txttime)/60

            if time_spread < sincelasttrade:
                # print('time since last trade is less than time spread')
                # # if in pos is true, put a close order here
                # if in_pos == True:

                sleepy = round(sincelasttrade-time_spread)*60
                sleepy_min = sleepy/60

                print(f'the time spead is less than {sincelasttrade} mins its been {time_spread}mins.. so we SLEEPING for 60 secs..')
                time.sleep(60)

            else:
                print(f'its been {time_spread} mins since last fill so not sleeping cuz since last trade is {sincelasttrade}')
            break 
        else:
            continue 

    print(f'done with the sleep on close function for {symbol}.. ')

def ob(symbol=symbol, vol_repeat=vol_repeat, vol_time=vol_time ):

    print(f'fetching order book data for {symbol}... ')

    df = pd.DataFrame()
    temp_df = pd.DataFrame()

    ob = phemex.fetch_order_book(symbol)
    #print(ob)
    bids = ob['bids']
    asks = ob['asks']

    first_bid = bids[0]
    first_ask = asks[0]

    bid_vol_list = []
    ask_vol_list = []

    # if SELL vol > Buy vol AND profit target hit, exit

    # get last 1 min of volume.. and if sell > buy vol do x 

# TODO - make range a var 
# repeat == the amount of times it go thru the vol process, and multiplues
# by repeat_time to calc the time 
    for x in range(vol_repeat):

        for set in bids:
        #print(set)
            price = set[0]
            vol = set[1]
            bid_vol_list.append(vol)
            # print(price)
            # print(vol)

            #print(bid_vol_list)
            sum_bidvol = sum(bid_vol_list)
            #print(sum_bidvol)
            temp_df['bid_vol'] = [sum_bidvol]

        for set in asks:
            #print(set)
            price = set[0] # [40000, 344]
            vol = set[1]
            ask_vol_list.append(vol)
            # print(price)
            # print(vol)

            sum_askvol = sum(ask_vol_list)
            temp_df['ask_vol'] = [sum_askvol]

        #print(temp_df)
# TODO - change sleep to var
        time.sleep(vol_time) # change back to 5 later
        df = df.append(temp_df)
        print(df)
        print(' ')
        print('------')
        print(' ')
    print(f'done collecting volume data for bids and asks.. ')
    print('calculating the sums...')
    total_bidvol = df['bid_vol'].sum()
    total_askvol = df['ask_vol'].sum()
    seconds = vol_time * vol_repeat
    mins = round(seconds / 60, 2)
    print(f'last {mins}mins for {symbol} this is total Bid Vol: {total_bidvol} | ask vol: {total_askvol}')

    if total_bidvol > total_askvol:
        control_dec = (total_askvol/total_bidvol )
        print(f'Bulls are in control: {control_dec}...')
        # if bulls are in control, use regular target
        bullish = True
    else:
        
        control_dec = (total_bidvol / total_askvol)
        print(f'Bears are in control: {control_dec}...')
        bullish = False
    
    # open_positions() open_positions, openpos_bool, openpos_size, long

    open_posi = open_positions(symbol)
    openpos_tf = open_posi[1]
    long = open_posi[3]
    print(f'openpos_tf: {openpos_tf} || long: {long}')

    # if target is hit, check book vol
    # if book vol is < .4.. stay in pos... sleep?
    # need to check to see if long or short

    if openpos_tf == True:
        if long == True:
            print('we are in a long position...')
            if control_dec < vol_decimal: # vol_decimal set to .4 at top
                vol_under_dec = True
                #print('going to sleep for a minute.. cuz under vol decimal')
                #time.sleep(6) # change to 60
            else:
                print('volume is not under dec so setting vol_under_dec to False')
                vol_under_dec = False
        else:
            print('we are in a short position...')
            if control_dec < vol_decimal: # vol_decimal set to .4 at top
                vol_under_dec = True
                #print('going to sleep for a minute.. cuz under vol decimal')
                #time.sleep(6) # change to 60
            else:
                print('volume is not under dec so setting vol_under_dec to False')
                vol_under_dec = False
    else:
        print('we are not in position...')
        vol_under_dec = None

    # when vol_under_dec == FALSE AND target hit, then exit
    print(vol_under_dec) # BUG

    return vol_under_dec

# pnl_close() [0] pnlclose and [1] in_pos [2]size [3]long TF
# takes in symbol, target, max loss
def pnl_close(symbol=symbol, target=target, max_loss=max_loss ):

#     target = 35
# max_loss = -55

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

    current_price = ask_bid(symbol)[1]

    print(f'side: {side} | entry_price: {entry_price} | lev: {leverage}')
    # short or long

    if side == 'long':
        diff = current_price - entry_price
        long = True
    else: 
        diff = entry_price - current_price
        long = False

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
            vol_under_dec = ob(symbol) # return TF
            if vol_under_dec == True:
                print(f'volume is under the decimal threshold we set of {vol_decimal}.. so sleeping 30s')
                time.sleep(30)
            else:
                print(f':) :) :) starting the kill switch because we hit our target of {target}% and already checked vol...')
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

    if in_pos == True:

        #if breaks over .8% over 15m sma, then close pos (STOP LOSS)

        # pull in 15m sma
        #call: df_sma(symbol, timeframe, limit, sma)
        timeframe = '15m'
        df_f = df_sma(symbol, timeframe, 100, 20)
        
        #print(df_f)
        #df_f['sma20_15'] # last value of this
        last_sma15 = df_f.iloc[-1][f'sma{sma}_{timeframe}']
        last_sma15 = int(last_sma15)
        #print(last_sma15)
        # pull current bid
        curr_bid = ask_bid(symbol)[1]
        curr_bid = int(curr_bid)
        #print(curr_bid)

        sl_val = last_sma15 * 1.008
        #print(sl_val)

    else:
        print('we are not in position.. ')
    



    print(f' for {symbol} just finished checking PNL close..')

    return pnlclose, in_pos, size, long

#open_positions() open_positions, openpos_bool, openpos_size, long, index_pos
