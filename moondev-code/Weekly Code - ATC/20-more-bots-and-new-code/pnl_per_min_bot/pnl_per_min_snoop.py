'''
please build me an algo that uses ccxt and connects to phemex to trade uBTCUSD and buy when we hit the vwap (use pandas ta) and sell after 5 minutes

if the price is over the 4 hour SMA, we will enter as a buy and if it is under under the SMA we will enter as a sell

todo-
- how to enter? why does it show entry time when no position? 
'''

import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
import dontshareconfig
import numpy as np
# hide all warning messages
import warnings
warnings.filterwarnings("ignore")

symbol = 'ETHUSD'
timeframe = '15m'
amount = 1  # Adjust the amount according to your needs
sma_length = 20

# change these to be the pnl perc/min max you want
pnl_perc_loss = -0.7
pnl_perc_gain = 0.9

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': dontshareconfig.xP_KEY, 
    'secret': dontshareconfig.xP_SECRET, 
})

def snoop_dogg_sayings(action):
    sayings = {
        'buy': [
            "Fo' shizzle!",
            "Drop it like it's hot!",
            "Laid back, with my mind on my money and my money on my mind.",
        ],
        'sell': [
            "It ain't no fun if the homies can't have none.",
            "I'm out, dogg.",
            "Gz up, hoes down!",
        ],
    }
    return np.random.choice(sayings[action])


import random

snoop_sayings = [
    "Loopin' it up like it's Snoop's greatest hits, dawg.",
    "Ridin' this loop like a G6, fo' shizzle.",
    "Loop de loop, we keepin' it gangsta, homie.",
    "Loopin' and rollin', ain't no stoppin' us now, nephew.",
    "Another loop in the game, just like Snoop's rhymes, playa.",
    "Back at it again with the loops, ain't nothin' but a G thang, baby.",
    "Loopin' it up, straight West Coast style, ya dig?",
    "One more loop for the hood, we keepin' it real, cuz.",
    "This loop's smokin' like Snoop's finest, fo' shizzle.",
    "Ain't no party like a loop party, 'cause a loop party don't stop, dawg."
]


def get_data(symbol, timeframe):
    ohlcv = phemex.fetch_ohlcv(symbol, timeframe)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    df['sma'] = df['close'].rolling(window=sma_length).mean()

    #print(df)
    return df

def place_order(symbol, side, amount, price):
    order_params = {
        'symbol': symbol,
        'side': side,
        'type': 'limit',
        'price': price,
        'amount': amount,
    }
    order = phemex.create_order(**order_params)
    return order

def calculate_pnl(entry_price, exit_price, amount, side):
    if side == 'buy':
        pnl = (exit_price - entry_price) * amount
    else:
        pnl = (entry_price - exit_price) * amount
    return pnl


def cancel_all_orders(symbol):
    orders = phemex.fetch_open_orders(symbol)
    for order in orders:
        phemex.cancel_order(order['id'], symbol)

import json

def get_position(symbol):
    positions = phemex.fetch_positions()
    for position in positions:
        if position['info']['symbol'] == symbol:
            return position
    print(position)
    
    return None

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
    
    active_sym_df.to_csv('march23/active_symbols.csv', index=False)
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

    # if perc > 0:
    #     in_pos = True
    #     #print(f'for {symbol} we are in a winning postion')
    #     if perc > target:
    #         #print(':) :) we are in profit & hit target.. checking volume to see if we should start kill switch')
    #         pnlclose = True
    #         print(f'{symbol} hit target of: {target}%')
    #         kill_switch(symbol) 
    #     else:
    #         #print('we have not hit our target yet')
    #         nokill = True

    # elif perc < 0: # -10, -20, 
    #     in_pos = True
    #     if perc <= max_loss: # under -55 , -56
    #         print(f'{symbol} max loss hit: {max_loss}')
    #         kill_switch(symbol)
    #     else:
    #         #print(f'we are in a losing position of {perc}.. but chillen cause max loss is {max_loss}')
    #         nothing = True
    # else:
    #     #print('we are not in position')
    #     nothing = True 

    #print(f' for {symbol} just finished checking PNL close..')

    return pnlclose, in_pos, size, long, perc



