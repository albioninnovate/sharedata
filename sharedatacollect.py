# coding: utf-8
#!/usr/bin/env python3

import time
from pprint import pprint

import pandas as pd
from alpha_vantage.timeseries import TimeSeries

"""
This project uses RomelTorres/alpha_vantage under the MIT licence (https://github.com/RomelTorres/alpha_vantage) 
It requires a free API, that can be requested here:  http://www.alphavantage.co/

Documentation for  alpha_vantage:  https://alpha-vantage.readthedocs.io/en/latest/

Python module to get stock data from the Alpha Vantage API Alpha Vantage http://www.alphavantage.co/ is a free 
JSON APIs for stock market data, plus a comprehensive set of technical indicators. T

the specific module use by this project is well documented internally:
https://github.com/RomelTorres/alpha_vantage/blob/develop/alpha_vantage/timeseries.py is

Note: Rather than calling the entire series of prices, the more efficient approach would be to fetch single values, using  
def get_batch_stock_quotes(self, symbols): or def get_quote_endpoint(self, symbol): functions. hwr, the functionally 
does not currently work for non-US shares.  So fetching a larger set and trimming to the most recent values is what is done below.  

# Set some initial and trial values 
"""

""" 
The structure of the project is:
1) data read from a CSV file of existing share data produced is places in a dataframe 
2) a list of shares and earnings data is read into a list and dictionary of EPS and Div values
3) API calls are made iterating over the list of shares, creating a new dataframe
4) data from the EPS and Div dictionary are then added to the new dataframe, some values are calculated
5) the new dataframe is then appended to the the existing data frame and duplicates are removed
6) the combined dataframe is writen to disk as a CSV file    
"""

# Alpha Vantage;  https://www.alphavantage.co/support/#api-key
# Alphavantage_API_key = 'YOUR_API_KEY'
Alphavantage_API_key = '21GBFSMHLICNID9Y'

# The existing data to which the retrieved data is added.  This is the main output file
datafile = 'share_data.csv'  # where the existing data is kept

# column order of the data file, used to re order data in the retrieved and existing data
datafile_col = ['symbol', 'high', 'low', 'open', 'close', 'volume', 'div', 'eps', 'pe', 'yld']

# where Share Symbol, eps and div data is kept. Updated for each share after the company reports. (ca once per quarter)
# earningsfile = 'berkshire.csv'
earningsfile = 'epsdiv.csv'

# time (s) to wait between API calls a multiple of this is use on error to allow time for server to reset
pause_call = 15


# # Define functions
def getnewdata(symbol, days=1, apikey=Alphavantage_API_key):
    print('making call :' , symbol)
    ts = TimeSeries(key=apikey, output_format='pandas')
    df, meta_df = ts.get_daily(symbol=symbol, outputsize='compact')
    # df, meta_df = ts.get_batch_stock_quotes(symbols=shrsymbol)  # only works with US stocks
    data = df.tail(days)
    return data


"""
Keyword Arguments to AV TimeSeries API call:
    days: use in dataframe tail function, the number of data points 
    symbol:  the symbol for the equity we want to get its data
    outputsize:  The size of the call, supported values are 'compact' and 'full; the first returns the last 100 points
 in the data series, and 'full' returns the full-length intraday times series, commonly above 1MB (default 'compact')
 
 Ideally the Batch Stock quote call or get quote would be used as it retrieved fewer values, But those only work for US shares 

"""


def getexistingdata(datafile):
    with open(datafile, 'r') as f:
        data_existing = pd.read_csv(f, index_col='date')  # set index to date as Alpha Vantage uses date as index
        return data_existing


if __name__ == '__main__':
    # Retrieve the existing data stored on disk in preparation for merging with the new data.
    print('...Retrieving existing data stored on disk in preparation for merging with the new data.')
    data_existing = getexistingdata(datafile)

    # put the columns in a particular order
    data_existing = data_existing[datafile_col]

    pprint(data_existing)

    # Read the symbols for each share to be used in the call to AV
    print('...reading share Symbols to retrieve from file', earningsfile)
    data = pd.read_csv(earningsfile, index_col=False)  # create a dataframe from the  csv file
    # Make sure there are only unique values in 'Symbol' column, reduces unnecessary API calls
    symbols = data['Symbol'].drop_duplicates().values.tolist()

    print('read ', len(symbols), ' unique share symbols')
    print('')

    # Create a dict of the Symbols and eps, div values to be put in the new data frame with values retrieved from AV
    # structure of file ;  Symbol,eps,div
    print('...reading share, eps, and div values for the Symbols from file', earningsfile)
    epsdiv = pd.read_csv(earningsfile, header=0, index_col=0).to_dict()
    # TODO could the csv file be read in once to a dataframe an exported to the Symbol list and eps/div dict from the single DF

    cnt = 1  # for a counter to track progress of the retrieval process.

    print('retrieving  data')
    for s in symbols:  # iterate over the Symbols retrieved from earnings file
        print(cnt, ' of', len(symbols))
        cnt = cnt + 1

        try:
            d = getnewdata(s)  # retrieves dataframe of date and prices
            d['eps'] = epsdiv['eps'][s]  # create a column 'eps' with the value from the dict epsdiv
            d['pe'] = d['4. close'] / epsdiv['eps'][s]  # calc the PE and add to dataframe
            d['div'] = epsdiv['div'][s]
            d['yld'] = epsdiv['div'][s] / d['4. close'] * 100  # calc the yld and add to dataframe
            d['symbol'] = str(s)

            d.rename(
                columns={'1. open': 'open', '2. high': 'high', '3. low': 'low', '4. close': 'close', '5. volume': 'volume'},
                inplace=True)
            # put the columns in a particular order
            d = d[datafile_col]



            pprint(d)  # take a look at the data
            print('')

            # put the columns in a particular order prior to appending
            data_existing = data_existing[datafile_col]

            # data_existing = pd.concat([data_existing, d])
            data_existing = data_existing.append(d)
            # print('data_existing.tail()',data_existing.tail())
            # print('')

            time.sleep(pause_call)  # Time between API calls, the AV server limits the number of calls in a given time

        except Exception as E:
            cnt_dwn = pause_call * 3  # Pause the API calls if the rate was too high and tossed an error
            print('An error', E, ' was encountered while retrieving data ', s)
            print('retrieval will pause for ', cnt_dwn, 'seconds')
            while cnt_dwn > 0:
                print(cnt_dwn)
                time.sleep(1)
                cnt_dwn = cnt_dwn - 1

    data_existing.drop_duplicates(['symbol', 'high', 'low', 'open', 'close', 'volume'],
                                  keep='last',
                                  inplace=True)  # remove duplicate values, keeping the later. This allows earnings data

    # round certain values to given precision
    d = d.round({'high': 2, 'low': 2, 'open': 2, 'close': 2, 'pe': 2, 'yld': 4})

    # to be updated in later runs
    print('data_existing after drop duplicates')
    # print(data_existing.tail(len(symbols)))
    pprint(data_existing)
    print('')

    print('Writing all data to disk as :', datafile)
    with open(datafile, 'w') as f:
        data_existing.to_csv(f, header=True)
