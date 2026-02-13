'''
this is the dydx starter code
it is a free gift to anyone who joins our email list
you also get access to our algo traders only discord here: https://discord.gg/8UPuVZ53bh 
watch the youtube videos to see how i evolve this code overtime: https://www.youtube.com/@moondevonyt
follow on twitter for more: https://twitter.com/MoonDevOnYT 

warning: do not run this code without making changes to adapt to your strategy
    - do not use this live in production without testing everything and making it your own.
'''


###### INPUTS #########

sym = 'SOL-USD'
close_under = 23 # bot will auto close under this number - this is used in Trailing Stop
lowest_bal_allowed = 88000 # bot will auto close if we fall under this number
timeframe = '15MINS' # 1MIN , 5MINS, 15MINS, 1HOUR # time frame for the DZ buys... 
pos_size = 13000
target_pnl = 4 
max_loss = -1
enter_interval = 1.1

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

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.terminal.close()
        self.log.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

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
            size = 0 if float(size) < 0.01 else size
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
    size = round(size, 3)

    return size


## UPDATING CLOSE TO BE MARKET
def pnl_close(symbol, target_pnl, max_loss, kill_switch=False):

    #print(f'starting pnl_close for {symbol}')
    #print(f'symbol is {symbol} and target_pnl is {target_pnl} and max_loss is {max_loss}')

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

#     error
# pnl percentage is 0.0000% for ETH-USD
# ask size 3 total is 47.102000000000004 and bid size 3 total is 138.711 for ETH-USD
# size is 0.0 for ETH-USD no need to change
# error getting position info
# pnl percentage is 0.0000% for ETH-USD
# ask size 3 total is 69.624 and bid size 3 total is 142.57600000000002 for ETH-USD
# size is 0.0 for ETH-USD no need to change
# error getting position info
# pnl percentage is 0.0000% for ETH-USD
    
    # print out all the variables in one line
    #print(f'in_pos is {in_pos} and symbol is {symbol} and side is {side} and size is {size} and unrealized_pnl is {unrealized_pnl} and entry_price is {entry_price} pnl percentage is {pnl_percentage:.2f}%')
    size = abs(size)
    size = round(size, 3)
    time.sleep(.2)

#######
    # how do we split up order size in an algorithmic way?
    # get the size from the top 3 asks or bids and add together
    # that will be our max

## 7/24 No need to chunk if we arent in a position
    # chunksize = size_chunker(symbol, size, side)
    # print('line 536')

    while pnl_percentage > target_pnl:

        #print('***************** ABOUT TO CLOSE 609')
        #time.sleep(777777)

        client.private.cancel_all_orders(market=symbol)

        # get ask and bid
        askbid =ask_bid(symbol)
        ask = askbid[0]
        bid = askbid[1]

