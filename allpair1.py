import MetaTrader5 as mt5
import pandas as pd
import time
import pytz
from datetime import datetime, timedelta

# Connect to MT5
if not mt5.initialize():
    print("MT5 initialization failed")
    quit()

# Configurable variables
symbols = ["BTCUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "USDCADm", "AUDUSDm", "NZDUSDm", "XAUUSDm","USTECm","USOILm"] # Bitcoin and Gold
lot_size = 0.09
sl_amount = 2.5  # Stop loss in dollars
tp_amount = 1.5  # Take profit in dollars
timeframe = mt5.TIMEFRAME_M1  # Timeframe (M1, M5, M15, etc.)
interval_minutes = 1  # Interval in minutes (should match the selected timeframe)

# Define IST timezone
ist = pytz.timezone("Asia/Kolkata")

def get_current_price(symbol):
    # Request current tick for XAUUSD
    #symbol = "XAUUSD"
    tick = mt5.symbol_info_tick(symbol)
    
    if tick is not None:
        # Get the bid price (current buy price)
        current_price = tick.bid
        return current_price
    else:
        print(f"Failed to get tick data for {symbol}")
        return None

def get_data(symbol):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 6)  # Get last 6 candles
    df = pd.DataFrame(rates)
    
    # Convert time to IST
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC').dt.tz_convert(ist)
    df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S IST')  # Readable format
    
    return df

def check_entry_condition(symbol):
    df = get_data(symbol)
    last_candle = df.iloc[-1]
    prev_candles = df.iloc[-6:-1]  # Last 5 candles before the current one
    prev_candle = df.iloc[-2]  # Previous candle

    avg_size = (prev_candles['high'] - prev_candles['low']).mean()
    last_candle_size = last_candle['high'] - last_candle['low']

    # Determine buy/sell direction
    trade_type = "BUY" if prev_candle['close'] > prev_candle['open'] else "SELL"
    print(f"last_candle_size: {last_candle_size} avg_size: {avg_size}")
    if last_candle_size >= 1 * avg_size:
        trigger_point = last_candle['low'] + (last_candle_size * 0.4) if trade_type == "BUY" else last_candle['high'] - (last_candle_size * 0.4)
        return trigger_point, trade_type, last_candle['high'], last_candle['low'], last_candle['time']
    
    return None, None, None, None, None

def place_trade(symbol, entry_price, trade_type):
    price = mt5.symbol_info_tick(symbol).ask if trade_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    sl = price - sl_amount if trade_type == "BUY" else price + sl_amount
    tp = price + tp_amount if trade_type == "BUY" else price - tp_amount

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": f"{trade_type} Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    order = mt5.order_send(request)
    if order.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] Trade failed for {symbol} ({trade_type}), error code:", order.retcode)
    else:
        print(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] {trade_type} Trade executed successfully for {symbol} at {entry_price}")

# Wait for the next exact interval mark
def wait_for_next_interval():
    now = datetime.now(ist)
    next_minute = (now.minute // interval_minutes + 1) * interval_minutes  # Next multiple of interval_minutes
    if next_minute >= 60:
        next_minute = 0
        next_hour = now.hour + 1
    else:
        next_hour = now.hour

    next_run_time = now.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
    wait_time = (next_run_time - now).total_seconds()
    
    print(f"Waiting until {next_run_time.strftime('%Y-%m-%d %H:%M:%S IST')} to start execution...")
    time.sleep(wait_time)  # Wait until the next exact interval mark

# Ensure execution starts exactly at the next interval mark
wait_for_next_interval()

# Main Loop
while True:
    for symbol in symbols:
        trigger_point, trade_type, high, low, candle_time = check_entry_condition(symbol)
        
        if trigger_point:
            print(f"[{candle_time}] Big candle detected for {symbol}. Monitoring trigger point {trigger_point} every second...")
            
            # Monitor every second until trigger point is touched
            while True:
                #df = get_data(symbol)
                current_price = get_current_price(symbol)

                if (trade_type == "BUY" and current_price <= trigger_point) or (trade_type == "SELL" and current_price >= trigger_point):
                    print(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] {trade_type} Entry triggered for {symbol} at {trigger_point}")
                    place_trade(symbol, trigger_point, trade_type)
                    break  # Exit monitoring loop once trade is placed

                time.sleep(1)  # Check price every second

    wait_for_next_interval()  # Ensure the script runs exactly at the next interval mark
