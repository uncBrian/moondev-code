'''
this is the QQE mod indicator translated into python 
the QQE mod is an indicator from trading view
i have made a bunch of videos on my youtube @moondev going over
how to transalte the QQE mod from pinescript (tradingview language) to python
but never finished on youtube. so this is exclusive for you
as always, please test yourself before running live. 
'''

import ccxt
import json 
import pandas as pd 
import numpy as np
import dontshareconfig as ds 
from datetime import date, datetime, timezone, tzinfo
import time, schedule
#from ta.volatility import *
from ta.momentum import rsi
from ta.trend import EMAIndicator , SMAIndicator
#from ta.volume import *
import math 
import nice_funcs as n 
import talib 

phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': '', 
    'secret': ''})

symbol = 'uBTCUSD'

# strategy("TradeIQ_1", overlay=true, initial_capital=1000000, 
#   default_qty_value = 100, default_qty_type= strategy.percent_of_equity)
initial_capital = 1000000
pos_size = 1000000

# RSI_Period = input(6, title='RSI Length')
RSI_Period = 6
# SF = input(5, title='RSI Smoothing')
# QQE = input(3, title='Fast QQE Factor')
# ThreshHold = input(3, title="Thresh-hold")

SF = 5 
QQE = 3
ThresHold = 3 

# Wilders_Period = RSI_Period * 2 - 1
# use close data 
Wilders_Period = RSI_Period * 2 - 1
 
# pulled in some data 
df = n.df_sma(symbol, '15m', 500, 20)
#print(df)

# src = input(close, title="RSI Source")
src = df[['timestamp', 'close']]
print(src)


# Get RSI
#Rsi = ta.rsi(src, RSI_Period) # TODO - GET THE VALUE NEEDED
#rsi = rsi(src['close'], RSI_Period)
src['Rsi'] = rsi(src['close'], RSI_Period)
Rsi = src.iloc[-1]['Rsi']
print(f'this is the last RSI {Rsi}')

#RsiMa = ta.ema(Rsi, SF) # TODO - GET THE VALUE NEEDED
ema = EMAIndicator(src['close'], SF)
src['RsiMa'] = ema.ema_indicator()
RsiMa_current = src.iloc[-1]['RsiMa']
#rsima current = rsi_index 
RsiMa_1back = src.iloc[-2]['RsiMa']
src['RsiMa_1back'] = src['RsiMa'].shift(1)
print(f'this is the last RsiMa {RsiMa_current}')
#print(src)


#AtrRsi = abs(RsiMa[1]- RsiMa) # TODO# get this in the df
AtrRsi = abs(RsiMa_1back - RsiMa_current )
print(f'this is the AtrRsi {AtrRsi}')
src['AtrRsi'] = abs((src['RsiMa_1back']) - (src['RsiMa']))

#MaAtrRsi = ta.ema(AtrRsi, Wilders_Period) # TODO
MaAtrRsi = EMAIndicator(src['AtrRsi'], Wilders_Period)
src['MaAtrRsi'] = MaAtrRsi.ema_indicator()

#dar = ta.ema(MaAtrRsi, Wilders_Period) * QQE

dar = EMAIndicator(src['MaAtrRsi'], Wilders_Period) 
src['dar'] = dar.ema_indicator() * QQE

longband = 0 
src['longband'] = 0
shortband = 0 
src['shortband'] = 0
trend = 0 

dar = src.iloc[-1]['dar']
src['DeltaFastAtrRsi'] = src['dar']
DeltaFastAtrRsi = dar

src['RSIndex'] = src['RsiMa']

# newshortband = RSIndex + DeltaFastAtrRsi
# newlongband = RSIndex - DeltaFastAtrRsi
src['newshortband'] = (src['RSIndex']) + (src['DeltaFastAtrRsi'])
src['newlongband'] = (src['RSIndex']) - (src['DeltaFastAtrRsi'])
newlongband_2back = src.iloc[-2]['newlongband']
src['newlongband_2back'] = src['newlongband'].shift(2)
newlongband_curr = src.iloc[-1]['newlongband']
newshortband_2back = src.iloc[-2]['newshortband']
src['newshortband_2back'] = src['newshortband'].shift(2)
newshortband_curr = src.iloc[-1]['newshortband']
#print(f'this is newshortband {newshortband} this is new long band {newlongband}')