### SETTING UP HERE TO RUN EACH LOOP
        posinfo = pos_info(symbol) 
        pos_df = posinfo[0]
        side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
        # get size
        size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
        # float size
        size = float(size)
        size = abs(size)
        if size > 1:
            chunksize = size_chunker(symbol, size, side)
            print('line 557')

        # while in position is true and 
        # if the position is long, place a sell limit order
        if side == 'LONG' and float(size) > .01:

            # get accept price

            # - only resubmit the pnl close order if its not already there
            
            #acceptprice = accept_price(symbol, side, entry_price)
            
            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            # use out function to place a limit order
            sell_limit_order = market_close_order(symbol, 'SELL', chunksize, ask)
            #print(sell_limit_order.data)
            print(f'just placed order for  - sleeping 15')
            time.sleep(5)

        # if the position is short, place a buy limit order
        elif side == 'SHORT' and float(size) > .01:

            # - only resubmit the pnl close order if its not already there

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)

            # use out function to place a limit order
            buy_limit_order = market_close_order(symbol, 'BUY', chunksize, bid)
            #print(buy_limit_order.data)
            print(f'just placed order - sleeping 15')
            time.sleep(5)

        else:

            break 

        # check the unrealized pnl again
        time.sleep(.2)
        posinfo = pos_info(symbol)
        # posinfo df 
        pos_df = posinfo[0]

        try:

            # get in postion from df of that symbol
            side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
            # get size
            size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
            # float size
            size = float(size)
            size = abs(size)
            size = round(size, 3)

            if size > 1:
                chunksize = size_chunker(symbol, size, side)
                print('line 631')

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
        except:
            print('no position')
            pnl_percentage = 0

        time.sleep(.2)
        # get ask and bid
        askbid = ask_bid(symbol)
        ask = askbid[0]
        bid = askbid[1]

        posinfo = pos_info(symbol)
        pnl_percentage = posinfo[8]
        print(f'pnl percentage is {pnl_percentage:.4f}% for {symbol}')

    # elif statement for if unrealized pnl is less than max loss
    while pnl_percentage < max_loss or kill_switch == True and size > 0:
        #print('***************** ABOUT TO CLOSE 724')
        #time.sleep(777777)
        askbid =ask_bid(symbol)
        ask = askbid[0]
        bid = askbid[1]
        time.sleep(.1)

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
        print('*******************')
        if size > 1:
            chunksize = size_chunker(symbol, size, side)
            print('line 689')
        else:
            chunksize = size 

        if float(size) < .01:
            kill_switch = False 
            print(f'size is {size} so setting kill switch to False')
            break 


        # if the position is long, place a sell limit order
        if side == 'LONG' and float(size) > .01:

            # MUST GET PNL PERC AGAIN
            pnl_percentage = get_pnl_perc(sym)

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            #print('just cancelled all orders')

            # use our function to place a limit order
            sell_limit_order = market_close_order(symbol, 'SELL', chunksize, ask)
            #print(sell_limit_order.data)
            print(f'just placed order - sleeping 10')
            time.sleep(10)

            # print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')
            print('pnl stuff')
            print(pnl_percentage)
            print(pnl_percentage * 1.1)
            pnl_percentage = get_pnl_perc(sym)
            # if the pnl is 3% more than our max loss - then use liq grab
            if pnl_percentage < max_loss * 1.03:

                # BUG - continues to order when liq grab is true
                # also, the size needs to be the pos size if liquidity is higher

                print('entering into liq grab')
                
                ask, bid, ask_size, bid_size, top3asks_total, top3bids_total=ask_bid(symbol)

                price = float(pos_info(sym)[5])
                markets = client.public.get_markets().data
                side = 'SELL'
                accept_price = price * 1.6 if side == 'BUY' else price * 0.4
                tick_size = markets['markets'][sym]['tickSize']
                accept_price = format_number(accept_price, tick_size)

                size = pos_info(sym)[4]

                if float(size) < float(bid_size):
                    size = size
                else:
                    size = bid_size

                size = float(size)
                size = abs(size)
                size = round(size, 3)
                size = str(size)

## UPDATED THIS TO BE MARKET_CLOSE_ORDER
                mkt = market_close_order(sym, 'SELL', size,accept_price)
                print('just placed market order sleeping 2')
                time.sleep(2)

               
        # if the position is short, place a buy limit order
        elif side == 'SHORT' and float(size) > .01:

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            #print('just cancelled all orders')

            # use our function to place a limit order
            buy_limit_order = market_close_order(symbol, 'BUY', chunksize, bid)
            #print(buy_limit_order.data)
            print(f'just placed order - sleeping 10')
            time.sleep(10)

            # print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')
            pnl_percentage = get_pnl_perc(sym)
            print(pnl_percentage)
            print(pnl_percentage * 1.1)
            # if the pnl is 10% more than our max loss - then use liq grab
            if pnl_percentage < max_loss * 1.1:

                print('entering into liq grab')
                
                ask, bid, ask_size, bid_size, top3asks_total, top3bids_total =ask_bid(symbol)

                price = float(pos_info(sym)[5])
                markets = client.public.get_markets().data
                print('line 687')
                side = 'BUY'
                accept_price = price * 1.6 if side == 'BUY' else price * 0.4
                tick_size = markets['markets'][sym]['tickSize']
                accept_price = format_number(accept_price, tick_size)
                print('line 691')
                size = pos_info(sym)[4]
                if float(size) < float(bid_size):
                    size = size
                else:
                    size = bid_size
                print('line 698')

                size = float(size)
                size = abs(size)
                size = round(size, 3)
                size = str(size)
                print('line 703')
                print(size)

                mkt = market_close_order(sym, 'BUY',size,accept_price)
                print('just placed market order sleeping 2')
                time.sleep(2)

            else:
                break

            
        # check the unrealized pnl again
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
        if size > 1:
            chunksize = size_chunker(symbol, size, side)
            print('line 689')
#  side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
# IndexError: index 0 is out of bounds for axis 0 with size 0
        # get in postion from df of that symbol

        try:
            side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
            # get size
            size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
            # float size
            size = float(size)
            size = abs(size)
            size = round(size, 3)

            # get in_pos
            if size > 0:
                in_pos = True
                print(f'In position: {symbol} and in_pos is {in_pos}')
            else:
                in_pos = False
                print(f'Not in position and in_pos is {in_pos} for {symbol}')
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
        except:
            print('error getting position info')
            pnl_percentage = 0

        posinfo = pos_info(symbol)
        pnl_percentage = posinfo[8]
        #print(f'pnl percentage is {pnl_percentage:.4f}% for {symbol}')

    posinfo = pos_info(symbol)
    size = float(posinfo[4])

    #print('pnl_close complete')

