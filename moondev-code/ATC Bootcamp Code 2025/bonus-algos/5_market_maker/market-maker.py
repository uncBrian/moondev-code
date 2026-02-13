'''
Market Maker 

note: this is built for phemex, if using a different exhange
you will need to make some tweaks 

disclaimer: please do not use this live in production without doing your own testing
this is meant to just be an example to quicken your dev process of your
own market maker
'''

import ccxt
import xconfig
import pandas as pd 
import time 
from datetime import datetime, timedelta 
import schedule 
import warnings
warnings.filterwarnings("ignore")

# JM ACCOUNT - 10/30 going back here
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': xconfig.phemex_KEY,
    'secret': xconfig.phemex_SECRET, 
})

############### INPUTS #####################
size = 4200 # total size we want to PER buy/sell 
# size_1 = size * .2 # 20%
# size_2_3 = size * .4 # 40%
symbol = 'DYDXUSD'
perc_from_lh = .35 
close_seconds = 60*47 # this is 47 minutes into seconds
trade_pause_mins = 15
max_lh = 1250 # 
timeframe = '5m' # 5 * 180 = 15 hours
num_bars = 180
max_risk = 1100 # $ value of max risk 
sl_perc = 0.1 
exit_perc = 0.004 
max_tr = 550 
quartile = 0.33 
time_limit = 120
sleep = 30 
#############################################


def get_bid_ask(symbol=symbol):

    '''
    this function gets bid and ask price
    and also bid and ask volume
    returns ask, bid, ask_vol, bid_vol
    '''
    # PULL ORDER BOOK FOR BTC
    btc_phe_book = phemex.fetch_order_book(symbol)
    #print(btc_phe_book)
    btc_phe_bid = btc_phe_book['bids'][0][0]
    btc_phe_ask = btc_phe_book['asks'][0][0]
    bid_vol = btc_phe_book['bids'][0][1]
    ask_vol = btc_phe_book['asks'][0][1]

    return btc_phe_ask, btc_phe_bid, ask_vol, bid_vol

# this function gets all of our open positions
def open_positions(symbol=symbol):

    '''
    this function gets all of our open positions
    returns: 
    open_positions, openpos_bool, openpos_size, long, pos_df
    '''
# PULL POSITIONS FOR BTC + LAST ENTRY
    params = {'type':"swap", "code": "USD"}
    all_phe_balance = phemex.fetch_balance(params=params)
    open_positions = all_phe_balance['info']['data']['positions']

    pos_df = pd.DataFrame.from_dict(open_positions)
    
    openpos_side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]
    openpos_size = pos_df.loc[pos_df['symbol']==symbol, 'size'].values[0]


    # getting a true or false if there is an open position
    if openpos_side == ('Buy'): 
        openpos_bool = True 
        long = True

    elif openpos_side == ('Sell'):
        openpos_bool = True 
        long = False
       
    else: 
        openpos_bool = False
        long = 0


    return open_positions, openpos_bool, openpos_size, long, pos_df # run this when i need to re read the dictionary

# for risk if size ever gets too big
def size_kill(symbol=symbol):

    params = {'type':"swap", "code": "USD"}
    all_phe_balance = phemex.fetch_balance(params=params)
    open_positions = all_phe_balance['info']['data']['positions']
    

    # pos_df = pd.DataFrame.from_dict(open_positions)
    # #print(pos_df)
    # #print(pos_df.columns)

    # side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]

    pos_df = pd.DataFrame.from_dict(open_positions)
    #print(pos_df)

    pos_cost = pos_df.loc[pos_df['symbol']==symbol, 'posCost'].values[0]
    pos_cost = float(pos_cost)
    #print(f'position cost: {pos_cost}')
    openpos_side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]
    openpos_size = pos_df.loc[pos_df['symbol']==symbol, 'size'].values[0]
    #print(f'openpos_side : {openpos_side}')


    if pos_cost > max_risk:

        print(f'EMERGENCY KILL SWITCH ACTIVATED DUE TO CURRENT POSITION SIZE OF {pos_cost} OVER MAX RISK OF:  {max_risk}')

        phemex.cancel_all_orders(symbol)
        # this cancels the conditional order
        phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
        print('just canceled all open orders bc we had a stop loss with no open orders')

        openpos_side = open_positions[0]['side']
        openpos_size = open_positions[0]['size']
        print(f'openpos_side : {openpos_side}')

        if openpos_side == 'Sell':

            phemex.create_market_buy_order(symbol, openpos_size)
            print('just close order with a market BUY cause we were SHORT')

            print('putting to sleep for 72 hours til i can see whats up')
            time.sleep(260000)

        elif openpos_side == 'Buy':

            phemex.create_market_sell_order(symbol, openpos_size)
            print('just close order with a market SELL cause we were LONG')

            print('putting to sleep for 72 hours til i can see whats up')
            time.sleep(260000)

        else:
            print('***no open orders to market so nothing submitted')


    else:

        size_kill = 'no'

        #print(f'size kill check: current position cost is: {pos_cost} we are gucci')


