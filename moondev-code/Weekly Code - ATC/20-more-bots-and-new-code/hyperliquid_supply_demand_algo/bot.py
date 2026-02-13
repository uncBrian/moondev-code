'''
Hyper Liquid connection and Supply Demand Zone Algo

NOTE-
as always do not run this without backtesting
this is not tested. use at your own risk. 

ex - https://github.com/hyperliquid-dex/hyperliquid-python-sdk 
docs- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint 
examples - https://github.com/hyperliquid-dex/hyperliquid-python-sdk/tree/master/examples 
fees-
Hyperliquid will have zero trading fees to start as well. 
Once a token is introduced, there will be a trading fee 
tied to that token, as well as rebates for makers. The fees
will be competitive with the top centralized exchanges.

We will share more about the fees, tokenomics, and referral program in Q2 23.

todo -
- figure out how to control leverage
DONE - make it so it doesnt need to re-set orders if they are there
DONE - make it easy to switch SDZ zones
- make easy to switch symbols and accts

NOTE - this is a single ticker system, need to update pnl close
if i want multiple tickers

https://api.hyperliquid.xyz/info


'''
from eth_account.signers.local import LocalAccount
import eth_account
import json
import dontshareconfig as ds
import time 
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt
import pandas as pd
import datetime
import schedule 

import requests 

symbol = 'INJ'
timeframe = '1h' # for sdz zone
limit = 300 # for sdz
max_loss = -3
target = 12
size = 25 

binance_symbol = symbol + '/USD'
print(binance_symbol)


def get_sz_decimals(symbol):

    '''
    this outputs the size decimals for a given symbol
    which is - the SIZE you can buy or sell at
    ex. if sz decimal == 1 then you can buy/sell 1.4
    if sz decimal == 2 then you can buy/sell 1.45
    if sz decimal == 3 then you can buy/sell 1.456

    if size isnt right, we get this error. to avoid it use the sz decimal func
    {'error': 'Invalid order size'}
    '''
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    data = {'type': 'meta'}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        # Success
        data = response.json()
        symbols = data['universe']
        symbol_info = next((s for s in symbols if s['name'] == symbol), None)
        if symbol_info:
            sz_decimals = symbol_info['szDecimals']
            return sz_decimals
        else:
            print('Symbol not found')
    else:
        # Error
        print('Error:', response.status_code)

