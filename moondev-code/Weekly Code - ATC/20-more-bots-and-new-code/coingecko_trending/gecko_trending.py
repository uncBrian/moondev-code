'''
this bot builds out a csv file with the trending coin gecko coins
and it loops every hour to get new data

full video tutorial here: https://www.youtube.com/watch?v=VYx2qhOZ2-k 
'''
import requests,json, time 
import pandas as pd 
import datetime 
# hide warnings
import warnings
warnings.filterwarnings("ignore")

my_exchanges = ['KuCoin', 'Uniswap (v2)','Coinbase Exchange', 'Sushiswap', 'Uniswap (v3)', 'Phemex', 'Bybit','1inch Liquidity Protocol','Sushiswap (Polygon POS)', 'PancakeSwap (v2)', 'Kraken', 'Bancor (V2)', 'Gemini']

def get_market_cap(symbol):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}"
    response = requests.get(url)
    data = response.json()
    #print(data)
    market_cap = data["market_data"]["market_cap"]["usd"]
    return market_cap

def categoies():
    # get all the categories from coingecko api
    url = "https://api.coingecko.com/api/v3/coins/categories/list"
    response = requests.get(url)
    data = response.json()
    #print(data)

    # put into a df
    df = pd.DataFrame(data)
    print(df)


    df.to_csv("feb23/categories.csv", index=False)


def nfts():

    # get the list of nfts
    url = "https://api.coingecko.com/api/v3/nfts/list?asset_platform_id=ethereum&order=h24_volume_native_desc"

    response = requests.get(url)
    data = response.json()
    #print(data)

    # put into a df
    df = pd.DataFrame(data)
    print(df)


    nftdatadf = pd.DataFrame()
    # for each id, get the current data using /nfts/{id}
    # only do it for the first 10
    for id in df["id"][:10]:
        url = f"https://api.coingecko.com/api/v3/nfts/{id}"
        response = requests.get(url)
        nftdata = response.json()
        #print(data)
        # put into a df
        df_nft_data = pd.DataFrame(nftdata)
        #print(nftdata)
        # append to the nftdatadf
        nftdatadf = nftdatadf.append(df_nft_data, ignore_index=True)
        time.sleep(1)
    
    # save nftdatadf to csv

    # take the nft data and only save every 3rd line
    
    print(nftdatadf)

    nftdata = nftdatadf.to_csv("feb23/nftdata.csv", index=False)

    df.to_csv("feb23/nfts.csv", index=False)


# make a function that reads in my csv file and makes a list of all the unique exchanges in that file and prints it out
def all_exchanges():
    df = pd.read_csv("feb23/gecko_trending.csv")
    # there are a bunch of exchange columns, so i need to loop through them and make a list of all the unique exchanges
    exchanges = []
    for col in df.columns:
        if "exchange" in col:
            exchanges.append(col)
            # for those exchange columns, loop through and get the unique exahange names
            
    unique_exchanges = []
    for exchange in exchanges:
        for item in df[exchange]:
            if item not in unique_exchanges:
                unique_exchanges.append(item)
                
                
    return unique_exchanges

# get the exchanges for each id
def get_exchange(symbol):
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/tickers"
    response = requests.get(url)
    data = response.json()
    #print(data)
    # loop through and get all exchanges
    exchanges = []
    for ticker in data["tickers"]:
        exchanges.append(ticker["market"]["name"])
        # put the exchanges into a df
        df = pd.DataFrame(exchanges)
        df.columns = ["exchange"]

    return exchanges

#print(get_exchange('deepbrain-chain'))

    
# print(drop_otherexchanges())
# time.sleep(7867)
# get the trending symbol, not coin name
def get_trending():
    url = "https://api.coingecko.com/api/v3/search/trending"
    response = requests.get(url)
    data = response.json()
    #print(data)
    trending = []
    #df = pd.DataFrame()
    # read in "feb23/gecko_trending.csv"
    df = pd.read_csv("feb23/gecko_trending.csv")
    temp_df = pd.DataFrame()
    for coin in data["coins"]:
        
        coinid = coin["item"]["id"]
        print(coinid)
        trending.append(coinid)
        print(trending)
   
        # get the market cap
        market_cap = get_market_cap(coinid)
        # get the date
        now = datetime.datetime.now().date()
        # get the rank
        rank = coin["item"]["market_cap_rank"]
        # make a df - date, symbol, rank, market cap, then all of the exhanges like this exchange, exchange, exchange etc.
        # use a temp df to return the data so i can later append it to the main df

        temp_df["date"] = [now]
        temp_df["symbol"] = [coinid]
        temp_df["rank"] = [rank]
        temp_df["market_cap"] = [market_cap]

        # get link to coingecko listing
        temp_df["link"] = [f"https://www.coingecko.com/en/coins/{coinid}"]

        # print(coinid)
        # print(type(coinid))
        # time.sleep(786)

        time.sleep(3)

        
        # get all the exchanges and put them in their own columns on the temp df as exchange1, exchange2, exchange3 etc.
        exchanges = get_exchange(coinid)
        # # add the exchanges to the temp df but only if they appear in my_exchanges
        # for i in range(len(exchanges)):
        #     temp_df[f"exchange{i}"] = [exchanges[i]]

        '''
        make the columns the exchange name from my_exchanges
        and put a yes or no in the column if the exchange is in the exchanges list
        '''
        for exchange in my_exchanges:
            if exchange in exchanges:
                temp_df[exchange] = ["yes"]
            else:
                temp_df[exchange] = ["no"]




        #print(exchanges)
        time.sleep(3)

        # append the temp df to the main df
        df = df.append(temp_df)

        #save as csv in this folder with no index
        df.to_csv("feb23/gecko_trending.csv", index=False)

    print(df)  
    return df
try:
    get_trending()
except:
    print("error - probably internet, sleeping for 10 seconds")
    time.sleep(10)
import schedule
schedule.every(3600).seconds.do(get_trending)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except:
        print("error - probably internet, sleeping for 10 seconds")
        time.sleep(10)