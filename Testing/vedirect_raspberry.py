#!/usr/bin/env python3
"""
Live VE.Direct Monitor GUI for Raspberry Pi

Connects to your Victron SmartShunt via VE.Direct (USB serial)
Displays real-time battery parameters in a tkinter window,
updating on each V, I, P, SOC, CE, TTG tag.
"""
import sys
import serial
import re
import tkinter as tk
from tkinter import font

# --- Configuration ---
DEFAULT_PORT = '/dev/ttyUSB0'      # Typical on Raspberry Pi
BAUDRATE = 19200                   # VE.Direct default
TIMEOUT = 0.1                      # seconds
POLL_INTERVAL = 100                # ms between reads

display_tags = ['V', 'I', 'P', 'SOC', 'CE', 'TTG']
tag_labels = {
    'V': 'Voltage (V)',
    'I': 'Current (A)',
    'P': 'Power (W)',
    'SOC': 'State of Charge (%)',
    'CE': 'Consumed Ah',
    'TTG': 'Time to Go'
}
TAG_PATTERN = re.compile(r'^([A-Z0-9]{1,4})\t(.+)$')

# --- Choose port ---
port = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PORT

# --- Open serial port ---
try:
    ser = serial.Serial(port, baudrate=BAUDRATE, timeout=TIMEOUT)
except Exception as e:
    print(f"Error opening serial port {port}: {e}")
    sys.exit(1)

# --- Build GUI ---
root = tk.Tk()
root.title("Victron SmartShunt Monitor")
frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

fonts = {'title': font.Font(size=14, weight='bold'), 'value': font.Font(size=18)}
widgets = {}
for r, tag in enumerate(display_tags):
    tk.Label(frame, text=tag_labels[tag], font=fonts['title']).grid(row=r, column=0, sticky='w')
    lbl = tk.Label(frame, text='--', font=fonts['value'])
    lbl.grid(row=r, column=1, sticky='e')
    widgets[tag] = lbl

# --- Update loop ---
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
            # convert and format
            try:
                num = float(val)
            except ValueError:
                text = val
            else:
                if key == 'V':
                    text = f"{num/1000.0:.1f}"
                elif key == 'I':
                    text = f"{num/1000.0:.2f}"
                elif key == 'P':
                    text = f"{num:.0f}"
                elif key == 'SOC':
                    text = f"{num/10.0:.1f}"
                elif key == 'CE':
                    text = f"{num/1000.0:.1f}"
                elif key == 'TTG':
                    t = int(num)
                    if t < 0:
                        text = '--'
                    elif t < 60:
                        text = f"{t} m"
                    elif t < 1440:
                        text = f"{t/60.0:.1f} h"
                    else:
                        text = f"{t/1440.0:.1f} d"
                else:
                    text = val
            widgets[key].config(text=text)
    except Exception:
        pass
    finally:
        root.after(POLL_INTERVAL, update_values)

# --- Clean up on close ---
root.protocol('WM_DELETE_WINDOW', lambda: (ser.close(), root.destroy()))
root.after(POLL_INTERVAL, update_values)
root.mainloop()
