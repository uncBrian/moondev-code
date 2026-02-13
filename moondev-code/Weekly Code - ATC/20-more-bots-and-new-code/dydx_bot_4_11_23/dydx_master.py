'''
as always do not run this without testing
this is not tested.

this bot helps enter into positions a bit more elegantly
and closes based on a PNL win or loss

it is for DYDX which is much more advanced and harder to set up
so im happy to have this file to help you a bit on your journey

add in your own strategy before runniing
'''

pos_size = 2000
target_pnl = 3 # this is dollars, need to change to %
max_loss = -1
price = '23827'
sym = 'MATIC-USD'
timeframe = '1HOUR'
limit = 30
sma = 20 
fundrate_max = 0.0000050303 # 4.51% per year
daily_max_loss_perc = 2 # this is in % terms
time_between_trades = 10

########

import pandas as pd 
import schedule, requests, os, sys
import dontshareconfig as ds
from dydx3 import Client 
from web3 import Web3 
from pprint import pprint 
from datetime import datetime, timedelta 
# from dydx3.constants import API_HOST_MAINNET # for main net
# mainet = API_HOST_MAINNET
import time , logging
from datetime import datetime
# hide all warnings
import warnings
warnings.filterwarnings('ignore')
from dydx3.constants import API_HOST_GOERLI, API_HOST_MAINNET # for test nets
net = API_HOST_MAINNET # change this to API_HOST_MAINNET for main net

# HTTP Provider - get this from alchemy (diff for main net/test net)
#alchemy = ds.alchemy_testnet 
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



# The rest of your code remains the same

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



