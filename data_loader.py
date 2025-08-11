# data_loader.py
import pandas as pd
import os
from config import DATA_FOLDER, SYMBOL_METADATA_FILE, DIVIDEND_TARGET_FILE, DIVIDEND_REINVESTMENT_MODE
import logging
from decimal import Decimal

def load_price_data():
    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv') and f not in {
        'transactions.csv', 'investment_plan.csv', 'dividend_reinvestment_targets.csv', 'symbol_metadata.csv'
    }]
    data = {}
    for f in files:
        symbol = f.replace('.csv', '')
        try:
            df = pd.read_csv(DATA_FOLDER / f, parse_dates=['Date'], index_col='Date').sort_index()
            for col in ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'Dividend']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            data[symbol] = df
            logging.info(f"Loaded price data for {symbol} ({len(df)} rows)")
        except Exception as e:
            logging.warning(f"Could not load {f}: {e}")
    return data

def load_symbol_metadata():
    if not SYMBOL_METADATA_FILE.exists():
        logging.warning("Symbol metadata file not found.")
        return pd.DataFrame(columns=['symbol', 'sector', 'country']).set_index('symbol')
    df = pd.read_csv(SYMBOL_METADATA_FILE)
    df = df.dropna(subset=['symbol'])
    df['sector'] = df['sector'].fillna('Unknown')
    df['country'] = df['country'].fillna('Unknown')
    logging.info(f"Loaded symbol metadata ({len(df)} symbols)")
    return df.set_index('symbol')

def load_reinvestment_targets():
    if DIVIDEND_REINVESTMENT_MODE != 'custom':
        return {}

    if not DIVIDEND_TARGET_FILE.exists():
        logging.warning("Dividend reinvestment file not found.")
        return {}

    df = pd.read_csv(DIVIDEND_TARGET_FILE)

    if df.empty or 'symbol' not in df.columns or 'weight' not in df.columns:
        logging.warning("Dividend reinvestment file is empty or missing required columns.")
        return {}

    df = df.dropna(subset=['symbol', 'weight'])
    if df.empty:
        logging.warning("Dividend reinvestment file contains no valid rows.")
        return {}

    weights = df.set_index('symbol')['weight'].to_dict()
    total = sum(weights.values())
    if total == 0:
        logging.warning("Total weight in dividend reinvestment targets is zero.")
        return {}

    normalized = {k: Decimal(str(v / total)) for k, v in weights.items()}
    logging.info(f"Loaded reinvestment targets: {normalized}")
    return normalized