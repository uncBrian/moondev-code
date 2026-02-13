################ BOT THAT SEARCHES FOR NEW LAUNCHES W/ OUR PARAMS ################

new_data = True # THIS ONLY RUNS FOR NEW DATA IF THIS IS TRUE - otherwise it uses last runs data
MARKET_CAP_MAX = 20000 # max market cap *ONLY APPLIES IF NEW_DATA = TRUE*
NUM_TOKENS_2SEARCH = 5000 # number of tokens to search through on solana *ONLY APPLIES IF NEW_DATA = TRUE* i found 15000 gets a lot
MIN_24HR_VOLUME = 1000 # min 24 hour volume *ONLY APPLIES IF NEW_DATA = TRUE*

MAX_SELL_PERCENTAGE = 40 # if the sell % more than MAX_SELL_PERCENTAGE sells in the last hour, drop it
MIN_TRADES_LAST_HOUR = 3 # if there are less than MIN_TRADES_LAST_HOUR trades in the last hour, drop it
MIN_UNQ_WALLETS2hr = 50 # if there are less than MIN_UNQ_WALLETS2hr unique wallets in the last 2 hours, drop it
MIN_VIEW24h = 20 # if there are less than MIN_VIEW24h views in the last 24 hours, drop it
MIN_LIQUIDITY = 200 # if there is less than MIN_LIQUIDITY liquidity, drop it

# NOTE - you need a birdeye api key to run this bot, you can get one here: https://birdeye.so/
# you need to put it in a file called dontshare.py and name it birdeye
# make a folder called data in the same directory as this file

#####################################

import pandas as pd 
# openai_key
import datetime 
import dontshare as d # this is where the birdeye api key is stored named birdeye
import requests
import time , json
import pprint
import re as reggie

def birdeye_bot():

    import requests
    import pandas as pd
    import datetime
    import time 

    # Replace with your module or variable for API key
    import dontshare as d

    base_url = "https://birdeye.so/token/"

    url = "https://public-api.birdeye.so/public/tokenlist"
    headers = {"x-chain": "solana", "X-API-KEY": d.birdeye}

    tokens = []
    offset = 0
    limit = 50
    total_tokens = 0
    num_tokens = NUM_TOKENS_2SEARCH
    mc_high = MARKET_CAP_MAX
    mc_low = 50

    # Set minimum liquidity and minimum 24-hour volume
    min_liquidity = MIN_LIQUIDITY
    min_volume_24h = MIN_24HR_VOLUME
    mins_last_trade = 59

    while total_tokens < num_tokens:
        print('looping...')
        params = {"sort_by": "v24hChangePercent", "sort_type": "desc", "offset": offset, "limit": limit}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            response_data = response.json()
            new_tokens = response_data.get('data', {}).get('tokens', [])
            tokens.extend(new_tokens)
            total_tokens += len(new_tokens)
            offset += limit
            time.sleep(1)  # Sleep to avoid hitting rate limits
        else:
            print(f"Error {response.status_code}: trying again...")
            time.sleep(15)  # Sleep longer on error before retrying
            continue  # Skip to the next pagination

        print(total_tokens)

    # Create a DataFrame from the fetched tokens
    df = pd.DataFrame(tokens)

    # Add the token URL column
    df['token_url'] = df['address'].apply(lambda x: base_url + x)

    # Drop rows with missing 'liquidity' or 'v24hUSD'
    df = df.dropna(subset=['liquidity', 'v24hUSD'])

    # Filter for minimum liquidity
    df = df[df['liquidity'] >= min_liquidity]

    # Filter for minimum 24-hour volume
    df = df[df['v24hUSD'] >= min_volume_24h]

    # Filter the DataFrame to keep only the tokens with 'mc' between mc_low and mc_high
    df = df[(df['mc'] >= mc_low) & (df['mc'] <= mc_high)]

    # Drop specified columns
    drop_columns = ['logoURI', '_id']
    for col in drop_columns:
        if col in df.columns:
            df = df.drop(columns=col)

    # Convert lastTradeUnixTime to UTC and make it tz-aware
    df['lastTradeUnixTime'] = pd.to_datetime(df['lastTradeUnixTime'], unit='s').dt.tz_localize('UTC')

    # Calculate the current time in UTC
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # Calculate the time 10 minutes ago in UTC
    ten_minutes_ago = current_time - datetime.timedelta(minutes=mins_last_trade)

    # Filter the DataFrame to keep only the rows with trades within the last 10 minutes based on the lastTradeUnixTime
    df = df[df['lastTradeUnixTime'] >= ten_minutes_ago]

    # Save the DataFrame to a local CSV file
    df.to_csv("data/filtered_pricechange_with_urls.csv", index=False)

    # Pretty-print the modified DataFrame with each piece of data in its own column
    pd.set_option('display.max_columns', None)  # Show all columns
    # print("Final DataFrame with URLs:")
    # print(df)

    return df


if new_data == True:
    # run bird eye bot in order to get the meme token data
    print('getting new data...')
    data = birdeye_bot()
    #data = pd.read_csv('filtered_pricechange_with_urls.csv')
else:
    # load the data from the csv
    data = pd.read_csv('data/filtered_pricechange_with_urls.csv')

