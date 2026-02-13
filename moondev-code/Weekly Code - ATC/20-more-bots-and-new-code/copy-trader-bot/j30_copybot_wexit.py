'''
we are building a bot that looks at the tape (recent trades)
we identify unique order values and assume thats a trader/bot
then we copy trade them 
exit - when they exit

## 3 is the tracker #
6/30 now live, and it exits when they exit
 
WARNING- DO NOT RUN LIVE WITHOUT TESTING  
'''

import ccxt, json 
import pandas as pd 
import numpy as np
from torch import less 
import dontshareconfig as ds 
from datetime import date, datetime, timezone, tzinfo 
import time, schedule
import nice_funcs as n 
import datetime as dt 
import warnings
warnings.filterwarnings('ignore')

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '', 
    'secret': '', 
})

symbol = 'BTCUSD'
trade_symbol = 'uBTCUSD'
min_perc = 40
pos_size = 3 
target = 12
max_loss = -10.5
copynum = 34603.0
timepast = 30 # max time passed to copy the trade

params2 =  {'timeInForce': 'PostOnly',}

def open_positions(trade_symbol=trade_symbol):

    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    open_positions = phe_bal['info']['data']['positions']
    #print(open_positions)

    # print('made 38')
    
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
    # print('made 67')

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

        #print('made 101')

        active_sym_df2 = active_sym_df2.append(active_sym_df_t)
        #print(active_sym_df2)
        #print('made 108, done')
        
        #print(f'open_position for {x}... | openpos_bool {openpos_bool} | openpos_size {openpos_size} | long {long} | index_pos {index_pos}')

    return active_symbols_list, active_sym_df2

def kill_switch(trade_symbol=trade_symbol):

    #print(f'starting the kill switch for {symbol}')

    index_pos_df = open_positions(trade_symbol)[1]
        # need to get LONG, Size
        # symbol open_side open_size  index_pos  open_bool  long
    openposi = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'open_bool'].iloc[0]
    long = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'long'].iloc[0]
    kill_size = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'open_size'].iloc[0]
    kill_size = int(kill_size) 

    #print(f'openposi {openposi}, long {long}, size {kill_size}')

    while openposi == True:

        #print('starting kill switch loop til limit fil..')

        phemex.cancel_all_orders(trade_symbol)
        # open_positions() return active_symbols_list ,active_sym_df2
        #index_pos = index_pos_df.loc[index_pos_df['symbol']==symbol, 'index_pos'].iloc[0]
        index_pos_df = open_positions(trade_symbol)[1]
        # need to get LONG, Size
        # symbol open_side open_size  index_pos  open_bool  long
        long = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'long'].iloc[0]
        kill_size = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'open_size'].iloc[0]
        kill_size = int(kill_size)
        
        ask = n.ask_bid(trade_symbol)[0]
        bid = n.ask_bid(trade_symbol)[1]

        if long == False:
            phemex.create_limit_buy_order(trade_symbol, kill_size, bid, params2)
            print(f'** BUY to CLOSE - {trade_symbol}')
            #print('sleeping for 7 seconds to see if it fills..')
            time.sleep(7)
        elif long == True:
            phemex.create_limit_sell_order(trade_symbol, kill_size, ask,params2 )
            print(f'** SELL to CLOSE - {trade_symbol}')
            #print('sleeping for 7 seconds to see if it fills..')
            time.sleep(7)
        else:
            print('++++++ SOMETHING I DIDNT EXCEPT IN KILL SWITCH FUNCTION')

        index_pos_df = open_positions(trade_symbol)[1]
        openposi = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'open_bool'].iloc[0]
    
