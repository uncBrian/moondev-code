'''
this bot trades 75 different cryptos,
it looks for opportunities in each market,
it is set up with a mean reversion strategy 
makes decisions executes orders automatically.
get code & tutorials in bootcamp. link below 

- this bot has not been back tested. do not run live.
'''

import ccxt
import json 
import pandas as pd 
import numpy as np
import dontshare_config as ds 
from datetime import date, datetime, timezone, tzinfo
import time, schedule
import nice_funcs as n 
import random 

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '', 
    'secret': ''})

#symbol = 'uBTCUSD'
pos_size = 30
target = 9 # % gain i want 
max_loss = -8
leverage = 10
timeframe = '15m' # this is for sma creation
limit = 97 # also for sma creation 96 = 24hrs
sma = 20 

params = {'timeInForce': 'PostOnly',}

params = {'type':'swap', 'code':'USD', 'leverage': 5}
# fetch all the market to get all the symbols
markets = phemex.fetch_markets(params=params)

# all_symbols = pd.read_csv('phe_symbols.csv')

# random_symbol_pos = random.randrange(0,78)
# random_symbol = all_symbols.iloc[random_symbol_pos]['symbol']
# print(random_symbol)

# symbols = all_symbols['symbol'].values.tolist()
# symbol = random_symbol

symbol = 'uBTCUSD'

# CREATE SMA
# call: df_sma(symbol, timeframe, limit, sma)
#  # if not passed, uses default

def ask_bid(symbol=symbol):

    ob = phemex.fetch_order_book(symbol)
    #print(ob)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

    #print(f'this is the ask for {symbol} {ask}')

    return ask, bid # ask_bid()[0] = ask , [1] = bid

# open_positions() return active_symbols_list ,active_sym_df2
def open_positions(symbol=symbol):

    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    open_positions = phe_bal['info']['data']['positions']
    #print(open_positions)
    

    openpos_df = pd.DataFrame()
    openpos_df_temp = pd.DataFrame()
    for x in open_positions:
        sym = x['symbol']
        openpos_df_temp['symbol'] = [sym]

        openpos_df = openpos_df.append(openpos_df_temp)
    #print(openpos_df)
    
    active_symbols_list = openpos_df['symbol'].values.tolist()
    #print(active_symbols_list)

    active_sym_df = pd.DataFrame()
    active_sym_df_temp = pd.DataFrame()
    for symb in active_symbols_list:
        #print(symb)
        indexx = active_symbols_list.index(symb, 0, 100)
        active_sym_df_temp['symbol'] = [symb]
        active_sym_df_temp['index'] = [indexx]
        active_sym_df = active_sym_df.append\
                        (active_sym_df_temp)
    
    active_sym_df.to_csv('active_symbols.csv', index=False)
    # time.sleep(744)

    # if the symbol is showing in the df then store
    # the index position as index_pos

    #print(active_sym_df)

    # active_symbols_list & active_sym_df
    active_sym_df_t = pd.DataFrame()
    active_sym_df2 = pd.DataFrame()
    for x in active_symbols_list:
        index_pos = active_sym_df.loc[active_sym_df['symbol'] \
        == x, 'index']
        index_pos = int(index_pos[0])
        #print(f'***** {x} THIS SHOULD BE INDEX: {index_pos}')
        #time.sleep(7836)
        openpos_side = open_positions[index_pos]['side'] # btc [3] [0] = doge, [1] ape
        openpos_size = open_positions[index_pos]['size']
        #print(open_positions)
        active_sym_df_t['symbol'] = [x]
        active_sym_df_t['open_side'] = [openpos_side]
        active_sym_df_t['open_size'] = [openpos_size]
        active_sym_df_t['index_pos'] = [index_pos]
        


        if openpos_side == ('Buy'):
            openpos_bool = True 
            long = True 
            active_sym_df_t['open_bool'] = True
            active_sym_df_t['long'] = True
        elif openpos_side == ('Sell'):
            openpos_bool = True
            long = False
            active_sym_df_t['open_bool'] = True
            active_sym_df_t['long'] = False
        else:
            openpos_bool = False
            long = None 
            active_sym_df_t['open_bool'] = False
            active_sym_df_t['long'] = None

        active_sym_df2 = active_sym_df2.append(active_sym_df_t)
        #print(active_sym_df2)
        
        #print(f'open_position for {x}... | openpos_bool {openpos_bool} | openpos_size {openpos_size} | long {long} | index_pos {index_pos}')

    return active_symbols_list, active_sym_df2

