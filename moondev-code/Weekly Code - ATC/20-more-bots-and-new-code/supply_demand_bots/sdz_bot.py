'''
this algo will trade based on supply and demand zones 

** please do not run this without testing it first and adding your own strategy & tweaks **
'''

import ccxt 
import math 
import pandas as pd
import time, schedule
from datetime import datetime 
import warnings
warnings.filterwarnings("ignore")
import numpy as np 
import nice_funcs as n 

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '', 
    'secret': '', 
})

symbol = 'MANAUSD'
usd_size = 25
target = 2
max_loss = -3
leverage = 5

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


def supply_demand_zones(symbol=symbol):

    '''
    out puts a df with supply and demand zones for each time frame
    # this is supply zone n demand zone ranges
    # row 0 is the CLOSE, row 1 is the WICK (high/low)
    # and the supply/demand zone is inbetween the two
    '''

    print('starting supply and demand zone calculations..')

    # get OHLCV data 
    sd_limit = 200
    sd_sma = 20     

    # df_1m = n.df_sma(symbol, '1m', sd_limit, sd_sma)
    # #print(df_1m)

    sd_df = pd.DataFrame() # supply and demand zone dataframe 

    # # get support and resistance 
    # supp_1m = df_1m.iloc[-1]['support']
    # resis_1m = df_1m.iloc[-1]['resis']
    # #print(f'this is support for 1m {supp_1m} and this is resis {resis_1m}')
    
    # # supply and demand, is where the wicks of supp/resis
    # # GET THE WICKS, wicks highs and the lows... 
    # # demand zone is BETWEEN the Support & Support on low

    # df_1m['supp_lo'] = df_1m[:-2]['low'].min()
    # supp_lo_1m = df_1m.iloc[-1]['supp_lo']
    # #print(f'this is the support lo: {supp_lo_1m} this is support {supp_1m} Demand zone is BETWEEN the 2')

    # df_1m['res_hi'] = df_1m[:-2]['high'].max()
    # res_hi_1m = df_1m.iloc[-1]['res_hi']
    # #print(f'this is the res hi: {res_hi_1m} this is resis {resis_1m} Supply Zone is BETWEEN the 2')

    # # this is supply zone n demand zone ranges
    # # row 0 is the low, row 1 is the high
    # # and the supply/demand zone is inbetween the two
    # sd_df['1m_dz'] = [supp_lo_1m, supp_1m]
    # sd_df['1m_sz'] = [res_hi_1m,resis_1m ]

    # time.sleep(1)

    # df_5m = n.df_sma(symbol, '5m', sd_limit, sd_sma)
    # supp_5m = df_5m.iloc[-1]['support']
    # resis_5m = df_5m.iloc[-1]['resis']
    # #print(df_5m)
    # #print(f'this is support for 5m {supp_5m} and this is resis {resis_5m}')

    # df_5m['supp_lo'] = df_5m[:-2]['low'].min()
    # supp_lo_5m = df_5m.iloc[-1]['supp_lo']
    # #print(f'this is the support lo: {supp_lo_5m} this is support {supp_5m} Demand zone is BETWEEN the 2')

    # df_5m['res_hi'] = df_5m[:-2]['high'].max()
    # res_hi_5m = df_5m.iloc[-1]['res_hi']
    # #print(f'this is the res hi: {res_hi_5m} this is resis {resis_5m} Supply Zone is BETWEEN the 2')

    # sd_df['5m_dz'] = [supp_lo_5m, supp_5m]
    # sd_df['5m_sz'] = [res_hi_5m,resis_5m ]

    # time.sleep(1)

    df_15m = n.df_sma(symbol, '15m', sd_limit, sd_sma)
    #print(df_15m)
    supp_15m = df_15m.iloc[-1]['support']
    resis_15m = df_15m.iloc[-1]['resis']
    #print(f'this is support for 15m {supp_15m} and this is resis {resis_15m}')

    df_15m['supp_lo'] = df_15m[:-2]['low'].min()
    supp_lo_15m = df_15m.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_15m} this is support {supp_15m} Demand zone is BETWEEN the 2')

    df_15m['res_hi'] = df_15m[:-2]['high'].max()
    res_hi_15m = df_15m.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_15m} this is resis {resis_15m} Supply Zone is BETWEEN the 2')

    sd_df['15m_dz'] = [supp_lo_15m, supp_15m]
    sd_df['15m_sz'] = [res_hi_15m,resis_15m ]

    # time.sleep(1)

    # df_1h = n.df_sma(symbol, '1h', sd_limit, sd_sma)
    # #print(df_1h)
    # supp_1h = df_1h.iloc[-1]['support']
    # resis_1h = df_1h.iloc[-1]['resis']
    # #print(f'this is support for 1h {supp_1h} and this is resis {resis_1h}')

    # df_1h['supp_lo'] = df_1h[:-2]['low'].min()
    # supp_lo_1h = df_1h.iloc[-1]['supp_lo']
    # #print(f'this is the support lo: {supp_lo_1h} this is support {supp_1h} Demand zone is BETWEEN the 2')

    # df_1h['res_hi'] = df_1h[:-2]['high'].max()
    # res_hi_1h = df_1h.iloc[-1]['res_hi']
    # #print(f'this is the res hi: {res_hi_1h} this is resis {resis_1h} Supply Zone is BETWEEN the 2')

    # sd_df['1h_dz'] = [supp_lo_1h, supp_1h]
    # sd_df['1h_sz'] = [res_hi_1h,resis_1h ]

    # time.sleep(1)

    # df_4h = n.df_sma(symbol, '4h', sd_limit, sd_sma)
    # #print(df_4h)
    # supp_4h = df_4h.iloc[-1]['support']
    # resis_4h = df_4h.iloc[-1]['resis']
    # #print(f'this is support for 4h {supp_4h} and this is resis {resis_4h}')

    # df_4h['supp_lo'] = df_4h[:-2]['low'].min()
    # supp_lo_4h = df_4h.iloc[-1]['supp_lo']
    # #print(f'this is the support lo: {supp_lo_4h} this is support {supp_4h} Demand zone is BETWEEN the 2')

    # df_4h['res_hi'] = df_4h[:-2]['high'].max()
    # res_hi_4h = df_4h.iloc[-1]['res_hi']
    # #print(f'this is the res hi: {res_hi_4h} this is resis {resis_4h} Supply Zone is BETWEEN the 2')

    # sd_df['4h_dz'] = [supp_lo_4h, supp_4h]
    # sd_df['4h_sz'] = [res_hi_4h,resis_4h ]

    # time.sleep(1)

    # df_1d = n.df_sma(symbol, '1d', sd_limit, sd_sma)
    # #print(df_1d)
    # supp_1d = df_1d.iloc[-1]['support']
    # resis_1d = df_1d.iloc[-1]['resis']
    # #print(f'this is support for 1d {supp_1d} and this is resis {resis_1d}')

    # df_1d['supp_lo'] = df_1d[:-2]['low'].min()
    # supp_lo_1d = df_1d.iloc[-1]['supp_lo']
    # #print(f'this is the support lo: {supp_lo_1d} this is support {supp_1d} Demand zone is BETWEEN the 2')

    # df_1d['res_hi'] = df_1d[:-2]['high'].max()
    # res_hi_1d = df_1d.iloc[-1]['res_hi']
    # #print(f'this is the res hi: {res_hi_1d} this is resis {resis_1d} Supply Zone is BETWEEN the 2')

    # sd_df['1d_dz'] = [supp_lo_1d, supp_1d]
    # sd_df['1d_sz'] = [res_hi_1d,resis_1d ]

    #print(sd_df)
    

    # NEXT STEP = BUILD AUTOMATED BOT OF THIS IN A NEW FUNC
    

    return sd_df # this is a df where the zone is indicated per timeframe
                # and range is between row 0 and 1