# kill switch 
def kill_switch(symbol=symbol):

    """
    This function cancels all orders and 
    closes any open positions for the 
    specified symbol.
    """


    openposi = open_positions(symbol)[1] # this returns T/F for open pos yes.no
    
    long = open_positions(symbol)[3] # this sets long to T/F

    print('KILL SWITCH ACTIVATED.... going to loop til limit close...')
    #print(f' open position is set to: {openposi} if true we continue to while exit loop') # why it saying false?

    btc_kill_size = open_positions(symbol)[2] # this gets the open position size
    btc_kill_size = int(btc_kill_size) # this puts it in int form
    
    while openposi == True:

        print('starting kill switch loop again til Limit fill...')
        temp_df = pd.DataFrame()
        print('just made a new temp_df for the kill switch, cancelling all orders...')

        # this cancels all orders
        phemex.cancel_all_orders(symbol)
        # this cancels the conditional order
        phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})

        #print('getting T/F for if open pos... and if long is T/F.... inside the Kill while..')
        openposi = open_positions(symbol)[1] # this returns T/F for open pos yes.no
        long = open_positions(symbol)[3] # this sets long to T/F

        # bringing kill size in here because i dont wanna ever over sell or buy
        btc_kill_size = open_positions(symbol)[2] # this gives perf kill size
        btc_kill_size = int(btc_kill_size)

        now = datetime.now()
        dt_string = now.strftime("%m/%d/%Y %H:%M:%S")
        # print(dt_string)
        comptime = int(time.time())
        # print(comptime)

        # get bid ask
        ask = get_bid_ask(symbol)[0]
        bid = get_bid_ask(symbol)[1]

        if long == False:
            phemex.cancel_all_orders(symbol)
            # this cancels the conditional order
            phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
            params = {'timeInForce': 'PostOnly',}
            phemex.create_limit_buy_order(symbol, btc_kill_size, bid) #, params)
            temp_df['desc'] = ['kill switch']
            temp_df['open_time'] = [comptime]
            print(f'just made a BUY to CLOSE order of {btc_kill_size} {symbol} at: ${ask}')
            print('sleeping for 30 sec to see if it fills....')
            time.sleep(30)

   
        elif long == True:
            phemex.cancel_all_orders(symbol)
            # this cancels the conditional order
            phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
            # create the close SELL order cause we LONG
            params = {'timeInForce': 'PostOnly',}
            phemex.create_limit_sell_order(symbol, btc_kill_size, ask) #, params)
            temp_df['desc'] = ['kill switch']
            temp_df['open_time'] = [comptime]
            print(f'just made a  SELL to CLOSE order of {btc_kill_size} {symbol} at: ${bid}')
            print('sleeping for 30 sec to see if it fills....')
            time.sleep(30)
        
        else:
            print('+++++SOMETHING WEIRD inside of KILL switch it essentially said no long, no short so went to else...')


