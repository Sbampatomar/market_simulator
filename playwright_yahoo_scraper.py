# playwright_yahoo_scraper.py

import asyncio
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

OUTPUT_FOLDER = Path("data")
OUTPUT_FOLDER.mkdir(exist_ok=True)

def parse_euro_float(txt):
    """Parses numbers like '2,63' to 2.63, and '61.132.029' to 61132029"""
    return float(txt.replace(",", "."))

# Helper to convert datetime to UNIX timestamp
def to_unix_timestamp(date_obj):
    return int(datetime(date_obj.year, date_obj.month, date_obj.day, tzinfo=timezone.utc).timestamp())

async def fetch_yahoo_table(symbol: str):
    # Set the full historical period range
    start_date = datetime(2000, 1, 1)  # adjust if needed
    end_date = datetime.today()

    period1 = to_unix_timestamp(start_date)
    period2 = to_unix_timestamp(end_date)

    url = f"https://finance.yahoo.com/quote/{symbol}/history?frequency=1d&filter=history&period1={period1}&period2={period2}"
    output_file = OUTPUT_FOLDER / f"{symbol}.csv"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"[playwright] Opening page for {symbol}...")
        print(f"[playwright] URL: {url}")
        await page.goto(url)

        # Accept cookies
        try:
            accept_button = page.locator("button:has-text('Accetta tutto')")
            await accept_button.wait_for(timeout=5000)
            await accept_button.click()
            print("[playwright] Cookie consent accepted.")
        except:
            print("[playwright] No cookie popup detected or already accepted.")

        # Wait for the table to load
        try:
            await page.wait_for_selector("table tr th:has-text('Date')", timeout=15000)
            print("[playwright] Table loaded.")
        except:
            print("[playwright] Table did not load in time.")
            return

        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            print(f"[playwright] No table found for {symbol}.")
            return

        rows = table.find_all("tr")
        records = []

        for row in rows:
            cols = row.find_all("td")
            if len(cols) == 2 and "Dividend" in cols[1].text:
                # Dividend row
                try:
                    date = pd.to_datetime(cols[0].text.strip())
                    dividend = parse_euro_float(cols[1].text.strip().replace("Dividend", "").strip())
                    records.append({"Date": date, "Dividend": dividend})
                except:
                    continue
            elif len(cols) >= 6:
                try:
                    date = pd.to_datetime(cols[0].text.strip())
                    open_ = parse_euro_float(cols[1].text)
                    high = parse_euro_float(cols[2].text)
                    low = parse_euro_float(cols[3].text)
                    close = parse_euro_float(cols[4].text)
                    adj_close = parse_euro_float(cols[5].text)
                    volume = int(cols[6].text.replace(".", "").replace(",", ""))
                    records.append({
                        "Date": date,
                        "Open": open_, "High": high, "Low": low,
                        "Close": close, "Adj Close": adj_close,
                        "Volume": volume, "Dividend": 0.0
                    })
                except:
                    continue

        if not records:
            print(f"[playwright] No usable data extracted for {symbol}.")
            return

        df = pd.DataFrame(records)
        df = df.groupby("Date").first().sort_index()
        df.to_csv(output_file)
        print(f"[playwright] ✅ Saved data for {symbol} to {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python playwright_yahoo_scraper.py SYMBOL")
        print("Example: python playwright_yahoo_scraper.py ISP.MI")
    else:
        asyncio.run(fetch_yahoo_table(sys.argv[1]))