def supply_demand_zones_og(symbol=symbol):

    '''
    this one calls all SZ and DZ for each timeframe -- the other one only calls the 15m

    out puts a df with supply and demand zones for each time frame
    # this is supply zone n demand zone ranges
    # row 0 is the CLOSE, row 1 is the WICK (high/low)
    # and the supply/demand zone is inbetween the two
    '''

    print('starting supply and demand zone calculations..')

    # get OHLCV data 
    sd_limit = 200
    sd_sma = 20     

    df_1m = n.df_sma(symbol, '1m', sd_limit, sd_sma)
    #print(df_1m)

    sd_df = pd.DataFrame() # supply and demand zone dataframe 

    # get support and resistance 
    supp_1m = df_1m.iloc[-1]['support']
    resis_1m = df_1m.iloc[-1]['resis']
    #print(f'this is support for 1m {supp_1m} and this is resis {resis_1m}')
    
    # supply and demand, is where the wicks of supp/resis
    # GET THE WICKS, wicks highs and the lows... 
    # demand zone is BETWEEN the Support & Support on low

    df_1m['supp_lo'] = df_1m[:-2]['low'].min()
    supp_lo_1m = df_1m.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_1m} this is support {supp_1m} Demand zone is BETWEEN the 2')

    df_1m['res_hi'] = df_1m[:-2]['high'].max()
    res_hi_1m = df_1m.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_1m} this is resis {resis_1m} Supply Zone is BETWEEN the 2')

    # this is supply zone n demand zone ranges
    # row 0 is the low, row 1 is the high
    # and the supply/demand zone is inbetween the two
    sd_df['1m_dz'] = [supp_lo_1m, supp_1m]
    sd_df['1m_sz'] = [res_hi_1m,resis_1m ]

    time.sleep(1)

    df_5m = n.df_sma(symbol, '5m', sd_limit, sd_sma)
    supp_5m = df_5m.iloc[-1]['support']
    resis_5m = df_5m.iloc[-1]['resis']
    #print(df_5m)
    #print(f'this is support for 5m {supp_5m} and this is resis {resis_5m}')

    df_5m['supp_lo'] = df_5m[:-2]['low'].min()
    supp_lo_5m = df_5m.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_5m} this is support {supp_5m} Demand zone is BETWEEN the 2')

    df_5m['res_hi'] = df_5m[:-2]['high'].max()
    res_hi_5m = df_5m.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_5m} this is resis {resis_5m} Supply Zone is BETWEEN the 2')

    sd_df['5m_dz'] = [supp_lo_5m, supp_5m]
    sd_df['5m_sz'] = [res_hi_5m,resis_5m ]

    time.sleep(1)

    df_15m = n.df_sma(symbol, '15m', sd_limit, sd_sma)
    #print(df_15m)
    supp_15m = df_15m.iloc[-1]['support']
    resis_15m = df_15m.iloc[-1]['resis']
    #print(f'this is support for 15m {supp_15m} and this is resis {resis_15m}')

    df_15m['supp_lo'] = df_15m[:-2]['low'].min()
    supp_lo_15m = df_15m.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_15m} this is support {supp_15m} Demand zone is BETWEEN the 2')

    df_15m['res_hi'] = df_15m[:-2]['high'].max()
    res_hi_15m = df_15m.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_15m} this is resis {resis_15m} Supply Zone is BETWEEN the 2')

    sd_df['15m_dz'] = [supp_lo_15m, supp_15m]
    sd_df['15m_sz'] = [res_hi_15m,resis_15m ]

    time.sleep(1)

    df_1h = n.df_sma(symbol, '1h', sd_limit, sd_sma)
    #print(df_1h)
    supp_1h = df_1h.iloc[-1]['support']
    resis_1h = df_1h.iloc[-1]['resis']
    #print(f'this is support for 1h {supp_1h} and this is resis {resis_1h}')

    df_1h['supp_lo'] = df_1h[:-2]['low'].min()
    supp_lo_1h = df_1h.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_1h} this is support {supp_1h} Demand zone is BETWEEN the 2')

    df_1h['res_hi'] = df_1h[:-2]['high'].max()
    res_hi_1h = df_1h.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_1h} this is resis {resis_1h} Supply Zone is BETWEEN the 2')

    sd_df['1h_dz'] = [supp_lo_1h, supp_1h]
    sd_df['1h_sz'] = [res_hi_1h,resis_1h ]

    time.sleep(1)

    df_4h = n.df_sma(symbol, '4h', sd_limit, sd_sma)
    #print(df_4h)
    supp_4h = df_4h.iloc[-1]['support']
    resis_4h = df_4h.iloc[-1]['resis']
    #print(f'this is support for 4h {supp_4h} and this is resis {resis_4h}')

    df_4h['supp_lo'] = df_4h[:-2]['low'].min()
    supp_lo_4h = df_4h.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_4h} this is support {supp_4h} Demand zone is BETWEEN the 2')

    df_4h['res_hi'] = df_4h[:-2]['high'].max()
    res_hi_4h = df_4h.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_4h} this is resis {resis_4h} Supply Zone is BETWEEN the 2')

    sd_df['4h_dz'] = [supp_lo_4h, supp_4h]
    sd_df['4h_sz'] = [res_hi_4h,resis_4h ]

    time.sleep(1)

    df_1d = n.df_sma(symbol, '1d', sd_limit, sd_sma)
    #print(df_1d)
    supp_1d = df_1d.iloc[-1]['support']
    resis_1d = df_1d.iloc[-1]['resis']
    #print(f'this is support for 1d {supp_1d} and this is resis {resis_1d}')

    df_1d['supp_lo'] = df_1d[:-2]['low'].min()
    supp_lo_1d = df_1d.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_1d} this is support {supp_1d} Demand zone is BETWEEN the 2')

    df_1d['res_hi'] = df_1d[:-2]['high'].max()
    res_hi_1d = df_1d.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_1d} this is resis {resis_1d} Supply Zone is BETWEEN the 2')

    sd_df['1d_dz'] = [supp_lo_1d, supp_1d]
    sd_df['1d_sz'] = [res_hi_1d,resis_1d ]

    #print(sd_df)
    

    # NEXT STEP = BUILD AUTOMATED BOT OF THIS IN A NEW FUNC
    

    return sd_df # this is a df where the zone is indicated per timeframe
                # and range is between row 0 and 1

