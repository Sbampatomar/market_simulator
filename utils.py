# utils.py
import pandas as pd
from scipy.optimize import newton
from decimal import Decimal
from config import BROKER_FEE, BROKER_FEES

def align_to_trading_day(date, valid_days):
    valid_after = valid_days[valid_days >= date]
    return valid_after[0] if not valid_after.empty else pd.NaT

def calculate_drawdown(series):
    peak = series.cummax()
    drawdown = (series - peak) / peak
    return drawdown

def calculate_xirr(cash_flows):
    def xnpv(rate):
        return sum(cf / (1 + rate) ** ((d - cash_flows[0][0]).days / 365.0) for d, cf in cash_flows)
    try:
        return newton(xnpv, 0.1)
    except Exception:
        return None

def resolve_broker_fee(symbol, metadata, row=None):
    if row is not None:
        try:
            fee_val = row.get("fee")
            if pd.notna(fee_val):
                return Decimal(str(fee_val))
        except Exception:
            pass
    country = metadata.loc[symbol, "country"] if symbol in metadata.index else "Unknown"
    return BROKER_FEES.get(country, BROKER_FEE)