# ge SWITCH FOR ALL POSITIONS
def kill_switch_all():

    print('starting kill switch all..')
 
    openpos = open_positions()
    active_symbols_list = openpos[0]
    df = openpos[1]
    df = df[df['open_bool']==True]
    print(df)
    openpos_list = df.values.tolist()
    print(openpos_list)

    ############ KILL SWITCH IN THIS LOOP
    
    for x in openpos_list:
        #print(f'starting the kill switch for {x}')
        sym = x[0]
        openposi = x[4] # true or false
        long = x[5]# t or false
        kill_size = x[2] # size thats open  

        #print(f'openposi {openposi}, long {long}, size {kill_size}')

        while openposi == True:

            

            #print(f'{sym} starting kill switch loop til limit fil..')

            phemex.cancel_all_orders(sym)
            kill_size = int(kill_size)
            
            ask = ask_bid(sym)[0]
            bid = ask_bid(sym)[1]

            if long == False:
                phemex.create_limit_buy_order(sym, kill_size, bid, params)
                print(f'** BUY to CLOSE - {sym}')
                #print('sleeping for 30 seconds to see if it fills..')
                #time.sleep(20)
            elif long == True:
                phemex.create_limit_sell_order(sym, kill_size, ask,params )
                print(f'** SELL to CLOSE - {sym}')
                #print('sleeping for 30 seconds to see if it fills..')
                #time.sleep(20)
            else:
                print('++++++ SOMETHING I DIDNT EXCEPT IN KILL SWITCH FUNCTION')
## COME BACK TO THIS
            #openposi = open_positions(x)[1]
            # re check if the position has been closed
            #print('sleeping 20 to see if it fills')
            time.sleep(10)
            openpos = open_positions()
            df = openpos[1]
            df = df[df['open_bool']==True]
            #print(df)
            openpos_list = df.values.tolist()
            #print(openpos_list)
            #if sym is in openpos_list = that sym still open
                # and openposi = True, so keep loopin
            openposi = any(sym in sublist for sublist \
                        in openpos_list)
            #print(f'************ {openpos}')
    #print('done with the kill switch for all positions!')

# MAKE KILL SWITCH FOR ONE POS
def kill_switch(symbol=symbol):

    #print(f'starting the kill switch for {symbol}')

    index_pos_df = open_positions(symbol)[1]
        # need to get LONG, Size
        # symbol open_side open_size  index_pos  open_bool  long
    openposi = index_pos_df.loc[index_pos_df['symbol']==symbol, 'open_bool'].iloc[0]
    long = index_pos_df.loc[index_pos_df['symbol']==symbol, 'long'].iloc[0]
    kill_size = index_pos_df.loc[index_pos_df['symbol']==symbol, 'open_size'].iloc[0]
    kill_size = int(kill_size) 

    #print(f'openposi {openposi}, long {long}, size {kill_size}')

    while openposi == True:

        #print('starting kill switch loop til limit fil..')

        phemex.cancel_all_orders(symbol)
        # open_positions() return active_symbols_list ,active_sym_df2
        #index_pos = index_pos_df.loc[index_pos_df['symbol']==symbol, 'index_pos'].iloc[0]
        index_pos_df = open_positions(symbol)[1]
        # need to get LONG, Size
        # symbol open_side open_size  index_pos  open_bool  long
        long = index_pos_df.loc[index_pos_df['symbol']==symbol, 'long'].iloc[0]
        kill_size = index_pos_df.loc[index_pos_df['symbol']==symbol, 'open_size'].iloc[0]
        kill_size = int(kill_size)
        
        ask = ask_bid(symbol)[0]
        bid = ask_bid(symbol)[1]

        if long == False:
            phemex.create_limit_buy_order(symbol, kill_size, bid, params)
            print(f'** BUY to CLOSE - {symbol}')
            #print('sleeping for 7 seconds to see if it fills..')
            time.sleep(7)
        elif long == True:
            phemex.create_limit_sell_order(symbol, kill_size, ask,params )
            print(f'** SELL to CLOSE - {symbol}')
            #print('sleeping for 7 seconds to see if it fills..')
            time.sleep(7)
        else:
            print('++++++ SOMETHING I DIDNT EXCEPT IN KILL SWITCH FUNCTION')

        index_pos_df = open_positions(symbol)[1]
        openposi = index_pos_df.loc[index_pos_df['symbol']==symbol, 'open_bool'].iloc[0]
    

