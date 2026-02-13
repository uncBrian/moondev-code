import pandas as pd
from datetime import datetime, time
from pytz import timezone
import pandas_ta as ta
from time import sleep 
import math



def get_candle_df(phemex,symbol,timeframe,limit=200):
    '''
    returns a pandas dataframe of the last n candles (n is limit variable)
    '''
    ohlcv = pd.DataFrame(phemex.fetch_ohlcv(symbol,timeframe,limit=limit),columns=['time','open','high','low','close','volume']).set_index('time')
    return ohlcv





def calc_stoch_rsi(df,lookback=14):
    '''
    calculate and add the stock_rsi to the input dataframe
    '''

    #use pandas_ta to calculate the rsi
    rsi = df.ta.rsi(length = lookback)

    #convert rsi to stoch rsi, equation: (current rsi - min rsi) / (max rsi - min rsi)
    df['stoch_rsi'] = (rsi.iloc[-1] - rsi.tail(lookback).min()) / (rsi.tail(lookback).max() - rsi.tail(lookback).min())





def calc_nadarya(df,bandwidth=8,source='close'):
    '''
    calculate the nadarya indicator and return the most recent buy/sell signals
    '''
    src = df[source]

    out = []
    
    for i,v1 in src.iteritems():
        tsum = 0
        sumw = 0
        for j,v2 in src.iteritems():
            w = math.exp(-(math.pow(i-j,2)/(bandwidth*bandwidth*2)))
            tsum += v2*w
            sumw += w
        out.append(tsum/sumw)
        
    df['nadarya'] = out
    d = df['nadarya'].rolling(window=2).apply(lambda x: x.iloc[1] - x.iloc[0])
    df['nadarya_buy'] = (d > 0) & (d.shift(1) < 0)
    df['nadarya_sell'] = (d < 0) & (d.shift(1) > 0)

    return df['nadarya_buy'].iloc[-1], df['nadarya_sell'].iloc[-1] #returns buy signal, sell signal





def is_oversold(rsi,window=14,times=1,target=10):
    '''
    returns True if the rsi in the given window has gone below 10.
    Times variable is how many times you want the oversold mark to be hit before returning True
    '''
    #rsi = rsi.tail(window)
    rsi = rsi.tail(window)

    #get a list of the values when the rsi has crossed under 20
    rsi_crossed = [v for ind,v in enumerate(rsi.values) if v <= target and rsi.values[ind-1] >= target and ind > 0]
    
    #return True if the rsi has crossed under 10 more than wanted
    if len(rsi_crossed) >= times:
        return True
    return False




def is_overbought(rsi,window=14,times=1,target=90):
    '''
    returns True if the rsi in the given window has gone above 90. 
    Times variable is how many times you want the overbought mark to be hit before returning True
    '''
    rsi = rsi.tail(window)

    #get a list of the values when the rsi has crossed over 80
    rsi_crossed = [v for ind,v in enumerate(rsi.values) if v >= target and rsi.values[ind-1] <= target and ind > 0]

    #return True if the rsi has crossed over 90 more than wanted
    if len(rsi_crossed) >= times:
        return True
    return False





def get_position(phemex,symbol):
    '''
    get the info of your position for the given symbol.
    '''
    params = {'type':'swap', 'code':'USD'}
    phe_bal = phemex.fetch_balance(params=params)
    #get your position for the provided symbol
    position_info = [pos for pos in phe_bal['info']['data']['positions'] if pos['symbol'] == symbol][0]

    #if there is a position (side is none when no current position)
    if position_info['side'] != 'None':
        in_position = True
        long = True if position_info['side'] == 'Buy' else False

    #if not in position currently
    else:
        in_position = False
        long = None 

    return position_info, in_position, long





def close_position(phemex,symbol):
    '''
    close your position for the given symbol
    '''

    #close all pending orders
    phemex.cancel_all_orders(symbol)

    #get your current position information (position is a dict of position information)
    position,in_position,long = get_position(phemex,symbol)
    

    #keep trying to close position every 30 seconds until sucessfully closed
    while in_position:

        #if position is a long create an equal size short to close. 
            #use reduceOnly to make sure you dont create a trade in the opposite direction
            #sleep for 30 seconds to give order a chance to fill
        if long:
            bid = phemex.fetch_ticker(symbol)['bid'] #get current bid price
            order = phemex.create_limit_sell_order(symbol, position['size'], bid, {'timeInForce': 'PostOnly', 'reduceOnly':True})
            print(f'just made a BUY to CLOSE order of {position["size"]} {symbol} at ${bid}')
            sleep(30)

        #if position is a short create an equal size long to close. 
            #use reduceOnly to make sure you dont create a trade in the opposite direction
            #sleep for 30 seconds to give order a chance to fill
        else:
            ask = phemex.fetch_ticker(symbol)['ask'] #get current ask price
            order = phemex.create_limit_buy_order(symbol, position['size'], ask, {'timeInForce': 'PostOnly', 'reduceOnly':True})
            print(f'just made a SELL to CLOSE order of {position["size"]} {symbol} at ${ask}')
            sleep(30)

        position,in_position,long = get_position(phemex,symbol)


    #cancel all outstanding orders
    phemex.cancel_all_orders(symbol)

    #sleep for a minute to avoid running twice
    sleep(60)