def ask_bid(symbol):

    '''
    sample of output [[{'n': 2, 'px': 768250, 'sz': 370}, {'n': 2, 'px': 767850, 'sz': 9080},
    notice px is price in diff format, may need to conver for orders
    '''

    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}

    data = {
    "type": "l2Book",
    "coin": symbol
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()

    # get bid and ask 
    bid = l2_data[0][0]['px']
    ask = l2_data[1][0]['px']

    ask = float(ask/100000)
    bid = float(bid/100000)

    return  ask, bid, l2_data



def datetime_to_epoch_ms(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return int((dt - epoch).total_seconds() * 1000.0)

def get_time_range_ms(minutes_back):
    current_time_ms = int(datetime.datetime.utcnow().timestamp() * 1000)
    start_time_ms = current_time_ms - (minutes_back * 60 * 1000)
    end_time_ms = current_time_ms
    return start_time_ms, end_time_ms

def get_ohlcv(binance_symbol, timeframe='1h', limit=100):

    coinbase = ccxt.coinbasepro()
    
    ohlcv = coinbase.fetch_ohlcv(binance_symbol, timeframe, limit)
    
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    df = df.tail(limit)

    df['support'] = df[:-2]['close'].min()
    df['resis'] = df[:-2]['close'].max()    

    return df

# df = get_ohlcv(binance_symbol, timeframe, limit)
# df_1h = get_ohlcv(binance_symbol, '1h', limit)
# print(df)

def supply_demand_zones(symbol, timeframe, limit):

    '''
    We can now pass in a timeframe and limit to change sdz easily

    out puts a df with supply and demand zones for each time frame
    # this is supply zone n demand zone ranges
    # row 0 is the CLOSE, row 1 is the WICK (high/low)
    # and the supply/demand zone is inbetween the two
    '''

    print('starting supply and demand zone calculations..')

    # get OHLCV data 
    sd_limit = 96
    sd_sma = 20     

    sd_df = pd.DataFrame() # supply and demand zone dataframe 

    df = get_ohlcv(binance_symbol, timeframe, limit)
    print(df)
    
    supp_1h = df.iloc[-1]['support']
    resis_1h = df.iloc[-1]['resis']
    #print(f'this is support for 1h {supp_1h} and this is resis {resis_1h}')

    df['supp_lo'] = df[:-2]['low'].min()
    supp_lo_1h = df.iloc[-1]['supp_lo']
    #print(f'this is the support lo: {supp_lo_1h} this is support {supp_1h} Demand zone is BETWEEN the 2')

    df['res_hi'] = df[:-2]['high'].max()
    res_hi_1h = df.iloc[-1]['res_hi']
    #print(f'this is the res hi: {res_hi_1h} this is resis {resis_1h} Supply Zone is BETWEEN the 2')

    sd_df['1h_dz'] = [supp_lo_1h, supp_1h]
    sd_df['1h_sz'] = [res_hi_1h,resis_1h ]


    

    return sd_df # this is a df where the zone is indicated per timeframe
                # and range is between row 0 and 1



#### this is the whole time thing... 
# start_time_ms, end_time_ms = get_time_range_ms(100)
# print(start_time_ms, end_time_ms)
# time.sleep(7867)

# symbol = 'ETH'
# interval = '15m'
# start_time = 1633089600000
# end_time = 1681923833000

# start_time = datetime.datetime(2021, 10, 1, 12, 0, 0)
# end_time = datetime.datetime(2022, 10, 1, 12, 0, 0)
# start_time_ms = datetime_to_epoch_ms(start_time)
# end_time_ms = datetime_to_epoch_ms(end_time)
# print(start_time_ms, end_time_ms)  # Output: 1633084800000

def limit_order(coin: str, is_buy: bool, sz: float, limit_px: float, reduce_only: bool = False):
    account: LocalAccount = eth_account.Account.from_key(ds.hyper_secret)
    exchange = Exchange(account, constants.MAINNET_API_URL)
    order_result = exchange.order(coin, is_buy, sz, limit_px, {"limit": {"tif": "Gtc"}}, reduce_only=reduce_only)
    

    if is_buy == True: 
        print(f"limit BUY order placed, resting: {order_result['response']['data']['statuses'][0]}")
    else:
        print(f"limit SELL order placed, resting: {order_result['response']['data']['statuses'][0]}")

    return order_result



def get_position():
    account: LocalAccount = eth_account.Account.from_key(ds.hyper_secret)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)
    positions = []
    for position in user_state["assetPositions"]:
        if float(position["position"]["szi"]) != 0:
            positions.append(position["position"])
            in_pos = True
            size = float(position["position"]["szi"])
            pos_sym = position["position"]["coin"]
            entry_px = float(position["position"]["entryPx"])
            pnl_perc = float(position["position"]["returnOnEquity"])*100
            print(f'this is pnl perc {pnl_perc}')
            # get size
        else:
            in_pos = False
            size = 0
            pos_sym = None
            entry_px = 0
            pnl_perc = 0
    if size > 0:
        long = True
    elif size< 0:
        long = False 
    else:
        long = None

    return positions, in_pos, size, pos_sym, entry_px, pnl_perc, long


def cancel_all_orders():

    ''' this cancels all open orders '''

    account: LocalAccount = eth_account.Account.from_key(ds.hyper_secret)
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    open_orders = info.open_orders(account.address)
    print(open_orders)
    print('above are the open orders... need to cancel any...')
    for open_order in open_orders:
        print(f"cancelling order {open_order}")
        exchange.cancel(open_order["coin"], open_order["oid"])


from typing import List
from decimal import Decimal

def get_open_order_prices() -> List[Decimal]:
    account = eth_account.Account.from_key(ds.hyper_secret)
    api_url = constants.MAINNET_API_URL
    exchange = Exchange(account, api_url)
    info = Info(api_url, skip_ws=True)
    open_orders = info.open_orders(account.address)
    print(open_orders)
    print('above are the open orders... need to cancel any...')
    open_order_prices = []
    for open_order in open_orders:
        open_order_prices.append(Decimal(open_order['limitPx']))
        print(f"cancelling order {open_order}")
    return open_order_prices



def kill_switch(symbol):

    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()

    while im_in_pos == True:

        cancel_all_orders()

        # get bid_ask
        askbid = ask_bid(pos_sym)
        ask = askbid[0]
        bid = askbid[1]

        pos_size = abs(pos_size)

        if long == True:
            limit_order(pos_sym, False, pos_size, ask)
            print('kill switch - SELL TO CLOSE SUBMITTED ')
            time.sleep(7)
        elif long == False:
            limit_order(pos_sym, True, pos_size, bid)
            print('kill switch - BUY TO CLOSE SUBMITTED ')
            time.sleep(7)
        
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()

    print('position successfully closed in kill switch')


def pnl_close():

    '''
    build a pnl close to mamage risk
    '''
    print('entering pnl close')
    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()
    if pnl_perc > target:
        print(f'pnl gain is {pnl_perc} and target is {target}... closing position WIN')
        kill_switch(pos_sym)
    elif pnl_perc <= max_loss:
        print(f'pnl loss is {pnl_perc} and max loss is {max_loss}... closing position LOSS')
        kill_switch(pos_sym)
    else:
        print(f'pnl loss is {pnl_perc} and max loss is {max_loss} and target {target}... not closing position')
    print('finished with pnl close')

def bot():

    sdz = supply_demand_zones(symbol, timeframe, limit)
    print(sdz)

    sz_1hr = sdz['1h_sz']
    sz_1hr_0 = sz_1hr.iloc[0]
    sz_1hr_1 = sz_1hr.iloc[-1]

    dz_1hr = sdz['1h_dz']
    dz_1hr_0 = dz_1hr.iloc[0]
    dz_1hr_1 = dz_1hr.iloc[-1]

    buy1 = max(dz_1hr_0, dz_1hr_1)
    buy2 = (dz_1hr_0 + dz_1hr_1) / 2
    #print(buy1, buy2)

    # if its a sell - sell # 1 at the lower and # 2 and avg
    sell1 = min(sz_1hr_0, sz_1hr_1)
    sell2 = (sz_1hr_0 + sz_1hr_1) / 2

    # see if in_pos - if no, place orders
    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()
    #print(positions, in_pos, size,  pos_sym ,entry_px, pnl_perc)

    # if pos_size >= size:
    #     in_full_pos = True

    # grab the current open orders
    openorderslist = get_open_order_prices()
    print(openorderslist)
    openorderslist = [float(d) for d in openorderslist]

## only doing one order now so just checkin that
    if buy2 and sell2 in openorderslist:
        new_orders_needed = False
        print('buy2 and sell2 in open orders')
    else:
        new_orders_needed = True
        print('no open orders')

    if not im_in_pos and new_orders_needed == True:

        print('not in position.. setting orders...')
        # cancel all orders
        cancel_all_orders()

        # create buy order
        # buy1 = limit_order(symbol, True, size, buy1, False)
        buy2 = limit_order(symbol, True, size, buy2, False)

        # create sell order
        # sell1 = limit_order(symbol, False, size, sell1, False)
        sell2 = limit_order(symbol, False, size, sell2, False)

    elif im_in_pos:
        print('we are in postion.. checking PNL loss')
        pnl_close()
    else:
        print('orders already set... chilling')
        



bot()
schedule.every(15).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ maybe an internet problem.. code failed. sleeping 10')
        time.sleep(10)