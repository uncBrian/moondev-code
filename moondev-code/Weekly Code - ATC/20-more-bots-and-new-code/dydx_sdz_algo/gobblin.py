'''
warning: do not run this code without making changes to adapt to your strategy
    - do not use this live in production without testing everything and making it your own.

updated 9/1/23 - make your own tweaks and tests before running this. 
updated 9/3- added order management system reasoning, file path management, updated close orders
 
warning: dont run this live without making your own tweaks and adding your strategy
'''


print('version -- 96')

###### INPUTS #########

sym = 'ETH-USD'
close_underr = 19 # bot will auto close under this number - this is used in Trailing Stop
lowest_bal_allowed = 100000 # bot will auto close if we fall under this number
timeframe = '15MINS' # 1MIN , 5MINS, 15MINS, 1HOUR # time frame for the DZ buys... 
pos_size = .1
target_pnl = .4
max_loss = -.1
enter_interval = 5 # ok we can only enter on the 5 minute
max_btc_downside_vol = 300 # this is the max vol for btc to the DOWNSIDE in past 4 hours
#########

price = '23827'
limit = 30
sma = 20 
fundrate_max = 0.000069 # now its 60% which is really 20%.... 13.9%... super chill 7/12 7/20 - markets are only trending 30% of the time.. so this yearly / 3 == what i can pay in funding... im down up to 40%/yr / 3 = 13%... so chill, my ccs are more
                        # 
daily_max_loss_perc = 1.1 # this is in % terms
time_between_trades = 10

import pytz

import pandas as pd 
import schedule, requests, os, sys
from datetime import datetime, timedelta
import dontshareconfig as ds
from dydx3 import Client 
from web3 import Web3 
from pprint import pprint 
from datetime import datetime, timedelta 
import time , logging
import warnings
warnings.filterwarnings('ignore')
from dydx3.constants import API_HOST_GOERLI, API_HOST_MAINNET # for test nets
net = API_HOST_MAINNET # change this to API_HOST_MAINNET for main net

alchemy = ds.alchemy_mainnet

# connect to dydx
client = Client(
    host=net,
    api_key_credentials={
        'passphrase': ds.dydx_api_passphrase,
        'key': ds.dydx_api_key,
        'secret': ds.dydx_api_secret,
    },
    stark_private_key=ds.stark_private_key,
    eth_private_key=ds.mm_private_key,
    default_ethereum_address=ds.eth_address,
    web3=Web3(Web3.HTTPProvider(alchemy)),
)

acc = client.private.get_account()
bal = acc.data['account']['quoteBalance']
print(f'connected to dydx...')

# Get the name of the current script file
script_name = os.path.basename(__file__)
log_file_name = f"{os.path.splitext(script_name)[0]}_log.log"
acc_resp = client.private.get_account()
position_id = acc_resp.data['account']['positionId']

def round_quantity(quantity, tick_size):
    if tick_size == 1.0:
        rounded_quantity = round(quantity)
    elif tick_size == 0.1:
        rounded_quantity = round(quantity * 10) / 10
    elif tick_size == 0.01:
        rounded_quantity = round(quantity * 100) / 100
    elif tick_size == 0.001:
        rounded_quantity = round(quantity * 1000) / 1000
    elif tick_size == 0.0001:
        rounded_quantity = round(quantity * 10000) / 10000
    else:
        rounded_quantity = round(quantity)

    return rounded_quantity

def get_step_size(pair):
    response = client.public.get_markets()
    markets = response.data['markets']
    
    # Create a pandas DataFrame
    df = pd.DataFrame(markets)
    
    # Transpose the DataFrame and reset the index
    df = df.transpose()
    df.reset_index(drop=True, inplace=True)
    
    # Filter the DataFrame for the specified symbol
    filtered_df = df[df['market'] == pair]

    print(filtered_df)
    
    # If the symbol is found, return the tick size
    if not filtered_df.empty:
        return float(filtered_df.iloc[0]['stepSize'])
    else:
        return None

def ohlcv(symbol=sym, timeframe=timeframe, limit=limit, sma=sma):

    candles = client.public.get_candles(
        market=symbol,
        resolution=timeframe,
        limit=limit,
    )
    # put the candles into a dataframe
    df = pd.DataFrame(candles.data['candles'])
    #print(df)
    #print(df.columns)
    #Index(['startedAt', 'updatedAt', 'market', 'resolution', 'low', 'high', 'open',
        #    'close', 'baseTokenVolume', 'trades', 'usdVolume',
        #    'startingOpenInterest'],
    # drop all candles besides the open, high, low, close, usdVolume
    df = df.drop(['updatedAt', 'market', 'resolution', 'baseTokenVolume', 'trades', 'startingOpenInterest'], axis=1)
    # rename usdVolume to volume
    df = df.rename(columns={'usdVolume': 'volume'})
    # rename startedAt to datetime
    df = df.rename(columns={'startedAt': 'datetime'})
    # set datetime as index
    df = df.set_index('datetime')
    # sort by datetime
    df = df.sort_index()
    # sort these so its datetime, open, high, low, close, volume
    ohlcv = df[['open', 'high', 'low', 'close', 'volume']]
    # remove .000Z from datetime
    df.index = df.index.str.replace('.000Z', '')
    # remove T from datetime
    df.index = df.index.str.replace('T', ' ')
    # convert datetime to datetime
    df.index = pd.to_datetime(df.index)
    # copy df and make it ohlcv
    ohlcv = df.copy()

    # add sma
    ohlcv[f'{sma}sma'] = ohlcv['close'].rolling(sma).mean()

    # make signal column, if close is above sma, signal is 1, else 0
    # 1 means buy, 0 means sell
    ohlcv['signal'] = 0
    ohlcv.loc[(ohlcv['close'].astype(float)) > ohlcv[f'{sma}sma'], 'signal'] = 1

    return ohlcv


def number_formatter(curr_num, match_num):
    '''
    give number with decimal desired 
    function resturns correct string to pass to dydx
    '''
    curr_num_string = f'{curr_num}'
    match_num_string = f'{match_num}'

    if '.' in match_num_string:
        match_decimals = len(match_num_string.split('.')[1])
        curr_num_string = f'{curr_num:.{match_decimals}f}'
        curr_num_string = curr_num_string[:]
        return curr_num_string
    else:
        return f'{int(curr_num)}'


###########

def markets():

    markets_dict = client.public.get_markets()
    #print(markets.data['markets'])

    # put the markets into a dataframe
    markets_df = pd.DataFrame(markets.data['markets'])

    '''
    columns:
    Index(['AAVE-USD', 'ZEC-USD', 'ALGO-USD', 'ETH-USD', 'UMA-USD', '1INCH-USD',
       'SOL-USD', 'ADA-USD', 'ENJ-USD', 'CRV-USD', 'SNX-USD', 'SUSHI-USD',
       'FIL-USD', 'CELO-USD', 'ATOM-USD', 'XTZ-USD', 'BTC-USD', 'LINK-USD',
       'COMP-USD', 'YFI-USD', 'ICP-USD', 'DOT-USD', 'DOGE-USD', 'TRX-USD',
       'NEAR-USD', 'EOS-USD', 'ZRX-USD', 'MKR-USD', 'UNI-USD', 'ETC-USD',
       'LTC-USD', 'LUNA-USD', 'XMR-USD', 'MATIC-USD', 'BCH-USD', 'AVAX-USD',
       'XLM-USD', 'RUNE-USD'],
    '''

    return markets_dict, markets_df

def pos_info(symbol):

    try:
        # get open positions
        open_positions = client.private.get_positions(status='OPEN')
        open_pos_info = open_positions.data['positions']
        # print(open_pos_info)
        # time.sleep(786786)

        # Extract the desired information from the open_pos_info list
        # Extract the desired information from the open_pos_info list
        data = []
        for position in open_pos_info:
            size = position['size']
            # Check if the size is less than 0.01 and set it to 0 if it is
            size = 0 if (0 < float(size) < 0.01) or (0 > float(size) > -.01) else size
            data.append({
                'market': position['market'],
                'side': position['side'],
                'size': size,
                'entryPrice': position['entryPrice'],
                'unrealizedPnl': position['unrealizedPnl'],
                # add realized pnl
                'realizedPnl': position['realizedPnl']
            })

        # Create a pandas DataFrame from the extracted data
        pos_info_df = pd.DataFrame(data)

        # Print the DataFrame
        #print(pos_info_df)

        # create a limit order to close the position, in profit
        # get the market of the position
        symbol = data[0]['market']
        # get the entry price of the position
        entry_price = data[0]['entryPrice']
        entry_price = float(entry_price)
        # get the size of the position
        size = data[0]['size']
        size = float(size)
        if size >= .01:
            in_pos = True
            #print(f'In position: {symbol} and in_pos is {in_pos}')


        # get the side of the position
        side = data[0]['side']
        # get the unrealized pnl of the position
        unrealized_pnl = data[0]['unrealizedPnl']
        unrealized_pnl = float(unrealized_pnl)
        # realized pnl
        realized_pnl = data[0]['realizedPnl']
        realized_pnl = float(realized_pnl)
        # print(unrealized_pnl)
        # print(realized_pnl)

        # added this to make the perc negative
        if side == 'LONG':
            pnl_percentage = (realized_pnl + unrealized_pnl) / (entry_price * size) * 100
        else:
            pnl_percentage = (realized_pnl + unrealized_pnl) / (entry_price * size) * -100

        #print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')
        
        pos_info_df['pnl_perc'] = [pnl_percentage]

        accept_price = entry_price * 1.6 if side == 'BUY' else entry_price * 0.4
        # get markets
        markets = client.public.get_markets().data 
        tick_size = markets['markets'][symbol]['tickSize']
        accept_price = number_formatter(accept_price, tick_size)
        in_pos = True

    except:
        in_pos = False
        #print(f'Not in position and in_pos is {in_pos}')
        symbol, side, size, entry_price, unrealized_pnl, accept_price,pnl_percentage = None, None, 0, 0, 0, None,0

    # Create a copy of the DataFrame without 'unrealizedPnl' and 'realizedPnl' columns
    try:
        pos_info_df_copy = pos_info_df.drop(columns=['unrealizedPnl', 'realizedPnl'])
    except:
        pos_info_df_copy = pos_info_df

    # Print the DataFrame copy without 'unrealizedPnl' and 'realizedPnl' columns
    #print(pos_info_df_copy)

    return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl, accept_price, pnl_percentage , pos_info_df_copy

