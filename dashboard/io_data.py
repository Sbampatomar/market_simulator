import pandas as pd
from pathlib import Path
# from .config import DATA_DIR, INPUT_DIR, KPI_FILE
from dashboard.config import DATA_DIR, INPUT_DIR, KPI_FILE

def load_data():
    daily_df = pd.read_csv(DATA_DIR / "daily_portfolio.csv", parse_dates=["date"], index_col="date")
    monthly_df = pd.read_csv(DATA_DIR / "monthly_stats.csv", parse_dates=["month"], index_col="month")
    dividends_df = pd.read_csv(DATA_DIR / "monthly_dividends.csv", index_col=0)
    dividends_df.index = pd.to_datetime(dividends_df.index)
    assert isinstance(dividends_df.index, pd.DatetimeIndex), "Index is not datetime!"
    metadata_df = pd.read_csv(INPUT_DIR / "symbol_metadata.csv")
    return daily_df, monthly_df, dividends_df, metadata_df

def load_kpis():
    lines = Path(KPI_FILE).read_text(encoding="utf-8").splitlines()
    kpis = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            kpis[k.strip()] = v.strip()
    return kpis