def active_orders2(symbol=symbol):


    btc_open_orders = phemex.fetch_open_orders(symbol)
    #print(btc_open_orders)

    # check to see that they both work, if not, then we go deeper
    need_sl = False
    need_close_order = False
    sl_n_close_bool = False
    already_limt_to_open = False

    try:
        ordertype_0 = btc_open_orders[0]['type']

        ordertype_1 = btc_open_orders[1]['type']

        if (ordertype_0 == ('StopLimit') or ('limit')) and (ordertype_1 == ('StopLimit') or ('limit')):
            sl_n_close_bool = True
            #print(f'sl_n_close_bool = True')
        else:
            print('++++++++active_orders2 try block worked but then something went wrong in the else statemet')
    except:
        
        print('we DO NOT have EITHER a CLOSE and a STOP LOSS (one or other)')

        try:
            #print('trying to see if we have one or the other')
            ordertype_0 = btc_open_orders[0]['type']
 
            if ordertype_0 == ('StopLimit') and (not open_positions):
                print('we only have a stop loss with NO open positions (NEED TO CX)')
                # canceling order because we have a stop loss with no open pos
                phemex.cancel_all_orders(symbol)
                # this cancels the conditional order
                phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
                print('just canceled all open orders bc we had a stop loss with no open orders')
            elif ordertype_0 == ('StopLimit' )and (open_positions):
                print('we only have a stop loss with ACTIVE open positions.. NEED CLOSE ORDER')
                # SUBMIT a CLOSE ORDER
                need_close_order = True
            elif ordertype_0 == ('limit') and (open_positions):
                print('we have a CLOSE order & OPEN POS but no STOP loss, turning need_sl to True')
                # SUBMIT A STOP LOSS, this should rarely happen tho bc we submit our
                need_sl = True
            elif ordertype_0 == ('limit') and (not open_positions):
                # this means we have a limit order that is pending to get filled
                print('have a limit order pending to get filled, no stop loss')
                already_limt_to_open = True
            else:
                print('+++++++++++++SOMETHING ELSE I DIDNT THINK OF HAPPENING IN ACTIVE_ORDERS2')
        except:
            print('CONFIRMED we dont have EITHER a SL or CLOSE')

            try:
                openpos = open_positions()[1]
    
                
                if openpos == True:
                    need_close_order = True
                    print('it looks like we need a close order so set needclose to True')
                else:
                    print('next statement')
            except:
                print('just checked if we need a close order and we dont')

    return sl_n_close_bool, need_sl, need_close_order, already_limt_to_open


# not using this for now but dont wanna delete
def active_orders(symbol=symbol):
    

    # checking to see if there are any open orders
    try:
        #print('MADE IT TO TRY BLOCCK')
        btc_open_orders = phemex.fetch_open_orders(symbol)
        #print(btc_open_orders)
        # referring to the dictionary position with 0 & 1
        ordertype_0 = btc_open_orders[0]['type']
        #print(f'ordertype_0 = {ordertype_0}')
        ordertype_1 = btc_open_orders[1]['type']

        btc_open_orders = btc_open_orders[0]['remaining']
        print(f'****remaining = {btc_open_orders}')

        #print(f'we have open BTC orders of: {btc_open_orders} contract')
        btc_open_orders_bool = True
        #print(f'btc_open_orders_bool set to: {btc_open_orders_bool}')
    except:
        btc_open_orders = phemex.fetch_open_orders(symbol)
        #print('for BTC there are NO OPEN ORDERS')
        btc_open_orders_bool = False 
        #print(f'btc_open_orders_bool set to: {btc_open_orders_bool}')

    return btc_open_orders_bool, btc_open_orders

def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])
    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    return tr 

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()
    return atr 

# no trading rule - if TR is higher than the var i made above, no trade
def notrade_atr(data):
    data['notrade_atr'] = (data['tr'] > max_tr).any() # sets T/F
    notrade_atr = data['notrade_atr']

    return notrade_atr

def frame(df, period=7):
    #print('making the data frame...')
    df['atr'] = atr(df, period)

    #print(df2)

    return df

##### PROFIT AND LOSS CHECK

