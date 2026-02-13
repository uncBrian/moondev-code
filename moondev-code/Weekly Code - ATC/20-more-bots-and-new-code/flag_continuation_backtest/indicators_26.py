import pandas as pd 
import pandas_ta as ta 
from math import *  
from scipy.stats import linregress  
import numpy as np 


def trend_lines(df):
    data0 = df.copy() 
    data0['date_id'] = np.arange(len(df))+ 1

    data1 = data0.copy()
    while len(data1) > 3:
        slope, intercept, r_value, p_value, std_err =linregress(x=data1['date_id'].values.tolist(), y=data1['High'].values.tolist())
        data1 = data1.loc[data1['High'] > slope * data1['date_id']+intercept]

    top_slope, intercept, r_value, p_value, std_err = linregress(x=data1['date_id'].values.tolist(), y=data1['Close'].values.tolist())
    data0['high_trend'] = top_slope * data0['date_id'] + intercept

    data1 = data0.copy()
    while len(data1) > 3:
        slope, intercept, r_value, p_value, std_err =linregress(x=data1['date_id'].values.tolist(), y=data1['Low'].values.tolist())
        data1 = data1.loc[data1['Low'] < slope * data1['date_id']+intercept]

    bot_slope, intercept, r_value, p_value, std_err = linregress(x=data1['date_id'].values.tolist(), y=data1['Close'].values.tolist())
    data0['low_trend'] = bot_slope * data0['date_id'] + intercept

    # get the amount of times the price has toouched the trend 
    data0['touched_top'] = ((data0['Open'] < data0['high_trend']) & (data0['Close'] < data0['high_trend']) & (data0['High'] > data0['high_trend']))
    data0['touched_bot'] = ((data0['Open'] > data0['low_trend']) & (data0['Close'] > data0['low_trend']) & (data0['Low'] < data0['low_trend']))

    return data0[['high_trend', 'low_trend', 'touched_top', 'touched_bot']]