RsiMa_1back 
RSIndex = src.iloc[-1]['RSIndex']


## SETTING UP LONG BAND DF 
src.loc[src['longband'] > src['newlongband_2back'], 'max'] = src['longband']
src.loc[src['longband'] < src['newlongband_2back'], 'max'] = src['newlongband_2back']

src.loc[((src['RsiMa_1back'] > src['longband'] & (src['RSIndex'] > src['longband']) ) ), 'longbandx'] =  src['max']

src.loc[src['longbandx'] == np.NaN, 'longband'] = src['longband']
src.loc[src['longbandx'] > 0, 'longband'] = src['longbandx']

src['longband_1back'] = src['longband'].shift(1)
src['longband_2back'] = src['longband'].shift(2)

print(src)

if (RsiMa_1back > longband) and (RSIndex > longband):
    longband = max(longband, newlongband_2back)
else:
    longband = newlongband_curr


## SETTING UP SHORT BAND DF 
src.loc[src['shortband'] > src['newshortband_2back'], 'max'] = src['shortband']
src.loc[src['shortband'] < src['newshortband_2back'], 'max'] = src['newshortband_2back']

src.loc[((src['RsiMa_1back'] > src['shortband'] & (src['RSIndex'] > src['shortband']) ) ), 'shortbandx'] =  src['max']

src.loc[src['shortbandx'] == np.NaN, 'shortband'] = src['shortband'] # BUG
src.loc[src['shortbandx'] > 0, 'shortband'] = src['shortbandx']

src['shortband_1back'] = src['shortband'].shift(1)
src['shortband_2back'] = src['shortband'].shift(2)    

if (RsiMa_1back < shortband) and (RSIndex < shortband):
    shortband = min(shortband, newshortband_curr)
else:
    shortband = newshortband_curr

src['prev_RSIndex'] = src['RSIndex'].shift(1)
src.dropna(inplace=True)

def find_cross(input1, prev_input1, input2):
    if input1 > input2 and prev_input1 < input2:
        return True #crossover
    elif input1 < input2 and prev_input1 > input2:
        return True # crossunder

    return False 

# getting cross on long band  cross_1 = ta.cross(longband[1], RSIndex)
src['cross_1'] = np.vectorize(find_cross)(src['longband_1back'], src['longband_2back'], src['RSIndex'])
cross_1 = src.iloc[-1]['cross_1']

# getting cross on shortbands 
# - trend := ta.cross(RSIndex, shortband[1]) ? 1 : cross_1 ? -1 : nz(trend[1], 1)
src['cross_s'] = np.vectorize(find_cross)(src['RSIndex'], src['prev_RSIndex'], src['shortband_1back'])
cross_s = src.iloc[-1]['cross_s']

print(src.tail(50))

print(f'cross_1 == {cross_1} shortband cross {cross_s}')

# THINK ABOUT THIS MORE TODO 
if cross_s == True: #curr_rsiindex vs shortband 1bakc 
    trend = 1 # true
elif cross_1 == True:
    trend = -1 
else:
    trend = 1 

# src.loc[((src['RsiMa_1back'] > src['shortband'] & (src['RSIndex'] > src['shortband']) ) ), 'shortbandx'] =  src['max']

# src.loc[src['shortbandx'] == np.NaN, 'shortband'] = src['shortband']

src.loc[src['cross_s'] == True, 'trend']= 1
src.loc[src['cross_1'] == True, 'trend']= -1
src.loc[(src['cross_1'] == False) & (src['cross_s']==False), 'trend'] = 1

# FastAtrRsiTL = trend == 1 ? longband : shortband
if trend == 1:
    FastAtrRsiTL = longband 
else:
    FastAtrRsiTL = shortband 

# do the same as above, but in pandas
src.loc[src['trend']==1, 'FastAtrRsiTL'] = src['longband']
src.loc[src['trend'] != 1, 'FastAtrRsiTL'] = src['shortband']
        
length= 50 
mult = 0.35 

# basis = ta.sma(FastAtrRsiTL - 50, length)
# dar = EMAIndicator(src['MaAtrRsi'], Wilders_Period) 
# src['dar'] = dar.ema_indicator() * QQE

