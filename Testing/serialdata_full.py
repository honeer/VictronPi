#!/usr/bin/env python3
"""
Live VE.Direct Monitor GUI

Connects to your Victron SmartShunt via VE.Direct (e.g. COM6 at 19200 baud)
and displays real-time battery parameters in a tkinter window, updating on each frame.
Supported parameters: Voltage, Current, Power, State of Charge, Consumed Ah, Time to Go.
Formatting:
  - Voltage: 1 decimal (e.g. 12.5 V)
  - Current: 2 decimals in A (e.g. 0.36 A)
  - Power: integer in W
  - SOC: 1 decimal percent
  - CE: in Ah, converted and 1 decimal
  - TTG: minutes if <60, hours if <1440, days otherwise
"""
import serial
import re
import tkinter as tk
from tkinter import font
import time

# --- Configuration ---
PORT = 'COM6'     # Change to your serial port if needed
BAUDRATE = 19200  # VE.Direct default
TIMEOUT = 0.1     # seconds
POLL_INTERVAL = 100  # ms between reads

# Tags to display and their display order
display_tags = ['V', 'I', 'P', 'SOC', 'CE', 'TTG']
# Human-readable labels
tag_labels = {
    'V': 'Voltage (V)',
    'I': 'Current (A)',
    'P': 'Power (W)',
    'SOC': 'State of Charge (%)',
    'CE': 'Consumed Ah',
    'TTG': 'Time to Go'
}

# Regex to match any VE.Direct tag-value line
TAG_PATTERN = re.compile(r'^([A-Z0-9]{1,4})\t(.+)$')

# --- Open serial port ---
try:
    ser = serial.Serial(PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
except Exception as e:
    print(f"Error opening serial port {PORT}: {e}")
    exit(1)

# --- Build GUI ---
root = tk.Tk()
root.title("Victron SmartShunt Monitor")
# Create a frame for grid layout
frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# Define fonts
fonts = {
    'title': font.Font(size=14, weight='bold'),
    'value': font.Font(size=18)
}

# Create label widgets for each tag
widgets = {}
for r, tag in enumerate(display_tags):
    lbl = tk.Label(frame, text=tag_labels.get(tag, tag), font=fonts['title'])
    lbl.grid(row=r, column=0, sticky='w', pady=2)
    val = tk.Label(frame, text='--', font=fonts['value'])
    val.grid(row=r, column=1, sticky='e', pady=2)
    widgets[tag] = val

# Update function: read serial, parse tags, update widgets
def update_values():
    try:
        while True:
            raw = ser.readline()
            if not raw:
                break
            line = raw.decode('ascii', errors='ignore').strip()
            m = TAG_PATTERN.match(line)
            if not m:
                continue
            key, val = m.groups()
            if key not in widgets:
                continue
            # Attempt numeric conversion
            try:
                num = float(val)
            except ValueError:
                widgets[key].config(text=val)
                continue
            # Format by tag
            if key == 'V':  # millivolts to volts
                volts = num / 1000.0
                text = f"{volts:.1f}"
            elif key == 'I':  # mA to A
                amps = num / 1000.0
                text = f"{amps:.2f}"
            elif key == 'P':  # W
                text = f"{num:.0f}"
            elif key == 'SOC':  # percent*10 to percent
                soc = num / 10.0
                text = f"{soc:.1f}"
            elif key == 'CE':  # raw in Ah*1000? convert to Ah
                ce = num / 1000.0
                text = f"{ce:.1f}"
            elif key == 'TTG':  # time to go in minutes
                ttg = int(num)
                if ttg < 0:
                    text = "--"
                elif ttg < 60:
                    text = f"{ttg} m"
                elif ttg < 1440:
                    hrs = ttg / 60.0
                    text = f"{hrs:.1f} h"
                else:
                    days = ttg / 1440.0
                    text = f"{days:.1f} d"
            else:
                text = val
            widgets[key].config(text=text)
    except Exception as e:
        print(f"Serial read error: {e}")
    finally:
        root.after(POLL_INTERVAL, update_values)

# Clean up on close
def on_close():
    try:
        ser.close()
    except:
        pass
    root.destroy()

root.protocol('WM_DELETE_WINDOW', on_close)
# Start updates
root.after(POLL_INTERVAL, update_values)
root.mainloop()
