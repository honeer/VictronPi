#!/usr/bin/env python3
"""
VE.Direct log parser for a single value (Voltage).
Usage:
  1. Save your PuTTY log output to 'putty.log' in this script's folder.
  2. Run: python vedirect_parse.py

This script scans all VE.Direct frames in the log, finds the first frame
containing a valid Voltage ('V') entry, converts the raw millivolt reading
to volts, and prints its value.
"""
import re

VALID_KEY_REGEX = re.compile(r'^[A-Z0-9]{1,4}$')


def parse_vedirect_block(block):
    """Parse a VE.Direct frame block into a dict of key->value, skipping invalid lines."""
    data = {}
    for line in block.strip().splitlines():
        parts = re.split(r"[\t ]+", line.strip(), maxsplit=1)
        if len(parts) != 2:
            continue
        key, val = parts
        if VALID_KEY_REGEX.match(key):
            data[key] = val.strip()
    return data


def main():
    # Load the entire PuTTY log
    try:
        with open('putty.log', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().replace('\r', '')
    except FileNotFoundError:
        print("Error: 'putty.log' not found. Please save your PuTTY log in the script folder.")
        return

    # Split into frames by blank line separators
    raw_frames = [f for f in content.split('\n\n') if f.strip()]
    if not raw_frames:
        print("No frames found in the log.")
        return

    # Find first frame containing 'V'
    voltage = None
    for frame in raw_frames:
        parsed = parse_vedirect_block(frame)
        if 'V' in parsed:
            try:
                raw_mv = int(parsed['V'])
                voltage = raw_mv / 1000.0  # convert mV to V
            except ValueError:
                print(f"Invalid raw voltage '{parsed['V']}'")
            break

    if voltage is not None:
        print(f"Voltage: {voltage:.3f} V")
    else:
        print("Voltage ('V') not found in any frame.")
        print("Available keys in frames:")
        for i, frame in enumerate(raw_frames[:3], 1):
            parsed = parse_vedirect_block(frame)
            print(f" Frame {i}: {sorted(parsed.keys())}")

if __name__ == '__main__':
    main()
