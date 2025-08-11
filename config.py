# config.py
from decimal import Decimal
import pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parent
DATA_FOLDER = ROOT_DIR / 'data'
INPUT_FOLDER = ROOT_DIR / 'input'
OUTPUT_FOLDER = ROOT_DIR / 'output'
OUTPUT_FOLDER.mkdir(exist_ok=True, parents=True)

TRANSACTION_FILE = INPUT_FOLDER / 'transactions.csv'
INVESTMENT_PLAN_FILE = INPUT_FOLDER / 'investment_plan.csv'
DIVIDEND_TARGET_FILE = INPUT_FOLDER / 'dividend_reinvestment_targets.csv'
SYMBOL_METADATA_FILE = INPUT_FOLDER / 'symbol_metadata.csv'

START_DATE = '2025-07-25'
END_DATE   = '2025-08-12'

TAX_RATE_DEFAULT = Decimal("0.26")
REINVESTMENT_THRESHOLD = Decimal("250")
ENABLE_MONTHLY_REINVESTMENT = True
BROKER_FEE = Decimal("5.00")  # fallback default
DIVIDEND_REINVESTMENT_MODE = 'custom'

TAX_RATES = {
    'Germany': Decimal("0.374"),
    'Portugal': Decimal("0.39"),
    'Spain': Decimal("0.30"),
    'Switzerland': Decimal("0.46"),
    'United Kingdom': Decimal("0.26"),
    'Sweden': Decimal("0.41"),
    'Denmark': Decimal("0.38"),
    'France': Decimal("0.26"),
    'Belgium': Decimal("0.41"),
    'Austria': Decimal("0.385"),
    'Ireland': Decimal("0.36"),
    'Norway': Decimal("0.36"),
    'Netherlands': Decimal("0.26"),
    'Italy': Decimal("0.26"),
    'USA': Decimal("0.26"),
    'Unknown': Decimal("0.26")
}

BROKER_FEES = {
    'Italy': Decimal("5.00"),
    'Germany': Decimal("9.00"),
    'France': Decimal("7.00"),
    'Spain': Decimal("6.50"),
    'Portugal': Decimal("6.00"),
    'USA': Decimal("5.00"),
    'Unknown': Decimal("5.00")
}