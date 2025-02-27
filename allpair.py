import sys
import MetaTrader5 as mt5
import pandas as pd
import time

# Connect to MT5
if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

symbols = ["BTCUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "USDCADm", "AUDUSDm", "NZDUSDm", "XAUUSDm"]
lot_size = 0.09
sl_amount = 5  # Stop loss in dollars
tp_amount = 10  # Take profit in dollars
timeframe = mt5.TIMEFRAME_M1

def get_data(symbol):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 6)  # Get last 6 candles
    df = pd.DataFrame(rates)
    df["symbol"]=symbol
    #print(df.head(1))
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def check_entry_condition(symbol):
    df = get_data(symbol)
    last_candle = df.iloc[-1]
    prev_candles = df.iloc[:-1]
    
    avg_size = (prev_candles['high'] - prev_candles['low']).mean()
    last_candle_size = last_candle['high'] - last_candle['low']
    
    if last_candle_size >= 2 * avg_size:
        trigger_point = last_candle['low'] + (last_candle_size * 0.4)
        return trigger_point, last_candle['high'], last_candle['low']
    return None, None, None

def place_trade(symbol, entry_price):
    point = mt5.symbol_info(symbol).point
    price = mt5.symbol_info_tick(symbol).ask
    sl = price - sl_amount
    tp = price + tp_amount
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": "Multi-Symbol Strategy",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    order = mt5.order_send(request)
    if order.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Trade failed for {symbol}, error code:", order.retcode)
    else:
        print(f"Trade executed successfully for {symbol}")

while True:
    for symbol in symbols:
        trigger_point, high, low = check_entry_condition(symbol)
        if trigger_point:
            df = get_data(symbol)
            for _, row in df.iterrows():
                if row['low'] <= trigger_point <= row['high']:
                    place_trade(symbol, trigger_point)
                    break
    time.sleep(60)  # Check every 5 minutes
