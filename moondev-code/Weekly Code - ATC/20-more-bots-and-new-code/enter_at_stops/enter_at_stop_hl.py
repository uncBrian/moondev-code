'''
this enters positions at the stop losses of supply and demand zone traders

WARNING: do not run this live without backtesting, this  is just an idea

TODO - 
[DONE] - buy/sell at stops
    - top of wick, last high, 2nd to last high/ low
- implemnt stop loss and can read in from file
    - Emergency stops @ -5% or w/e we put in the file 
- switch from b data to hl 
'''

from eth_account.signers.local import LocalAccount
import eth_account
import json
import time 
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt
import pandas as pd
import datetime
import schedule 
import requests 
from dontshareconfig import hyper_secret, hyper_wallet

symbol = 'ETH'
timeframe = '5m'
limit = 100
max_tr = 500
no_trading_past_hrs = 7 # the past hour of checking atr
max_loss = -3
stop_perc = -5
target = 9 

min_acct_value = 90

binance_symbol = symbol + '/USD'

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

##########
#########
# API CALL - NOT CHANGING
##########
#########
    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()
    l2_data = l2_data['levels']
    #print(l2_data)

    # get bid and ask 
    bid = float(l2_data[0][0]['px'])
    ask = float(l2_data[1][0]['px'])
    
    ask = float(ask)
    bid = float(bid)
    print(f'ask: {ask} bid: {bid}')

    return  ask, bid, l2_data

import random 
def adjust_leverage_size_signal():

        '''
        this function sets lev, calcs size, and gets signal from 
        may23/signals.txt and below are the options
        # options are n for neutral 50/50
        # b60, b70, s60, s70 for skewed
        '''

        
        leverage = 20
        # get balance 
        # get volume 

        print('leverage:', leverage)

        # Get the latest signal from signals.txt
        with open('june23/1-signals.txt') as f:
            signal = f.read().strip()

        # Initialize long_only and short_only parameters to False
        long_only = False
        short_only = False

        print(f'this is the signal {signal}')

        # Update long_only and short_only based on signal
        if signal == 'n':
            long_only = False
            short_only = False
        elif signal == 'b60':
            long_only = (random.random() < 0.6)
            short_only = False
        elif signal == 'b70':
            long_only = (random.random() < 0.7)
            short_only = False
        elif signal == 's60':
            long_only = False
            short_only = (random.random() < 0.6)
        elif signal == 's70':
            long_only = False
            short_only = (random.random() < 0.7)

        print('leverage:', leverage, 'signal:', signal)

##########
#########
# API CALL
##########
#########
        account: LocalAccount = eth_account.Account.from_key(hyper_secret)
        exchange = Exchange(account, constants.MAINNET_API_URL)
        info = Info(constants.MAINNET_API_URL, skip_ws=True)

        # Get the user state and print out leverage information for ETH
        user_state = info.user_state(account.address)
        acct_value = user_state["marginSummary"]["accountValue"]
        acct_value = float(acct_value)
        print(acct_value)
        acct_val95 = acct_value * .95
        #print(f"Current leverage for {symbol}:")
        #print(json.dumps(user_state["assetPositions"][exchange.coin_to_asset[symbol]]["position"]["leverage"], indent=2))

##########
#########
# API CALL
##########
#########
        #print('adjusting leverage....')
        # Set the ETH leverage to 21x (cross margin)
        print(exchange.update_leverage(leverage, symbol))

##########
#########
# API CALL
##########
#########
        price = ask_bid(symbol)[0]

        # size == balance / price * leverage
        # INJ 6.95 ... at 10x lev... 10 INJ == $cost 6.95
        size = (acct_val95 / price) * leverage
        size = int(size)
        print(f'this is the size we can use 95% fo acct val {size}')

    # may23/signals.txt
        # # Set the ETH leverage to 22x (isolated margin)
        # print(exchange.update_leverage(21, symbol, False))

        # # Add 1 dollar of extra margin to the ETH position
        # print(exchange.update_isolated_margin(1, "ETH"))

        # Get the user state and print out the final leverage information after our changes
        user_state = info.user_state(account.address)
        #print(f"Current leverage for {symbol}:")
        #print(json.dumps(user_state["assetPositions"][exchange.coin_to_asset[symbol]]["position"]["leverage"], indent=2))

            
        return leverage, size, long_only, short_only

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

##########
#########
# API CALL - NOT CHANGING
##########
#########
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

# return sd_df, extended_high, extended_low
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

    # get OHLCV data for the last 1.5 times the limit
    extended_df = get_ohlcv(binance_symbol, timeframe, limit=int(limit*1.5))

    # get high and low values for last 1.5 times the limit
    extended_high = extended_df['high'].max()
    extended_low = extended_df['low'].min()
    
    # print high and low values for last 1.5 times the limit
    print(f'High for last 1.5x {limit} bars: {extended_high}')
    print(f'Low for last 1.5x {limit} bars: {extended_low}')

    df = get_ohlcv(binance_symbol, timeframe, limit)
    df = df.tail(96) # consider only the last 96 bars
        
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

    return sd_df, extended_high, extended_low