def ask_bid(symbol):

    ob = phemex.fetch_order_book(symbol)
    #print(ob)

    bid = ob['bids'][0][0]
    ask = ob['asks'][0][0]

    bid_liq = ob['bids'][0][1]
    ask_liq = ob['asks'][0][1]


    ask_10  = ob['asks'][9][0]
    bid_10  = ob['bids'][9][0]

    # trying to get the 29th bid/ask if it fails, set to 10th
    try:

        ask_29  = ob['asks'][28][0]
        bid_29  = ob['bids'][28][0]
    except:

        ask_29  = ask_10
        bid_29  = bid_10



    # we can get up to 30 of the bid/asks
    # verfied with a loop

    #print(f'this is the ask for {symbol} {ask}')

    return ask, bid, ask_liq, bid_liq, ask_10, bid_10, ask_29, bid_29 # ask_bid()[0] = ask , [1] = bid

# call func, pass symbol, size in usd wanted, leverage
def contract_calc(symbol, usd_size, leverage):

    '''
    this converts dollars to contracts
    DONE - 1. figure out how much 1 contract for the symbol
    D2. pull in the leverage being used

    ** this works now, but its a few dollars off
    need to think about how to make this even better
    i dont know if its a rounding error or what
    '''

    # ticker = phemex.fetch_ticker(symbol)
    ticker = phemex.fetch_markets()
    # for the markets lets put into df
    ticker = pd.DataFrame.from_dict(ticker)
    #print(ticker)
    
    sym_df = ticker[ticker['id']==symbol]
    #print(sym_df)

    info = sym_df['info'].values
    info = info[0]
    contract_size = info['contractSize']
    sep = ' '
    contract_size = contract_size.split(sep, 1)[0]
    contract_size = float(contract_size)
    #print(contract_size)

    bid = ask_bid(symbol)[0]
    usd_per_contract = bid * contract_size
    #print(usd_per_contract)

    # set leverage -- 
    phemex.set_leverage(leverage, symbol)

    # divide contract size by lev to get USD cost
    cost_per_contract_w_lev = usd_per_contract / leverage
    cost_per_contract_w_lev = round(cost_per_contract_w_lev,2)
    #print(cost_per_contract_w_lev)

    # how much USD do we want?
    contracts_needed = usd_size / cost_per_contract_w_lev # 1000 
    contracts_needed = int(contracts_needed)
    #print(f'if we want {size_usd} USD in {symbol} then {contracts_needed} contracts needed')

    return contracts_needed

