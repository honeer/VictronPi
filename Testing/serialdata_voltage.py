#!/usr/bin/env python3
"""
Live VE.Direct Voltage Monitor GUI

Connects to your Victron SmartShunt via VE.Direct (e.g. COM6 at 19200 baud)
and displays the real-time battery voltage in a simple tkinter window, updating on every available V-tag line.
"""
import serial
import re
import tkinter as tk
from tkinter import font
import time

# --- Configuration ---
PORT = 'COM6'     # Change to your serial port if needed
BAUDRATE = 19200  # VE.Direct default
TIMEOUT = 0.1     # shorter timeout for more responsive reads

# Pattern to match voltage lines: V<tab><millivolts>
TAG_PATTERN = re.compile(r'^V\t(\d+)$')

# --- Open serial port ---
try:
    ser = serial.Serial(PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
except Exception as e:
    print(f"Error opening serial port {PORT}: {e}")
    exit(1)

# --- Build GUI ---
root = tk.Tk()
root.title("Victron SmartShunt Voltage")
root.geometry("300x100")
root.resizable(False, False)

volt_font = font.Font(size=24, weight='bold')
label = tk.Label(root, text="--.- V", font=volt_font)
label.pack(expand=True, padx=10, pady=10)

# Update function
def update_voltage():
    try:
        # Read all available lines in buffer
        while True:
            raw = ser.readline()
            if not raw:
                break
            line = raw.decode('ascii', errors='ignore').strip()
            m = TAG_PATTERN.match(line)
            if m:
                mv = int(m.group(1))
                volts = mv / 1000.0
                # Update label immediately
                label.config(text=f"{volts:.3f} V")
    except Exception as e:
        label.config(text="Error")
        print(f"Serial read error: {e}")
    finally:
        # schedule next poll
        root.after(100, update_voltage)

# Clean up on close
def on_close():
    try:
        ser.close()
    except:
        pass
    root.destroy()

root.protocol('WM_DELETE_WINDOW', on_close)
# Start updates
root.after(100, update_voltage)
root.mainloop()
