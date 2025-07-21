#!/usr/bin/env python3
"""
Live VE.Direct Voltage Console Logger

Connects to your Victron SmartShunt via VE.Direct (e.g. COM6 at 19200 baud)
and prints each voltage reading (V) with a timestamp as soon as it is received.
"""
import serial
import re
import time

# --- Configuration ---
PORT = 'COM6'     # Change to your serial port if needed
BAUDRATE = 19200  # VE.Direct default
TIMEOUT = 1       # seconds

# Pattern to match a VE.Direct tag-value line
TAG_PATTERN = re.compile(r'^V\t(\d+)$')

# --- Open serial port ---
try:
    ser = serial.Serial(PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
    print(f"Opened serial port {PORT} at {BAUDRATE} baud")
except serial.SerialException as e:
    print(f"Error: cannot open serial port {PORT}: {e}")
    exit(1)

print("Listening for Voltage ('V') readings... (press Ctrl+C to exit)")

try:
    while True:
        raw = ser.readline()
        if not raw:
            continue
        # Decode and strip CR/LF
        line = raw.decode('ascii', errors='ignore').strip()
        # Match voltage tag
        m = TAG_PATTERN.match(line)
        if m:
            # raw millivolt value
            mv = int(m.group(1))
            volts = mv / 1000.0
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{timestamp} Voltage: {volts:.3f} V")

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    ser.close()
