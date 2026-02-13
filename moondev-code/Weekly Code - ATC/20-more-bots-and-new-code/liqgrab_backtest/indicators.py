import pandas_ta as ta
from datetime import time
import pandas as pd
from indicators import *



def crossover(series,value,last=True):
    '''
    returns True if the series crosses over the value
    '''
    temp_df = pd.DataFrame()
    temp_df['col1'] = series.tolist()

    if type(value) in [float,int]:
        # return True if series.iloc[-1] > value and series.iloc[-2] < value else False
        temp_df['col2'] = [value]*len(series)
    else:
        temp_df['col2'] = value.tolist()

    out = (temp_df['col1'] > temp_df['col2']) & (temp_df['col1'].shift(1) < temp_df['col2'].shift(1))

    return out.iloc[-1] if last else out


def crossunder(series,value,last=True):
    '''
    returns True if the series crosses under the value
    '''

    temp_df = pd.DataFrame()
    temp_df['col1'] = series.tolist()

    if type(value) in [float,int]:
        # return True if series.iloc[-1] > value and series.iloc[-2] < value else False
        temp_df['col2'] = [value]*len(series)
    else:
        temp_df['col2'] = value.tolist()

    out = (temp_df['col1'] > temp_df['col2']) & (temp_df['col1'].shift(1) < temp_df['col2'].shift(1))

    return out.iloc[-1] if last else out


def asian_range(df,start_time=time(19,0,0),end_time=time(1,0,0)):
    '''
    returns a pandas series which will be true if the index is within the asian range (defined by start and end time parameters) 
    '''
    df['timestamp'] = [val.time() for val in df.index.tolist()]
    df['asian_range'] = ((df['timestamp'] >= start_time) | (df['timestamp'] <= end_time))


    new_col_high_vals = []
    new_col_low_vals = []
    high_values = []
    low_values = []
    for index,row in df.iterrows():
        if row['asian_range']:
            high_values.append(row['High'])
            low_values.append(row['Low'])

            new_col_high_vals.append(max(high_values))
            new_col_low_vals.append(min(low_values))

        else:
            high_values.clear()
            low_values.clear()
            
            new_col_high_vals.append(new_col_high_vals[-1])
            new_col_low_vals.append(new_col_low_vals[-1])

    df['asian_range_max'] = new_col_high_vals
    df['asian_range_min'] = new_col_low_vals


    
    return df['asian_range'],df['asian_range_max'],df['asian_range_min']



def break_asian_range(candles,side):
    if side == 'high':
        candles['crossed_asian_high_up'] = crossover(candles['High'],candles['asian_range_max'],last=False).tolist()
        candles['crossed_asian_high_down'] = crossunder(candles['Close'],candles['asian_range_max'],last=False).tolist()
        candles['crossed_asian_high'] = candles['crossed_asian_high_up'].shift(1) & candles['crossed_asian_high_down']
        del candles['crossed_asian_high_up'],candles['crossed_asian_high_down']
        return candles['crossed_asian_high']

    else:
        candles['crossed_asian_low_down'] = crossunder(candles['Low'],candles['asian_range_min'],last=False).tolist()
        candles['crossed_asian_low_up'] = crossover(candles['Close'],candles['asian_range_min'],last=False).tolist()
        candles['crossed_asian_low'] = candles['crossed_asian_low_down'].shift(1) & candles['crossed_asian_low_up']
        del candles['crossed_asian_low_up'],candles['crossed_asian_low_down']
        return candles['crossed_asian_low']



def break_structure(candles,side):
    if side == 'high':
        return ((candles['Low'] > candles['Low'].shift(1)) & (candles['Low'].shift(1) < candles['Low'].shift(2)) & (candles['High'] > candles['High'].shift(1)) & (candles['High'].shift(1) < candles['High'].shift(2)))
    else:
        return ((candles['High'] < candles['High'].shift(1)) & (candles['High'].shift(1) > candles['High'].shift(2)) & (candles['Low'] < candles['Low'].shift(1)) & (candles['Low'].shift(1) > candles['Low'].shift(2)))
