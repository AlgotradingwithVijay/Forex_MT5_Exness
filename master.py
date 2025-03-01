import subprocess
import time

 

# Dictionary storing different parameters for each symbol
symbol_configs = {
   
    # "EURUSDm":   {"lot_size": 0.03,  "profit_target": 3, "sl_trailing_trigger": 8,  "sl_trailing_adjustment": 1.5, "timeframe": "M1", "interval_minutes": 1,"sl": 0.01,"tp": 0.01},
    # "GBPUSDm":   {"lot_size": 0.05, "profit_target": 4, "sl_trailing_trigger": 9,  "sl_trailing_adjustment": 1.8, "timeframe": "M1", "interval_minutes": 1,"sl": 0.001,"tp": 0.002},
    # "USDJPYm":   {"lot_size": 0.09, "profit_target": 6, "sl_trailing_trigger": 12, "sl_trailing_adjustment": 2.5, "timeframe": "M1", "interval_minutes": 1,"sl": 0.100,"tp": 0.200},
    # "USDCADm":   {"lot_size": 0.05, "profit_target": 3, "sl_trailing_trigger": 7,  "sl_trailing_adjustment": 1.2, "timeframe": "M1", "interval_minutes": 1,"sl": 0.001,"tp": 0.002},
    # "AUDUSDm":   {"lot_size": 0.09, "profit_target": 1, "sl_trailing_trigger": 2,  "sl_trailing_adjustment": 0.6, "timeframe": "M1", "interval_minutes": 1,"sl": 0.0004,"tp": 0.0009},
    # "NZDUSDm":   {"lot_size": 0.04, "profit_target": 2, "sl_trailing_trigger": 5,  "sl_trailing_adjustment": 2, "timeframe": "M1", "interval_minutes": 1,"sl": 0.0025,"tp": 0.0052},
    # "XAUUSDm":   {"lot_size": 0.09,  "profit_target": 10, "sl_trailing_trigger": 15, "sl_trailing_adjustment": 3, "timeframe": "M1", "interval_minutes": 1,"sl": 2.5,"tp": 6},
    # "USTECm":    {"lot_size": 0.09,  "profit_target": 7,  "sl_trailing_trigger": 11, "sl_trailing_adjustment": 2.2, "timeframe": "M1", "interval_minutes": 1,"sl": 3,"tp": 1},
    # "USOILm":    {"lot_size": 0.09,  "profit_target": 5,  "sl_trailing_trigger": 9,  "sl_trailing_adjustment": 1.5, "timeframe": "M1", "interval_minutes": 1,"sl": 0.15,"tp": 0.32},
    # Add Crypto  symbols here
    "BTCUSDm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},
    "BTCAUDm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},
    "BTCCNHm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},
    "BTCJPYm":    {"lot_size": 0.9, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 40000,"tp": 40000},
    "BTCTHBm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},
    "BTCXAGm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},
    "BTCXAUm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": .1,"tp": .1},
    "BTCZARm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},
    "ETHUSDm":    {"lot_size": 0.5, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "H1", "interval_minutes": 1,"sl": 15,"tp": 15},



}

# Path to Python interpreter (adjust if needed)
PYTHON_EXECUTABLE = ".venv\Scripts\python.exe"  # Use "python" for Windows

# Centralized log file


# Store subprocess references
processes = {}
log_file = "All_trades.log"
err_file = "All_trades_error.log"
# Start a subprocess for each symbol
with open(log_file, "w") as out, open(err_file, "w") as err:
    for symbol, config in symbol_configs.items():
        print(f"Starting child.py for {symbol}...")

        # Pass parameters based on symbol-specific config
        process = subprocess.Popen(
            [
                PYTHON_EXECUTABLE, "child.py", 
                symbol, 
                str(config["lot_size"]), 
                str(config["profit_target"]), 
                str(config["sl_trailing_trigger"]), 
                str(config["sl_trailing_adjustment"]), 
                config["timeframe"], 
                str(config["interval_minutes"]),
                str(config["sl"]),
                str(config["tp"]),
            ],
            stdout=out,
            stderr=err
        )
        processes[symbol] = process  # Store process reference

# Monitor processes
try:
    while True:
        time.sleep(5)  # Check status every 5 seconds
        for symbol, process in processes.items():
            if process.poll() is not None:  # If the process has exited
                print(f"Process for {symbol} exited.")
except KeyboardInterrupt:
    print("Stopping all processes...")
    for process in processes.values():
        process.terminate()  # Terminate all subprocesses
