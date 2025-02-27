import MetaTrader5 as mt5
import pandas as pd
import time

# Connect to MetaTrader 5
if not mt5.initialize():
    print("MT5 Initialization Failed")
    quit()

SYMBOL = "BTCUSDm"
LOT_SIZE = 0.09
SL_AMOUNT = 5  # Stop Loss in dollars
TP_AMOUNT = 10  # Take Profit in dollars
TIMEFRAME = mt5.TIMEFRAME_M1
HISTORY_BARS = 6  # Last 5 candles + current

# Function to fetch last N bars
def get_candles():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, HISTORY_BARS)
    return pd.DataFrame(rates)

# Function to place an order
def place_order(direction, entry_price):
    sl = entry_price - SL_AMOUNT if direction == "buy" else entry_price + SL_AMOUNT
    tp = entry_price + TP_AMOUNT if direction == "buy" else entry_price - TP_AMOUNT

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL,
        "price": entry_price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 123456,
        "comment": "Algo Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }
    result = mt5.order_send(request)
    print("Trade Result:", result)

# Backtesting Function
def backtest():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 288 * 30)  # 1 month of 5-minute candles
    df = pd.DataFrame(rates)
    
    trades = 0
    profit = 0

    for i in range(5, len(df)):
        last_5 = df.iloc[i-5:i]
        last_6 = df.iloc[i-6:i]
        current_candle = df.iloc[i]
        # print(f'current_candle low {current_candle["open"]}, low {current_candle["low"]}')
        # print(f'{df.iloc[i]}')


        max_body = (last_5["high"] - last_5["low"]).max()
        current_body = current_candle["high"] - current_candle["low"]
        #print(f'{max_body} {current_body}')
        if current_body >= 2 * max_body:
            entry_price = current_candle["low"] + 0.4 * (current_candle["high"] - current_candle["low"])
            
            for j in range(i+1, min(i+6, len(df))):
                if df.iloc[j]["low"] <= entry_price:
                    trades += 1
                    sl = entry_price + SL_AMOUNT
                    tp = entry_price - TP_AMOUNT
                    
                    if df.iloc[j]["low"] <= tp:
                        profit += TP_AMOUNT
                        print(f"Trade {trades}: Target Hit {profit}")
                    elif df.iloc[j]["high"] >= sl:
                        profit -= SL_AMOUNT
                        print(f"Trade {trades}: SL Hit {profit}")
                    break
    
    print(f"Total Trades: {trades}, Total Profit: {profit}")

# Run backtest
backtest()