def pos_info_even_up(symbol):

    try:
        # get open positions
        open_positions = client.private.get_positions(status='OPEN')
        open_pos_info = open_positions.data['positions']
        # print(open_pos_info)
        # time.sleep(786786)

        # Extract the desired information from the open_pos_info list
        # Extract the desired information from the open_pos_info list
        data = []
        for position in open_pos_info:
            size = position['size']
            # # Check if the size is less than 0.01 and set it to 0 if it is
            # size = 0 if float(size) < 0.01 else size
            data.append({
                'market': position['market'],
                'side': position['side'],
                'size': size,
                'entryPrice': position['entryPrice'],
                'unrealizedPnl': position['unrealizedPnl'],
                # add realized pnl
                'realizedPnl': position['realizedPnl']
            })

        # Create a pandas DataFrame from the extracted data
        pos_info_df = pd.DataFrame(data)

        # Print the DataFrame
        #print(pos_info_df)

        # create a limit order to close the position, in profit
        # get the market of the position
        symbol = data[0]['market']
        # get the entry price of the position
        entry_price = data[0]['entryPrice']
        entry_price = float(entry_price)
        # get the size of the position
        size = data[0]['size']
        size = float(size)
        if size >= .0001:
            in_pos = True
            #print(f'In position: {symbol} and in_pos is {in_pos}')


        # get the side of the position
        side = data[0]['side']
        # get the unrealized pnl of the position
        unrealized_pnl = data[0]['unrealizedPnl']
        unrealized_pnl = float(unrealized_pnl)
        # realized pnl
        realized_pnl = data[0]['realizedPnl']
        realized_pnl = float(realized_pnl)
        # print(unrealized_pnl)
        # print(realized_pnl)

        # added this to make the perc negative
        if side == 'LONG':
            pnl_percentage = (realized_pnl + unrealized_pnl) / (entry_price * size) * 100
        else:
            pnl_percentage = (realized_pnl + unrealized_pnl) / (entry_price * size) * -100

        #print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')
        
        pos_info_df['pnl_perc'] = [pnl_percentage]

        accept_price = entry_price * 1.6 if side == 'BUY' else entry_price * 0.4
        # get markets
        markets = client.public.get_markets().data 
        tick_size = markets['markets'][symbol]['tickSize']
        accept_price = number_formatter(accept_price, tick_size)
        in_pos = True

    except:
        in_pos = False
        #print(f'Not in position and in_pos is {in_pos}')
        symbol, side, size, entry_price, unrealized_pnl, accept_price,pnl_percentage = None, None, 0, 0, 0, None,0

    # Create a copy of the DataFrame without 'unrealizedPnl' and 'realizedPnl' columns
    try:
        pos_info_df_copy = pos_info_df.drop(columns=['unrealizedPnl', 'realizedPnl'])
    except:
        pos_info_df_copy = pos_info_df

# ### IMPLEMENTED THIS TO GRAB THE POS AGAIN
#     # get open positions
#     open_positions = client.private.get_positions(status='OPEN')
#     open_pos_info = open_positions.data['positions']
#     # print(open_pos_info)
#     # time.sleep(786786)

#     # Extract the desired information from the open_pos_info list
#     # Extract the desired information from the open_pos_info list
#     data = []
#     for position in open_pos_info:
#         size = position['size']
        
#         data.append({
#             'market': position['market'],
#             'side': position['side'],
#             'size': size,
#             'entryPrice': position['entryPrice'],
#             'unrealizedPnl': position['unrealizedPnl'],
#             # add realized pnl
#             'realizedPnl': position['realizedPnl']
#         })

#     # Create a pandas DataFrame from the extracted data
#     pos_info_df = pd.DataFrame(data)

#     # Print the DataFrame
#     #print(pos_info_df)

#     # create a limit order to close the position, in profit
#     # get the market of the position
#     symbol = data[0]['market']
#     # get the entry price of the position
#     entry_price = data[0]['entryPrice']
#     entry_price = float(entry_price)
#     # get the size of the position
    # size = data[0]['size']
    # size = float(size)
    print(f'**** THIS IS THE SIZE {size}')

    if size >= .0001:
        in_pos = True
        #print(f'In position: {symbol} and in_pos is {in_pos}')

    return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl, accept_price, pnl_percentage , pos_info_df_copy


def accept_price(symbol, side, entry_price):

    '''
    this function is needed when closing orders
    we have to get an accept price
    '''
    # get markets
    markets = client.public.get_markets().data 
    tick_size = markets['markets'][symbol]['tickSize']
    accept_price = entry_price * 1.6 if side == 'LONG' else entry_price * 0.4
    accept_price = number_formatter(accept_price, tick_size)

    return accept_price

def ask_bid(symbol):

    # get the ask and bid
    ask_bid = client.public.get_orderbook(market=symbol)
    #print(ask_bid.data)
    # get the ask price
    ask = ask_bid.data['asks'][0]['price']
    ask_size = ask_bid.data['asks'][0]['size']
    # get the bid price
    bid = ask_bid.data['bids'][0]['price']
    bid_size = ask_bid.data['bids'][0]['size']

    ask_size2 = ask_bid.data['asks'][1]['size']
    ask_size3 = ask_bid.data['asks'][2]['size']

    top3asks = float(ask_size) + float(ask_size2) + float(ask_size3)
    # make a string
    top3asks_total = str(top3asks)

    # do the same for bid_size
    bid_size2 = ask_bid.data['bids'][1]['size']
    bid_size3 = ask_bid.data['bids'][2]['size']

    top3bids = float(bid_size) + float(bid_size2) + float(bid_size3)
    # make a string
    top3bids_total = str(top3bids)


    #print(f'ask is {ask} and bid is {bid} for {symbol}')
    #print(f'ask size is {ask_size} and bid size is {bid_size} for {symbol}')

    return ask, bid, ask_size, bid_size, top3asks_total, top3bids_total

def get_pnl_perc(symbol):

    #  return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl
    posinfo = pos_info(symbol)
    # posinfo df 
    pos_df = posinfo[0]
    #print(pos_df)
    
    in_pos = posinfo[1]
    #print(in_pos)

    # get in postion from df of that symbol
    side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
    # get size
    size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
    # float size
    size = float(size)
    size = size

    # get in_pos
    if size > 0:
        in_pos = True
        #print(f'In position: {symbol} and in_pos is {in_pos}')
    else:
        in_pos = False
        #print(f'Not in position and in_pos is {in_pos} for {symbol}')
    # entry price
    entry_price = pos_df.loc[pos_df['market']==symbol, 'entryPrice'].values[0]
    # float
    entry_price = float(entry_price)
    # unrealized pnl
    unrealized_pnl = pos_df.loc[pos_df['market']==symbol, 'unrealizedPnl'].values[0]
    # float
    unrealized_pnl = float(unrealized_pnl)
    # realized pnl
    realized_pnl = pos_df.loc[pos_df['market']==symbol, 'realizedPnl'].values[0]
    #flloat
    realized_pnl = float(realized_pnl)
    
    #print(unrealized_pnl, realized_pnl)
    #print(f'size is {size} and entry_price is {entry_price} and unrealized_pnl is {unrealized_pnl} and realized_pnl is {realized_pnl} for {symbol}')

# putting the one print here for pos info df
    #print(posinfo[9])

    # get pnl %
    try:
        pnl_percentage = (realized_pnl + unrealized_pnl) / (entry_price * size) * 100
    except:
        pnl_percentage = 0 

#print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')

    return pnl_percentage

def size_chunker(symbol, size, side):

    '''
    this function chunks orders in case our size is
    too big. it takes the top 3 bid sizez or asks
    and combines them to make a new size
    '''

    askbidinfo = ask_bid(symbol)
    ask_size_3_total = askbidinfo[4]
    bid_size_3_total = askbidinfo[5]
    print(f'ask size 3 total is {ask_size_3_total} and bid size 3 total is {bid_size_3_total} for {symbol}')

    if side == 'BUY' and float(size) > float(ask_size_3_total):
        size = float(ask_size_3_total)
        print(f'new size is {size} for {symbol}')
    elif side == 'SELL' and float(size) > float(bid_size_3_total):
        size = float(bid_size_3_total)
        print(f'new size is {size} for {symbol}')
        print('line 478')
    else:
        print(f'size is {size} for {symbol} no need to change')
        print('line 481')
    
    size = abs(size)
    size = round(size, 2)

    return size


## UPDATING CLOSE TO BE MARKET
def pnl_close(symbol, target_pnl, max_loss, kill_switch=False, reason='pnl close'):

    #  return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl
    posinfo = pos_info(symbol)
    # posinfo df 
    pos_df = posinfo[0]

    print(pos_df)

    try:
        # get in postion from df of that symbol
        side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
        # get size
        size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
    except:
        side = None
        size = 0 
    # float size
    size = float(size)
    size = abs(size)

    # get in_pos
    if size > 0:
        in_pos = True
        #print(f'In position: {symbol} and in_pos is {in_pos}')
    else:
        in_pos = False
        print(f'Not in position and in_pos is {in_pos} for {symbol}')

    # updated the pnl perc to be a function
    #posinfo = pos_info(symbol)
    pnl_percentage = posinfo[8]
    #print(f'pnl percentage is {pnl_percentage:.4f}% for {symbol}')

    #print(f'in_pos is {in_pos} and symbol is {symbol} and side is {side} and size is {size} and unrealized_pnl is {unrealized_pnl} and entry_price is {entry_price} pnl percentage is {pnl_percentage:.2f}%')
    size = abs(size)
    size = round(size, 3)
    time.sleep(.2)

    while pnl_percentage > target_pnl:

        #print('***************** ABOUT TO CLOSE 609')
        #time.sleep(777777)

        client.private.cancel_all_orders(market=symbol)

        # get ask and bid
        askbid =ask_bid(symbol)
        ask = askbid[0]
        bid = askbid[1]

        reason = reason + '- target profit hit'