# open_positions() return active_symbols_list ,active_sym_df2
def open_positions(symbol):

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
    
    active_sym_df.to_csv('jan23/active_symbols.csv', index=False)
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

def kill_switch(symbol):

    '''
    closes any symbol
    '''

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
  
#### PNL CLOSE
# pnl_close() [0] pnlclose and [1] in_pos [2]size [3]long TF
# takes in symbol, target, max loss, index_pos
def pnl_close(symbol, target, max_loss):

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

def sz_bot():

    print('')
    print(f'----SUPPLY ZONE BOT LIVE on {symbol}----')
    print('')

    # set the leverage
    phemex.set_leverage(leverage, symbol)

    # get the supply and demand zones for all timeframes
    sd_df = supply_demand_zones(symbol)
    print(sd_df)

    '''
    bot logic- buys ETHUSD at the 15m demand zone
    and sells at the 15m SZ 
    '''
    sz_15m = sd_df['15m_sz']
    #print(sz_4h)
    sz_15m_0 = sz_15m.iloc[0]
    sz_15m_1 = sz_15m.iloc[-1]
    #print(sz_15m_0, sz_15m_1) # if selling, sell between these 2

    dz_15m = sd_df['15m_dz']
    #print(sz_4h)
    dz_15m_0 = dz_15m.iloc[0]
    dz_15m_1 = dz_15m.iloc[-1]
    #print(dz_15m_0, dz_15m_1)

    # where do we bid and ask? and when?
    # if over the 20sma, we are looking for longs
    # if under the 20sma, we are looking for shorts
    # df_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):
    df_sma = n.df_sma(symbol, '4h', 200, 20)
    #print(df_sma)
    # supp_1m = df_1m.iloc[-1]['support']
    sig = df_sma.iloc[-1]['sig']
    #print(sig)

    # TODO - 
    # if its buy - buy # 1 at the higher or demand zone
    buy1 = max(dz_15m_0, dz_15m_1)
    buy2 = (dz_15m_0 + dz_15m_1) / 2
    #print(buy1, buy2)

    # if its a sell - sell # 1 at the lower and # 2 and avg
    sell1 = min(sz_15m_0, sz_15m_1)
    sell2 = (sz_15m_0 + sz_15m_1) / 2
    #print(sell1, sell2)

    # pos_info() pos_cost, side, size, entry_price, leverage
    pos_size = pos_info(symbol)[2]

    in_pos = False
    if pos_size > 0:
        in_pos = True

    # this function gets the contracts needed for the usd size
    contracts = contract_calc(symbol, usd_size, leverage)

    size = contracts / 2 # splitting the order in half

    #print(in_pos)
    if in_pos == False:

        if sig == 'BUY':
            print('signal is buy we are going to place buy orders at the 15m Demand Zone')
            phemex.cancel_all_orders(symbol)
            phemex.create_limit_buy_order(symbol, size, buy1)
            phemex.create_limit_buy_order(symbol, size, buy2)
            print('just created the 2 buy orders, sleeping 5mins')
            time.sleep(300)
        elif sig == 'SELL':
            print('signal is SELL we are going to place sell orders at the 15m Supply Zone')
            phemex.cancel_all_orders(symbol)
            phemex.create_limit_sell_order(symbol, size, sell1)
            phemex.create_limit_sell_order(symbol, size, sell2)
            print('just created the 2 buy orders, sleeping 5mins')
            time.sleep(300)
        else:
            print('we didnt get a buy or sell signal... look into this... ')
    else:
        print('we are already in position, checking pnl close')
        #pnl_close(symbol=symbol, target=target, max_loss=max_loss )
        pnl_close(symbol, target, max_loss) # this will close our position

       # istead of big target max losses, i want use smaller ones


schedule.every(34).seconds.do(sz_bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ maybe an internet problem.. code failed. sleeping 10')
        time.sleep(10)