def limit_order(symbol, side, size, price):

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


    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)

    expiration = eastern_tz.localize(expiration).astimezone(eastern_tz)

    size = round(size,1)
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

    # Update oms.csv with order details
    order_data = {
        'Datetime': [current_time],  # Include the current date and time in the order_data dictionary
        'Bot': [script_name],
        'ID': [limit_order['id']],
        'Symbol': [limit_order['market']],
        'Side': [limit_order['side']],
        'Size': [limit_order['size']],
        'Price': [limit_order['price']],
        'Status': [limit_order['status']]
    }
    order_df = pd.DataFrame(order_data)

    # Read the existing oms.csv file if it exists
    existing_df = pd.read_csv('/root/algos/dydx/0oms.csv')

    # Concatenate the existing DataFrame with the order_df
    updated_df = pd.concat([existing_df, order_df], ignore_index=True)

    # Append the updated DataFrame to the oms.csv file
    updated_df.to_csv('/root/algos/dydx/0oms.csv', index=False)

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

def market_close_order(symbol, side, size, price):

    '''
**** THIS IS SO IMPORTANT
    THIS MARKET ORDER REDUCE ONLY
    NOTE: MUST SEND IN PRICE OF ASK if BUYING,and BUY IF SELING
    -- so i made this permenant below. 
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

# L@@K - this makes size 1% bigger than w/e we calculated so when reduce only
# order is put in, it will close the full position
    #size = 1.1 * size 
    print(f'size before round quantity func {size}')
    print(f'this is the type {type(size)}')
    size = round_to_minsize(size, min_order_size)
    print(f'this is the New rounded, ready to order size {size}')
    size = round(float(size),1)
    size = str(size)
    #print(f'about to place an order for {size} on {symbol}')

    '''
    this is the size sent 99.0 type <class 'str'> min size: 1
Traceback (most recent call last):
  File "/root/algos/dydx/gobblin.py", line 1763, in <module>
    bot()
  File "/root/algos/dydx/gobblin.py", line 1759, in bot
    pnl_close(symbol, target_pnl, max_loss)
  File "/root/algos/dydx/gobblin.py", line 811, in pnl_close
    mkt = market_close_order(sym, 'SELL', size,accept_price)
  File "/root/algos/dydx/gobblin.py", line 1076, in market_close_order
    size = round_to_minsize(size, min_order_size)
  File "/root/algos/dydx/gobblin.py", line 1027, in round_to_minsize
    rounded_quantity = round(quantity)
TypeError: type str doesn't define __round__ method
[root@finer-lamprey dydx]# python gobblin.py
connected to dydx...