index_pos = 0
#### PNL CLOSE
# pnl_close() [0] pnlclose and [1] in_pos [2]size [3]long TF
# takes in symbol, target, max loss, index_pos
def pnl_close(symbol=symbol, target=target, max_loss=max_loss, index_pos=index_pos ):


    #print(f'checking to see if its time to exit for {symbol}... ')

    params = {'type':"swap", 'code':'USD'}
    pos_dict = phemex.fetch_positions(params=params)
    #print(pos_dict)

    index_pos_df = open_positions(symbol)[1]
    index_pos = index_pos_df.loc[index_pos_df['symbol']==symbol, 'index_pos'].iloc[0]
    #open_size = active_pos_df.loc[active_pos_df['symbol']==symbol, 'open_size'].iloc[0]
    pos_dict = pos_dict[index_pos] 
    side = pos_dict['side']

    size = pos_dict['contracts']
    entry_price = float(pos_dict['entryPrice'])
    leverage = float(pos_dict['leverage'])


    current_price = ask_bid(symbol)[1]

    #print(f'side: {side} | entry_price: {entry_price} | lev: {leverage}')
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
    print(f'{symbol} PnL: {round((perc),2)}%')

    pnlclose = False 
    in_pos = False
    #print('made it 298')

    if perc > 0:
        in_pos = True
        #print(f'for {symbol} we are in a winning postion')
        if perc > target:
            #print(':) :) we are in profit & hit target.. checking volume to see if we should start kill switch')
            pnlclose = True
            print(f'{symbol} hit target of: {target}%')
            kill_switch(symbol) 
        else:
            #print('we have not hit our target yet')
            nokill = True

    elif perc < 0: # -10, -20, 
        in_pos = True
        if perc <= max_loss: # under -55 , -56
            print(f'{symbol} max loss hit: {max_loss}')
            kill_switch(symbol)
        else:
            #print(f'we are in a losing position of {perc}.. but chillen cause max loss is {max_loss}')
            nothing = True
    else:
        #print('we are not in position')
        nothing = True 

    #print(f' for {symbol} just finished checking PNL close..')

    return pnlclose, in_pos, size, long




def get_times():

    now = datetime.now()
    dt_string = now.strftime("%m/%d/%Y %H:%M:%S")
    #print(dt_string)
    epochtime = int(time.time())
    #print(epochtime)
    comp24time = now.strftime('%H%M')
    #print(f'this is comptime: {comp24time}')

    # is time now within 5-15min of funding time of 0, 8 epoch
    # this gets the time stamp
    orderbook = phemex.fetch_order_book(symbol)
    ex_timestamp = orderbook['timestamp']
    # it comes in ms so convert to regular

    ex_timestamp = int(ex_timestamp /1000)
    #print(ex_timestamp)

    # got it nice. utc time of exchange below
    ex_utc_time = datetime.utcfromtimestamp(ex_timestamp).strftime('%H%M')
    ex_utc_time = int(ex_utc_time)
    #print(f'this is the exchange utc time: {ex_utc_time}')

    return dt_string, epochtime, comp24time, ex_utc_time # get_time() 0: dt_string, 1: epochtime, 2: comp24time, 3: ex_utc_time