### SETTING UP HERE TO RUN EACH LOOP
        posinfo = pos_info(symbol) 
        pos_df = posinfo[0]
        side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
        # get size
        size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
        # float size
        size = float(size)
        size = abs(size)

## 9/3 - adding in new way to get the limit_size and that will serve as new chunk size
    # removed chunk size
        top3asks = askbid[4]
        top3bids = askbid[5]
        top3asksbids = float(top3asks) + float(top3bids)
        if size > top3asksbids:
            limit_size = size/2 # half the size of position
        else:
            limit_size = size 

        # while in position is true and 
        # if the position is long, place a sell limit order
        if side == 'LONG' and float(size) > .001:

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            # use out function to place a limit order
            pre_limit_order = limit_order(symbol, 'SELL', limit_size, ask, reason=reason)
            sell_limit_order = market_close_order(symbol, 'SELL', limit_size, ask, reason=reason)
        
            print(f'just placed order  - sleeping 2')
            time.sleep(2)

        # if the position is short, place a buy limit order
        elif side == 'SHORT' and float(size) > .001:

            # - only resubmit the pnl close order if its not already there

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)

            # use out function to place a limit order
            pre_limit_order = limit_order(symbol, 'BUY', limit_size, bid , reason=reason)
            buy_limit_order = market_close_order(symbol, 'BUY', limit_size, bid, reason=reason)

            print(f'just placed order - sleeping 2')
            time.sleep(2)

        else:

            break 

### NOTE -- 9/3- IS THIS NEEDED TO ASK PPOS INFO 2X?
        # # check the unrealized pnl again
        # time.sleep(.2)
        # posinfo = pos_info(symbol)
        # # posinfo df 
        # pos_df = posinfo[0]

        posinfo = pos_info(symbol)
        pnl_percentage = posinfo[8]
        print(f'pnl percentage is {pnl_percentage:.4f}% for {symbol}')

    # elif statement for if unrealized pnl is less than max loss
    while pnl_percentage < max_loss or kill_switch == True and float(size) > 0:
        #print('***************** ABOUT TO CLOSE 724')
        #time.sleep(777777)
        askbid =ask_bid(symbol)
        ask = askbid[0]
        bid = askbid[1]
        time.sleep(.1)

        reason = reason + '- max loss hit'

        if kill_switch == True:
            reason = reason + '- kill switch called'


## GET SIZE HERE CAUSE IT CHANGES
        posinfo = pos_info(symbol) 
        pos_df = posinfo[0]
        try:
            # get in postion from df of that symbol
            side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
            # get size
            size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
        except:
            side = None
            size = 0 
            kill_switch = False
            break
        # float size
        size = float(size)
        size = abs(size)
        top3asks = askbid[4]
        top3bids = askbid[5]
        top3asksbids = float(top3asks) + float(top3bids)
        if size > top3asksbids:
            limit_size = size/2 # half the size of position
        else:
            limit_size = size 

        if float(size) < .001:
            kill_switch = False 
            print(f'size is {size} so setting kill switch to False')
            break 


        # if the position is long, place a sell limit order
        if side == 'LONG' and float(size) > .001:

            # MUST GET PNL PERC AGAIN
            pnl_percentage = get_pnl_perc(sym)

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            #print('just cancelled all orders')

            # use our function to place a limit order
            pre_limit_order = limit_order(symbol, 'SELL', limit_size, ask, reason=reason)
            sell_limit_order = market_close_order(symbol, 'SELL', limit_size, ask, reason=reason)

            print(f'just placed order - sleeping 2')
            time.sleep(2)

               # LONG, we need to sell to close, to sell immedaitely you sell at the bid
        # if the position is short, place a buy limit order
        elif side == 'SHORT' and float(size) > .001:

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)

            pre_limit_order = limit_order(symbol, 'BUY', limit_size, bid, reason=reason)
            buy_limit_order = market_close_order(symbol, 'BUY', limit_size, bid, reason=reason)
        
            print(f'just placed order - sleeping 2')
            time.sleep(2)

        posinfo = pos_info(symbol)
        pnl_percentage = posinfo[8]
        # posinfo df 
        pos_df = posinfo[0]
        ## GET SIZE HERE CAUSE IT CHANGES

        try:
            # get in postion from df of that symbol
            side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
            # get size
            size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
        except:
            side = None
            size = 0 
            kill_switch = False
            
        # float size
        size = float(size)
        size = abs(size)

    posinfo = pos_info(symbol)
    size = float(posinfo[4])

def nopost_limit_order(symbol, side, size, price, reason='no reason'):

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current UTC time
    current_time = datetime.utcnow()

    # Convert the current UTC time to Eastern Time
    current_time_eastern = current_time.astimezone(eastern_tz)

    # Format the current Eastern Time in the desired format
    current_time = current_time_eastern.strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)
    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)

    size = round(size, 1)
    size = str(size)
    print(f'about to place an order for {size} on {symbol}')

    # place limit buy order
    response = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side=side,
        order_type='LIMIT',
        post_only=False,
        size=size,
        price=price,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='GTT',
        reduce_only=False,
    )
    print(response.data)

    limit_order = response.data['order']  # Extract the JSON response from the Response object

    # Define the file path to the existing oms.csv file
    current_directory = os.path.dirname(os.path.abspath(__file__))
    oms_file_path = os.path.join(current_directory, 'oms.csv')

    # Update oms.csv with order details
    order_data = {
        'Datetime': [current_time],  # Include the current date and time in the order_data dictionary
        'Bot': [script_name],
        'Func': 'nopost_limit_order',
        'Symbol': [limit_order['market']],
        'Side': [limit_order['side']],
        'Size': [limit_order['size']],
        'Price': [limit_order['price']],
        'Reason': [reason],
        'ID': [limit_order['id']],
    }
    order_df = pd.DataFrame(order_data)

    # Read the existing oms.csv file if it exists
    if os.path.exists(oms_file_path):
        existing_df = pd.read_csv(oms_file_path)
    else:
        existing_df = pd.DataFrame()

    # Concatenate the existing DataFrame with the order_df
    updated_df = pd.concat([existing_df, order_df], ignore_index=True)

    # Append the updated DataFrame to the oms.csv file
    updated_df.to_csv(oms_file_path, index=False)

    return limit_order    


def pnl_close2(symbol, target_pnl, max_loss, kill_switch=False, reason='pnl close'):

    while True:
        # Fetch position info and decide what needs to be done
        print('looping pnl close... ')
        posinfo = pos_info(symbol)
        pos_df = posinfo[0]
        pnl_percentage = posinfo[8]
        size = float(posinfo[4])
        size = abs(size)
        print(pos_df)
        print(size)

        # If size is too small, exit loop
        if size < 0.001:
            break

        # Get current bid and ask prices
        askbid = ask_bid(symbol)
        ask = float(askbid[0])
        bid = float(askbid[1])
        print(bid)
        
        # Decide on the action based on PnL and position side
        action_required = None
        if pnl_percentage > target_pnl:
            action_required = 'profit'
        elif pnl_percentage < max_loss or kill_switch:
            action_required = 'loss'
        
        if not action_required: # because that means we are not in prof or loss
            break
        print(action_required)
        # Determine order side based on position side and action required
        order_side = None
        if pos_df.loc[pos_df['market'] == symbol, 'side'].values[0] == 'LONG':
            order_side = 'SELL'
            # Slightly lower the ask for faster execution 
            order_price = round(float(bid * 0.9995),1)
        elif pos_df.loc[pos_df['market'] == symbol, 'side'].values[0] == 'SHORT':
            order_side = 'BUY'
            # Slightly increase the bid for faster execution
            order_price = round(float(ask * 1.0005),1)

        if not order_side:
            break

        # Determine the chunk size for the order
        top3asks = float(askbid[4])
        top3bids = float(askbid[5])
        top3asksbids = top3asks + top3bids
        limit_size = min(size, top3asksbids / 2)
        limit_size = abs(limit_size)
        order_price = str(order_price)

        # Cancel any previous orders
        client.private.cancel_all_orders(market=symbol)
        print(f'placing a {order_side} order for {symbol} of {limit_size} at {order_price} current price = {bid}')
        # Place the new order and wait a bit before next iteration
        nopost_limit_order(symbol, order_side, limit_size, order_price, reason=reason)
        time.sleep(0.5)


def limit_order(symbol, side, size, price, reason='no reason'):

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current UTC time
    current_time = datetime.utcnow()

    # Convert the current UTC time to Eastern Time
    current_time_eastern = current_time.astimezone(eastern_tz)

    # Format the current Eastern Time in the desired format
    current_time = current_time_eastern.strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)
    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)

    size = round(size, 1)
    size = str(size)
    print(f'about to place an order for {size} on {symbol}')

    # place limit buy order
    response = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side=side,
        order_type='LIMIT',
        post_only=True,
        size=size,
        price=price,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='GTT',
        reduce_only=False,
    )
    print(response.data)

    limit_order = response.data['order']  # Extract the JSON response from the Response object

    # Define the file path to the existing oms.csv file
    current_directory = os.path.dirname(os.path.abspath(__file__))
    oms_file_path = os.path.join(current_directory, 'oms.csv')

    # Update oms.csv with order details
    order_data = {
        'Datetime': [current_time],  # Include the current date and time in the order_data dictionary
        'Bot': [script_name],
        'Func': 'limit_order',
        'Symbol': [limit_order['market']],
        'Side': [limit_order['side']],
        'Size': [limit_order['size']],
        'Price': [limit_order['price']],
        'Reason': [reason],
        'ID': [limit_order['id']],
    }
    order_df = pd.DataFrame(order_data)

    # Read the existing oms.csv file if it exists
    if os.path.exists(oms_file_path):
        existing_df = pd.read_csv(oms_file_path)
    else:
        existing_df = pd.DataFrame()

    # Concatenate the existing DataFrame with the order_df
    updated_df = pd.concat([existing_df, order_df], ignore_index=True)

    # Append the updated DataFrame to the oms.csv file
    updated_df.to_csv(oms_file_path, index=False)

    return limit_order