---------
time (GMT): 2023-07-27 15:57:19 SOL-USD size: 10000 ti
    '''

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
        'ID': [limit_order['id']],
        'Symbol': [limit_order['market']],
        'Side': [limit_order['side']],
        'Size': [limit_order['size']],
        'Price': [limit_order['price']],
        'Status': [limit_order['status']]
    }
    order_df = pd.DataFrame(order_data)

    # Read the existing oms.csv file if it exists
    existing_df = pd.read_csv('/root/algos/dydx/0oms.csv')

    # Concatenate the existing DataFrame with the order_df
    updated_df = pd.concat([existing_df, order_df], ignore_index=True)

    # Append the updated DataFrame to the oms.csv file
    updated_df.to_csv('/root/algos/dydx/0oms.csv', index=False)

    return limit_order

def market_order(symbol, side, size, price):

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)

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
        time_in_force='FOK', # could be 'GTT' or 'FOK'
        reduce_only=False,
)

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

    if dydx_funding_rate > 

# NOTE - change below back to 57
    if 57 <= current_minute < 60 and current_second != 0 and noskip == False:
        print(f'current minute is {current_minute} and no skip is {noskip} so killing position')

        # updated our pnl close in order to accept a kill switch flag
        pnl_close(sym, target_pnl, max_loss, kill_switch=True)
        time.sleep(181)

def enter_position(bs):

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

    # #- get the current position size and adjust orders based on it
    # if not in_pos:
    #     size = pos_size/2
    # else:
    #     size = (pos_size - opensize)/2

     #- get the current position size and adjust orders based on it
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

        #print(f'active order prices are {active_order_prices}')
       
        # if float(buy1) not in active_order_prices and opensize == 0:

           
        #     limit_order(sym, side, size, buy1)
        #     print(f'just placed buy1')
        # else:
        #     print(f'buy1 already in active orders OR we already have a pos')
        # if float(buy2) not in active_order_prices and 0 < size < pos_size:

           
        #     limit_order(sym, side, size, buy2)
        #     print(f'just placed buy2')
        # else:
        #     print(f'buy2 already in active orders')

        if float(buy3) not in active_order_prices and float(opensize) < pos_size:
            client.private.cancel_all_orders(market=sym)
           
            limit_order(sym, side, size, buy3)
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

            limit_order(sym, side, size, sell1)
            print(f'just placed sell1')
        else:
            print(f'sell1 already in active orders OR we already have a pos')
        if float(sell2) not in active_order_prices and 0 < size < pos_size:
        

            limit_order(sym, side, size, sell2)
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
    file_name_lockout = 'lockoutchecker.csv'
    # Join the script directory and file name to create the full file path
    file_path = os.path.join(script_dir, file_name_lockout)
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
            pnl_close(sym, target_pnl, max_loss, kill_switch=False)
        
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

def trailing_stop():

    '''
    part 1 - simple update by hand if price falls under x price close
    part 2- hey if pnl get to X%, then implement trailing stop
    '''

    # get price 
    price = ask_bid(sym)[0]

    if float(price) < close_under:

        print(f'price is {price} and close_under is {close_under} CLOSING POSITION')

        pnl_close(sym, target_pnl, max_loss, kill_switch=True)

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
    else:
        print('we did not enter in the last minute...')

    if in_pos and entered_in_last_min == True:

        if float(askprice) < float(bottom_third):
            print('we are ok that we entered...')
            ok_to_enter = True
        else:
            print('get out of this position asap, we are in the top 2/3 of the candle.. calling kill switch')
            ok_to_enter = False
            pnl_close(sym, target_pnl, max_loss, kill_switch=True)

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

    ohlc = ohlcv(symbol='ETH-USD', timeframe='1DAY', limit=50, sma=20)

    if ohlc['signal'] == 1:

        no_trading = False 
        print('sig is 1 so no_trading = False')
    else:
        no_trading = True
        print('sig is 0 so no_trading = True')

    no_trading

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
    
        if .4 > pnlperc > .2 and open_size < (2*pos_size):
            print('entering 1 more pos size...')

            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid)
            print(f'just placed order since we are between .2% and .4% in profit')

        elif .6 > pnlperc > .4 and open_size < (3*pos_size):

            print('entering 1 more pos_size... ')
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid)
            print(f'just placed order since we are between .2% and .4% in profit')

        elif .8 > pnlperc > .6 and open_size < (4*pos_size):

            print('entering 1 more pos_size... ')
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid)
            print(f'just placed order since we are between % and .4% in profit')

        elif 1 > pnlperc > .8 and open_size < (5*pos_size):

            print('entering 1 more pos_size... ')
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, pos_size, bid)
            print(f'just placed order since we are between .8% and 1% in profit')



def close_toolong_in_sz():

    '''
    if we are in position and have been chilling in a SZ 
    or dip out of it for more than 15mins, i bounce and can rebuy later in the DZ
    '''


# ask if we want to Buy or Sell all day
#bs = input('buying or selling today? (b/s or anything to control risk):')
bs = 'b'

def bot():

    current_time_utc = datetime.utcnow()
    formatted_time = current_time_utc.strftime("%Y-%m-%d %H:%M:%S")
    
# this gets our position size by looking at the time 
    pos_size = check_time_for_size()

    no_trading = False

# check if above 20sma, if under no_trading = true
    no_trading = over20sma()

    # Usage example
    total_vol_24hrs = total_24_volume()

    if total_vol_24hrs > 1000000:
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

    # CHECKING IF WE ARE HITTING TRAILING STOP, IF FALSE PROCEED
    trailingstop = trailing_stop()

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
    
        enter_position(bs)

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
    
    # loop through the symbols list and then check pnl close for each
    for symbol in open_symbols:

        # run pnl_close function
        pnl_close(symbol, target_pnl, max_loss)

    

bot()

with Logger(log_file_name) as logger:
    sys.stdout = logger
    sys.stderr = logger

    def log_input(prompt):
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return input()

    # The rest of your code remains the same

    schedule.every(10).seconds.do(bot)

    while True:
        try:
            schedule.run_pending()
            time.sleep(10)
        except Exception as e:
            print('***Maybe internet connection lost?***')
            print(e)
            time.sleep(10)
