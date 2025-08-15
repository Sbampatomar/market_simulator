# dashboard/io_data.py
from pathlib import Path
import pandas as pd

OUTPUT = Path("output")

def _read_csv_if_exists(path: Path, parse_dates=None, index_col=None):
    try:
        if path.exists():
            return pd.read_csv(path, parse_dates=parse_dates, index_col=index_col)
    except Exception:
        pass
    return pd.DataFrame()

def _first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def load_data():
    """
    Returns: (daily_df, monthly_df, dividends_df, metadata_df)
      - daily_df: output/daily_portfolio.csv (index=date)
      - monthly_df: output/monthly_stats.csv (index=month)
      - dividends_df: output/dividends_events.csv (for inspection / tables)
      - metadata_df: symbol metadata if available (optional)
    """
    daily_df = _read_csv_if_exists(OUTPUT / "daily_portfolio.csv", parse_dates=["date"])
    if not daily_df.empty:
        if "date" in daily_df.columns:
            daily_df["date"] = pd.to_datetime(daily_df["date"], errors="coerce")
            daily_df = daily_df.set_index("date").sort_index()
        elif not isinstance(daily_df.index, pd.DatetimeIndex):
            daily_df.index = pd.to_datetime(daily_df.index, errors="coerce")
            daily_df = daily_df.sort_index()

    monthly_df = _read_csv_if_exists(OUTPUT / "monthly_stats.csv", parse_dates=["month"])
    if not monthly_df.empty:
        if "month" in monthly_df.columns:
            monthly_df["month"] = pd.to_datetime(monthly_df["month"], errors="coerce")
            monthly_df = monthly_df.set_index("month").sort_index()

    dividends_df = _read_csv_if_exists(OUTPUT / "dividends_events.csv", parse_dates=["date"])
    # keep dividends_df WITHOUT setting index; many tables like a flat df

    # Try to find metadata (optional)
    candidate_meta = _first_existing([
        Path("input") / "symbol_metadata.csv",
        OUTPUT / "symbol_metadata.csv",
        Path("symbol_metadata.csv"),
    ])
    metadata_df = pd.read_csv(candidate_meta) if candidate_meta else pd.DataFrame()

    return daily_df, monthly_df, dividends_df, metadata_df


def load_kpis():
    """
    Reads output_kpis.txt if present. Returns dict[str, str].
    Accepts 'Key: Value' per line.
    """
    path = OUTPUT / "output_kpis.txt"
    if not path.exists():
        return {}
    data = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data
