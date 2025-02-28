import MetaTrader5 as mt5
import pandas as pd
import time
import pytz
import sys
import logging
from datetime import datetime, timedelta
import os

# Argument validation
if len(sys.argv) < 10:
    print("Usage: python child.py <symbol> <lot_size> <profit_target> <sl_trailing_trigger> <sl_trailing_adjustment> <timeframe> <interval_minutes> <sl> <tp>")
    sys.exit(1)

# Parse input arguments
symbol = sys.argv[1]
lot_size = float(sys.argv[2])
profit_target = float(sys.argv[3])
sl_trailing_trigger = float(sys.argv[4])
sl_trailing_adjustment = float(sys.argv[5])
timeframe_str = sys.argv[6]
interval_minutes = int(sys.argv[7])
sl = float(sys.argv[8])
tp = float(sys.argv[9])

# Map timeframe
timeframe_map = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30}
timeframe = timeframe_map.get(timeframe_str, mt5.TIMEFRAME_M1)

# Ensure "logs" folder exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Logging setup
log_file = os.path.join("logs", f"{symbol}.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Connect MT5
if not mt5.initialize():
    logging.error("Failed to initialize MT5")
    sys.exit(1)

# Timezone
ist = pytz.timezone("Asia/Kolkata")


def get_current_price():
    tick = mt5.symbol_info_tick(symbol)
    return tick.bid if tick else None


def get_open_trade_type():
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return None
    return 'BUY' if positions[0].type == mt5.ORDER_TYPE_BUY else 'SELL'


def close_all_trades():
    positions = mt5.positions_get(symbol=symbol)
    for pos in positions:
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
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
            logging.info(f"Closed trade {pos.ticket} for {symbol}")
        else:
            logging.error(f"Failed to close trade {pos.ticket}, retcode: {result.retcode}")


def place_trade(trade_type, entry_price):
    # Enforce trade type check every time
    open_type = get_open_trade_type()
    if open_type and open_type != trade_type:
        logging.info(f"Reversing trade for {symbol} from {open_type} to {trade_type}")
        close_all_trades()

    elif open_type == trade_type:
        logging.info(f"Skipping {trade_type} trade for {symbol} - already in {trade_type} trade")
        return False

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
        "comment": f"{trade_type} Entry",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    logging.info(f"Placing {trade_type} trade for {symbol} at {price}")
    logging.info(f"SL: {request['sl']} | TP: {request['tp']}")
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

    last = df.iloc[-1]
    avg_size = (df['high'] - df['low']).iloc[-6:-1].mean()
    last_size = last['high'] - last['low']

    trade_type = 'BUY' if last['close'] > last['open'] else 'SELL'
    if last_size >= 1.2 * avg_size:
        trigger_point = (last['low'] + 0.4 * last_size) if trade_type == 'BUY' else (last['high'] - 0.4 * last_size)
        logging.info(f"Found singals for {symbol} - {trade_type} at {trigger_point}")
        logging.info(f'{symbol}  last_size >= 1.2 * avg_size | {last_size} >= 1.2 * {avg_size} | aftermultiply {1.2 * avg_size}')
        return trigger_point, trade_type
    return None, None


def watch_price(trigger_point, trade_type):
    logging.info(f"Watching price for {symbol} {trade_type} entry at {trigger_point}")
    last_log_time = time.time()
    now = datetime.now(ist)
    SingalLogTime=  now.strftime('%Y-%m-%d %H:%M:%S')
    SignalFoundTime = f"Single was found at {SingalLogTime} for {symbol} {trade_type} entry at {trigger_point}"
    while True:
        price = get_current_price()

        if (trade_type == "BUY" and price <= trigger_point) or (trade_type == "SELL" and price >= trigger_point):
            if place_trade(trade_type, trigger_point):
                logging.info(f'{SignalFoundTime}')
                return
        current_time = time.time()
        if current_time - last_log_time >= 15:
            logging.info(f"{symbol} Current price: {price} and {trigger_point}")
            last_log_time = current_time
        time.sleep(1)


def wait_for_next_candle():
    now = datetime.now(ist)
    next_minute = (now.minute // interval_minutes + 1) * interval_minutes

    if next_minute >= 60:
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_time = now.replace(minute=next_minute, second=0, microsecond=0)

    wait_time = (next_time - now).total_seconds()
    logging.info(f"Waiting until {next_time.strftime('%Y-%m-%d %H:%M:%S')} for next candle")
    time.sleep(max(wait_time, 0))


def main():
    while True:
        trigger_point, trade_type = check_entry_condition()

        if trigger_point:
            logging.info(f"Trigger found for {symbol} - {trade_type} at {trigger_point}")
            watch_price(trigger_point, trade_type)

        wait_for_next_candle()


if __name__ == "__main__":
    main()