def format_number(curr_num, match_num):
    '''
    give the number with decimal desired
    function will return the correct formated string
    '''

    curr_num_string = f'{curr_num}'
    match_num_string = f'{match_num}'

    if '.' in match_num_string:
        match_decimals = len(match_num_string.split('.')[1])
        curr_num_string = f'{curr_num:.{match_decimals}f}'
        curr_num_string = curr_num_string[:]
        return curr_num_string
    else:
        return f"{int(curr_num)}"

def round_to_minsize(quantity, min_order_size):
    print(f'this is the size sent {quantity} type {type(quantity)} min size: {min_order_size}')
    min_order_size = float(min_order_size)
    quantity = float(quantity)
    if min_order_size == 1.0:
        rounded_quantity = round(quantity)
    elif min_order_size == 0.1:
        rounded_quantity = round(quantity,1)
    elif min_order_size == 0.01:
        rounded_quantity = round(quantity,2)
    elif min_order_size == 0.001:
        rounded_quantity = round(quantity,3)
    elif min_order_size == 0.0001:
        rounded_quantity = round(quantity,4)
    else:
        rounded_quantity = round(quantity)

    return rounded_quantity

def market_close_order(symbol, side, size, price, reason='no reason'):

    '''
**** THIS IS SO IMPORTANT
    THIS MARKET ORDER REDUCE ONLY
    NOTE: MUST SEND IN PRICE OF ASK if BUYING,and BUY IF SELING
    -- so i made this permenant below. 
    MARKET ORDERS ARE IOC or FOK only - so if you wanna get quicker
    use the nopost_limit_order that will close it all.
    '''

    askbid = ask_bid(symbol)
    if side == 'BUY':
        price = askbid[0]
    else:
        price = askbid[1]

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current date and time in the desired format
    current_time = datetime.now().strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)

    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)

    markets = client.public.get_markets().data 
    min_order_size = markets['markets'][symbol]['minOrderSize']
    #print(f'this is the min order size {min_order_size} for {symbol}')

    #size = 1.1 * size 
    print(f'size before round quantity func {size}')
    print(f'this is the type {type(size)}')
    size = round_to_minsize(size, min_order_size)
    print(f'this is the New rounded, ready to order size {size}')
    size = round(float(size),1)
    size = str(size)
    #print(f'about to place an order for {size} on {symbol}')

    # place limit buy order
    response = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side=side,
        order_type='MARKET',
        post_only=False,
        size=size,
        price=price,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='IOC',
        reduce_only=False,
    )
    print(response.data)

    limit_order = response.data['order']  # Extract the JSON response from the Response object

    # Update oms.csv with order details
    order_data = {
        'Datetime': [current_time],  # Include the current date and time in the order_data dictionary
        'Bot': [script_name],
        'Func': 'mkt_close_order',
        'Symbol': [limit_order['market']],
        'Side': [limit_order['side']],
        'Size': [limit_order['size']],
        'Price': [limit_order['price']],
        'Reason': [reason],
        'ID': [limit_order['id']],
    }
    order_df = pd.DataFrame(order_data)

    # Define the file path to the existing oms.csv file
    current_directory = os.path.dirname(os.path.abspath(__file__))
    oms_file_path = os.path.join(current_directory, 'oms.csv')
    
    # Read the existing oms.csv file if it exists
    if os.path.exists(oms_file_path):
        existing_df = pd.read_csv(oms_file_path)
    else:
        existing_df = pd.DataFrame()

    # Concatenate the existing DataFrame with the order_df
    updated_df = pd.concat([existing_df, order_df], ignore_index=True)

    # Append the updated DataFrame to the oms.csv file
    updated_df.to_csv(oms_file_path, index=False)

    return limit_order

# ask = ask_bid(sym)[0]
# market_close_order(sym, 'BUY', 1, ask)
# print(pos_info(sym))
# market_close_order(sym, 'SELL', 1, ask)
# print(pos_info(sym))
# time.sleep(89789)
# NOTE - 9/2 - i dont really use this market order, because on entry i limit
    # and on market close, i have a market close order right above.
def market_order(symbol, side, size, price):

    '''
    this marketorder works, i use it for the even up process which i implemented 8/15
    '''

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current date and time in the desired format
    current_time = datetime.now().strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)

    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)

    print(f'size before round quantity func {size}')
    print(f'this is the type {type(size)}')
    size = str(size)
    print(f'should be string now -- this is the type {type(size)}')

    # # Set the trigger price for GTT order
    # trigger_price = round(float(price) * 1.001,1)  # Adjust this value as needed .9997 == .03% slippage
    # trigger_price = str(trigger_price)

    # print(f'price of order {price} trigger price {trigger_price}')

    #place a MARKET order
    place_order = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side=side,
        order_type='MARKET',
        post_only=False,
        size=size,
        price=price,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='IOC', # could be 'GTT' or 'FOK'
        reduce_only=False,
)

# price = ask_bid(sym)[0]
# market_close_order(sym, 'BUY', .1, price, reason='testing our pnl close')

def sdz(symbol, timeframe):

    '''
    building out the supply and demand zones

    supply and demand is where the wicks of supp/resis ar
    demand zone - between the lowest low and lowest close
    '''

    sdz_df = pd.DataFrame()

    # get the ohlcv for the 15m timeframe
    ohlcv_df = ohlcv(symbol, timeframe, limit, sma)

    # get the lowest low and lowest close
    lowest_low = ohlcv_df['low'].min()
    lowest_close = ohlcv_df['close'].min()
    #print(lowest_low, lowest_close)

    # get the highest high and highest close
    highest_high = ohlcv_df['high'].max()
    highest_close = ohlcv_df['close'].max()

    # add 15m_sz to the dataframe
    # print symbol for sdz zone
    #print(f'this is the symbol {symbol}')
    sdz_df[f'{timeframe}_sz'] = [highest_close, highest_high]
    # add 15m_dz to the dataframe
    sdz_df[f'{timeframe}_dz'] = [lowest_close, lowest_low]

    return sdz_df

def get_dydx_funding_rate(dydxsymbol, fundrate_max, side):
    url = "https://api.dydx.exchange/v3/markets"
    response = requests.get(url)
    data = response.json()

    highest_funding_rate = -1
    highest_funding_symbol = ''

    # we want next funding rate cause that's the one that will be applied
    dydx_funding_rate = float(data['markets'][dydxsymbol]['nextFundingRate'])
    #print(f"Funding rate for {dydxsymbol}:", dydx_funding_rate)

    # if funding is positive, LONGS pay and shorts EARN
    # if funding is negative, SHORTS pay and LONGS EARN
    noskip = False
    if side == 'LONG':
        if dydx_funding_rate < fundrate_max:
            #print('we are long, funding rate is less than max.. no skip')
            noskip = True
        else:
            print('we are long, and funding too high, skipping...')
    elif side == 'SHORT':
        if dydx_funding_rate > -fundrate_max:
            #print('we are short, funding rate is greater than max.. no skip')
            noskip = True
        else:
            print('we are short, and funding too high, skipping...')
    else:
        #print('not in positon, no skip')
        noskip = False

    dydx_funding_rate = (dydx_funding_rate * 24 * 365)

    return dydx_funding_rate, noskip

def funding_skipper(sym, side):
    '''
    this closes positions in the last 3 mins of the hour
    and sleeps til new hour 
    '''

    current_time = datetime.utcnow()
    current_minute = current_time.minute
    current_second = current_time.second
    current_hour = current_time.hour
    #print(f'UTC: current hour is {current_hour} and current minute is {current_minute} and current second is {current_second}')

    dydx_funding_rate, noskip = get_dydx_funding_rate(sym, fundrate_max, side)
    print(f'funding rate is {round(dydx_funding_rate*100,3)}%/year')

    if side == 'LONG' or 'SHORT':
        dydx_funding_rate, noskip = get_dydx_funding_rate(sym, fundrate_max, side)


# NOTE - change below back to 57
    if 57 <= current_minute < 60 and current_second != 0 and noskip == False:
        print(f'current minute is {current_minute} and no skip is {noskip} so killing position')

        # updated our pnl close in order to accept a kill switch flag
        pnl_close2(sym, target_pnl, max_loss, kill_switch=True, reason='SKIPPER - pnl close kill switch')
        time.sleep(181)

def enter_position(bs, size):

    '''
    build a function to enter a position
    ask user to input daily bias, long or short
    if long, we will be buying dips, and if short, selling rips
    we only are going to enter at supply and demand zones
    '''

    # get the supply and demand zones
    sdz_df = sdz(sym, timeframe)
    #print(sdz_df)

    askbid = ask_bid(sym)
    ask = float(askbid[0])
    bid = float(askbid[1])


    # Access the 1HOUR_sz values in rows 0 and 1
    sz_row_0 = float(sdz_df[f'{timeframe}_sz'].iloc[0])
    sz_row_1 = float(sdz_df[f'{timeframe}_sz'].iloc[1])
    
    # 2 variables, sell1 (average of two sz rows) and sell2 (slightly under higher in % terms sz row)
    sell1 = str(round((sz_row_0 + sz_row_1) / 2,1))
    sell2 = str(round(sz_row_1 - (sz_row_1 * 0.01), 1))
    
    # Access the 1HOUR_sz values in rows 0 and 1
    dz_row_0 = float(sdz_df[f'{timeframe}_dz'].iloc[0])
    dz_row_1 = float(sdz_df[f'{timeframe}_dz'].iloc[1])
    #print(f'dz_row0 {dz_row_0} dz_row_1{dz_row_1}')

    # 2 variables, buy1 (average of two dz rows) and buy2 (slightly over lower in % terms dz row)
    buy1 = str(round((dz_row_0 + dz_row_1) / 2,1))
    buy2 = str(round(dz_row_1 *.997 ,1))
    #print(f'this is buy1 {buy1} and buy2 {buy2}')

    buy3 = str(round((float(buy1) + float(buy2))/2,1))
    #print(f'**** this would be buy 3 {buy3}')