def get_pnl(symbol=symbol):

    '''
    this gets the positions pnl 
    '''

    # grab the $ amount of profit/loss and then figure %
    params = {'type':'swap', 'code':'USD'}
    balance = phemex.fetch_balance(params)
    balance_usd = balance['USD']['total']
    open_positions = balance['info']['data']['positions']


    pos_df = pd.DataFrame.from_dict(open_positions)

    side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]

    leverage = pos_df.loc[pos_df['symbol']==symbol, 'leverage'].values[0]

    leverage = float(leverage)
    sizeee = pos_df.loc[pos_df['symbol']==symbol, 'size'].values[0]
    sizeee = float(sizeee)

    entryPrice = pos_df.loc[pos_df['symbol']==symbol, 'avgEntryPrice'].values[0]

    entry_price = float(entryPrice)

    # get ask_bid 
    ob = phemex.fetch_order_book(symbol)
    current_price = ob['bids'][0][0]
    ask = ob['asks'][0][0]
    bid = current_price

    if side == 'Buy':
        diff = float(current_price - entry_price)
    elif side == 'Sell': 
        diff = float(entry_price - current_price)

    try: 
        perc = round(((diff/entry_price) * leverage), 10)
    except:
        perc = 0

    perc = 100*perc
    pnl = f'PNL: {perc}%'
    print(pnl)

    return pnl, ask, bid

def trade_in_last_n_mins(n=trade_pause_mins):
    '''
    returns True if there was a trade in the last N mins
    False if there was not a trade in the last N mins
    if False, we can continue to move forward

    this doesnt work cause its getting all recent trades, not just mine
    '''
    # Retrieve a list of the recent trades
    trades = phemex.fetch_trades(symbol)
    #print(trades)

    # Check the timestamp of each trade to see if it was made within the last 10 minutes
    for trade in trades:
        # Convert the timestamp to a datetime object
        trade_time = datetime.fromtimestamp(float(trade['timestamp']) / 1000)
        
        # Check if the trade was made within the last 10 minutes
        if (datetime.now() - trade_time) < timedelta(minutes=n):
            print(datetime.now())
            print(trade_time)
            print(datetime.now() - trade_time)
            print(timedelta(minutes=n))
            return True
    
    # If no trades were made within the last 10 minutes, return False
    return False

def stop_order(symbol, hi_lo, dir):  

    '''
    this makes a stop loss order
    '''

    # get the size of the open pos or set to size
    open_size = float(open_positions()[2])
    print(f'this is the current size {open_size}')
    print(type(open_size))
    
    if open_size == 0: 
        open_size = size
    print(f'now is the open size {open_size}')

    if dir == 'SELL':
        
        # stop_price = (hi_lo *10000) +10000 # hi = 10 and the stop price = 12
        stop_price = ((hi_lo) * 1.001) 
        # stop_trigger = stop_price + 20000
        stop_trigger = (stop_price * 1.001) 
        print(f'stop price {stop_price}')
        print(f'stop trigger {stop_trigger}')

        
        
        sl_params = {
            "clOrdID": "stop-loss-order-then-limit",
            'timeInForce': 'PostOnly',
            "symbol": symbol,
            "side": "Buy",
            "ordType": "StopLimit",
            "triggerType": "ByLastPrice",
            "stopPx": stop_trigger, 
            "price": stop_price, 
            "orderQty": open_size
        }
        stop_order = phemex.create_order(symbol, type='limit', side='Buy',  amount=open_size, price=stop_price, params=sl_params) # THESE VALUES ARE IN USD, NOT BTC
        print("****JUST MADE STOP LOSS AS BUY BACK****")
        # temp_df['stop_loss'] = [stop_price/10000]

    elif dir == 'BUY':

        stop_price = ((hi_lo) * 0.999) 
        # stop_trigger = stop_price + 20000
        stop_trigger = (stop_price * 0.999) 
        print(f'stop price {stop_price}')
        print(f'stop trigger {stop_trigger}')

        
        sl_params = {
            "clOrdID": "stop-loss-order-then-limit",
            'timeInForce': 'PostOnly',
            "symbol": symbol,
            "side": "Sell",
            "ordType": "StopLimit",
            "triggerType": "ByLastPrice",
            "stopPx": stop_trigger, 
            "price": stop_price, 
            "orderQty": open_size
        }
        stop_order = phemex.create_order(symbol, type='limit', side='Sell',  amount=open_size, price=stop_price, params=sl_params) # THESE VALUES ARE IN USD, NOT BTC
        print("****JUST MADE STOP LOSS AS SELL BACK****")
        # temp_df['stop_loss'] = [stop_price/10000]


#######################################################
################### BOT #######################
#######################################################

def bot():
    print(' ')
    print('---- MARKET MAKER IS LIVE ---')
    print(' ')
    # CHECK PNL
    pnl = get_pnl(symbol) # setting to a variable bc i want bid/ask
    ask = pnl[1]
    bid = pnl[2] #return pnl, ask, bid

    size_kill() # closes position if ever over max_risk $1000



