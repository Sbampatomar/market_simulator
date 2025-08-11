# batch_yahoo_scraper.py

import asyncio
import pandas as pd
import subprocess

CSV_FILE = "tracked_symbols.csv"

def read_symbols():
    df = pd.read_csv(CSV_FILE)
    return df["symbol"].dropna().unique().tolist()

async def run_scraper_for(symbol):
    print(f"\n🔄 Fetching data for {symbol}")
    process = await asyncio.create_subprocess_exec(
        "python", "yahoo_html_scraper_logged_in.py", symbol
    )
    await process.communicate()

async def main():
    symbols = read_symbols()
    for symbol in symbols:
        await run_scraper_for(symbol)

if __name__ == "__main__":
    asyncio.run(main())
