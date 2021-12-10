from binance.client import Client
from binance.enums import *
from dotenv import dotenv_values
from binance_time_utils import convertToStartTime, convertToInterval
import pandas as pd
import logging
from algo_utils import MACD, EMA

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
    
    # A cumulative product is a sequence of partial products of a given sequence
    def calcCumulativeProduct(self, frame, column):
        cumret = (frame[column].pct_change() + 1).cumprod() -1
        return cumret

    def calculateOrderPrice(self, response) -> float:
        frame = pd.DataFrame(response['fills'])
        frame['price'] = frame['price'].astype(float)
        frame['qty'] = frame['qty'].astype(float)
        frame['profit'] = frame['price'] * frame['qty']
        total = frame['profit'].sum()
        return total


    def cumulativeStrategyTest(self,interval, start, symbol, buyThreshold, sellThreshold, sellStopThreshold, qnty):
        frame = self.getHistoricalData(interval, start, symbol)
        #self.logger.info(f'Last historical data\n{frame.iloc[-1]}')
        if self.openBuyOrder is None:
            cumret = self.calcCumulativeProduct(frame, 'Open')    
            self.logger.info(f'Checking if we can buy, cumulative return: {cumret[-1]}, buy threshold: {buyThreshold}')
            
            if cumret[-1] < buyThreshold:
                self.logger.info(f'BUYING: Cumulative ret {cumret[-1]} Price: {frame.Close[-1]}')
                self.openBuyOrder = self.client.create_order(symbol = symbol, type='MARKET', side='BUY', quantity = qnty)
                self.logger.info(f'Buy order was executed: {self.openBuyOrder}')
                #self.openBuyOrder = frame.iloc[-1, :]
        else:
            orderBuyTime = pd.to_datetime(self.openBuyOrder['transactTime'], unit='ms')
            frame = frame.loc[frame.index > orderBuyTime]
            frameLen = len(frame)
            if frameLen == 0:
                  return False
            cumret = self.calcCumulativeProduct(frame, 'Open')    
            self.logger.info(f'Checking if we can sell the order, cumulative return: {cumret[-1]}')
            if cumret[-1] > sellThreshold or cumret[-1] < sellStopThreshold:
                openSellOrder = self.client.create_order(symbol = symbol, type='MARKET', side='SELL', quantity = qnty)
                sellPaid = self.calculateOrderPrice(openSellOrder)
                buyPaid = self.calculateOrderPrice(self.openBuyOrder)
                profit = sellPaid - buyPaid
                self.totalProfit +=profit
                self.closedOrders.append({'profit': profit, 'buy': self.openBuyOrder, 'sell': openSellOrder})
                self.logger.info(f'Sell order was executed with profit: {profit} {openSellOrder}')
                self.openBuyOrder = None
                return True
        
        return False

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
             buy = frame['EMA_Fast'][-1] > frame['EMA_Signal'][-1] and frame['EMA_Fast'][-2] > frame['EMA_Signal'][-2]
             sell = frame['EMA_Fast'][-1] < frame['EMA_Signal'][-1] and frame['EMA_Fast'][-2] < frame['EMA_Signal'][-2]   
             self.logger.info(f'Fast: {frame["EMA_Fast"][-1]} Signal: { frame["EMA_Signal"][-1]}')
        return {"buy":buy, "sell": sell, "fast":  frame['EMA_Fast'][-1], "signal": frame['EMA_Signal'][-1]}
        
    def getAllTradableTickets(self):
        response = self.client.get_ticker()
    def emaStrategy(self, interval, start, symbol, qnty):
        frame = self.getHistoricalData(interval, start, symbol)
        frame = EMA(frame)
        fast = frame['EMA_Fast'][-1]
        signal = frame['EMA_Signal'][-1] 
        open_orders = self.client.get_open_orders(symbol=symbol)
        if (len(open_orders) > 0):
            self.logger.info(f'Cannot place new order, there are still open orders: {open_orders}')
            return False

        if self.openBuyOrder is None:
            self.logger.info(f'Checking if we can buy the order, EMA : {fast}, signal: {signal} ')
            if fast > signal:
                self.logger.info(f'BUYING, Price: {frame.Close[-1]}')
                self.openBuyOrder = self.client.create_order(symbol = symbol, type=ORDER_TYPE_LIMIT, side=SIDE_BUY, quantity = qnty, price=frame['Close'][-1], timeInForce=TIME_IN_FORCE_GTC)
                self.logger.info(f'Buy order was executed: {self.openBuyOrder}')
                
        else:
            self.logger.info(f'Checking if we can sell the order, EMA: {fast}, signal: {signal} ')
            if fast < signal:
                openSellOrder = self.client.create_order(symbol = symbol, type=ORDER_TYPE_LIMIT, side=SIDE_SELL, quantity = qnty, price=frame['Close'][-1], timeInForce=TIME_IN_FORCE_GTC)
                sellPaid = frame['Close'][-1]
                buyPaid = float(self.openBuyOrder['price'])
                profit = sellPaid - buyPaid
                self.totalProfit +=profit
                self.closedOrders.append({'profit': profit, 'buy': self.openBuyOrder, 'sell': openSellOrder})
                self.logger.info(f'Sell LIMIT order was executed with estimated profit: {profit}, status: {openSellOrder["status"]}, cummulativeQuoteQty: {openSellOrder["cummulativeQuoteQty"]}')
                self.openBuyOrder = None
                return True    
            
        return False

    def ema_checker(self, interval, start, tickers):
        result = {}
        for ticker in tickers:
            result[ticker] = self.ema_signal(interval=interval, start=start, symbol=ticker)
        return result    
        

if __name__ == '__main__':
    bClient = BinanceClient()
    #open_orders = bClient.client.get_open_orders(symbol='BTCUSDT')
    #print(open_orders) 
    prices = bClient.client.get_all_tickers()
    frame = pd.DataFrame(prices)
    #frame = frame.loc[ frame.symbol.str.contains("USDT"), :]
    print(frame)
    bClient.ema_checker()
 #   {
 #   "symbol": "BTCUSDT",
 #   "orderId": 28,
 #   "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
 #   "transactTime": 1507725176595,
 #   "price": "0.00000000",
 #   "origQty": "10.00000000",
 #   "executedQty": "10.00000000",
 #   "cummulativeQuoteQty": "10.00000000",
 #   "status": "FILLED",
 #   "timeInForce": "GTC",
 #   "type": "MARKET",
 #   "side": "SELL"
#}