#sma = SMAIndicator(FastAtrRsiTL-50, length)
sma = SMAIndicator(src['FastAtrRsiTL']-50, length)
src['basis'] = sma.sma_indicator()


#################### STANDARD DEVIATION
# standard deviation is the variance from the mean, usually 3 STD 1, 2, 3..
# 66% should lay within 1 std of mean, then like 20% within 2, then the 3 is the last lil
#####################
######################

src['dev'] = src['close'].std()

src['upper'] = src['basis'] + src['dev']
src['lower'] = src['basis'] - src['dev']

#if src['RsiMa'] - 50 > src['upper']:
src.loc[(src['RsiMa'] - 50) > src['upper'], 'color']= 'Blue'
src.loc[(src['RsiMa'] - 50) < src['lower'], 'color']= 'Red'
src.loc[((src['RsiMa'] - 50) > src['lower']) & ((src['RsiMa'] - 50) < src['upper']), 'color']= 'Gray'

QQEzlong = 0
src['QQEzlong'] = 0 
src.loc[src['QQEzlong'] == np.NaN, 'QQEzlong'] = 0
if QQEzlong == np.NaN:
    QQEzlong = 0

QQEzshort = 0
src['QQEzshort'] = 0 
src.loc[src['QQEzshort'] == np.NaN, 'QQEzshort'] = 0
if QQEzshort == np.NaN:
    QQEzshort = 0

src.loc[src['RSIndex'] >= 50, 'QQEzlong'] = src['QQEzlong'] + 1
src.loc[src['RSIndex'] < 50, 'QQEzlong'] = 0

src.loc[src['RSIndex'] < 50, 'QQEzshort'] = src['QQEzshort'] + 1
src.loc[src['RSIndex'] < 50, 'QQEzshort'] = 0

print(src['dev'].tail(100))

#### PART 2

RSI_Period2 = 6
SF2 = 5 
QQE2 = 1.61
ThresHold2 = 3 


# use close data 
Wilders_Period2 = RSI_Period * 2 - 1
 
df2 = n.df_sma(symbol, '15m', 500, 20)
#print(df)

src2 = df2[['timestamp', 'close']]

# Get RSI

src2['Rsi2'] = rsi(src2['close'], RSI_Period2)

Rsi2 = src2.iloc[-1]['Rsi2'] # BUG HERE
print(f'this is the last RSI {Rsi2}')


#RsiMa = ta.ema(Rsi, SF) # TODO - GET THE VALUE NEEDED
ema2 = EMAIndicator(src['close'], SF)
src2['RsiMa2'] = ema2.ema_indicator()
RsiMa_current2 = src2.iloc[-1]['RsiMa2']
#rsima current = rsi_index 
RsiMa_1back2 = src2.iloc[-2]['RsiMa2']
src2['RsiMa_1back2'] = src2['RsiMa2'].shift(1)
print(f'this is the last RsiMa {RsiMa_current2}')
#print(src)


#AtrRsi = abs(RsiMa[1]- RsiMa) # TODO# get this in the df
AtrRsi2 = abs(RsiMa_1back2 - RsiMa_current2 )
print(f'this is the AtrRsi {AtrRsi2}')
src2['AtrRsi2'] = abs((src2['RsiMa_1back2']) - (src2['RsiMa2']))

#MaAtrRsi = ta.ema(AtrRsi, Wilders_Period) # TODO
MaAtrRsi2 = EMAIndicator(src2['AtrRsi2'], Wilders_Period2)
src2['MaAtrRsi2'] = MaAtrRsi2.ema_indicator()

#dar = ta.ema(MaAtrRsi, Wilders_Period) * QQE

dar2 = EMAIndicator(src2['MaAtrRsi2'], Wilders_Period2) 
src2['dar2'] = dar2.ema_indicator() * QQE2

longband2 = 0 
src2['longband2'] = 0
shortband2 = 0 
src2['shortband2'] = 0
trend2 = 0 
src2['trend2'] = 0

dar2 = src2.iloc[-1]['dar2']

src2['DeltaFastAtrRsi2'] = src2['dar2']
DeltaFastAtrRsi2 = dar2

src2['RSIndex2'] = src2['RsiMa2']

