import subprocess
import time

 

# Dictionary storing different parameters for each symbol
symbol_configs = {
    "BTCUSDm":   {"lot_size": 0.09, "profit_target": 5, "sl_trailing_trigger": 10, "sl_trailing_adjustment": 2, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "EURUSDm":   {"lot_size": 0.1,  "profit_target": 3, "sl_trailing_trigger": 8,  "sl_trailing_adjustment": 1.5, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "GBPUSDm":   {"lot_size": 0.08, "profit_target": 4, "sl_trailing_trigger": 9,  "sl_trailing_adjustment": 1.8, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "USDJPYm":   {"lot_size": 0.07, "profit_target": 6, "sl_trailing_trigger": 12, "sl_trailing_adjustment": 2.5, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "USDCADm":   {"lot_size": 0.05, "profit_target": 3, "sl_trailing_trigger": 7,  "sl_trailing_adjustment": 1.2, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "AUDUSDm":   {"lot_size": 0.06, "profit_target": 4, "sl_trailing_trigger": 8,  "sl_trailing_adjustment": 1.6, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "NZDUSDm":   {"lot_size": 0.04, "profit_target": 2, "sl_trailing_trigger": 5,  "sl_trailing_adjustment": 1, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "XAUUSDm":   {"lot_size": 0.2,  "profit_target": 10, "sl_trailing_trigger": 15, "sl_trailing_adjustment": 3, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "USTECm":    {"lot_size": 0.1,  "profit_target": 7,  "sl_trailing_trigger": 11, "sl_trailing_adjustment": 2.2, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
    "USOILm":    {"lot_size": 0.1,  "profit_target": 5,  "sl_trailing_trigger": 9,  "sl_trailing_adjustment": 1.5, "timeframe": "M1", "interval_minutes": 1,"sl": 1,"tp": 1},
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