# in the case that the bid is higher than the buy3, then we would enter
# at buy2 which is the lower SDZ
    if float(bid) < float(buy3):
        buy3 = buy2
        print(f'using BUY2 {buy2} and Buy3 cause Bid: {bid} is LESS than buy3 {buy3}')

    pos_info_df, in_pos, symbol, side, opensize, entry_price, unrealized_pnl, accept_price, pnl_percentage , pos_df_copy = pos_info(sym)

    #print(f'***** in pos {in_pos}')
    if in_pos == True:
        funding_skipper(sym, side)

    if not in_pos:
        size = pos_size *1 
    else:
        size = (pos_size - opensize)

    time.sleep(.1)

    
    # had to implement this in order to make it right tick
    buy1_fixed = round(((bid + float(buy2))/2),1)
    sell1_fixed = round(((ask+ float(sell2))/2),1)

    if float(buy1) > bid:
        buy1 = str(buy1_fixed)
    if float(buy2) > bid:
        buy2 = str(round(bid*.995,1))
    if float(sell1) < ask:
        sell1 = str(sell1_fixed)
    if float(sell2) < ask:
        sell2 = str(round(ask*1.005,1))

    #print(f'this is size{size}')
    #print(f'this is possize{pos_size}')

    size = abs(size)

    if bs == 'b':

        side = 'BUY'

        active_orders = client.private.get_active_orders(market=sym)
        active_orders = active_orders.data

        active_order_prices = [float(order['price']) for order in active_orders['orders']]

        if float(buy3) not in active_order_prices and float(opensize) < pos_size:
            client.private.cancel_all_orders(market=sym)
           
            limit_order(sym, side, size, buy3, reason='entering initial position as a buy')
            print(f'just placed buy3')
        else:
            print(f'buy3 already in  -- not submitting new orders but --OK TO ENTER')
        
    elif bs == 's':
        side = 'SELL'
        active_orders = client.private.get_active_orders(market=sym)
        active_orders = active_orders.data

        active_order_prices = [float(order['price']) for order in active_orders['orders']]

        print(f'active order prices are {active_order_prices}')
        client.private.cancel_all_orders(market=sym)

        
        if float(sell1) not in active_order_prices and opensize == 0:

            limit_order(sym, side, size, sell1, reason='entering initial position as a sell')
            print(f'just placed sell1')
        else:
            print(f'sell1 already in active orders OR we already have a pos')
        if float(sell2) not in active_order_prices and 0 < size < pos_size:
        

            limit_order(sym, side, size, sell2, reason='entering initial position as a sell')
            print(f'just placed sell2')
        else:
            print(f'sell2 already in active orders')

    # if open_size => pos_size, cancel all orders
    pos_info_df, in_pos, symbol, side, opensize, entry_price, unrealized_pnl, accept_price, pnl_percentage , pos_df_copy = pos_info(sym)
    if opensize >= pos_size:
        client.private.cancel_all_orders(market=sym)
        print(f'cancelled all orders, we are in a full position')

    return sdz_df

def daily_max_loss():

    '''
    looking at the portfolio max loss for the day
    looking at yesterdays value, vs todays
    if its bigger than max loss, close all positions
    '''

    # Get the current script's directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # Define the relative file path
    file_name = 'lockoutchecker.csv'
    # Join the script directory and file name to create the full file path
    file_path = os.path.join(script_dir, file_name)
    # Read the CSV file
    df = pd.read_csv(file_path)

    temp_df = pd.DataFrame()

    # get total balance on dydx
    acc = client.private.get_account()
    bal = acc.data['account']['quoteBalance']
    bal = float(bal)
    #print(bal)

     # get time 
    now = datetime.now()
    dt_string = now.strftime('%m/%d/%Y %H:%M:%S')
    #print(dt_string)
    comptime = int(time.time())
    comptime = comptime 
    #print(comptime)

    # get all positions and then sum up the pnl 
    posinfo = pos_info(sym)
    side = posinfo[3]
    size = posinfo[4]
    size_usd = size * float(ask_bid(sym)[0])
    posinfo_df = posinfo[0]

    if side == 'LONG':
        bal = bal + size_usd# + # position size
    elif side == 'SHORT': # short works now
        bal = bal - abs(size_usd)
    else:
        bal = bal

    try:
        pnlsum = posinfo_df['unrealizedPnl'].sum()
        bal = float(bal)
        pnlsum = float(pnlsum)
    except:
        pnlsum = 0

    realtime_balance = bal + pnlsum

    temp_df['comptime'] = [comptime] 
    temp_df['datetime'] = [dt_string]
    #temp_df['total_bal'] = [total_bal]
    temp_df['realtime_bal'] =[realtime_balance]

    lockout_hours = 60 * 60 * 16
    twenty_4hrs_ago = comptime - lockout_hours

    df_24hrs_ago = df.loc[df['comptime'] <= twenty_4hrs_ago]

    try: # this will fail if not 24 hours of data
        # then we just grab earliest data
        bal_24hrs_ago = df_24hrs_ago['realtime_bal'].values[-1]
        dt_24hrs_ago = df_24hrs_ago['datetime'].values[-1]
    except:
        bal_24hrs_ago = df['realtime_bal'].values[0]
        dt_24hrs_ago = df['datetime'].values[0]

    #########
    bal_24hrs_ago = float(bal_24hrs_ago)
    # do same for last bal

    lockout_loss = (bal_24hrs_ago * (daily_max_loss_perc/100))
    #print(f'this is lockout_loss {lockout_loss}')

    # get the last balance 
    last_bal = df['realtime_bal'].values[-1]
    #print(f'this is lastbal {last_bal}') # 688
    last_bal = float(last_bal)

    #print(f'this is bal 24 hours ago {bal_24hrs_ago}')

    # lowestbal_allowerd = add total bal + locklos
## 7/13- just marked this out cause im using a fixed variable
    #lowest_bal_allowed = lowest_bal_allowed # 16 hr bal - lockoutloss
    print(f'this is lowest_bal_allowed {lowest_bal_allowed} this is current: {last_bal}')

    # need to see if last total bal < loswestbal_allowed
    last_bal_small_q_24hrsago = last_bal < lowest_bal_allowed


    ## 8/15 only check this if NOT in position

    if last_bal_small_q_24hrsago == True:
        # kill switch - for ALL positions cause lock out actived
        print('we are under the lowest balance so will not enter anymore.. 8/15- not closing, but wont open again...')

        posinfo_df, in_pos, symbol, side, opensize, entry_price, unrealized_pnl, accept_price, pnl_percentage , pos_df_copy = pos_info(sym)
        
        try:
            open_symbols = posinfo_df['market'].unique().tolist()
        except:
            open_symbols = []
        # for symbol in open_symbols:
        #     pnl_close(symbol, target_pnl, max_loss, kill_switch=True)
    else:
        #print('we are gucci on the lockout, not needed')
        hi = 'hi'

    # Append the new data to the DataFrame
    df = pd.concat([df, temp_df])


    # Save the updated DataFrame to the CSV file in the same directory as the script
    df.to_csv(file_path, index=False)

    return last_bal_small_q_24hrsago