# newshortband = RSIndex + DeltaFastAtrRsi
# newlongband = RSIndex - DeltaFastAtrRsi
src2['newshortband2'] = (src2['RSIndex2']) + (src2['DeltaFastAtrRsi2'])
src2['newlongband2'] = (src2['RSIndex2']) - (src2['DeltaFastAtrRsi2'])

newlongband_2back2 = src2.iloc[-2]['newlongband2']
src2['newlongband_2back2'] = src2['newlongband2'].shift(2)
newlongband_curr2 = src2.iloc[-1]['newlongband2']
newshortband_2back2 = src2.iloc[-2]['newshortband2']
src2['newshortband_2back2'] = src2['newshortband2'].shift(2)
newshortband_curr2 = src2.iloc[-1]['newshortband2']
#print(f'this is newshortband {newshortband} this is new long band {newlongband}')


RsiMa_1back2 
RSIndex2 = src2.iloc[-1]['RSIndex2']


## SETTING UP LONG BAND DF 
src2.loc[src2['longband2'] > src2['newlongband_2back2'], 'max2'] = src2['longband2']
src2.loc[src2['longband2'] < src2['newlongband_2back2'], 'max2'] = src2['newlongband_2back2']

src2.loc[((src2['RsiMa_1back2'] > src2['longband2'] & (src2['RSIndex2'] > src2['longband2']) ) ), 'longbandx2'] =  src2['max2']

src2.loc[src2['longbandx2'] == np.NaN, 'longband2'] = src2['longband2']
src2.loc[src2['longbandx2'] > 0, 'longband2'] = src2['longbandx2']

src2['longband_1back2'] = src2['longband2'].shift(1)
src2['longband_2back2'] = src2['longband2'].shift(2)



if (RsiMa_1back2 > longband2) and (RSIndex2 > longband2):
    longband2 = max(longband2, newlongband_2back2)
else:
    longband2 = newlongband_curr2


## SETTING UP SHORT BAND DF 
src2.loc[src2['shortband2'] > src2['newshortband_2back2'], 'max2'] = src2['shortband2']
src2.loc[src2['shortband2'] < src2['newshortband_2back2'], 'max2'] = src2['newshortband_2back2']

src2.loc[((src2['RsiMa_1back2'] > src2['shortband2'] & (src2['RSIndex2'] > src2['shortband2']) ) ), 'shortbandx2'] =  src2['max2']

src2.loc[src2['shortbandx2'] == np.NaN, 'shortband2'] = src2['shortband2'] # BUG
src2.loc[src2['shortbandx2'] > 0, 'shortband2'] = src2['shortbandx2']

src2['shortband_1back2'] = src2['shortband2'].shift(1)
src2['shortband_2back2'] = src2['shortband2'].shift(2)    

if (RsiMa_1back2 < shortband2) and (RSIndex2 < shortband2):
    shortband2 = min(shortband2, newshortband_curr2)
else:
    shortband2 = newshortband_curr2

src2['prev_RSIndex2'] = src2['RSIndex2'].shift(1)
src2.dropna(inplace=True)


def find_cross2(input12, prev_input12, input22):
    if input12 > input22 and prev_input12 < input22:
        return True #crossover
    elif input12 < input22 and prev_input12 > input22:
        return True # crossunder

    return False 


# cross_1 = ta.cross(longband[1], RSIndex)
    # long band_2back crossing RSIindex current
    # input1 = longband_1back, prev_input1= longband_2back, input2= RSIndex curr

# getting cross on long band  cross_1 = ta.cross(longband[1], RSIndex)
src2['cross_12'] = np.vectorize(find_cross2)(src2['longband_1back2'], src2['longband_2back2'], src2['RSIndex2'])
cross_12 = src2.iloc[-1]['cross_12']


# getting cross on shortbands 
# - trend := ta.cross(RSIndex, shortband[1]) ? 1 : cross_1 ? -1 : nz(trend[1], 1)
src2['cross_s2'] = np.vectorize(find_cross2)(src2['RSIndex2'], src2['prev_RSIndex2'], src2['shortband_1back2'])
cross_s2 = src2.iloc[-1]['cross_s2']


print(f'cross_12 == {cross_12} shortband2 cross {cross_s2}')

