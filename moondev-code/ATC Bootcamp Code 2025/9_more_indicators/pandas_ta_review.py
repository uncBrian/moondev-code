'''
Pandas_TA review
documentation
https://github.com/twopirllc/pandas-ta

'''
import pandas_ta as ta 
import pandas as pd 

print('hi')

df = pd.read_csv('/Users/md/Desktop/dev/hyper liquid bots/storage_MANA-USD1h30.csv')

# SMA 
df['sma_10'] = ta.sma(df['close'], length=10)

# EMA
df['ema_10'] = ta.sma(df['close'], length=10)

# RSI
df['rsi_14'] = ta.rsi(df['close'], length=14)

# macd 
#df[['macd_line', 'macd_signal', 'macd_hist']] = ta.macd(df['close'], fast=12, slow=26, signal=9)

# stochastic oscillator
df[['stoch_k', 'stoch_d']] = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)

print(df)

# GET ALL OF THE INDICATORS HERE
help(df.ta)

# RBI --> Researching, Backtesting