def sleep_and_check_pnl(minutes):
    seconds_interval = 60  # Check pnl_close every minute
    for _ in range(minutes * 60 // seconds_interval):
        # Call your pnl_close function here
        in_pos = pos_info(sym)[1]
        print('inpos =')
        if in_pos:
            pnl_close2(sym, target_pnl, max_loss, kill_switch=False, reason='sleep n check pnl func pnl close')
        
        print(f'canceling all orders and sleeping for 30s and checking again')
        client.private.cancel_all_orders(market=sym)
        time.sleep(30)

def was_fill_in_last_minutes(fills, minutes):
    current_time = datetime.utcnow()
    time_threshold = current_time - timedelta(minutes=minutes)

    for fill in fills:
        fill_time_str = fill['createdAt']
        fill_time = datetime.strptime(fill_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')

        if fill_time >= time_threshold:
            return True

    return False

def total_24_volume():

    # New code for fill checking and sleeping
    all_fills = client.private.get_fills(market=sym)
    all_fills = all_fills.data
    #print(all_fills)
    fills = all_fills['fills']
    fill_side = fills[0]['side']

    bid = ask_bid(sym)[1]

    current_time = datetime.utcnow()
    time_threshold = current_time - timedelta(minutes=1440) # this is 24 hours

    total_volume = 0

    for fill in fills:
        fill_time_str = fill['createdAt']
        fill_time = datetime.strptime(fill_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        if fill_time > time_threshold:
            total_volume += float(fill['size']) * float(bid)


    return total_volume



def place_order_time():
    current_time = datetime.now()
    minutes = current_time.minute
    return minutes % 15 == 0 and minutes != 45

def trailing_stop(close_under=close_underr, reason='Trailing Stop'):

    '''
    part 1 - simple update by hand if price falls under x price close
    part 2- hey if pnl get to X%, then implement trailing stop
    '''

    # get price 
    price = ask_bid(sym)[0]

    if float(price) < close_under:

        print(f'price is {price} and close_under is {close_under} CLOSING POSITION')

        pnl_close2(sym, target_pnl, max_loss, kill_switch=True, reason=reason)

        trailingstop = True

    else:
        print(f'price is {price} and close_under is {close_under} not closing position')
        trailingstop = False

    return trailingstop
        
def no_top_candle_entries():

    '''
    this function doesnt let us buy the top portion of a 15min candle when
    a signal for buy has happened, and the inverse for short.
    '''
    # print current time in gmt 
    current_time_utc = datetime.utcnow()
    #print(f'current time in gmt is {current_time_utc}')

    # get the ohlcv 
    df = ohlcv(symbol=sym, timeframe='15MINS', limit=limit, sma=sma)
    #print(df)

    # get the last bars low and high
    last_low = float(df['low'].iloc[-1])
    last_high = float(df['high'].iloc[-1])

    # get the current price 
    askprice = ask_bid(sym)[0]
    print(f'last low is {last_low} and last high is {last_high} and askprice is {askprice}')

    # calculate the total range and bottom third
    total_range = last_high - last_low
    bottom_third = last_low + (total_range * 0.33)

### ONLY DO THIS IF IN POSITION AND AND we just entered in last 1 min
    # check if in position
    posinfo = pos_info(sym)
    posinfo_df = posinfo[0]
    df_less = posinfo[9]
    open_poside = posinfo[3]
    side = posinfo[3]
    in_pos = posinfo[1]
# did we just enter in the last minute?
    all_fills = client.private.get_fills(market=sym)
    all_fills = all_fills.data
    #print(all_fills)
    fills = all_fills['fills']
    fill_side = fills[0]['side']
    #print(fills)
    df_fills = pd.DataFrame(fills)
    #print(df_fills)
    #print(df_fills.columns)
    entered_in_last_min = False

    # last createdAt time
    last_createdAt = df_fills['createdAt'].iloc[0]
    #print(last_createdAt)

    dt = datetime.fromisoformat(last_createdAt.replace('Z', '+00:00'))
    epoch_time = int(dt.timestamp())
    #print(epoch_time)

    now = datetime.now()
    dt_string = now.strftime('%m/%d/%Y %H:%M:%S')
    #print(dt_string)
    comptime = int(time.time())
    comptime = comptime 
    #print(comptime)

    if comptime - epoch_time < 20:
        entered_in_last_min = True
        print('we entered in the last minute, setting entered to true')


    if in_pos and entered_in_last_min == True:

        if float(askprice) < float(bottom_third):
            print('we are ok that we entered...')
            ok_to_enter = True
        else:
            print('entered in the top 2/3rd when we shouldnt have... ')
            ok_to_enter = False
            #pnl_close2(sym, target_pnl, max_loss, kill_switch=True, reason='TOP 2/3rd - pnl close kill switch True')

    if float(askprice) < float(bottom_third):
        print('------- WE ARE OK TO ENTER')
        ok_to_enter = True
    else:
        print('we are in the top 2/3 of the candle. setting ok to enter to FALSE')
        ok_to_enter = False

    return ok_to_enter

def check_time_for_size():

    '''
    if the time eastern is between 7am and 8p we are full size 
    if its overnight, we are 1/5th size

    HOW TO IMPLMENT
    pos_size = check_time_for_size()
    '''

    eastern_tz = pytz.timezone('America/New_York')
    current_time_eastern = datetime.now(eastern_tz).hour

    if 7 <= current_time_eastern < 19:
        return pos_size 
    else:
        return pos_size / 5 

def over20sma():

    # hard coding in the 20 sma 

    ohlc = ohlcv(symbol='ETH-USD', timeframe='1HOUR', limit=50, sma=20)

     # Assuming the 'signal' column contains multiple values and you want the last one
    last_signal = ohlc['signal'].iloc[-1]

    if last_signal == 1:

        no_trading = False 
        print('sig is 1 so no_trading = False')
    else:
        no_trading = True
        print('sig is 0 so no_trading = True')

    return no_trading

def add_to_winners():

    '''
    build a function that adds to winners, this will only happen
    if we are winning and in position

    TODO -
    - figure out how to pass in a new trailiing stop here
        - maybe a while loop that it chills in until closed, but may not be good
        - maybe write to a file the new trailing stop 

    - adding up to 5x Pos_size if in profit, but need to figure out how to exit on entry price in this case or smaller stop 

    what if, i do tsomething like, log the first entry and if over 1 hour, we put the sotp at b/e?

    '''

    # check to see if in profit, if yes, add pos_size again up to 5x size

    posinfo = pos_info(sym)
    posinfo_df = posinfo[0]
    df_less = posinfo[9]
    open_size = posinfo[4]
    side = posinfo[3]
    in_pos = posinfo[1]
    pnlperc = posinfo[8]
    entryprice = posinfo[5]

    # get price a few under bid 
    bid = ask_bid(sym)[1]


    if open_size < (5 * pos_size) and pnlperc > .19:
        ## MAKE THE TRAILING STOP ENTRY PRICE AND IT WILL CHANGE AS WE GET BIGGER
        
        side = 'BUY'
    
        if .6 > pnlperc > .4 and open_size < (2*pos_size):
            print('entering 1 more pos size...')

            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid, reason='adding size cuz up .4-.6%')
            print(f'just placed order since we are between .4% and .6% in profit')

        elif .8 > pnlperc > .6 and open_size < (3*pos_size):

            print('entering 1 more pos_size... ')
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid, reason='adding size cuz up .6-.8%')
            print(f'just placed order since we are between .6-.8% in profit')

        elif 1 > pnlperc > .8 and open_size < (4*pos_size):

            print('entering 1 more pos_size... ')
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid, reason='adding size cuz up .8-1%')
            print(f'just placed order since we are between %.8-1% in profit')


        print('sleeping 61 seconds to not trigger close..')
        time.sleep(61)



def close_toolong_in_sz():

    '''
    if we are in position and have been chilling in a SZ 
    or dip out of it for more than 15mins, i bounce and can rebuy later in the DZ
    '''

def count_bars_in_zone(symbol, ohlcv_data, zone):
    ''' 
    Count how many bars the price has been in a specific zone 

    ELIF1
    Imagine you have a toy box, and inside this toy box are toy blocks stacked 
    one on top of the other. Each block has a number written on it, representing its value. 
    Now, let's pretend you want to see how many blocks have a number that falls between two other 
    specific numbers, let's say 5 and 10. Every time you find a block with a number between 5 and 10 
    (including 5 and 10), you'll place a bead in a jar. At the end, by counting the beads in the jar, 
    you'll know how many blocks had a number between 5 and 10.

    So, in simple words, this code is checking how many times a certain value (row['close']) falls 
    between two other specific values (zone[0] and zone[1]) and counting them.
    '''
    # Get the current ask price as the current_price
    current_price, _, _, _, _, _ = ask_bid(symbol)
    
    count = 0
    for _, row in ohlcv_data.iterrows(): # This is like going through each toy block inside the toy box, one by one.
        # Compare the current_price to the zone
        if zone[0] <= current_price <= zone[1]: # if zone[0] <= row['close'] <= zone[1]:: This checks if the number on the block (represented by row['close']) is between our two specific numbers (which are zone[0] and zone[1] - similar to 5 and 10 in our analogy).
            count += 1
    return count

def time_in_zones(symbol):
    '''
    If in SZ too long, and in position, get out. If fly through SZ, hold.
    If in DZ too long, exit.
    Emergency exit is also considered.

    TODO - think of a more sophisticated way to check DZ, cause what if just entered/?
    ''' 

    # Get the current position information
    pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl, accept_price, pnl_percentage, pos_info_df_copy = pos_info(symbol)
    
    # Check if we're in a position
    if in_pos:
        # Get the OHLCV data
# NOTE - this is where i put the timeframe -- for now, over 20 mins close. 
        ohlcv_data = ohlcv(symbol=symbol, timeframe='5MINS', limit=100, sma=50)  # Parameters set as examples

        # Get the supply and demand zones
        zones_df = sdz(symbol, timeframe)
        #print(zones_df)
        
        # Check bars in the SZ
        sz_time = count_bars_in_zone(symbol, ohlcv_data, zones_df[f'{timeframe}_sz'].tolist())
        
        if sz_time >= 3:  # More than 45 minutes in SZ
            # TODO: Implement exit mechanism here
            # e.g. pnl_close(kill_switch) 
            pnl_close2(symbol, target_pnl, max_loss, kill_switch=True, reason='TIME IN ZONES - pnl close kill switch True')
        else:
            print(f'in a supply zone by less than 20mins...')

        # # Check bars in the DZ
        # dz_time = count_bars_in_zone(symbol, ohlcv_data, zones_df[f'{timeframe}_dz'].tolist())
        
        # if dz_time > 4:  # More than 60 minutes in DZ
        #     # TODO: Implement exit mechanism here
        #     pnl_close(symbol, target_pnl, max_loss, kill_switch=True)
        # else:
        #     print('in a demand zone by less than 60mins...')
    else:
        print('Not in a position currently.')