# TODO - change back to read csv
    # store our close time.. 
    df2 = pd.DataFrame() # store our trades, only run on the first time thru
    #df2 = pd.read_csv('dec22/live_models/algo-trades.csv')

    now = datetime.now()
    dt_string = now.strftime("%m/%d/%Y %H:%M:%S")
    print(dt_string)
    comptime = int(time.time())
    print(comptime)
    # time.sleep(344444)

    try:

        last_close_time = df2['close_time'].values[-1]
        last_close_time = int(last_close_time)
        print(f'this is last_close_time {last_close_time}')

    except:

        last_close_time = comptime
        last_close_time = int(last_close_time)
        print(f'EXCEPTION - this is last_close_time {last_close_time}')


    
    activeorders2  = active_orders2()

    sl_n_close_bool = activeorders2[0]
    need_sl = activeorders2[1]
    need_close = activeorders2[2]
    already_limt_to_open = activeorders2[3]


    bars = phemex.fetch_ohlcv(symbol, timeframe=timeframe, limit=num_bars) 
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']) 
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    frame_data = frame(df)

    low = df['low'].min()
    hi = df['high'].max()
    l2h = hi - low 
    avg = (hi+low)/2

    print(f'the low is {low} the high is {hi} | low to hi: {l2h} | avg price: {avg} | max L2h: {max_lh} ')

    if l2h > max_lh:
        no_trading = True 
        print('XXXXXXX NO TRADING CUZ L2H XXXXXXX')
        kill_switch()
        return # this essentially kills the function. 
    else:
        no_trading = False 
        #print('no trading is False')

    df_tolist = df['low'].tolist()
    last17 = df_tolist[-17:]

    for num in last17:
        if low >= num:
            no_trading = True 
            #print(f'the low is bigger than any of the last N bars so no trading = True low {low} num: {num}')
        elif hi <= num:
            no_trading = True 
            #print(f'the hi is less than any of the last N bars so no trading = True hi: {hi} num: {num}')
        else:
            #print(f'no trading wasnt triggered by the last 17 bars meaning we are not making higher his or lower lows low: {low} hi {hi} num {num}')
            no_trading = False 

    atr_high = df['atr'].max()
    low =df['low'].min()
    #print(f'this is the LOW in the period: {low}')
    hi = df['high'].max() 
    #print(f'this is the HI in the period: {hi}')

    temp_df = pd.DataFrame()
    
    bid_1 = bid * .9991
    bid_2 = bid * .997
    bid_3 = bid * .995
    ask_1 = ask * 1.0009
    ask_2 = ask * 1.003
    ask_3 = ask * 1.005

    def buy_order():
        params = {'timeInForce': 'PostOnly'}
        phemex.create_limit_buy_order(symbol, size, bid_1, params)
        # buy 2
        #phemex.create_limit_buy_order(symbol, size_2_3, bid_2, params)
        # buy 3
        #phemex.create_limit_buy_order(symbol, size_2_3, bid_3, params)
        # change entry price to bid_1
        temp_df['entry_price'] = [bid_1]
        temp_df['dir'] = ['long']
        # 8/20 - since im not on the bid/ask anymore, i sleep
        print('submitted 3 BUY orders to OPEN, sleeping 5mins')
        
        time.sleep(300)

    def sell_order():
        params = {'timeInForce': 'PostOnly'}
        phemex.create_limit_sell_order(symbol, size, ask_1, params)
        # sell 2
        #phemex.create_limit_sell_order(symbol, size_2_3, ask_2, params)
        # sell 3
        #phemex.create_limit_sell_order(symbol, size_2_3, ask_3, params)
        # change entry price to ask_1
        temp_df['entry_price'] = [ask_1]
        temp_df['dir'] = ['short']
        # 8/20 - since im not on the bid/ask anymore, i sleep
        print('submitted 3 SELL orders to OPEN, sleeping 5mins')
    
        time.sleep(300)
    
    openposinfo = open_positions()
    open_pos = openposinfo[0]
    btc_open_pos = open_pos[0]
    pos_df = openposinfo[4]
  
    # return open_positions, openpos_bool, openpos_size, long, pos_df

    open_pos_side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]
    open_pos_entry = pos_df.loc[pos_df['symbol']==symbol, 'avgEntryPrice'].values[0]
    open_pos_size = pos_df.loc[pos_df['symbol']==symbol, 'size'].values[0]
    btc_pos_side = pos_df.loc[pos_df['symbol']==symbol, 'side'].values[0]

    #open_pos_side = btc_open_pos['side']
    open_pos_entry = float(open_pos_entry)
    open_pos_size = float(open_pos_size)
    print(f'pos side: {open_pos_side} | entry price: {open_pos_entry} | size: {open_pos_size}')
    
    #btc_pos_side = btc_open_pos['side']
    if btc_pos_side == 'Sell':
        long = False 
        print('we are in a SHORT position')
    elif btc_pos_side == 'Buy':
        long = True 
        print('we are in a LONG position')
    else:
        print('no open positions..')
        long = 0 

    # set position to true false
    if open_pos_size > 0:
        btc_open_pos = True 
        #print(f'btc_open_pos set to {btc_open_pos}')
    else:
        btc_open_pos = False 
        #print(f'btc_open_pos set to {btc_open_pos}')

    # stop loss is diff for long and short
    if long == True:
        exit_price = open_pos_entry * (1+exit_perc)
    elif long == False:
        exit_price = open_pos_entry * (1-exit_perc)
    else:
        print('no stop loss or exit cuz no position')

    low = df['low'].min()
    hi = df['high'].max()
    l2h = hi - low
    avg = (hi+low)/2
    #print(f'the low is {low} the high is {hi} | low to hi: {l2h} | avg price: {avg} | max L2h: {max_lh} ')

    max_time_plus_last_close = last_close_time + (time_limit * 60)

    # if been in a trade too long, get out
    if (comptime > max_time_plus_last_close) and (btc_open_pos == True):
        openposi = open_positions()[1]
        print('KILL SWITCH ACTIVATED - bc TIME LIMIT reached, canceling and killing')
        btc_kill_size = open_positions()[2]
        btc_kill_size = int(btc_kill_size)

        while openposi == True:

            print('starting kill switch looop again')

            btc_kill_size = open_positions()[2]
            btc_kill_size = int(btc_kill_size)

            phemex.cancel_all_orders(symbol)
            phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})

            askbid = get_bid_ask()
            ask = askbid[0]
            bid = askbid[1]

            # close all positions
            if long == False:
                phemex.cancel_all_orders(symbol)
                phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
                closed = False 

                params = {'timeInForce': 'PostOnly',}
                phemex.create_limit_buy_order(symbol, btc_kill_size, bid, params)
                temp_df['desc'] = ['kill switch']
                temp_df['open_time'] = [comptime]
                close_time = comptime + close_seconds
                temp_df['close_time'] = [close_time]
                print(f'just made a post only BUY to CLOSE order of {btc_kill_size} {symbol} at: ${ask}')
                print('sleeping for 30 sec to see if it fills')
                time.sleep(30)
                openposi = open_positions()[1]

            elif long == True:
                phemex.cancel_all_orders(symbol)
                phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
                closed = False

                params = {'timeInForce': 'PostOnly',}
                phemex.create_limit_sell_order(symbol, btc_kill_size, ask, params)
                temp_df['desc'] = ['kill switch']
                temp_df['open_time'] = [comptime]
                close_time = comptime + close_seconds
                temp_df['close_time'] = [close_time]
                print(f'just made a post only SELL to CLOSE order of {btc_kill_size} {symbol} at: ${bid}')
                print('sleeping for 30 sec to see if it fills')
                time.sleep(30)
                openposi = open_positions()[1]

            else:
                print('++++++ something in the time close is off... ')


            open_pos = open_positions()[0]
            btc_open_pos = open_pos[3]

            open_pos_side = btc_open_pos['side']
            open_pos_entry = float(btc_open_pos['avgEntryPrice'])
            open_pos_size = float(btc_open_pos['size'])
            print(f'pos side: {open_pos_side} | entry price: {open_pos_entry} | size: {open_pos_size}')
            
            btc_pos_side = btc_open_pos['side']
            if btc_pos_side == 'SELL':
                long = False 
                print('we are in a SHORT position')
                openposi = True
            elif btc_pos_side == 'BUY':
                long = True 
                print('we are in a LONG position')
                openposi = True
            else:
                print('no open positions..')
                long = 0 
                openposi = False 


    else: 
        #print('we have not been in a position too long...')
    
        # make sure we dont trade in bad ranges
        open_range = l2h * perc_from_lh
        #print(f'the open range == {open_range} meaning we only trade that range from l2h')
        sell2open_limit = hi - open_range
        #print(f'this is the sell2open_limit: {sell2open_limit}')
        buy2open_limit = low + open_range
        #print(f'this is the buy2open_limit {buy2open_limit}')

        ## OPEN AN ORDER
        if (not btc_open_pos) and (not already_limt_to_open) and (no_trading == False):

            open_size = open_positions()[2]
            if open_size == 0: open_size = size

            if ask > sell2open_limit:
                print('SELLING to open because the ASK is less than the sell2open limit')
                phemex.cancel_all_orders(symbol)

                # this cancels the conditional order
                phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
                print('just canceled all orders and conditional orders')
                sell_order()

                #temp_df['order_time'] = [dt_string]
                comptime = time.time() 
                temp_df['desc'] = ['sell2open']
                temp_df['open_time'] = [comptime]
                close_time = comptime + close_seconds
                temp_df['close_time'] = [close_time]
                temp_df['dt'] = [dt_string]
                print('***Just made a SELL to open***')
                # put in stop loss here

                # using my new stop_order function instead of the old code
                stop_order(symbol, hi, 'SELL')
            
            elif bid < buy2open_limit: 

                print('BUYING to open bc the Bid is less than the buy2open limit')
                print('got inside the buy order')
                phemex.cancel_all_orders(symbol)
                # this cancels the conditional order
                phemex.cancel_all_orders(symbol=symbol, params={'untriggered': True})
                print('just canceled all orders and conditional orders')
                buy_order()
                #temp_df['order_time'] = [dt_string]
                comptime = time.time() 
                temp_df['desc'] = ['buy2open']
                temp_df['open_time'] = [comptime]
                close_time = comptime + close_seconds
                temp_df['close_time'] = [close_time]
                temp_df['dt'] = [dt_string]
                print('***Just made a BUY to open***')

                # using my new stop_order function instead of the old code
                stop_order(symbol, low, 'BUY')
            
            else:
                print('no order submitted, prob in the middle of range')

        # checking to see if need a close order
        elif need_close == True:

            btc_kill_size = open_positions()[2]
            btc_kill_size = int(btc_kill_size)

            if long == False:
                closed = False 
                params = {'timeInForce': 'PostOnly',}
                order = phemex.create_limit_buy_order(symbol, btc_kill_size, exit_price) #, params)
                print(f'just made a post only BUY to CLOSE order of {btc_kill_size} {symbol} at: ${exit_price}')

            elif long == True:
                params = {'timeInForce': 'PostOnly',}
                order = phemex.create_limit_sell_order(symbol, btc_kill_size, exit_price) #, params)
                print(f'just made a post only SELL to CLOSE order of {btc_kill_size} {symbol} at: ${exit_price}')

            else:
                print('+++ SOMETHING WEIRD HAPPENED in NEED_CLOSE')

        # checking to see if we need a stop loss
        elif need_sl == True:

            askbid = get_bid_ask()
            ask = askbid[0]
            bid = askbid[1]

            open_size = open_positions()[2]
            if open_size == 0: open_size = size

            if long == False:

                # using my new stop_order function instead of the old code
                stop_order(symbol, hi, 'SELL')


            elif long == True:

                # using my new stop_order function instead of the old code
                stop_order(symbol, hi, 'BUY')

            else:
                print('+++ SOMETHING WEIRD in the last Stop loss hapened')
        
        else:
            print(':) :) :) we gucci, all orders are in place, taking 20s nap')
            time.sleep(12)

    df2 = df2.append(temp_df)
    df2.to_csv('algo-trades.csv', index=False)

    

    print('========================')
    #print('')
    #print('========================')


bot() 

schedule.every(25).seconds.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(15)
    except:
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        print('++++++++++++++++ MAYBE INTERNET PROBLEM BOT DOWN ++++++++++++++++')
        time.sleep(75)