# MEAN REVERSION
# SMA 
# TRENDING
def bot(symbol=symbol):


    allposinfo = open_positions()
    active_pos_list = allposinfo[0]
    active_pos_df = allposinfo[1]
    #print(active_pos_df)


    openpos_df = active_pos_df.loc[active_pos_df['open_bool']==True, 'symbol'].iloc[0:]
    openpos_list = openpos_df.tolist()
    #print(f'this is the open position list {openpos_list}')
    


    # check to see open positions, any that have TRUE, pass
    # that symbol to pnl_close.. and then pnl close it before
    # moving on to the rest of the code

    ### WE HAVE NOT IMPLEMENTED ANY CLOSE OF POSITIONS - to implement
    #pnl_close(symbol)
    # TODO -
        # we need to do this for all open positions.. 

    all_symbols = pd.read_csv('phe_symbols.csv')

    random_symbol_pos = random.randrange(0,78)
    random_symbol = all_symbols.iloc[random_symbol_pos]['symbol']
    #print(random_symbol)

    symbols = all_symbols['symbol'].values.tolist()
    symbol = random_symbol

    phemex.set_leverage(leverage, symbol)

    comp24time = get_times()[2]
    comp24time = int(comp24time)
    #print(f'this is the time: {comp24time}')


#### CX EVERY 30 mins
    cx_times = [0, 30, 100, 130, 200, 230, 300, 330, 400, 430, 500, 530, 600, 630, 700, 730, 800, 830, 900, 930, 1000, 1030, 1100, 1130, 1200, 1230, 1300, 1430, 1400, 1500, 1530, 1600, 1600, 1730, 1700, 1800, 1830, 1930, 1900, 2000, 2030, 2100, 2130, 2230, 2200, 2330, 2300, 2400]
    #print(cx_times)
    for x in cx_times:
        int(x)
        if comp24time == x:
            print('its time to cancel all pending orders...')
            for sym in symbols:
                phemex.cancel_all_orders(sym)
            
        
            
        else:
            #print('it is not time to cancel all positions..')
            noclose = True

    for symbol in openpos_list:
        symbol = symbol 
        pnl_close(symbol)

    # get SMAS
# returns: df_sma with sma (can customize with below)
# call: df_sma(symbol, timeframe, limit, sma) 
# # if not passed, uses default

#### 15m SMA.. 
    time15m = '15m'
    limit15 = 97
    df_sma15m = n.df_sma(symbol, time15m, limit15, sma)
    #print(df_sma15m)

#### 4 hour SMA 
    timeframe4h = '4h'
    limit4h = 31 # is about 5 days
    # this gets the df with sma for a symbol
    df_sma4hr = n.df_sma(symbol, timeframe4h, limit4h, sma) # gets sma for the symbol
    #print(df_sma4hr)

#### 5 min SMA
    timeframe5m = '5m'
    limit5m = 100 
    df_sma5m = n.df_sma(symbol, timeframe5m, limit5m, sma) 
    #print(df_sma5m)

    # TRUE / FALSE for last close bigger than prev close lcBpc
    lcBpc5m = df_sma5m['lcBpc'].iloc[-1]
    #print(lcBpc5m)

################## MEAN REVERSION STRATEGY ##################
    # if the price gets too far from the 15mSMA, trade back
    # to the sma BUT only do this w/ the trend (4hr)
        # how to define when to open order???
    # meaning, if the 4hr price < SMA = BEARISH trend
    # if price > SMA = BULLISH trend.. in the long term
    # if in BULLISH then only trade mean reversion 
        # to the upside, aka if price gets too far under
        # 15m sma then we BUY/ Long it
    # if in BEARISH trend... look for sells when the 
        # price gets too HIGH over the 15m sma, short it
################## STRATEGY ##################

    askbid = ask_bid()
    ask = askbid[0]
    bid = askbid[1]
    #print(f'bid {bid}')
    #print(f'bid {bid/leverage}')


