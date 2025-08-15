from pathlib import Path
import pandas as pd

def build_monthly_dividends(output_dir: Path):
    """
    Read output/dividends_events.csv and produce output/monthly_dividends.csv
    Columns: month,total,<SYMBOL_1>,<SYMBOL_2>,...
    month format: YYYY-MM
    """
    events_path = output_dir / "dividends_events.csv"
    out_path = output_dir / "monthly_dividends.csv"

    if not events_path.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("month,total\n", encoding="utf-8")
        return

    df = pd.read_csv(events_path, parse_dates=["date"])
    if df.empty:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("month,total\n", encoding="utf-8")
        return

    df["month"] = df["date"].dt.to_period("M").astype(str)  # "YYYY-MM"

    sym_pivot = (df.pivot_table(index="month", columns="symbol", values="dividend_net",
                                aggfunc="sum", fill_value=0.0)
                   .sort_index())

    total = sym_pivot.sum(axis=1).rename("total")
    result = pd.concat([total, sym_pivot], axis=1).reset_index()

    cols = ["month", "total"] + sorted([c for c in result.columns if c not in ("month","total")])
    result = result[cols]
    result.to_csv(out_path, index=False, float_format="%.2f")