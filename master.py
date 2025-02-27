import subprocess
import time

# List of trading symbols
symbols = ["BTCUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "USDCADm", "AUDUSDm", "NZDUSDm", "XAUUSDm", "USTECm", "USOILm"]

# Path to Python interpreter (adjust if needed)
PYTHON_EXECUTABLE = ".venv\Scripts\python.exe"  # Use "python" for Windows

# Store subprocess references
processes = {}

# Start a subprocess for each symbol
for symbol in symbols:
    log_file = f"{symbol}.log"  # Create a log file for each symbol
    err_file = f"{symbol}_error.log"

    with open(log_file, "w") as out, open(err_file, "w") as err:
        print(f"Starting child.py for {symbol}...")
        process = subprocess.Popen(
            [PYTHON_EXECUTABLE, "child.py", symbol],
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