#  return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl
def pos_info(symbol):

    try:
        # get open positions
        open_positions = client.private.get_positions(status='OPEN')
        open_pos_info = open_positions.data['positions']
        # print(open_pos_info)
        # time.sleep(786786)

        # Extract the desired information from the open_pos_info list
        data = []
        for position in open_pos_info:
            data.append({
                'market': position['market'],
                'side': position['side'],
                'size': position['size'],
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
        if size > 0:
            in_pos = True
            print(f'In position: {symbol} and in_pos is {in_pos}')

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
    in_pos = posinfo[1]

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
    pnl_percentage = (realized_pnl + unrealized_pnl) / (entry_price * size) * 100
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

    if side == 'BUY' and size > float(ask_size_3_total):
        size = float(ask_size_3_total)
        print(f'new size is {size} for {symbol}')
    elif side == 'SELL' and size > float(bid_size_3_total):
        size = float(bid_size_3_total)
        print(f'new size is {size} for {symbol}')
    else:
        print(f'size is {size} for {symbol} no need to change')
    
    size = abs(size)
    size = round(size, 1)

    return size


def pnl_close(symbol, target_pnl, max_loss, kill_switch=False):

    #print(f'starting pnl_close for {symbol}')
    #print(f'symbol is {symbol} and target_pnl is {target_pnl} and max_loss is {max_loss}')

    #  return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl
    posinfo = pos_info(symbol)
    # posinfo df 
    pos_df = posinfo[0]

    print(pos_df)

    # get in postion from df of that symbol
    side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
    # get size
    size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
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
    pnl_percentage = posinfo[8]
    print(f'pnl percentage is {pnl_percentage:.4f}% for {symbol}')
    
    # print out all the variables in one line
    #print(f'in_pos is {in_pos} and symbol is {symbol} and side is {side} and size is {size} and unrealized_pnl is {unrealized_pnl} and entry_price is {entry_price} pnl percentage is {pnl_percentage:.2f}%')
    size = abs(size)
    size = round(size, 1)
    time.sleep(.2)

#######
    # how do we split up order size in an algorithmic way?
    # get the size from the top 3 asks or bids and add together
    # that will be our max
    chunksize = size_chunker(symbol, size, side)

    while pnl_percentage > target_pnl:

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
        chunksize = size_chunker(symbol, size, side)

        # while in position is true and 
        # if the position is long, place a sell limit order
        if side == 'LONG':

            # get accept price
            
            #acceptprice = accept_price(symbol, side, entry_price)
            
            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            # use out function to place a limit order
            sell_limit_order = limit_order(symbol, 'SELL', chunksize, ask)
            #print(sell_limit_order.data)
            print(f'just placed order for  - sleeping 15')
            time.sleep(15)

        # if the position is short, place a buy limit order
        elif side == 'SHORT':

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)

            # use out function to place a limit order
            buy_limit_order = limit_order(symbol, 'BUY', chunksize, bid)
            #print(buy_limit_order.data)
            print(f'just placed order - sleeping 15')
            time.sleep(15)

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
            size = round(size, 1)

            chunksize = size_chunker(symbol, size, side)

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

    # elif statement for if unrealized pnl is less than max loss
    while pnl_percentage < max_loss or kill_switch == True:
        askbid =ask_bid(symbol)
        ask = askbid[0]
        bid = askbid[1]
        time.sleep(.1)


## GET SIZE HERE CAUSE IT CHANGES
        posinfo = pos_info(symbol) 
        pos_df = posinfo[0]
        side = pos_df.loc[pos_df['market']==symbol, 'side'].values[0]
        # get size
        size = pos_df.loc[pos_df['market']==symbol, 'size'].values[0]
        # float size
        size = float(size)
        size = abs(size)
        chunksize = size_chunker(symbol, size, side)


        # if the position is long, place a sell limit order
        if side == 'LONG':

            # MUST GET PNL PERC AGAIN
            pnl_percentage = get_pnl_perc(sym)

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            #print('just cancelled all orders')

            # use our function to place a limit order
            sell_limit_order = limit_order(symbol, 'SELL', chunksize, ask)
            #print(sell_limit_order.data)
            print(f'just placed order - sleeping 5')
            time.sleep(5)

            # print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')
            print('pnl stuff')
            print(pnl_percentage)
            print(pnl_percentage * 1.1)
            # if the pnl is 10% more than our max loss - then use liq grab
            if pnl_percentage < max_loss * 1.1:

                # BUG - continues to order when liq grab is true
                # also, the size needs to be the pos size if liquidity is higher

                print('entering into liq grab')
                
                ask, bid, ask_size, bid_size=ask_bid(symbol)

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
                size = round(size,1)
                size = str(size)

                mkt = market_order(sym, 'SELL', size,accept_price)
                print('just placed market order sleeping 2')
                time.sleep(2)

               
        # if the position is short, place a buy limit order
        elif side == 'SHORT':

            # cancel open orders
            client.private.cancel_all_orders(market=symbol)
            #print('just cancelled all orders')

            # use our function to place a limit order
            buy_limit_order = limit_order(symbol, 'BUY', chunksize, bid)
            #print(buy_limit_order.data)
            print(f'just placed order - sleeping 5')
            time.sleep(5)

            # print(f'pnl percentage is {pnl_percentage:.2f}% for {symbol}')
            print(pnl_percentage)
            print(pnl_percentage * 1.1)
            # if the pnl is 10% more than our max loss - then use liq grab
            if pnl_percentage < max_loss * 1.1:

                print('entering into liq grab')
                
                ask, bid, ask_size, bid_size=ask_bid(symbol)

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
                size = round(size,1)
                size = str(size)
                print('line 703')
                print(size)

                mkt = market_order(sym, 'BUY',size,accept_price)
                print('just placed market order sleeping 2')
                time.sleep(2)

            
        # check the unrealized pnl again
        posinfo = pos_info(symbol)
        # posinfo df 
        pos_df = posinfo[0]
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
            size = round(size, 1)

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

    print('pnl_close complete')
    # cancel open orders
    


# all things passed in as strings_
def limit_order(symbol, side, size, price):

    # expiration times
    server_time = client.public.get_time()
    expiration = datetime.fromisoformat(server_time.data['iso'].replace('Z', '')) + timedelta(seconds=70)

    size = str(size)

    # place limit buy order
    limit_order = client.private.create_order(
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

    return limit_order

 # this gets us out of the position at any price 

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

   


# # place order to close
# order = place_market_order(symbol, side, position['sumOpen'], accept_price)

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
    print(f'UTC: current hour is {current_hour} and current minute is {current_minute} and current second is {current_second}')

    dydx_funding_rate, noskip = get_dydx_funding_rate(sym, fundrate_max, side)
    print(f'funding rate is {round(dydx_funding_rate*100,3)}%/year')

    if side == 'LONG' or 'SHORT':
        dydx_funding_rate, noskip = get_dydx_funding_rate(sym, fundrate_max, side)

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

    # Access the 1HOUR_sz values in rows 0 and 1
    sz_row_0 = float(sdz_df[f'{timeframe}_sz'].iloc[0])
    sz_row_1 = float(sdz_df[f'{timeframe}_sz'].iloc[1])
    
    # 2 variables, sell1 (average of two sz rows) and sell2 (slightly under higher in % terms sz row)
    sell1 = str(round((sz_row_0 + sz_row_1) / 2,2))
    sell2 = str(round(sz_row_1 - (sz_row_1 * 0.01), 2))
    
    # Access the 1HOUR_sz values in rows 0 and 1
    dz_row_0 = float(sdz_df[f'{timeframe}_dz'].iloc[0])
    dz_row_1 = float(sdz_df[f'{timeframe}_dz'].iloc[1])

    # 2 variables, buy1 (average of two dz rows) and buy2 (slightly over lower in % terms dz row)
    buy1 = str(round((dz_row_0 + dz_row_1) / 2,2))
    buy2 = str(round(dz_row_1 + (dz_row_1 * 0.01),2))

    # check to see if in full position
    # if in partial position our size will be smaller
    pos_info_df, in_pos, symbol, side, opensize, entry_price, unrealized_pnl, accept_price, pnl_percentage , pos_df_copy = pos_info(sym)
    # print the position info
    #print(pos_info_df)

    ### putting in the function to check if in the last 3 minutes of 
# the hour, if so, we will not enter a position and exit any open positions
    if in_pos == True:
        funding_skipper(sym, side)

    #- get the current position size and adjust orders based on it
    if not in_pos:
        size = pos_size/2
    else:
        size = (pos_size - opensize)/2

    time.sleep(.1)

# - if already orders, no need to set more

# - if one of the bids/asks already over price, then put on ask 
    askbid = ask_bid(sym)
    ask = float(askbid[0])
    bid = float(askbid[1])

    if float(buy1) > bid:
        buy1 = str(bid)
    if float(buy2) > bid:
        buy2 = str(bid)
    if float(sell1) < ask:
        sell1 = str(ask)
    if float(sell2) < ask:
        sell2 = str(ask)

    
    # Fetch active orders for the market
    active_orders = client.private.get_active_orders(market=sym)
    active_orders = active_orders.data
    #print(active_orders)
    # Extract the active order prices
    active_order_prices = [float(order['price']) for order in active_orders['orders']]

    print(f'active order prices are {active_order_prices}')


    if bs == 'b':
        side = 'BUY'
        #cancel open orders
        # cancel open orders
        
        # print(f'going to place 2 order {size}')

        # Place orders only if the prices are not the same as the active orders
        # added if opensize == 0 for both of the below so it doesnt jsut keep putting in more order
        if float(buy1) not in active_order_prices and opensize == 0:
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, size, buy1)
            print(f'just placed buy1')
        else:
            print(f'buy1 already in active orders OR we already have a pos')
        if float(buy2) not in active_order_prices:
            limit_order(sym, side, size, buy2)
            print(f'just placed buy2')
        else:
            print(f'buy2 already in active orders')
        
        
    elif bs == 's':
        side = 'SELL'
        # cancel open orders
        
        if float(sell1) not in active_order_prices and opensize == 0:
            limit_order(sym, side, size, sell1)
            print(f'just placed sell1')
        else:
            print(f'sell1 already in active orders OR we already have a pos')
        if float(sell2) not in active_order_prices:
            client.private.cancel_all_orders(market=sym)
            limit_order(sym, side, size, sell2)
            print(f'just placed sell2')
        else:
            print(f'sell2 already in active orders')

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

    # 768.18
    # if we are long - $557.4 in position and now bal is 210.436554
        # if we are long we need to add the bal + position to get real bal
    # if we are short - was 768.18, in a position of 557.4$ and now its 1325.38
        # if we are short we need to subtract the bal - position to get real bal
    # write above code
    if side == 'LONG':
        bal = bal + size_usd# + # position size
    elif side == 'SHORT': # short works now
        bal = bal - abs(size_usd)
    else:
        bal = bal

    # if in position, our balance will be different because dydx accounts the position

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
    lowest_bal_allowed = bal_24hrs_ago - lockout_loss # 16 hr bal - lockoutloss
    print(f'this is lowest_bal_allowed {lowest_bal_allowed} this is current: {last_bal}')

    # need to see if last total bal < loswestbal_allowed
    last_bal_small_q_24hrsago = last_bal < lowest_bal_allowed
    #print(last_bal_small_q_24hrsago)
    #print(f'this is last_bal_small_q_24hrsago {last_bal_small_q_24hrsago}')

    # put a sleep if lock out is activated, and sleep for 24 hours
    if last_bal_small_q_24hrsago == True:
        # kill switch - for ALL positions cause lock out actived
        print('starting kill_switch')

        # get all open positions
        posinfo = pos_info(sym)
        posinfo_df = posinfo[0]
        try:
            open_symbols = posinfo_df['market'].unique().tolist()
        except:
            open_symbols = []
        for symbol in open_symbols:
            pnl_close(symbol, target_pnl, max_loss, kill_switch=True)
    else:
        print('we are gucci on the lockout, not needed')

    # Append the new data to the DataFrame
    df = df.append(temp_df)

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

from datetime import datetime, timedelta

def was_fill_in_last_minutes(fills, minutes):
    current_time = datetime.utcnow()
    time_threshold = current_time - timedelta(minutes=minutes)

    for fill in fills:
        fill_time_str = fill['createdAt']
        fill_time = datetime.strptime(fill_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')

        if fill_time >= time_threshold:
            return True

    return False

def place_order_time():
    current_time = datetime.now()
    minutes = current_time.minute
    return minutes % 15 == 0 and minutes != 45

# ask if we want to Buy or Sell all day
bs = input('buying or selling today? (b/s or anything to control risk):')

def bot():

    current_time_utc = datetime.utcnow()
    formatted_time = current_time_utc.strftime("%Y-%m-%d %H:%M:%S")

    print('')
    print('---------')
    print(f"time (GMT): {formatted_time} {sym} size: {pos_size} timeframe: {timeframe} ")

    #  return pos_info_df, in_pos, symbol, side, size, entry_price, unrealized_pnl
    posinfo = pos_info(sym)
    posinfo_df = posinfo[0]
    df_less = posinfo[9]
    open_poside = posinfo[3]
    

######## RISK SECTION ###############

    hit_daily_loss = daily_max_loss()

    current_time = datetime.now()
    minutes = current_time.minute

    # build a new function that only enters trades part of hour
    # this conditional now only enters on the 10 min mark, and skips the 50 before funding.
    if minutes % 10 == 0 and minutes != 50 and hit_daily_loss == False:
        enter_position(bs)
    else:
        print(f'not entering position, not on 10 min mark {minutes} or daily max loss: {hit_daily_loss}')

##################

    '''
    DONE - 1. see open positions and then loop the pnl close
    2. change the pnl close from $ to %
    '''

    



    # get each open symbol from the posinfo_df
    try:
        open_symbols = posinfo_df['market'].tolist()
    except:
        open_symbols = []
    #print(f'these are our open positions: {open_symbols}')

    # New code for fill checking and sleeping
    all_fills = client.private.get_fills(market=sym)
    all_fills = all_fills.data
    #print(all_fills)
    fills = all_fills['fills']
    fill_side = fills[0]['side']
    # print(open_poside, fill_side)

    # if (open_poside == 'SHORT' and fill_side == 'SELL') or (open_poside == 'LONG' and fill_side == 'BUY'):
    #     currently_filling = True


    

    # if was_fill_in_last_minutes(fills, time_between_trades):
    #     print(f"A fill occurred in the last {time_between_trades} minutes. Sleeping and checking pnl_close...")
    #     client.private.cancel_all_orders(market=sym)
    #     sleep_and_check_pnl(time_between_trades)

    # loop through the symbols list and then check pnl close for each
    for symbol in open_symbols:

        # run pnl_close function
        pnl_close(symbol, target_pnl, max_loss)

    # loop until we exit the position, if we are in a position

bot()

with Logger(log_file_name) as logger:
    sys.stdout = logger
    sys.stderr = logger

    def log_input(prompt):
        sys.stdout.write(prompt)
        sys.stdout.flush()
        return input()

    # The rest of your code remains the same

    schedule.every(20).seconds.do(bot)

    while True:
        try:
            schedule.run_pending()
            time.sleep(10)
        except Exception as e:
            print('***Maybe internet connection lost?***')
            print(e)
            time.sleep(10)
# change to its mathmaticlaly better to long, so do you want to long? we dont short