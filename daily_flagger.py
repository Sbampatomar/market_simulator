# simulation/daily_flagger.py
import pandas as pd

def apply_dividend_flags(daily_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 'dividend_event' (0/1) and 'daily_dividend_net' to daily_df.
    If a 'comment' column exists, append '; dividend' on event days.
    Assumes daily_df has a 'date' column (or DatetimeIndex).
    """
    if daily_df is None or daily_df.empty:
        return daily_df.copy()

    df = daily_df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
        df = df.set_index("date")
    elif not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
        df = df.sort_index()

    # default zeros
    df["daily_dividend_net"] = 0.0
    df["dividend_event"] = 0

    if events_df is not None and not events_df.empty:
        e = events_df.copy()
        e["date"] = pd.to_datetime(e["date"], errors="coerce")
        per_day = e.groupby(e["date"].dt.normalize())["dividend_net"].sum()
        # align to daily index
        aligned = per_day.reindex(df.index, fill_value=0.0)
        df["daily_dividend_net"] = aligned.values
        df["dividend_event"] = (df["daily_dividend_net"] > 0).astype(int)

        if "comment" in df.columns:
            df.loc[df["dividend_event"] == 1, "comment"] = (
                df.loc[df["dividend_event"] == 1, "comment"].fillna("").astype(str)
                .apply(lambda s: (s + "; dividend") if "dividend" not in s.lower() else s)
            )

    return df.reset_index()