index_pos = 0 
# pnl_close() [0] pnlclose and [1] in_pos [2]size [3]long TF
# takes in symbol, target, max loss, index_pos
def pnl_close(symbol=symbol, target=target, max_loss=max_loss, index_pos=index_pos ):


    print(f'checking to see if its time to exit for {symbol}... ')

    params = {'type':"swap", 'code':'USD'}
    pos_dict = phemex.fetch_positions(params=params)
    #print(pos_dict)

    index_pos_df = open_positions(trade_symbol)[1]
    index_pos = index_pos_df.loc[index_pos_df['symbol']==trade_symbol, 'index_pos'].iloc[0]
    #open_size = active_pos_df.loc[active_pos_df['symbol']==symbol, 'open_size'].iloc[0]
    pos_dict = pos_dict[index_pos] 
    side = pos_dict['side']

    size = pos_dict['contracts']
    entry_price = float(pos_dict['entryPrice'])
    leverage = float(pos_dict['leverage'])


    current_price = n.ask_bid(symbol)[1]

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
            print(f'{trade_symbol} hit target of: {target}%')
            kill_switch(trade_symbol) 
        else:
            #print('we have not hit our target yet')
            nokill = True

    elif perc < 0: # -10, -20, 
        in_pos = True
        if perc <= max_loss: # under -55 , -56
            print(f'{trade_symbol} max loss hit: {max_loss}')
            kill_switch(trade_symbol)
        else:
            #print(f'we are in a losing position of {perc}.. but chillen cause max loss is {max_loss}')
            nothing = True
    else:
        #print('we are not in position')
        nothing = True 

    print(f' for {symbol} just finished checking PNL close..')

    return pnlclose, in_pos, size, long

def indentify_orders():

    print('we are trying to identify similar orders... ')

    df = pd.read_csv('/Users/arb/Dropbox/dev/zeldar/live_strategies/june22/tape_reader_df.csv')

    # FIND REPEATING NUMBERS IN THE BUY AMOUNT OR SELL AMOUNT ['amount']
    # COUNT DUPES + see what the number is

    dupes = df[df.duplicated('amount')]
    #print('duplicated rows based on amount:')
    #print(dupes.tail(100))

    #amount_count = df['amount'].value_counts().reset_index(name='count').query('count > 10')['index']
    amount_count = df.amount.value_counts().loc[lambda x: x>50].reset_index()['index']
    print(amount_count)

    '''
    traders that have traded more than 25 times in the past 4 days
    0    500000.0
    1     15000.0 *
    2     34603.0 * #1 any time we see this order go through, we copy
    3     45185.0 * 
    4     20000.0
    5     33500.0 *
    6     13433.0 *
    7     22572.0 *
    8     39164.0 *
    '''
    # print(amount_count[amount_count > 5].index[0])
    # only print value counts over 20

    # 34603.0 -- copy this trader
    # any time we see this order go through, ddo the ssame thing 
    # later, start trying to find in OB
    # look for that amount in buy_amount and sell_amount and do same 
    print(df.tail(20))

#     openposi = active_symbol_df.loc[active_symbol_df['symbol']==symbol, \
#    'open_bool'].iloc[0]

    copynum = 34603.0

    # grab epoch time and if in last 15 seconds, make trade
    buy_trade = df.loc[df['buy_amount']==copynum, 'epoch' ].iloc[-1]
    print(f'this iis the last buy_trade {buy_trade}')
    sell_trade = df.loc[df['sell_amount']==copynum, 'epoch' ].iloc[-1]
    print(f'this iis the last sell_trade {sell_trade}')

    # now we know the time its happen, what next?
    # if this was in the last 30 seconds, copy it 

    #print(df)


