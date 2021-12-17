from typing import List
import time
from binance.client import Client
from binance.enums import *
from dotenv import dotenv_values
from binance_time_utils import convertToStartTime, convertToInterval
import pandas as pd
import logging
from algo_utils import MACD, EMA
from utils import symbols_to_table

class BinanceClient:
    client = None
    env = None
    openBuyOrder = None
    totalProfit = 0
    closedOrders = []
    testnet=True

    def __init__(self, testnet = True) -> None:
        self.logger = logging.getLogger('trading_bot.binance_client')
        self.logger.info('creating an instance of BinanceClient')
        self.env = dotenv_values('.env')
        self.testnet = testnet
        if self.testnet == True:
            self.client = Client(api_key=self.env['API_KEY_TEST'], api_secret=self.env['API_SECRET_TEST'], testnet=True)
        else:
            self.client = Client(api_key=self.env['API_KEY'], api_secret=self.env['API_SECRET'])
            

    def getHistoricalData(self, interval, start, symbol) -> pd.DataFrame:
          rawData = self.client.get_historical_klines(symbol=symbol, interval=interval, start_str=start)
          if len(rawData) == 0:
              rawData = [[time.time() * 1000,0,0,0,0,0]]
              print(f'get_historical_klines for symbol {symbol}, data: {rawData}')    
          frame = self.convertKlinesToFrame(rawData)
          return frame

    # https://binance-docs.github.io/apidocs/spot/en/#compressed-aggregate-trades-list
    def convertKlinesToFrame(self, rawData):
        frame = pd.DataFrame(rawData)
        frame = frame.iloc[:, :6]
        frame = frame.astype(float)
        frame.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        frame = frame.set_index('Time')
        frame['Time'] = pd.to_datetime( frame.index, unit='ms')
        frame.index = pd.to_datetime( frame.index, unit='ms')
        return frame
    

    def calcMACD(self, interval, start, symbol):
        frame = self.getHistoricalData(interval, start, symbol)
        frame = MACD(frame)
        return  frame

    def ema_signal(self, interval, start, symbol):
        frame = self.getHistoricalData(interval, start, symbol)
        frame = EMA(frame)
        buy = False
        sell = False
        if (len(frame) > 1):
             buy = frame['EMA_Fast'][-1] > frame['EMA_Signal'][-1] # and frame['EMA_Fast'][-2] > frame['EMA_Signal'][-2]
             sell = frame['EMA_Fast'][-1] < frame['EMA_Signal'][-1] # and frame['EMA_Fast'][-2] < frame['EMA_Signal'][-2]   
             self.logger.info(f'Symbol:  {symbol} Fast: {frame["EMA_Fast"][-1]} Signal: { frame["EMA_Signal"][-1]}')
        return {"buy":buy, "sell": sell, "fast":  frame['EMA_Fast'][-1], "signal": frame['EMA_Signal'][-1]}
        

    def ema_checker(self, interval, start, tickers):
        result = {}
        for ticker in tickers:
            try:
                result[ticker] = self.ema_signal(interval=interval, start=start, symbol=ticker)
            except Exception:
                print(f'failed to get ema signal for ticker {ticker}')    
        return result    
        
    def get_usdt_tickers(self) -> List:
        prices = self.client.get_all_tickers()
        frame = pd.DataFrame(prices)
        frame = frame.loc[ (frame.symbol.str.endswith("USDT")) & (frame.symbol.str.contains('DOWN') == False) & (frame.symbol.str.contains('UP') == False) & (frame.symbol.str.contains('BEAR') == False) & (frame.symbol.str.contains('BULL') == False), ['symbol']]
        symbols = frame.symbol.values.tolist()
        return symbols
                

if __name__ == '__main__':
    bClient = BinanceClient(testnet=False)
    #open_orders = bClient.client.get_open_orders(symbol='BTCUSDT')
    #print(open_orders) 
    symbols = bClient.get_usdt_tickers()
    print(symbols_to_table(symbols))
  