def evenup_market_close_order(symbol, side, size, price, reason='no reason'):

    '''
**** THIS IS SO IMPORTANT
    THIS MARKET ORDER REDUCE ONLY
    NOTE: MUST SEND IN PRICE OF ASK if BUYING,and BUY IF SELING
    -- so i made this permenant below. 
    MARKET ORDERS ARE IOC or FOK only
    '''

    askbid = ask_bid(symbol)
    if side == 'BUY':
        price = askbid[0]
    else:
        price = askbid[1]

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current date and time in the desired format
    current_time = datetime.now().strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)

    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)

    markets = client.public.get_markets().data 
    min_order_size = markets['markets'][symbol]['minOrderSize']
    #print(f'this is the min order size {min_order_size} for {symbol}')

    #size = 1.1 * size 
    print(f'size before round quantity func {size}')
    print(f'this is the type {type(size)}')
    #size = round_to_minsize(size, min_order_size)
    print(f'this is the New rounded, ready to order size {size}')

    if symbol == 'ETH-USD':
        size = round(float(size),3)
    elif symbol == 'SOL-USD':
        size = round(float(size), 2)
    size = str(size)
    #print(f'about to place an order for {size} on {symbol}')

    # place limit buy order
    response = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side=side,
        order_type='MARKET',
        post_only=False,
        size=size,
        price=price,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='IOC',
        reduce_only=False,
    )
    print(response.data)

    limit_order = response.data['order']  # Extract the JSON response from the Response object

    # Update oms.csv with order details
    order_data = {
        'Datetime': [current_time],  # Include the current date and time in the order_data dictionary
        'Bot': [script_name],
        'Func': 'mkt_close_order',
        'Symbol': [limit_order['market']],
        'Side': [limit_order['side']],
        'Size': [limit_order['size']],
        'Price': [limit_order['price']],
        'Reason': [reason],
        'ID': [limit_order['id']],
    }
    order_df = pd.DataFrame(order_data)

    # Define the file path to the existing oms.csv file
    current_directory = os.path.dirname(os.path.abspath(__file__))
    oms_file_path = os.path.join(current_directory, 'oms.csv')
    
    # Read the existing oms.csv file if it exists
    if os.path.exists(oms_file_path):
        existing_df = pd.read_csv(oms_file_path)
    else:
        existing_df = pd.DataFrame()

    # Concatenate the existing DataFrame with the order_df
    updated_df = pd.concat([existing_df, order_df], ignore_index=True)

    # Append the updated DataFrame to the oms.csv file
    updated_df.to_csv(oms_file_path, index=False)

    return limit_order
    
def even_up(sym, size):

    '''
    checks to see if we have a weird number under 1 size
    '''

    ask = ask_bid(sym)[0]

    if (0 < abs(size) < .1 )or (size < 0): # closing shorts

        print(f'**{sym} abs(size) is smaller than .1 its {size} so going to even up')

        if sym == 'SOL-USD':

            even_size = 2

            if size > 0:
                
                buy_size = even_size-size # .008 SOL .. 2 - .008 == 1.992
                buy_mkt_order = evenup_market_close_order(sym, 'BUY', buy_size, ask, reason='Even up function - buy')
                print(f'just bought {buy_size} SOL to even up so i can sell two and fix bot...')
                time.sleep(1)

                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]

                print(f'now about to sell back to even up selling {sym} {opensize}')
                sell_mkt_order = evenup_market_close_order(sym, 'SELL', opensize, ask, reason='Even up function - sell')
                # market_close_order(sym, 'SELL', opensize, ask, reason='Even up function - sell')
                print('just closed the order and should be clean now...')
                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]
                print(f'for {sym} opensize is now {opensize}')
                time.sleep(3)
            elif size < 0:
                sell_size = even_size+size # -.1+ -.009 = -.1009
                
                opensize = abs(sell_size)
                sell_mkt_order = evenup_market_close_order(sym, 'SELL', sell_size, ask, reason='Even up function - sell') # should now how 1.0018

                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]

                print(f'now about to buy back to even up selling {sym} {opensize}')
                
                opensize = abs(opensize)
                buy_mkt_order = evenup_market_close_order(sym, 'BUY', opensize, ask, reason='Even up function - buy')
            # market_close_order(sym, 'SELL', opensize, ask, reason='Even up function - sell')
                print(f'just bought {opensize} SOL to even up so i can sell two and fix bot...') # .1
                time.sleep(1)

                print('just closed the order and should be clean now...')
                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]
                print(f'for {sym} opensize is now {opensize}')
                time.sleep(3)
        elif sym == 'ETH-USD':

            '''
            min size on eth is .01
            '''

            if size > 0: # means its in a long

                even_size = .1 

                buy_size = even_size-size # .09 .1-.009 = .091
                buy_mkt_order = evenup_market_close_order(sym, 'BUY', buy_size, ask, reason='Even up function - buy')
            # market_close_order(sym, 'SELL', opensize, ask, reason='Even up function - sell')
                print(f'just bought {buy_size} ETH to even up so i can sell two and fix bot...') # .1
                time.sleep(1)

                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]

                print(f'now about to sell back to even up selling {sym} {opensize}')
                opensize = abs(opensize)
                sell_mkt_order = evenup_market_close_order(sym, 'SELL', opensize, ask, reason='Even up function - sell')
                print('just closed the order and should be clean now...')
                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]
                print(f'for {sym} opensize is now {opensize}')
                time.sleep(3)
            elif size < 0:

                even_size = -.1 

                sell_size = even_size+size # -.1+ -.009 = -.1009
                sell_size = abs(sell_size)
                sell_mkt_order = evenup_market_close_order(sym, 'SELL', sell_size, ask, reason='Even up function - sell') # should now how 1.0018

                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]

                print(f'now about to buy back to even up selling {sym} {opensize}')
                
                opensize = abs(opensize)
                buy_mkt_order = evenup_market_close_order(sym, 'BUY', opensize, ask, reason='Even up function - buy')
            # market_close_order(sym, 'SELL', opensize, ask, reason='Even up function - sell')
                print(f'just bought {opensize} ETH to even up so i can sell two and fix bot...') # .1
                time.sleep(1)

                print('just closed the order and should be clean now...')
                posinfo = pos_info_even_up(sym)
                posinfo_df = posinfo[0]
                df_less = posinfo[9]
                open_poside = posinfo[3]
                side = posinfo[3]
                in_pos = posinfo[1]
                opensize = posinfo[4]
                print(f'for {sym} opensize is now {opensize}')
                time.sleep(3)

    else:
        print('even up function done.. no clean up needed cause not in between...')

def btc_vol():
    '''
    if the volatility in the last 4 hours is too high, go to the beach
    if BTC range > max_btc_downside_vol to the downside
    '''
    btc_ohlc = ohlcv('BTC-USD', '1HOUR', 5, 20)

    # Convert 'close' column to float
    btc_ohlc['close'] = btc_ohlc['close'].astype(float)


    # Get the minimum close value in the last 4 hours
    min_close_last_4_hours = btc_ohlc['close'].tail(4).min()

    # Get the maximum close value in the last 4 hours
    max_close_last_4_hours = btc_ohlc['close'].tail(4).max()

    # Calculate the range
    range_last_4_hours = max_close_last_4_hours - min_close_last_4_hours

    # Determine the direction of change
    direction = btc_ohlc['close'].iloc[-1] - btc_ohlc['close'].iloc[-4]

    # Check conditions
    if range_last_4_hours > max_btc_downside_vol and direction < 0:
        no_trading = True
    else:
        no_trading = False

    return no_trading

import time
import pandas as pd

def time_to_fill(symbol, size):
    """
    NOTE - i removed Post only so all orders will fill. 

    Places an order of a given type (buy/sell) and size for a given symbol. 
    Measures the time it takes for the order to be filled.
    
    Args:
    - symbol (str): The asset's symbol.
    - side (str): The type of order (e.g., 'BUY' or 'SELL').
    - size (float): The size of the order.
    
    Returns:
    - fill_time (float): The time taken for the order to be filled.
    - volume (float): Market volume at the time of order fill.
    - volatility (float): Market volatility at the time of order fill.

    TODO - 
    - implement random start with buy or sell 
    - assume what means --> add to indicator excel 
    - think about, what about when we put an order in and then price goes against us?
        then it will take super long to fill cuz the price is far away
    - lookbsvk and backtest to see what happens when long fill time
        - it may be liquidity
    SOLVED - pos only false - if status is not 'OPEN' or 'FILLED' reorder, cause rejected 'CANCELED'
        - if cancled, reorder, but i need to put in a new function for ordering so its not dirty
    BENEFITS -
    - liquidity indication, if both sides take a long time, low liq in market, move to other
    - 

    Ideas
    - if its taking tooo long to fill the buy... thats and indi right? maybe. market buy.
        - could be a great scalp opp

    ideas for later
     ## could be super interesting to lok at volume at the same time.. and vol...
 #  chat gpt suggested this.   
    # # Get market data
    # market_data = client.public.get_market_data(symbol=symbol)
    # volume = market_data['volume']
    # volatility = market_data['volatility']  # assuming the API provides this
    
    """

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current UTC time
    current_time = datetime.utcnow()

    # Convert the current UTC time to Eastern Time
    current_time_eastern = current_time.astimezone(eastern_tz)

    # Format the current Eastern Time in the desired format
    current_time = current_time_eastern.strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)
    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)
    
    size = round(size, 1)
    size = str(size)
    print(f'about to place an order for {size} on {symbol}')


#################################################

## BUY SIDE FIRST
    askbid = ask_bid(symbol)
    ask = askbid[0]
    bid = askbid[1]
    response_buy = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side='BUY',
        order_type='LIMIT',
        post_only=False,
        size=size,
        price=bid,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='GTT',
        reduce_only=False,
    )
    print(response_buy.data)
    order_id_buy = response_buy.data['order']['id']
  
    print(order_id_buy)
    #time.sleep(8978)
    
    start_time_buy = time.time()
    print(f'this is start time for buy {start_time_buy}')
    
    # Poll for the order's status until it's filled
    while True:
        print('===')
        status_response_buy = client.private.get_order_by_id(order_id_buy)
        print(status_response_buy.data)
        if (status_response_buy.data['order']['status'] == 'FILLED') or ( status_response_buy.data['order']['status'] == 'CANCELED'):
            break
        time.sleep(.2)  # Wait for 5 seconds before checking again
    
    fill_time_buy = time.time() - start_time_buy
    print(f'this is fill time for buy {fill_time_buy}')
    print('')
    print('----')

