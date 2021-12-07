import numpy as np

def MACD(frame, fast=12, slow=26, signal=9, type = 'EMA'):
    df = frame.copy()
    if type == 'EMA':
        df['MA_Fast'] = df['Close'].ewm(span=fast, min_periods=fast).mean()
        df['MA_Slow'] = df['Close'].ewm(span=slow, min_periods=slow).mean()
        df['MACD'] = df['MA_Fast'] - df['MA_Slow']
        df['SIGNAL'] = df['MACD'].ewm(span=signal, min_periods=signal).mean()
    elif type == 'SMA':
        df['MA_Fast'] = df['Close'].rolling(fast).mean()
        df['MA_Slow'] = df['Close'].rolling(slow).mean()
        df['MACD'] = df['MA_Fast'] - df['MA_Slow']
        df['SIGNAL'] = df['MACD'].rolling(signal).mean()
    return df


def EMA(frame, fast=5, slow=30, signal=10):
    df = frame.copy()
    df['EMA_Fast'] = df['Close'].ewm(span=fast, adjust=False, min_periods=0).mean()
    df['EMA_Slow'] = df['Close'].ewm(span=slow,adjust=False, min_periods=0).mean()
    df['EMA_Signal'] =df['Close'].ewm(span=signal,adjust=False, min_periods=0).mean()     
    return df

