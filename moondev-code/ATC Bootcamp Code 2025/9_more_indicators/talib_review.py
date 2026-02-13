'''
10 new indicators using TA-Lib
TA-Lib - a package that give a bunch of techinical analysis indictors
talib docs - https://ta-lib.github/ta-lib-python/doc_index.html 

you can use these indicators for backtesting and for bots

'''
import talib as ta 
import pandas as pd 

# GET DATA
df = pd.read_csv('/Users/md/Desktop/dev/hyper liquid bots/storage_SOL-USD6h20.csv')


# SMA 
# df['sma'] = ta.SMA(df['close'], timeperiod=20)

# RSI
# df['rsi'] = ta.RSI(df['close'], timeperiod=14)

# EMA 
#df['ema'] = ta.EMA(df['close'], timeperiod=10)

# bollinger bands 
#df['boll_upper'], df['boll_mid'], df['boll_lower'] = ta.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)

# MACD
#df['macd_line'], df['macd_signal'], df['macd_hist'] = ta.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)

# ATR - average true range
#df['atr_14'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=14)

# stochastic oscillator
#df['stoch_k'], df['stoch_d'] = ta.STOCH(df['high'], df['low'], df['close'], fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)

# commodity channel index
#df['cci_20'] = ta.CCI(df['high'], df['low'], df['close'], timeperiod=20)

# parabolic sar
#df['sar'] = ta.SAR(df['high'], df['low'], acceleration=0.02, maximum=0.2)

# obv - on balance volume
# df['obv'] = ta.OBV(df['close'], df['volume'])

print(df)