## SELL SIDE 2ND

    eastern_tz = pytz.timezone('America/New_York')

    # Get the current UTC time
    current_time = datetime.utcnow()

    # Convert the current UTC time to Eastern Time
    current_time_eastern = current_time.astimezone(eastern_tz)

    # Format the current Eastern Time in the desired format
    current_time = current_time_eastern.strftime('%m-%d-%y %H:%M:%S')

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)
    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)
    
    askbid = ask_bid(symbol)
    ask = askbid[0]
    bid = askbid[1]
    response_sell = client.private.create_order(
        position_id=position_id,
        market=symbol,
        side='SELL',
        order_type='LIMIT',
        post_only=False,
        size=size,
        price=ask,
        limit_fee='0.015',
        expiration_epoch_seconds=expiration.timestamp(),
        time_in_force='GTT',
        reduce_only=False,
    )
    print(response_sell.data)
    order_id_sell = response_sell.data['order']['id']
  
    print(order_id_sell)
    #time.sleep(8978)
    
    start_time_sell = time.time()
    print(f'this is start time for sell {start_time_sell}')
    
    # Poll for the order's status until it's filled
    while True:
        print('===')
        status_response_sell = client.private.get_order_by_id(order_id_sell)
        print(status_response_sell.data)
        if (status_response_sell.data['order']['status'] == 'FILLED') or (status_response_sell.data['order']['status'] == 'CANCELED'):
            break
        time.sleep(.2)  # Wait for 5 seconds before checking again
    
    fill_time_sell = time.time() - start_time_sell
    print(f'this is fill time for sell {fill_time_sell}')
    print('')
    print('----')

     # Get the path to the current directory
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # Check if the CSV file already exists in the directory
    csv_filename = os.path.join(current_directory, 'time_to_fill.csv')
    if os.path.exists(csv_filename):
        # Load the existing DataFrame from the CSV file
        df = pd.read_csv(csv_filename)
    else:
        # Create a new DataFrame if the CSV file doesn't exist
        df = pd.DataFrame(columns=['Timestamp', 'Fill Time Buy', 'Fill Time Sell'])

    # Add new data to the DataFrame
    new_data = {
        'Timestamp': [current_time_eastern],
        'Fill Time Buy': [round(fill_time_buy,1)],
        'Fill Time Sell': [round(fill_time_sell,1)]
    }
    new_df = pd.DataFrame(new_data)
    df = pd.concat([df, new_df], ignore_index=True)

    # Save the DataFrame as a CSV file
    df.to_csv(csv_filename, index=False)


    print(f'fill time csv updated... saved to {csv_filename}')

    return fill_time_buy, fill_time_sell, df 

# You can then integrate this function into your existing system to get insights
# and add the data to an indicator dataframe:
def add_time_to_fill_indicator(symbol, order_type, order_size):

    fill_time, volume, volatility = time_to_fill(symbol, order_type, order_size)
    indicator_data = {
        'symbol': symbol,
        'order_type': order_type,
        'order_size': order_size,
        'fill_time': fill_time,
        'volume': volume,
        'volatility': volatility
    }
    indicator_df = pd.DataFrame([indicator_data])
    return indicator_df

# # Example:
# indicator_df = add_time_to_fill_indicator('BTC', 'BUY', 1.0)
# print(indicator_df)



def calculate_profit_per_minute(unrealized_profit, time_interval):

    '''
    implement Profit Per Minute Indicator:

You can use the profit per minute as an indicator in your trading algorithm to assess 
the current profitability rate. Here's how you can use this indicator:

Calculate the profit per minute when you're evaluating your position's unrealized profit. 
Compare it to your historical data or a predefined threshold to assess whether the current profit 
per minute is higher or lower than usual.
If the profit per minute is abnormally high, it might indicate a strong short-term price 
movement in your favor. This could signal that the market is moving quickly and may continue to do so.
If the profit per minute is abnormally low or negative, it might suggest that the market 
is moving against your position quickly. This could prompt you to reconsider your strategy 
and potentially close the position to limit losses.
Close Position Based on Profit Per Minute:

When the profit per minute reaches a certain threshold or deviates significantly from 
your historical data, you can use it as a trigger to take action:

If the profit per minute is exceptionally high, it might be a signal to consider 
closing your position to secure the gains.
If the profit per minute is exceptionally low or negative, it might indicate 
unfavorable market conditions, and you might want to close the position to limit potential losses.
    '''
    return unrealized_profit / time_interval

# ask if we want to Buy or Sell all day
#bs = input('buying or selling today? (b/s or anything to control risk):')
bs = 'b'

def bot():

    '''
    this is is where you make changes to your strategy
    '''

    current_time_utc = datetime.utcnow()
    formatted_time = current_time_utc.strftime("%Y-%m-%d %H:%M:%S")
    
# this gets our position size by looking at the time 
# DONE and tested
    #pos_size = check_time_for_size()

    no_trading = False

# check if above 20sma, if under no_trading = true
# DONE but not activating yet.. cause i may want to buy some capitulations
    # no_trading = over20sma()
    # print(f'just checked the sma if over 20 and its {no_trading}')

# CHECKING TOTAL VOLUME TO NOT OVER TRADE
    total_vol_24hrs = total_24_volume()

    if total_vol_24hrs > 10000000:
        no_trading = True

# CHECKING BTC VOLATILITY IN PAST 4 HOURS TO THE DOWNSIDE
    no_trading_status = btc_vol()
    print(f'BTC Vol No Trading: {no_trading_status}')

    if no_trading_status == True:
        no_trading = True 

    print('')
    print('---------')
    print(f"time (GMT): {formatted_time} {sym} size: {pos_size} timeframe: {timeframe} ")
    print(f'target: {target_pnl}% and max loss: {max_loss}%')

    print(f'this is total volume past 24 hours: {total_vol_24hrs} no trading is set to {no_trading}')

    posinfo = pos_info(sym)
    posinfo_df = posinfo[0]
    df_less = posinfo[9]
    open_size = posinfo[4]
    side = posinfo[3]
    in_pos = posinfo[1]
    entryprice = posinfo[5]

# DONE - 828 - now if in a pos < .99 we even up and close it. 
# now the bot should never get stuck. 
    evenupsize = pos_info_even_up(sym)[4]
    
    if (0 < evenupsize < .01) or (0 > evenupsize > -.01):
        print(f'****this is the current evenup size: {evenupsize}')
        #print(f'this is the current size: {evenupsize} so we running even_up')
        even_up(sym, evenupsize)

    # CHECKING IF WE ARE HITTING TRAILING STOP, IF FALSE PROCEED
    trailingstop = trailing_stop(close_underr, reason='Trailing Stop - regular check on each loop')

## CHECKING MAX LOSS ON THE DAY
    hit_daily_loss = daily_max_loss()

# CHECKING FUNDING SKIPPER TO NOT PAY HIGH FEES
    if in_pos == True:

        funding_skipper(sym, side)
        skipping_4funding = True

        ## CLOSE IN SZ TOO LONG CHECK 

    current_time = datetime.now()
    minutes = current_time.minute

    ask = ask_bid(sym)[0]

# MAKING SURE WE ARE ONLY ENTERING ON BOTTOM OF BAR
    ok_to_enter = no_top_candle_entries()

    if (bs == 's'):
        if ok_to_enter == True:
            ok_to_enter = False 
        else:
            ok_to_enter = True

# ENTERING POSITION - ONLY ENTERS ON 10 MIN MARK, BOTTOM PART OF BAR AND NOT THE 50 MIN MARK
# updting this to enter every 5 mins instead... but this is probably the problem... because its looking in bars
# so instead i made it 3... this will really limit trading
# switching to 5 mins, so it doesnt over trade
    if (minutes % enter_interval == 0 )and (minutes != 50 or 55) and (hit_daily_loss == False) and (ok_to_enter == True) and (trailingstop == False) and (no_trading==False):
        print('entering position or adding if in profit...')
    
        enter_position(bs, pos_size)

        # after running above, run add to position
        add_to_winners()

    else:
        print(f'not entering position, min mark {minutes} daily max loss: {hit_daily_loss} inbottom15m: {ok_to_enter} trailing stop: {trailingstop}')
        print('must be 5min mark | false | true | false')

    # get each open symbol from the posinfo_df
    try:
        open_symbols = posinfo_df['market'].tolist()
    except:
        open_symbols = []
    #print(f'these are our open positions: {open_symbols}')

# IF SIZE > POS_SIZE then set trailing stop to 1.001, nah 2 back 
# so essentially get the low of last 30 mins, and make that the trailing stop close_under
    open_size_float = float(open_size)
    pos_size_float = float(pos_size)
    print(f"Open Size: {open_size_float}, Pos Size: {pos_size_float}, Entry Price: {entryprice}")
    if open_size_float > (pos_size_float * 1.5):

        ohlc = ohlcv(symbol=sym, timeframe='15MINS', limit=2, sma=sma)
        #print(ohlc)

        min_low = float(ohlc['low'].min())
        if min_low > (1.001*float(entryprice)):
            close_under = min_low
        else:
            close_under = (1.001*float(entryprice))

        print(f'open size {open_size} is greater than pos size {pos_size} so setting trailing stop at {close_under}') 

        trailing_stop(close_under, 'Trailing Stop - Open Size > possize*1.1')

        print(f'finished setting close_under to above entry price... entry: {entryprice} close_under: {close_under}')
    
    # loop through the symbols list and then check pnl close for each
    for symbol in open_symbols:

        # run pnl_close function
        pnl_close2(symbol, target_pnl, max_loss, kill_switch=False, reason='pnl close og - main loop')

        # run time in zones
        time_in_zones(symbol)

## IF NO TRADING IS TRUE EVER, PNL CLOSE WITH KILL SWITCH
    if no_trading == True:
        for symbol in open_symbols:
        # run pnl_close function
            pnl_close2(symbol, target_pnl, max_loss, kill_switch=True, reason='NO TRADING TRUE - pnl close kill switch true')
    else:
        print(f'no trading is {no_trading} so not closing anything')

    print('')
    print('-----')


# ## TEST ORDERS
# askbid = ask_bid(sym)
# ask = askbid[0]
# bid = askbid[1]

# client.private.cancel_all_orders(market=sym)
# limit_order(sym, 'BUY', 1000, bid, reason='Testing why trailing stop goes off')
# time.sleep(20)
# print(pos_info(sym))
# time.sleep(7867)
# bot()

# if in winning position where im adding to winners, trailing stop == entry price * 1.001

schedule.every(10).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(10)
    except Exception as e:
        print('***Maybe internet connection lost?***')
        print(e)
        time.sleep(10)