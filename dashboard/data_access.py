# dashboard/data_access.py
from pathlib import Path
import pandas as pd
import logging

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

def _read_csv_if_exists(path: Path, parse_dates=None):
    try:
        if path.exists():
            return pd.read_csv(path, parse_dates=parse_dates)
    except Exception as e:
        logging.warning(f"Failed reading {path}: {e}")
    return None

def load_monthly_dividends_tables():
    """
    Single source of truth for monthly dividend data used by heatmaps.

    Returns a tuple:
      (monthly_total, monthly_by_symbol, calendar_df)

    - monthly_total: tidy with columns ["year","month","dividend_net"]
    - monthly_by_symbol: tidy with columns ["year","month","symbol","dividend_net"]
    - calendar_df: wide with columns ["year", 1, 2, ..., 12]
    Prefers output/monthly_dividends.csv (month,total,<SYMBOLS...>).
    Falls back to dividends_events.csv, then to daily_portfolio.csv if necessary.
    """

    # 0) Preferred: single-file monthly wide
    monthly_wide = _read_csv_if_exists(OUTPUT / "monthly_dividends.csv")
    if isinstance(monthly_wide, pd.DataFrame) and not monthly_wide.empty and "month" in monthly_wide.columns:
        # monthly_wide columns: month,total,<SYMBOLS...>, month = "YYYY-MM"
        mw = monthly_wide.copy()

        # monthly_total tidy
        mt = mw[["month", "total"]].copy()
        mt["year"] = mt["month"].str.slice(0, 4).astype(int)
        mt["month"] = mt["month"].str.slice(5, 7).astype(int)
        monthly_total = mt[["year", "month", "total"]].rename(columns={"total": "dividend_net"})

        # monthly_by_symbol tidy
        symbol_cols = [c for c in mw.columns if c not in ("month", "total")]
        if symbol_cols:
            mbs = mw[["month"] + symbol_cols].melt(id_vars="month", var_name="symbol", value_name="dividend_net")
            mbs["year"] = mbs["month"].str.slice(0, 4).astype(int)
            mbs["month"] = mbs["month"].str.slice(5, 7).astype(int)
            monthly_by_symbol = mbs[["year", "month", "symbol", "dividend_net"]]
        else:
            monthly_by_symbol = pd.DataFrame(columns=["year", "month", "symbol", "dividend_net"])

        # calendar: year × month 1..12
        cal = monthly_total.pivot(index="year", columns="month", values="dividend_net").fillna(0.0)
        for m in range(1, 13):
            if m not in cal.columns:
                cal[m] = 0.0
        cal = cal.reindex(columns=sorted(cal.columns)).sort_index()
        calendar_df = cal.reset_index()

        return monthly_total, monthly_by_symbol, calendar_df

    # 1) Fallback: atomic events
    events = _read_csv_if_exists(OUTPUT / "dividends_events.csv", parse_dates=["date"])
    if isinstance(events, pd.DataFrame) and not events.empty and "date" in events.columns:
        e = events.copy()
        e["date"] = pd.to_datetime(e["date"], errors="coerce")
        e = e.dropna(subset=["date"])
        e["year"] = e["date"].dt.year
        e["month"] = e["date"].dt.month

        monthly_total = (e.groupby(["year", "month"], as_index=False)["dividend_net"]
                           .sum().sort_values(["year", "month"]))

        if "symbol" in e.columns and e["symbol"].notna().any():
            monthly_by_symbol = (e.dropna(subset=["symbol"])
                                   .groupby(["year", "month", "symbol"], as_index=False)["dividend_net"]
                                   .sum().sort_values(["year", "month", "symbol"]))
        else:
            monthly_by_symbol = pd.DataFrame(columns=["year", "month", "symbol", "dividend_net"])

        cal = monthly_total.pivot(index="year", columns="month", values="dividend_net").fillna(0.0)
        for m in range(1, 13):
            if m not in cal.columns:
                cal[m] = 0.0
        cal = cal.reindex(columns=sorted(cal.columns)).sort_index()
        calendar_df = cal.reset_index()

        return monthly_total, monthly_by_symbol, calendar_df

    # 2) Last resort: daily_portfolio
    daily = _read_csv_if_exists(OUTPUT / "daily_portfolio.csv", parse_dates=["date"])
    if isinstance(daily, pd.DataFrame) and not daily.empty:
        d = daily.copy()
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"])
        # try common column names that your simulator now writes
        candidates = ["daily_dividend_net", "dividend_net", "dividends"]
        divcol = next((c for c in candidates if c in d.columns), None)
        if divcol is None:
            logging.warning("daily_portfolio.csv has no dividend column; using zeros.")
            empty = pd.DataFrame(columns=["year", "month", "dividend_net"])
            return empty, pd.DataFrame(columns=["year","month","symbol","dividend_net"]), pd.DataFrame(columns=["year"] + list(range(1,13)))

        d["year"] = d["date"].dt.year
        d["month"] = d["date"].dt.month
        monthly_total = (d.groupby(["year","month"], as_index=False)[divcol]
                           .sum().rename(columns={divcol: "dividend_net"}))
        monthly_by_symbol = pd.DataFrame(columns=["year","month","symbol","dividend_net"])
        cal = monthly_total.pivot(index="year", columns="month", values="dividend_net").fillna(0.0)
        for m in range(1, 13):
            if m not in cal.columns:
                cal[m] = 0.0
        cal = cal.reindex(columns=sorted(cal.columns)).sort_index()
        calendar_df = cal.reset_index()
        return monthly_total, monthly_by_symbol, calendar_df

    # 3) Nothing available
    logging.warning("No suitable dividend sources found in /output.")
    return (
        pd.DataFrame(columns=["year","month","dividend_net"]),
        pd.DataFrame(columns=["year","month","symbol","dividend_net"]),
        pd.DataFrame(columns=["year"] + list(range(1,13))),
    )