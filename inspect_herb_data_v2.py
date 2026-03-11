import pandas as pd
import os
import sys

# Set output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

file_path = r"d:\01_Projects\OpenSource\neural-nexus\Herb modelling example data.xlsx"

if os.path.exists(file_path):
    print(f"Reading {file_path}...")
    try:
        # Load without headers first to see where data starts
        df = pd.read_excel(file_path, header=None, nrows=10)
        print("First 10 rows (Raw):")
        print(df.to_string())
    except Exception as e:
        print(f"Error reading Excel: {e}")
else:
    print(f"File not found: {file_path}")