from datetime import datetime

from datetime import datetime, timezone
import pytz

def calculate_position_duration(position):
    # Assuming 'transactTimeNs' represents the transaction time in nanoseconds
    transaction_time_ns = position['info']['transactTimeNs']
    transaction_time = datetime.fromtimestamp(int(transaction_time_ns) // 1000000000)

    # Convert transaction time to UTC
    local_timezone = datetime.now(timezone.utc).astimezone().tzinfo
    transaction_time_utc = transaction_time.astimezone(pytz.UTC)

    # Get the current time in UTC
    current_time_utc = datetime.now(timezone.utc)

    # Calculate the duration
    position_duration = current_time_utc - transaction_time_utc

    return position_duration

def trade_logic():

    position = None

    while True:
        cancel_all_orders(symbol)

        snoop_print = random.choice(snoop_sayings)
        print(snoop_print)

        data = get_data(symbol, timeframe)
        current_price = data.iloc[-1]['close']
        vwap = data.iloc[-1]['vwap']
        sma = data.iloc[-4]['sma']

        orderbook = phemex.fetch_order_book(symbol)
        bid_price = orderbook['bids'][0][0] if len(orderbook['bids']) > 0 else None
        ask_price = orderbook['asks'][0][0] if len(orderbook['asks']) > 0 else None

        askbidinfo = ask_bid(symbol)
        ask = askbidinfo[0]
        bid = askbidinfo[1]

        buy_threshold = vwap * 1.0005  # 0.05% above VWAP
        sell_threshold = vwap * 0.9995  # 0.05% below VWAP

        position = get_position(symbol)

        if current_price > vwap and current_price > sma and current_price <= buy_threshold:
            print("Buy signal")
            if bid_price is not None and position is None:
                buy_order = place_order(symbol, 'buy', amount, bid)
                print("Buy order placed", snoop_dogg_sayings('buy'))

        elif current_price < vwap and current_price < sma and current_price >= sell_threshold:
            print("Sell signal")
            if ask_price is not None and position is None:
                sell_order = place_order(symbol, 'sell', amount, ask)
                print("Sold ETH:", snoop_dogg_sayings('sell'))

        else:
            print("No signal")

        position = get_position(symbol)
        #print(position)

        if position['info']['side'] != 'None':
            position_duration = calculate_position_duration(position)
            position_duration_seconds = position_duration.total_seconds()
            position_duration_minutes = position_duration_seconds / 60
            print('position duration in seconds: ', position_duration_seconds)
            pnlinfo = pnl_close(symbol, 0, 0 )
            pnl = pnlinfo[4]
            size = pnlinfo[2]
            long = pnlinfo[3]
            print(f'pnl is {pnl}')
        
            pnl_per_minute = pnl / (position_duration_seconds / 60)

            # print above info
            print(f"Chillin' on this position for: {position_duration_minutes} minutes, dawg")
            print(f"Stackin' paper with this PnL: {pnl:.3f}%, fo' shizzle")
            print(f"Gettin' paid per minute like a boss: {pnl_per_minute:.3f}%, ya dig")

            if pnl_per_minute <= pnl_perc_loss or pnl_per_minute >= pnl_perc_gain:
                cancel_all_orders(symbol)
                if long == True and ask_price is not None:
                    sell_order = place_order(symbol, 'sell', size, ask_price)
                    print("Sellin' like a G at this price, nephew:", ask_price)
                elif long == False and bid_price is not None:
                    buy_order = place_order(symbol, 'buy', size, bid_price)
                    print("Buyin' like it's hot, hot, hot at this price, cuz:", bid_price)

        print("Aight, we done with this loop... time to chill for 60 seconds, playa")

                
        time.sleep(60)  # Sleep for 1 minute between iterations
  # Sleep for 1 minute between iterations

import schedule

trade_logic()
schedule.every(29).seconds.do(trade_logic)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ maybe an internet problem.. code failed. sleeping 10')
        time.sleep(10)

