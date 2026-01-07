import pandas as pd
import numpy as np

class DataProcessor:
    """
    Pure transformation logic for market data.
    Calculates technical indicators without side effects.
    """
    
    @staticmethod
    def clean_and_normalize(df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans raw dataframe: standardizes column names, handles missing values.
        """
        # Standardize columns to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        # Drop extra S3 columns not in DB model
        df.drop(columns=['transactions', 'window_start'], errors='ignore', inplace=True)
        
        # Ensure required columns exist
        required = {'ticker', 'date', 'open', 'high', 'low', 'close', 'volume'}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")
            
        # Convert date column
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Drop rows with NaN in critical columns
        df.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
        
        return df

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds technical indicators: RSI, SMA, MACD, Bollinger Bands, VWAP.
        """
        # Ensure sorted by date per ticker for rolling calculations
        df = df.sort_values(by=['ticker', 'date'])
        
        # Group by ticker to handle multiple stocks in one DF (if applicable)
        # However, typically ingestion is per-file. Assuming one big DF or per-ticker.
        # Efficient rolling operations on grouped DF:
        grouped = df.groupby('ticker')
        
        # 1. SMA (Simple Moving Average)
        df['sma_50'] = grouped['close'].transform(lambda x: x.rolling(window=50).mean())
        df['sma_200'] = grouped['close'].transform(lambda x: x.rolling(window=200).mean())
        
        # 2. RSI (Relative Strength Index) - 14 period
        def calculate_rsi(series, period=14):
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
            
        df['rsi_14'] = grouped['close'].transform(lambda x: calculate_rsi(x))

        # 3. MACD
        def calculate_macd(series):
            exp12 = series.ewm(span=12, adjust=False).mean()
            exp26 = series.ewm(span=26, adjust=False).mean()
            macd = exp12 - exp26
            signal = macd.ewm(span=9, adjust=False).mean()
            return macd, signal
            
        # Applying MACD is tricky with transform returning multiple, separate calls needed
        # Or custom apply. For simplicity/speed doing separate transforms.
        # Note: Optimization would be vectorized operations.
        # Here we iterate because transform with multiple outputs is complex.
        
        # Calculate EWMA 12 & 26
        df['ema_12'] = grouped['close'].transform(lambda x: x.ewm(span=12, adjust=False).mean())
        df['ema_26'] = grouped['close'].transform(lambda x: x.ewm(span=26, adjust=False).mean())
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = grouped['macd'].transform(lambda x: x.ewm(span=9, adjust=False).mean())
        
        # 4. Bollinger Bands
        df['bollinger_mid'] = grouped['close'].transform(lambda x: x.rolling(window=20).mean())
        df['bollinger_std'] = grouped['close'].transform(lambda x: x.rolling(window=20).std())
        df['bollinger_upper'] = df['bollinger_mid'] + (df['bollinger_std'] * 2)
        df['bollinger_lower'] = df['bollinger_mid'] - (df['bollinger_std'] * 2)
        
        # 5. VWAP (Volume Weighted Average Price)
        # Typically VWAP is intraday. For daily, it's just (High+Low+Close)/3 * Vol / Vol sum??
        # Usually VWAP is reset daily. If this is DAILY data, typical VWAP formula:
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        
        # Cleanup intermediate cols
        df.drop(columns=['ema_12', 'ema_26', 'bollinger_mid', 'bollinger_std'], inplace=True)
        
        return df