def bot():

    # create the final df/ append df at end of this and save
    #tape_reader_df = pd.DataFrame()
    #tape_reader_df = pd.read_csv('/Users/arb/Dropbox/dev/yt_vids/tape_reader_df_big.csv')
    tape_reader_df = pd.read_csv('/Users/johnmayhew/Dropbox/dev/zeldar/live_strategies/june22/tape_reader_df.csv')

    # total up the last 10 mins

    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    open_pos = phe_bal['info']['data']['positions']
    #print(open_positions)

    openpos_df = pd.DataFrame()
    openpos_df_temp = pd.DataFrame()

    # look at open positiong and get active symbols
    for x in open_pos:
        sym = x['symbol']
        openpos_df_temp['symbol'] = [sym]
        openpos_df = openpos_df.append(openpos_df_temp)

    active_symbols_list = openpos_df['symbol'].values.tolist()
    #print(active_symbols_list)

    # GRABBING ALL RECENT TRADES AND SAVING
    out = open('recenttrades.json', 'w')
    trades = phemex.fetch_trades(symbol)
    json.dump(trades, out, indent=6)
    out.close()

    df = pd.read_json('recenttrades.json')
    df['datetime'] = df['datetime'].dt.strftime('%m/%d/%Y %H:%M:%S')
    df = df.drop(['cost', 'info', 'timestamp', 'id', 'fee', 'order', 'takerOrMaker', 'fees', 'type'], 1)
    df['amount'] = df['amount']*100000000
    df = df[df.amount>10000]
    
    # turn date time into epoch... 
    df['datetime'] = pd.to_datetime(df['datetime'], format="%m/%d/%Y %H:%M:%S")
    df['epoch'] = df['datetime'].apply(lambda x : x.timestamp())

    # IF DATETIME IS BIGGER THAN LAST ROW IN PAST DF, THEN MAKE A NEW DF AND APPEND TO OLD
    

    # TOTALING UP THE BUY AMOUNTS IN THE PAST 9 MINS OR SO
    df.loc[df['side']== 'buy', 'buy_amount'] = df['amount']
    df['buy_amount'] = df['buy_amount'].fillna(0)
    total_buy_amount = df['buy_amount'].sum()

    # TOTALING UP THE SELL AMOUNTS IN THE PAST 9 MINS OR SO
    df.loc[df['side']== 'sell', 'sell_amount'] = df['amount']
    df['sell_amount'] = df['sell_amount'].fillna(0)
    total_sell_amount = df['sell_amount'].sum()

    diff = abs(total_sell_amount - total_buy_amount)
    
    # which one is bigger
    if total_buy_amount > total_sell_amount:
        print('There have been more BUYs than SELLs')
        perc = round((diff/total_buy_amount)*100, 2)
        moreof = 'BUYs'
        lessof = 'SELLs'
        # 1000 / 10000 = .1 
    else:
        print('There have been more SELLs than BUYs')
        moreof = 'SELLs'
        lessof = 'BUYs'
        perc = round((diff/total_sell_amount)*100, 2)
        

    total_buy_amount = '{:,}'.format(total_buy_amount)
    perc2 = f'{perc}%'
    total_sell_amount = '{:,}'.format(total_sell_amount)
    diff = '{:,}'.format(diff)
    print(f'this is the total buy amount {total_buy_amount}')
    print(f'this is the total sell amount {total_sell_amount}')
    print(f'this is the difference {diff}')
    print(f'this is the % difference {perc2} more {moreof} than {lessof} ')

    # 1000 200 - 800 250 - 1000 - 750 

    print(df.tail(10000))
    
    print('')
    print('------')

    print('sleeping .8 seconds...')
    #df = df.append(temp_df)

    # 1656076000

    # LAST EPOCH OF PREV DATAFRAME
    
    last_epoch = tape_reader_df['epoch'].iloc[-1]
    print(f'****** this is the last value of last tape reader epoch {last_epoch}')
    # DF = where the above DF epch > is bigger than the last one
    df = df[df['epoch'] > last_epoch]
    # print(df)
    #time.sleep(7947)
    tape_reader_df = tape_reader_df.append(df)
    tape_reader_df.to_csv('tape_reader_df.csv', index=False)

    # GET THE SMA 
    # def df_sma(symbol=symbol, timeframe=timeframe, limit=limit, sma=sma):
    df_sma = n.df_sma(symbol, '15m', 200, 20)
    #print(df_sma)
    sig = df_sma['sig'].iloc[-1]
    print(f'*******this is the signal: {sig}')


    ###################################
    ###################################
    #########FINDING TRADERS TO COPY##########
    ###################################
    ###################################
    ###################################

    print('we are trying to identify similar orders... ')

    #df = pd.read_csv('/Users/arb/Dropbox/dev/yt_vids/tape_reader_df_big.csv')

    # setting the df to old tape reader df so everything works
    df = tape_reader_df

    # FIND REPEATING NUMBERS IN THE BUY AMOUNT OR SELL AMOUNT ['amount']
    # COUNT DUPES + see what the number is

    dupes = df[df.duplicated('amount')]
    #print('duplicated rows based on amount:')
    #print(dupes.tail(100))

    #amount_count = df['amount'].value_counts().reset_index(name='count').query('count > 10')['index']
    amount_count = df.amount.value_counts().loc[lambda x: x>50].reset_index()['index']
    print(amount_count)

    '''
    traders that have traded more than 25 times in the past 4 days
    0    500000.0
    1     15000.0 *
    2     34603.0 * #1 any time we see this order go through, we copy
    3     45185.0 * 
    4     20000.0
    5     33500.0 *
    6     13433.0 *
    7     22572.0 *
    8     39164.0 *
    '''
    # print(amount_count[amount_count > 5].index[0])
    # only print value counts over 20

    # 34603.0 -- copy this trader
    # any time we see this order go through, ddo the ssame thing 
    # later, start trying to find in OB
    # look for that amount in buy_amount and sell_amount and do same 
    print(df.tail(20))

