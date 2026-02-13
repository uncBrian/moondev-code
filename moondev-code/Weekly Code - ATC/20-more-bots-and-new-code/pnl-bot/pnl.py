import ccxt,config,datetime,schedule,time
from pytz import timezone


'''
create 'config.py' to store phemex_key and phemex_secret variables  
'''

#connect to the phemex exchange
phemex = ccxt.phemex({
    'enableRateLimit': True, 
    'apiKey': config.phemex_key,
    'secret': config.phemex_secret
})


#config settings for bot
symbol = 'ETHUSD'
tz = 'EST' #your timezone. Used to only fetch trades from your midnight of the current day



def get_pnl():
    start_of_day = datetime.datetime.combine(datetime.datetime.now().date(),datetime.datetime.min.time(),timezone(tz)) #get midnight time of your timezone
    start_of_day_ms = int(start_of_day.timestamp()*1000) #convert datetime object to ms


    #get all trades for a symbol on your account

    trades = phemex.fetch_closed_orders(symbol,start_of_day_ms)

    #loop through trades
    pnl = 0
    for trade in trades:
        pnl += float(trade['info']['closedPnlEv'])/1000


    balance = phemex.fetch_balance({'type':'swap', 'code':'USD'})['USD']['total'] #get your current total balance

    percent_pnl = (balance - (balance - pnl))/(balance - pnl) #calculate the percentage change from before the trades to now (percent pnl)


    pnl = f'${pnl}' if pnl >= 0 else f'-${abs(pnl)}'
    percent_pnl = f'{round(percent_pnl,4)}%'
    with open('pnl.txt','a') as file:
        file.write(f'{datetime.datetime.today().date()},  pnl: {pnl},  percent_pnl: {percent_pnl}\n')


#run the pnl function immediately
get_pnl()

#run the bot once per day
schedule.every(1).days.do(get_pnl)

while True:
    try:
        schedule.run_pending()
    except:
        print('+++++ ERROR RUNNING BOT, SLEEPING FOR 30 SECONDS BEFORE RETRY')
        time.sleep(30)