def limit_order(coin: str, is_buy: bool, sz: float, limit_px: float, reduce_only: bool = False):
    ##########
    # API CALL - NOT CHANGING
    ##########
    account: LocalAccount = eth_account.Account.from_key(hyper_secret)
    exchange = Exchange(account, constants.MAINNET_API_URL)
    sz = round(sz, 1)
    limit_px = round(limit_px, 1)
    print(f'placing limit order for {coin} {sz} @ {limit_px}')

    # Calculate stop price
    if is_buy:
        # Assuming stop_perc is defined somewhere above
        stop = limit_px * (1 - (stop_perc / 100))
    else:
        stop = limit_px * (1 + (stop_perc / 100))
    stop = round(stop, 1)
    print(f'this is entry {limit_px} and stop {stop}')
    
    ##########
    # API CALL
    ##########
    # Entry order
    entry_order_type = {"limit": {"tif": "Gtc"}}
    order_result = exchange.order(coin, is_buy, sz, limit_px, entry_order_type, reduce_only=reduce_only)

    # Stop order
    stop_order_type = {"trigger": {"triggerPx": str(stop), "isMarket": True, "tpsl": "sl"}}  # Note: Typo "trigerPx" should be checked if it's correct.
    stop_result = exchange.order(coin, not is_buy, sz, stop, stop_order_type, reduce_only=True)

    # Output result
    if is_buy:
        print(f"limit BUY order placed, resting: {order_result['response']['data']['statuses'][0]}")
    else:
        print(f"limit SELL order placed, resting: {order_result['response']['data']['statuses'][0]}")

    return order_result

def get_position():

##########
#########
# API CALL - not changing
##########
#########
    account: LocalAccount = eth_account.Account.from_key(hyper_secret)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)
    print(f"this is current account value: {user_state['marginSummary']['accountValue']}")
    positions = []
    #print(f'****{user_state["assetPositions"]}')
    for position in user_state["assetPositions"]:
        #print(float(position["position"]["szi"]))
        if (position["position"]['coin'] == symbol) and float(position["position"]["szi"]) != 0:
            #print('***********')
            positions.append(position["position"])
            in_pos = True
            size = float(position["position"]["szi"])
            pos_sym = position["position"]["coin"]
            entry_px = float(position["position"]["entryPx"])
            pnl_perc = float(position["position"]["returnOnEquity"])*100
            #print(f'this is pnl perc {pnl_perc}')
            break
            # get size
            #print(positions)
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
##########
#########
# API CALL
##########
#########
    account: LocalAccount = eth_account.Account.from_key(hyper_secret)
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

##########
#########
# API CALL
##########
#########
    open_orders = info.open_orders(account.address)
    #print(open_orders)
    print('above are the open orders... need to cancel any...')
    for open_order in open_orders:
        #print(f"cancelling order {open_order}")
        exchange.cancel(open_order["coin"], open_order["oid"])


from typing import List
from decimal import Decimal

def get_open_order_prices() -> List[Decimal]:

##########
#########
# API CALL - i could start storing orders
##########
#########
    account = eth_account.Account.from_key(hyper_secret)
    api_url = constants.MAINNET_API_URL
    exchange = Exchange(account, api_url)
    info = Info(api_url, skip_ws=True)

##########
#########
# API CALL
##########
#########
    open_orders = info.open_orders(account.address)
    #print(open_orders)
    
    open_order_prices = []
    for open_order in open_orders:
        open_order_prices.append(Decimal(open_order['limitPx']))
        
    return open_order_prices

def kill_switch(symbol):

##########
#########
# API CALL
##########
#########

    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()

    while im_in_pos == True:

##########
#########
# API CALL
##########
#########

        cancel_all_orders()

        # get bid_ask
##########
#########
# API CALL
##########
#########
        askbid = ask_bid(pos_sym)
        ask = askbid[0]
        bid = askbid[1]

        pos_size = abs(pos_size)

        if long == True:
##########
#########
# API CALL
##########
#########
            limit_order(pos_sym, False, pos_size, ask)
            print('kill switch - SELL TO CLOSE SUBMITTED ')
            time.sleep(7)
        elif long == False:
##########
#########
# API CALL
##########
#########
            limit_order(pos_sym, True, pos_size, bid)
            print('kill switch - BUY TO CLOSE SUBMITTED ')
            time.sleep(7)
##########
#########
# API CALL
##########
#########

        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()

    print('position successfully closed in kill switch')

def pnl_close():

    '''
    build a pnl close to mamage risk
    '''
    print('entering pnl close')
##########
#########
# API CALL
##########
#########
    positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()
    if pnl_perc > target:
        print(f'pnl gain is {pnl_perc} and target is {target}... closing position WIN')

