import pandas as pd
import os

file_path = r"d:\01_Projects\OpenSource\neural-nexus\Herb modelling example data.xlsx"

if os.path.exists(file_path):
    print(f"Reading {file_path}...")
    try:
        df = pd.read_excel(file_path, nrows=5)
        print("Columns:", df.columns.tolist())
        print("\nFirst 5 rows:")
        print(df.to_string())
    except Exception as e:
        print(f"Error reading Excel: {e}")
else:
    print(f"File not found: {file_path}")
