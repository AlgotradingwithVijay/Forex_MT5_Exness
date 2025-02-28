import MetaTrader5 as mt5
import pandas as pd
import time
import pytz
import sys
import logging
from datetime import datetime

# Argument validation
if len(sys.argv) < 10:
    print("Usage: python child.py <symbol> <lot_size> <profit_target> <sl_trailing_trigger> <sl_trailing_adjustment> <timeframe> <interval_minutes> <sl> <tp>")
    sys.exit(1)

# Logging setup
logging.basicConfig(
    filename="all_trades.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Argument parsing
symbol = sys.argv[1]
lot_size = float(sys.argv[2])
profit_target = float(sys.argv[3])
sl_trailing_trigger = float(sys.argv[4])
sl_trailing_adjustment = float(sys.argv[5])
timeframe_str = sys.argv[6]
interval_minutes = int(sys.argv[7])
sl = float(sys.argv[8])
tp = float(sys.argv[9])

# Timeframe mapping
timeframe_map = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30
}
timeframe = timeframe_map.get(timeframe_str, mt5.TIMEFRAME_M1)

# Connect to MT5
if not mt5.initialize():
    logging.error("Failed to initialize MT5")
    sys.exit(1)

# Timezone
ist = pytz.timezone("Asia/Kolkata")

# Trade tracking variables
TradeFlag = False
current_trade_type = None  # 'BUY' or 'SELL'

def get_current_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    return tick.bid if tick else None

def get_open_positions(symbol):
    positions = mt5.positions_get(symbol=symbol)
    return positions if positions else []

def get_open_trade_type():
    positions = get_open_positions(symbol)
    if not positions:
        return None
    return 'BUY' if positions[0].type == mt5.ORDER_TYPE_BUY else 'SELL'

def close_all_trades(symbol):
    positions = get_open_positions(symbol)
    for position in positions:
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": 123456,
            "comment": "Close opposite trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Closed position {position.ticket} for {symbol}")
        else:
            logging.error(f"Failed to close position {position.ticket} for {symbol}, retcode: {result.retcode}")

def place_trade(symbol, trade_type, entry_price):
    price = mt5.symbol_info_tick(symbol).ask if trade_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if trade_type == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": entry_price - sl if trade_type == "BUY" else entry_price + sl,
        "tp": entry_price + tp if trade_type == "BUY" else entry_price - tp,
        "deviation": 10,
        "magic": 123456,
        "comment": f"{trade_type} Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"{trade_type} trade placed for {symbol} at {price}")
        return True
    else:
        logging.error(f"Failed to place {trade_type} trade for {symbol}, retcode: {result.retcode}")
        return False

def check_entry_condition():
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 6)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC').dt.tz_convert(ist)

    last_candle = df.iloc[-1]
    prev_candles = df.iloc[-6:-1]
    avg_size = (prev_candles['high'] - prev_candles['low']).mean()
    last_size = last_candle['high'] - last_candle['low']

    trade_type = 'BUY' if last_candle['close'] > last_candle['open'] else 'SELL'
    trigger_point = None

    if last_size >= 1.2 * avg_size:
        if trade_type == 'BUY':
            trigger_point = last_candle['low'] + 0.4 * last_size
        else:
            trigger_point = last_candle['high'] - 0.4 * last_size

    return trigger_point, trade_type

def handle_trade(trigger_point, trade_type):
    global TradeFlag, current_trade_type

    open_trade_type = get_open_trade_type()

    if open_trade_type:
        if open_trade_type != trade_type:
            logging.info(f"Reversing trade for {symbol} from {open_trade_type} to {trade_type}")
            close_all_trades(symbol)
        else:
            logging.info(f"Same direction trade detected, skipping new entry for {symbol}")
            return  # Skip if already in same direction trade

    if place_trade(symbol, trade_type, trigger_point):
        TradeFlag = True
        current_trade_type = trade_type

def wait_for_next_interval():
    now = datetime.now(ist)
    next_minute = (now.minute // interval_minutes + 1) * interval_minutes
    next_time = now.replace(minute=next_minute, second=0, microsecond=0)
    if next_minute >= 60:
        next_time = next_time.replace(hour=now.hour + 1, minute=0)

    wait_seconds = (next_time - now).total_seconds()
    logging.info(f"Waiting until {next_time.strftime('%Y-%m-%d %H:%M:%S')} for next cycle")
    time.sleep(wait_seconds)

def main():
    wait_for_next_interval()

    while True:
        trigger_point, trade_type = check_entry_condition()

        if trigger_point:
            logging.info(f"Entry condition met for {symbol} - {trade_type} at {trigger_point}")
            handle_trade(trigger_point, trade_type)

        wait_for_next_interval()

if __name__ == "__main__":
    main()
