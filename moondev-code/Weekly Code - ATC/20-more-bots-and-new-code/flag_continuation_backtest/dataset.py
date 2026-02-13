from math import ceil
import ccxt
import pandas as pd
import datetime
import cbpro
from os.path import exists
import pathlib

phemex = ccxt.phemex()



def get_data(symbol,timeframe,limit=200):
    '''
    returns a pandas dataframe of the last n candles (n is limit variable) of the timeframe
    '''
    ohlcv = pd.DataFrame(phemex.fetch_ohlcv(symbol,timeframe,limit=limit),columns=['datetime','open','high','low','close','volume'])
    ohlcv['datetime'] = pd.to_datetime(ohlcv['datetime'],unit='ms')
    ohlcv = ohlcv.set_index('datetime')
    return ohlcv




def timeframe_to_sec(timeframe):
    if 'm' in timeframe:
        return int(''.join([char for char in timeframe if char.isnumeric()]))*60
    
    elif 'h' in timeframe:
        return int(''.join([char for char in timeframe if char.isnumeric()]))*60*60

    elif 'd' in timeframe:
        return int(''.join([char for char in timeframe if char.isnumeric()]))*24*60*60




def get_historical_data(symbol,timeframe,weeks,save_data=True):

    #check if we already have the data and return it if we do
    if exists(f'storage/{symbol}{timeframe}{weeks}.csv'):
        df = pd.read_csv(f'storage/{symbol}{timeframe}{weeks}.csv',index_col=0)
        df.index = pd.to_datetime(df.index)
        return df


    now = datetime.datetime.utcnow() #get the current time in utc timezone
    
    coinbase = cbpro.PublicClient() #connect to coinbase api

    total_time = weeks*7*24*60*60 #convert weeks to seconds
    max_time = timeframe_to_sec(timeframe)*200 #get the amount of seconds in one call to the api for 200 candles
    run_times = ceil(total_time/max_time)+1 #get the minimum amount of times we need to request a set of 200 candles from coinbase api

    
    dataframe = pd.DataFrame(columns=['datetime','low','high','open','close','volume']).set_index('datetime') #create empty dataframe to append candles to
    
    for i in range(run_times-1,-1,-1):
        s = now - datetime.timedelta(seconds=max_time*i) #get the time to start getting the candles
        e = now - datetime.timedelta(seconds=max_time*(i-1)) #get the time at the 200th candle


        data = coinbase.get_product_historic_rates(symbol,start=s,end=e,granularity=timeframe_to_sec(timeframe)) #get candles data from coinbase api
        df = pd.DataFrame(data,columns=['datetime','low','high','open','close','volume'])
        df = df.astype({"open": float, "close": float, "high": float, "low": float, "volume": float})
        df['datetime'] = pd.to_datetime(df['datetime'],unit='s') #convert timestamp to datetime object
        df = df.reindex(index=df.index[::-1])
        df = df.set_index('datetime')
        dataframe = pd.concat([dataframe,df])

    dataframe = dataframe[["open", "high", "low", "close", "volume"]] #reorganize the dataframe to the standard OHLCV format
    if save_data:
        dataframe.to_csv(str(pathlib.Path(__file__).parent.resolve())+f"/storage/{symbol}{timeframe}{str(weeks).replace('.','_')}.csv") #save the data to a file so you can quickly use later
    
    
    return dataframe



def get_candles_since_date(symbol,timeframe,start_time,save_data=True):

    #check if we already have the data and return it if we do
    if exists(f'storage/{symbol}{timeframe}{start_time.date()}.csv'):
        df = pd.read_csv(f'storage/{symbol}{timeframe}{start_time.date()}.csv',index_col=0)
        df.index = pd.to_datetime(df.index)
        return df

    

    now = datetime.datetime.utcnow() #get the current time in utc timezone
    
    coinbase = cbpro.PublicClient() #connect to coinbase api

    total_time = round((now - start_time).total_seconds()) #get time in seconds since the start date
    max_time = timeframe_to_sec(timeframe)*200 #get the amount of seconds in one call to the api for 200 candles
    run_times = ceil(total_time/max_time) #get the minimum amount of times we need to request a set of 200 candles from coinbase api

    
    dataframe = pd.DataFrame(columns=['datetime','low','high','open','close','volume']).set_index('datetime') #create empty dataframe to append candles to
    
    for i in range(run_times):
        s = start_time + datetime.timedelta(seconds=max_time*i) #get the time to start getting the candles
        e = start_time + datetime.timedelta(seconds=max_time*(i+1)) #get the time at the 200th candle


        data = coinbase.get_product_historic_rates(symbol,start=s,end=e,granularity=timeframe_to_sec(timeframe)) #get candles data from coinbase api
        df = pd.DataFrame(data,columns=['datetime','low','high','open','close','volume'])
        df = df.astype({"open": float, "close": float, "high": float, "low": float, "volume": float})
        df['datetime'] = pd.to_datetime(df['datetime'],unit='s') #convert timestamp to datetime object
        df = df.reindex(index=df.index[::-1])
        df = df.set_index('datetime')
        dataframe = pd.concat([dataframe,df])

    dataframe = dataframe[["open", "high", "low", "close", "volume"]] #reorganize the dataframe to the standard OHLCV format
    dataframe = dataframe.drop_duplicates()
    if save_data:
        dataframe.to_csv(str(pathlib.Path(__file__).parent.resolve())+f"/storage/{symbol}{timeframe}{start_time.date()}.csv") #save the data to a file so you can quickly use later
    
    
    return dataframe