##########
#########
# API CALL
##########
#########
        kill_switch(pos_sym)
    elif pnl_perc <= max_loss:
        print(f'pnl loss is {pnl_perc} and max loss is {max_loss}... closing position LOSS')
##########
#########
# API CALL
##########
#########
        kill_switch(pos_sym)
    else:
        print(f'pnl loss is {pnl_perc} and max loss is {max_loss} and target {target}... not closing position')
    print('finished with pnl close')

def tr(data):
        data['previous_close'] = data['close'].shift(1)
        data['high-low'] = abs(data['high'] - data['low'])
        data['high-pc'] = abs(data['high'] - data['previous_close'])
        data['low-pc'] = abs(data['low'] - data['previous_close'])
        tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)
        return tr

    # after creating the true range formula above, i was able to create true range
def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()
    return atr

def no_trading(data,period):
    data['no_trading'] = (data['tr'] > max_tr).any()
    # if any are over the max_tr, it is not tradeable, so we want a false
    no_trading = data['no_trading'] 

    return no_trading

def get_atr_notrading():

    '''
    checks atr and if its too big dont trade
    BTC ATR
    '''
##########
#########
# API CALL
##########
#########
    bars = get_ohlcv('BTC/USD', timeframe='1h', limit=no_trading_past_hrs)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

##########
#########
# API CALL
##########
#########
    atrr= atr(df, 7)
    #print(atrr)

    df['no_trading'] = (df['tr'] > max_tr).any()
    # if any are over the max_tr, it is not tradeable, so we want a false
    no_trading = df['no_trading'].iloc[-1]  
    #print(df)

    print(f'no trading {no_trading}')

    return no_trading

def bot():

    # return sd_df, extended_high, extended_low
#def supply_demand_zones(symbol, timeframe, limit)

        sdz, extended_high, extended_low = supply_demand_zones(symbol, timeframe, limit)
        #print(sdz)

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

        '''
        6/20- update the buys and sells to order at their stops
        - define: two his/lows back
        .. in the last 8 hours... whats the high, and whats the low
            - thats where we enter... .1% under the high / low
        '''

        extended_high = extended_high * .999
        extended_low = extended_low * 1.001

        # see if in_pos - if no, place orders
##########
#########
# API CALL
##########
#########
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long = get_position()
        #print(positions, in_pos, size,  pos_sym ,entry_px, pnl_perc)
        # print im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, long
        print(f'pos size is {pos_size} im in pos is {im_in_pos} pnl perc is {pnl_perc} and long is {long}')

        # if pos_size >= size:
        #     in_full_pos = True

        # grab the current open orders
##########
#########
# API CALL
##########
#########
        openorderslist = get_open_order_prices()
        #print(openorderslist)
        openorderslist = [float(d) for d in openorderslist]

    ## only doing one order now so just checkin that
        if buy2 and sell2 in openorderslist:
            new_orders_needed = False
            print('buy2 and sell2 in open orders')
        else:
            new_orders_needed = True
            print('no open orders')

##########
#########
# API CALL
##########
#########
        account: LocalAccount = eth_account.Account.from_key(hyper_secret)
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        user_state = info.user_state(account.address)
        acct_value = user_state["marginSummary"]["accountValue"]
        acct_value = float(acct_value)

        # check the ATR to see if we need to set no_trading as True
        no_trading = get_atr_notrading() # this returns no_trading if atr is over max atr in passed 6 hours

        if acct_value < min_acct_value:  
            no_trading = True  

        if not im_in_pos and new_orders_needed == True and no_trading ==False:

            print('not in position.. setting orders...')
##########
#########
# API CALL
##########
#########
            # cancel all orders
            cancel_all_orders()
##########
#########
# API CALL
##########
#########
            leverage, size, long_only, short_only= adjust_leverage_size_signal()

            if long_only == True:
            # create buy order
            # buy1 = limit_order(symbol, True, size, buy1, False)
                buy2 = limit_order(symbol, True, size, extended_low, False)

            elif short_only == True:

            # create sell order
            # sell1 = limit_order(symbol, False, size, sell1, False)
                sell2 = limit_order(symbol, False, size, extended_high, False)
            else:
                buy2 = limit_order(symbol, True, size/2, extended_low, False)
                sell2 = limit_order(symbol, False, size/2, extended_high, False)

        elif im_in_pos and no_trading == False:
            print('we are in postion.. checking PNL loss')
##########
#########
# API CALL
##########
#########
            pnl_close()
        elif no_trading == True:
            # print(f'no trading is true cause acct value: {acct_value} and lowest value is {min_acct_value} cancelling orders')
##########
#########
# API CALL
##########
#########            
            cancel_all_orders()
            kill_switch(pos_sym)
        else:
            print('orders already set... chilling')

        time.sleep(3)

bot()