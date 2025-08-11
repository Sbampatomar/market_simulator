# pw_yahoo_scraper_update.py

import asyncio
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

DATA_FOLDER = Path("data")


def parse_euro_float(txt):
    return float(txt.replace(",", "."))

def get_yesterday_date():
    return datetime.today().date() - timedelta(days=1)

# Helper: convert date to UNIX timestamp in seconds
def to_unix_timestamp(date_obj):
    return int(datetime(date_obj.year, date_obj.month, date_obj.day, tzinfo=timezone.utc).timestamp())

async def fetch_updates(symbol: str, start_date: datetime):
    period1 = to_unix_timestamp(start_date + timedelta(days=1))  # day after last available
    period2 = to_unix_timestamp(datetime.today().date())         # today at 00:00

    #url = f"https://finance.yahoo.com/quote/{symbol}/history?frequency=1d&filter=history"
    url = f"https://finance.yahoo.com/quote/{symbol}/history?frequency=1d&filter=history&period1={period1}&period2={period2}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"[playwright] Opening Yahoo Finance page for {symbol}...")
        print(f"url: {url}")
        await page.goto(url)
        await page.wait_for_timeout(1000)  # Extra wait after full page load
        await page.mouse.wheel(0, 1000)
        await page.wait_for_timeout(2000)  # Extra wait after full page load

        try:
            accept_button = page.locator("button:has-text('Accetta tutto')")
            await accept_button.wait_for(timeout=5000)
            await accept_button.click()
            print("[playwright] Cookie popup accepted.")
        except:
            print("[playwright] Cookie popup not found or already handled.")

        try:
            await page.wait_for_selector("table", timeout=15000)
        except:
            print("[playwright] Table failed to load.")
            return []

        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            print("[playwright] Table not found.")
            return []

        new_rows = []
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 2 and "Dividend" in cols[1].text:
                try:
                    date = pd.to_datetime(cols[0].text.strip())  # Don't convert to .date()
                    if date <= start_date:
                        continue
                    dividend = parse_euro_float(cols[1].text.strip().replace("Dividend", "").strip())
                    new_rows.append({"Date": date, "Dividend": dividend})
                except:
                    continue
            elif len(cols) >= 6:
                try:
                    date = pd.to_datetime(cols[0].text.strip()).date()
                    if date <= start_date:
                        continue
                    open_ = parse_euro_float(cols[1].text)
                    high = parse_euro_float(cols[2].text)
                    low = parse_euro_float(cols[3].text)
                    close = parse_euro_float(cols[4].text)
                    adj_close = parse_euro_float(cols[5].text)
                    volume = int(cols[6].text.replace(".", "").replace(",", ""))
                    new_rows.append({
                        "Date": date,
                        "Open": open_, "High": high, "Low": low,
                        "Close": close, "Adj Close": adj_close,
                        "Volume": volume, "Dividend": 0.0
                    })
                except:
                    continue

        return new_rows


async def main(symbol: str):
    file_path = DATA_FOLDER / f"{symbol}.csv"
    if not file_path.exists():
        print(f"[error] CSV file for {symbol} not found in /data folder.")
        return

    df_existing = pd.read_csv(file_path, parse_dates=["Date"])
    last_date = df_existing["Date"].max().date()
    print(f"[update] Last available date for {symbol}: {last_date}")

    yesterday = get_yesterday_date()
    if last_date >= yesterday:
        print("[update] Data already up to date.")
        return

    new_data = await fetch_updates(symbol, last_date)
    if not new_data:
        print("[update] No new data found.")
        return

    df_new = pd.DataFrame(new_data)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined["Date"] = pd.to_datetime(df_combined["Date"])  # <- Normalize here
    df_combined = df_combined.drop_duplicates(subset="Date").sort_values("Date")
    df_combined.to_csv(file_path, index=False)
    print(f"[update] ✅ Updated CSV for {symbol} with {len(df_new)} new rows.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python pw_yahoo_scraper_update.py SYMBOL")
        print("Example: python pw_yahoo_scraper_update.py LDO.MI")
    else:
        asyncio.run(main(sys.argv[1]))