# THINK ABOUT THIS MORE TODO 
if cross_s2 == True: #curr_rsiindex vs shortband 1bakc 
    trend2 = 1 # true
elif cross_12 == True:
    trend2 = -1 
else:
    trend2 = 1 


src2.loc[src2['cross_s2'] == True, 'trend2']= 1
src2.loc[src2['cross_12'] == True, 'trend2']= -1
src2.loc[(src2['cross_12'] == False) & (src2['cross_s2']==False), 'trend2'] = 1


# FastAtrRsiTL = trend == 1 ? longband : shortband
if trend2 == 1:
    FastAtrRsiTL2 = longband2
else:
    FastAtrRsiTL2= shortband2 

# do the same as above, but in pandas
src2.loc[src2['trend2']==1, 'FastAtrRsiTL2'] = src2['longband2']
src2.loc[src2['trend2'] != 1, 'FastAtrRsiTL2'] = src2['shortband2']
        
length2= 50 
mult2 = 0.35 

#sma = SMAIndicator(FastAtrRsiTL-50, length)
sma2 = SMAIndicator(src2['FastAtrRsiTL2']-50, length2)
src2['basis2'] = sma2.sma_indicator()


#IMPLEMENTING STANDARD DEVIATION
src2['dev2'] = src2['close'].std()

src2['upper2'] = src2['basis2'] + src2['dev2']
src2['lower2'] = src2['basis2'] - src2['dev2']

#if src['RsiMa'] - 50 > src['upper']:
src2.loc[(src2['RsiMa2'] - 50) > src2['upper2'], 'color2']= 'Blue2'
src2.loc[(src2['RsiMa2'] - 50) < src2['lower2'], 'color2']= 'Red2'
src2.loc[((src2['RsiMa2'] - 50) > src2['lower2']) & ((src2['RsiMa2'] - 50) < src2['upper2']), 'color2']= 'Gray2'


QQEzlong2 = 0
src2['QQEzlong2'] = 0 
src2.loc[src2['QQEzlong2'] == np.NaN, 'QQEzlong2'] = 0
if QQEzlong2 == np.NaN:
    QQEzlong2 = 0

QQEzshort2 = 0
src2['QQEzshort2'] = 0 
src2.loc[src2['QQEzshort2'] == np.NaN, 'QQEzshort2'] = 0
if QQEzshort2 == np.NaN:
    QQEzshort2 = 0

src2.loc[src2['RSIndex2'] >= 50, 'QQEzlong2'] = src2['QQEzlong2'] + 1
src2.loc[src2['RSIndex2'] < 50, 'QQEzlong2'] = 0

src2.loc[src2['RSIndex2'] < 50, 'QQEzshort2'] = src2['QQEzshort2'] + 1
src2.loc[src2['RSIndex2'] < 50, 'QQEzshort2'] = 0


# silver bars
src2.loc[(src2['RSIndex2']-50) > ThresHold2, 'color'] = 'silver'
src2.loc[(src2['RsiMa2']-50) < 0 - ThresHold2, 'color'] = 'silver'
# else the color is na
src2.loc[(src2['RSIndex2']-50) < ThresHold2, 'color'] = 'na'
src2.loc[(src2['RsiMa2']-50) > 0 - ThresHold2, 'color'] = 'na'


# NOTE: the below does calculations based on both dataframes(src1, src2)
    # but im adding only to the src2
# Green barr1
src2.loc[(src2['RsiMa2'] - 50) > ThresHold2, 'greenbar1'] = True
src2.loc[(src2['RsiMa2'] - 50) < ThresHold2, 'greenbar1'] = False

# Green barr2
src2.loc[(src['RsiMa'] - 50) > src['upper'], 'greenbar2'] = True
src2.loc[(src['RsiMa'] - 50) < src['upper'], 'greenbar2'] = False

# Red Bar 1
src2.loc[(src2['RsiMa2'] - 50) < 0- ThresHold2, 'redbar1'] = True
src2.loc[(src2['RsiMa2'] - 50) > 0- ThresHold2, 'redbar1'] = False

# Red Bar 2
src2.loc[(src['RsiMa'] - 50) <  src['lower'], 'redbar2'] = True
src2.loc[(src['RsiMa'] - 50) >  src['lower'], 'redbar2'] = True

print(src)
print(src2)
# time.sleep(673)