############ WORKING ON POSITION SIZE HERE TO MAKE IT $25 per
    # pos_size = int(25/(bid/leverage))
    # print(f'*******pos_size in {pos_size}')
    # time.sleep(783632)

    sig4hr = df_sma4hr['sig'].iloc[-1]
    #print(sig4hr)

    sma15m = df_sma15m['sma20_15m'].iloc[-1]
    #print(sma15m)
    sma15m_plus004 = sma15m * 1.004
    sma15m_minus004 = sma15m * .996
    sma15m_minus002 = sma15m * .998
    sma15m_plus008 = sma15m * 1.008
    sma15m_minus008 = sma15m * .992
    sma15m_plus002 = sma15m * 1.002

    open_size = active_pos_df.loc[active_pos_df['symbol']==symbol, 'open_size'].iloc[0]
    #print(f'***this is the opensize {open_size}')
    open_size = int(open_size)

## FIGURE OUT IF IN POSITION IS T OR F
    if open_size > 0:
        in_pos = True
    else:
        in_pos = False 

    #print(f'in_pos == {in_pos}')

    if sig4hr == 'BUY':
        #print(f'{symbol} price > SMA 4 hr == BULLISH TREND')
        bullish = True
        # if price is way higher than sma, open order
        # we only long in this instance so we place orders if
        # we are too much LOWER from the 15m sma
        if ((bid <= sma15m) and (in_pos == False) and (lcBpc5m == True)):
            #print(f'{symbol} price < sma, so going to submit a buy at .8perc lower {sma15m_minus008}')
            phemex.cancel_all_orders(symbol)
            phemex.create_limit_buy_order(symbol, pos_size, sma15m_minus008, params)
            print(f'** BUY TO OPEN: {symbol}')
        else:
            noorder = True
            #print('not submitting order cuz bid is over sma.. or already in position ')
    elif sig4hr == 'SELL':
        #print(f'{symbol} price < SMA 4hr == BEARISH TREND')
        bullish = False
        # if price is > than sma, open order
        # we only short in this instance so we place orders if
        # we are too much HIGHER from the 15m sma
        if ((bid >= sma15m) and (in_pos == False) and (lcBpc5m == False)):
            #print(f'{symbol} price > sma, so going to submit a sell at .8perc higher {sma15m_plus008}')
            phemex.cancel_all_orders(symbol)
            phemex.create_limit_sell_order(symbol, pos_size, sma15m_plus008, params)
            print(f'** SELL TO OPEN: {symbol}')
        else:
            noorder = True
            #print('not submitting order cuz bid is over sma.. or already in position ')
    else:
        #print(f'+++++ {symbol} price must be == sma??? maybe something i didnt think of... ')
        bullish = False 


schedule.every(10).seconds.do(bot)

while True:
    try:
        # kill_switch_all()
        # time.sleep(367)
        schedule.run_pending()
    except:
        print('+++++ MAYBE AN INTERNET PROB OR SOMETHING')
        time.sleep(7)






##################################

########## GETTING ALL SYMBOLS OF PHEMEX, dont need to run
            # more than once so marking out


#markets = phemex.fetch_markets(params=params)
# symbols_df = pd.DataFrame()
# temp_df = pd.DataFrame()
# for n in markets:
    
#     type = n['info']['type']
#     if type == 'Perpetual':
        
#         #print(type)
#         symbol = n['id']
#         print(n['id'])
#         temp_df['symbol'] = [symbol]
#         # make a df to store
    
#         print('--')

#         symbols_df = symbols_df.append(temp_df)

# print(symbols_df)
# symbols_df.to_csv('phe_symbols.csv', index=False)


# outfile = open('jsontickers.json', 'w')
# json.dump(markets, outfile, indent=6)

# outfile.close()

# now we have every contract ticker on phemex, now what
# we want to look for opps and then buy or sell 
    # mean reversion
    # breakouts
    # trending 
    # sma cross 

####### BELOW CODE ACTIVATES ALL TICKRS
# get all tickers and submit an order to activate all
    
    # for n in range(0,78):
    #     random_symbol_pos = random.randrange(0,75)
    #     one_sym_pertime = all_symbols.iloc[n]['symbol']
    #     print(one_sym_pertime)
    #     bid = ask_bid(one_sym_pertime)[1]
        
    #     phemex.create_limit_buy_order(one_sym_pertime,pos_size,bid, params )
    #     time.sleep(2)
    #     print('---')