#     openposi = active_symbol_df.loc[active_symbol_df['symbol']==symbol, \
#    'open_bool'].iloc[0]

    
    #copynum = 22572.0

    # grab epoch time and if in last 15 seconds, make trade
    buy_time = df.loc[df['buy_amount']==copynum, 'epoch' ].iloc[-1]
    print(f'this iis the last buy_time {buy_time}')

    sell_time = df.loc[df['sell_amount']==copynum, 'epoch' ].iloc[-1]
    print(f'this iis the last sell_time {sell_time}')


    


    # if the order is in the last 30 seconds, copy it 
    # we also need to know the side

    # get current exchange time stamp
    orderbook = phemex.fetch_order_book(symbol)
    ex_timestamp = orderbook['timestamp'] # in ms 
    ex_timestamp = int(ex_timestamp/1000)

    print(f'this the is exahnge epoch: {ex_timestamp}')

    if buy_time > sell_time:
        time_diff = ex_timestamp - buy_time
        side = 'BUY'
    elif sell_time > buy_time:
        time_diff = ex_timestamp - sell_time
        
        side = 'SELL'
    else:
        print('somehting unexpectedd happend in buy time> sell time..')
        side = None 

    time_diff = int(time_diff)
    print(f'this the is time diff since the last trade of {copynum}: {time_diff}')


    ###################################
    ###################################
    #########IMPLEMENTIN BUYS AND SELlS##########
    ###################################
    ###################################
    ###################################

    # check pnl close - if target hit, close, if maxloss hit, close
    #pnl_close(trade_symbol)

  

    # kill size is the positions size
    # the is 
    bidask = n.ask_bid(trade_symbol)
    bid = bidask[1]
    ask = bidask[0]

    # bid = bid * .995
    # ask = ask * 1.005

    #print('gotbid')

    # return active_symbols_list, active_sym_df2
    posinfo = open_positions(trade_symbol)
    #print('got open pos')
    active_sym_df2 = posinfo[1]
    #print(active_sym_df2)

    kill_size = active_sym_df2.loc[active_sym_df2['symbol']==trade_symbol, \
        'open_size'].iloc[0]
    kill_size = int(kill_size)
    if kill_size > 0:
        in_pos = True
    else:
        in_pos = False
    #print(f'this is the open size {kill_size}')

    print('got after kil size')

    if ((time_diff < timepast) and(side == 'BUY') and (in_pos == False)): #  
        print('we are going to BUY... ')
        phemex.cancel_all_orders(trade_symbol)
        phemex.create_limit_buy_order(trade_symbol, pos_size, bid, params2)
        print(f'just made a BUY of {pos_size} {trade_symbol} at {bid} now sleeping 40...')
        time.sleep(40)
    elif ( (time_diff < timepast) and(side == 'SELL') and (in_pos == False)): # 
        print('we are going to SHORT')
        phemex.cancel_all_orders(trade_symbol)
        phemex.create_limit_sell_order(trade_symbol, pos_size, ask, params2)
        print(f'just made a SELL of {pos_size} {trade_symbol} at {ask} now sleeping 40...')
        time.sleep(40)
    else:
        print('doing nothing this time through.. params were not hit.. checking if time to close... ')

    # IMPLEMENT BUY AND SELL ORDERS
    # exit position

    # EXIT WHEN THEY EXIT 
    
    if (in_pos == True) and (time_diff < timepast):

        print('starting the kill switch to close... ')

    # CLoses the position
        kill_switch()

    elif in_pos == True:
        
        print('we are in position but no need to exit yet.. ')

    else:
        print('we are not in position.. so looping again')

        # check to see if they exited, if yes, close
        # check to see our position side 

        # if copynum exits, we exit
        
# RUN THIS EVERY 10 SECONDS SO WE DONT MISS THEIR TRADES
schedule.every(10).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++ maybe an internet problem... code failed, sleeping 10')
        time.sleep(10)


