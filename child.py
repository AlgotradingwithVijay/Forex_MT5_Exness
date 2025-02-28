import MetaTrader5 as mt5
import pandas as pd
import time
import pytz
from datetime import datetime, timedelta
import sys
import logging
from datetime import datetime


# Validate arguments
if len(sys.argv) < 10:
    logging.info("Usage: python child.py <symbol> <lot_size> <profit_target> <sl_trailing_trigger> <sl_trailing_adjustment> <timeframe> <interval_minutes>")
    sys.exit(1)

# Set up centralized logging
log_file = "all_trades.log"
logging.basicConfig(
    filename=log_file, 
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Receive arguments from master.py
symbol = sys.argv[1]
lot_size = float(sys.argv[2])
profit_target = float(sys.argv[3])
sl_trailing_trigger = float(sys.argv[4])
sl_trailing_adjustment = float(sys.argv[5])
timeframe = sys.argv[6]
interval_minutes = int(sys.argv[7])
sl = int(sys.argv[8])
tp = int(sys.argv[9])


# Log received parameters
logging.info(f"Started trading for {symbol} with Lot Size: {lot_size}, Profit Target: {profit_target}, SL Trailing Trigger: {sl_trailing_trigger}, SL Adjustment: {sl_trailing_adjustment}, Timeframe: {timeframe}")



# Connect to MT5
if not mt5.initialize():
    logging.info("MT5 initialization failed")
    quit()

# Configurable variables
symbols = [symbol]
lot_size = 0.09
profit_target = 1  # Exit when profit reaches $20
sl_trailing_trigger = 10  # Move SL and TP when profit moves by $10
sl_trailing_adjustment = 2  # Move SL and TP by $2 when trailing triggers
timeframe = mt5.TIMEFRAME_M1  # 1-minute timeframe
interval_minutes = 1  # Should match the selected timeframe

# Define IST timezone
ist = pytz.timezone("Asia/Kolkata")

# Store open trades to track positions
open_trades = {}

def get_current_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    return tick.bid if tick else None

def get_open_trade(symbol):
    """Check if there is an open position for the symbol"""
    positions = mt5.positions_get(symbol=symbol)
    return positions[0] if positions else None

def close_trade(symbol):
    """Close the existing trade for the given symbol"""
    trade = get_open_trade(symbol)
    if not trade:
        logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] No open trade found for {symbol}, skipping close request.")
        return False  # No trade to close

    order_type = mt5.ORDER_TYPE_SELL if trade.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    close_price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

    if close_price is None:
        logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] Failed to get close price for {symbol}.")
        return False

    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": trade.volume,
        "type": order_type,
        "price": close_price,
        "deviation": 10,
        "magic": 123456,
        "comment": "Closing trade for new opposite signal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(close_request)

    if result is None:
        logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] Order send failed for {symbol}.")
        return False

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] Successfully closed trade for {symbol}.")
        return True
    else:
        logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] Close trade failed for {symbol}, error code: {result.retcode}")
        return False

def get_data(symbol):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 6)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC').dt.tz_convert(ist)
    df['time'] = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S IST')
    return df

def check_entry_condition(symbol):
    df = get_data(symbol)
    last_candle = df.iloc[-1]
    prev_candles = df.iloc[-6:-1]
    prev_candle = df.iloc[-2]

    avg_size = (prev_candles['high'] - prev_candles['low']).mean()
    last_candle_size = last_candle['high'] - last_candle['low']
    trade_type = "BUY" if last_candle['close'] > last_candle['open'] else "SELL"

    if last_candle_size >= 1.2 * avg_size:
        trigger_point = last_candle['low'] + (last_candle_size * 0.4) if trade_type == "BUY" else last_candle['high'] - (last_candle_size * 0.4)
        return trigger_point, trade_type, last_candle['high'], last_candle['low'], last_candle['time']
    
    return None, None, None, None, None

def place_trade(symbol, entry_price, trade_type):
    price = mt5.symbol_info_tick(symbol).ask if trade_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": 10,
        "magic": 123456,
        "comment": f"{trade_type} Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    order = mt5.order_send(request)
    if order.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] {trade_type} Trade executed successfully for {symbol} at {entry_price}")
        open_trades[symbol] = order.order
        return order.order
    return None

def check_trailing_stop(symbol):
    trade = get_open_trade(symbol)
    if not trade:
        return

    current_price = get_current_price(symbol)
    if not current_price:
        return

    entry_price = trade.price_open
    profit = (current_price - entry_price) * trade.volume * 100  # Adjust for lot size

    if profit >= profit_target:
        close_trade(symbol)

    elif profit >= sl_trailing_trigger:
        new_sl = trade.price_sl + sl_trailing_adjustment if trade.type == mt5.ORDER_TYPE_BUY else trade.price_sl - sl_trailing_adjustment
        update_request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": trade.ticket,
            "sl": new_sl,
            "tp": trade.price_tp,
        }
        result = mt5.order_send(update_request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"[{datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')}] Updated SL for {symbol}")

# Wait for next exact interval
def wait_for_next_interval():
    now = datetime.now(ist)
    next_minute = (now.minute // interval_minutes + 1) * interval_minutes
    if next_minute >= 60:
        next_minute = 0
        next_hour = now.hour + 1
    else:
        next_hour = now.hour

    next_run_time = now.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
    wait_time = (next_run_time - now).total_seconds()
    
    logging.info(f"Waiting until {next_run_time.strftime('%Y-%m-%d %H:%M:%S IST')} to start execution...")
    time.sleep(wait_time)

# Start at next interval
wait_for_next_interval()

while True:
    for symbol in symbols:
        trigger_point, trade_type, high, low, candle_time = check_entry_condition(symbol)
        
        if trigger_point:
            trade = get_open_trade(symbol)
            if trade and trade.type != (mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL):
                close_trade(symbol)

            logging.info(f"[{candle_time}] Monitoring {symbol} every second for {trade_type} entry at {trigger_point}")
            while True:
                current_price = get_current_price(symbol)

                if (trade_type == "BUY" and current_price <= trigger_point) or (trade_type == "SELL" and current_price >= trigger_point):
                    place_trade(symbol, trigger_point, trade_type)
                    break
                
                check_trailing_stop(symbol)
                time.sleep(1)

    wait_for_next_interval()
