import asyncio
import pandas as pd
import os
import sys
import json
from app.services.gemini_service import gemini_service
from app.logging_utils import ai_logger

# Set output to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

async def debug_extraction():
    file_path = r"d:\01_Projects\OpenSource\neural-nexus\Herb modelling example data.xlsx"
    
    if not os.path.exists(file_path):
        print("File not found.")
        return

    print(f"Loading {file_path}...")
    df = pd.read_excel(file_path)
    
    # Cleaning as per excel_service.py
    df = df.dropna(how='all')
    df = df[df.notna().sum(axis=1) >= 3]
    df = df.reset_index(drop=True)
    
    print(f"Cleaned data has {len(df)} rows.")
    
    # Take the first batch (rows 0-5)
    batch = df.iloc[0:5]
    text_content = batch.to_string(index=False)
    
    print("\n--- BATCH TEXT START ---")
    print(text_content)
    print("--- BATCH TEXT END ---\n")
    
    print("Calling Gemini...")
    extracted = await gemini_service.extract_scientific_entities(text_content)
    
    print("\n--- GEMINI RESPONSE ---")
    print(json.dumps(extracted, indent=2))
    print("------------------------\n")

if __name__ == "__main__":
    asyncio.run(debug_extraction())