# in the df if the v24hUSD column has a number in it, drop it from the data and make a new df + save as 'new_launces-mm-dd-hh.csv'
# THIS ONE IS CHILL IT JUST DROPS A COLUMN TO GET NEW LAUNCHES ONLY
def new_launches(data):
    # Create a new DataFrame with rows where 'v24hUSD' is NaN (empty)
    new_launches = data[data['v24hChangePercent'].isna()]
    
    # Generate a timestamp for the current date and time
    timestamp = datetime.datetime.now().strftime("%m-%d-%H")
    
    # Construct the CSV file name with the timestamp
    csv_filename = 'data/new_launches.csv'
    
    # Save the new launches DataFrame as a CSV file with the generated filename
    new_launches.to_csv(csv_filename, index=False)
    
    #print(new_launches)
    
    return new_launches

# RUN NEW LAUNCHES TO GET RID OF THINGS THAT LAUNCHED TOO LONG AGO
new_launches(data)


# Custom function to print JSON in a human-readable format
def print_pretty_json(data):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)

# Function to print JSON in a human-readable format - assuming you already have it as print_pretty_json
# Helper function to find URLs in text
def find_urls(string):
    # Regex to extract URLs
    return reggie.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)

BASE_URL = "https://public-api.birdeye.so/defi"
# API Key from your 'dontshare' file
API_KEY = d.birdeye

# UPDATED TO RMEOVE THE OTHER ONE so now we can just use this filter instead of filtering twice
def token_overview(address, MAX_SELL_PERCENTAGE, MIN_TRADES_LAST_HOUR, MIN_UNQ_WALLETS2hr, MIN_VIEW24h, MIN_LIQUIDITY):
    overview_url = f"{BASE_URL}/token_overview?address={address}"
    headers = {"X-API-KEY": API_KEY}

    response = requests.get(overview_url, headers=headers)
    result = {}

    if response.status_code == 200:
        overview_data = response.json().get('data', {})
        
        buy1h = overview_data.get('buy1h', 0)
        sell1h = overview_data.get('sell1h', 0)
        trade1h = buy1h + sell1h
        total_trades = trade1h

        # Perform buy/sell percentage calculations:
        buy_percentage = (buy1h / total_trades * 100) if total_trades else 0
        sell_percentage = (sell1h / total_trades * 100) if total_trades else 0

        # Criteria checks:
        if sell_percentage > MAX_SELL_PERCENTAGE:
            return None  # Drop the data if sell percentage is too high
        if trade1h < MIN_TRADES_LAST_HOUR:
            return None  # Drop the data if not enough trades
        if overview_data.get('uniqueWallet24h', 0) < MIN_UNQ_WALLETS2hr:
            return None  # Drop the data if not enough unique wallets
        if overview_data.get('view24h', 0) < MIN_VIEW24h:
            return None  # Drop the data if not enough views
        if overview_data.get('liquidity', 0) < MIN_LIQUIDITY:
            return None  # Drop the data if not enough liquidity

        # Add calculated data to the result dictionary:
        result.update({
            'address': address,
            'buy1h': buy1h,
            'sell1h': sell1h,
            'trade1h': trade1h,
            'buy_percentage': buy_percentage,
            'sell_percentage': sell_percentage,
            'liquidity': overview_data.get('liquidity', 0),
            # Add other necessary data from overview_data that passed the checks
        })

        # Process description links if 'extensions' is not None:
        extensions = overview_data.get('extensions', {})
        description = extensions.get('description', '') if extensions else ''
        urls = find_urls(description)
        links = [{'telegram': u} for u in urls if 't.me' in u]
        links.extend([{'twitter': u} for u in urls if 'twitter.com' in u])
        links.extend([{'website': u} for u in urls if 't.me' not in u and 'twitter.com' not in u])
        result['description'] = links

        return result

    else:
        print(f"Failed to retrieve token overview for address {address}: HTTP status code {response.status_code}")
        return None
  

# here we are using the nice_funcs token overview to get the token data for each address in the csv
# goal of trying to filter down any rug pulls, which is done.
# Load the CSV with addresses
df = pd.read_csv('data/new_launches.csv')

# Create an empty list to store individual DataFrames for concatenation
dfs_to_concat = []

# Iterate over each row in the DataFrame
for index, row in df.iterrows():
    # Calling the updated token_overview function with passing parameters
    token_data = token_overview(
        row['address'],
        MAX_SELL_PERCENTAGE=MAX_SELL_PERCENTAGE,
        MIN_TRADES_LAST_HOUR=MIN_TRADES_LAST_HOUR,
        MIN_UNQ_WALLETS2hr=MIN_UNQ_WALLETS2hr,
        MIN_VIEW24h=MIN_VIEW24h,
        MIN_LIQUIDITY=MIN_LIQUIDITY
    )

    # Check if there is data to process
    if token_data:
        # Add the address to the data
        token_data['address'] = row['address']

        # Create the URL and add it to the token_data
        token_data['url'] = f"https://dexscreener.com/solana/{token_data['address']}"
        
        # Remove priceChanges from the data as we won't be needing it
        token_data.pop('priceChangesXhrs', None)

        # Convert the token_data dictionary to a DataFrame
        temp_df = pd.DataFrame([token_data])

        # Append the DataFrame to the list for concatenation
        dfs_to_concat.append(temp_df)

# Conditional execution if there's at least one DataFrame to concatenate
if dfs_to_concat:
    # Concatenate all the DataFrames in the list
    results_df = pd.concat(dfs_to_concat, ignore_index=True)
    
    # Save the results to a CSV file
    csv_file_path = 'data/hyper-sorted-sol.csv'
    results_df.to_csv(csv_file_path, index=False)

    # Print a horizontal line for readability
    print('-' * 80)

    # Print the final DataFrame
    print(results_df)
else:
    # Print a process completion text with instructions
    print('-' * 80)
    print("After filtering, there are no tokens meeting the criteria."
          "Try changing your parameters or increasing NUM_TOKENS_2SEARCH.")