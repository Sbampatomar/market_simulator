# --- bootstrap import path so "dashboard" is importable when run by panel ---
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ---------------------------------------------------------------------------

from pathlib import Path
import pandas as pd
import panel as pn
pn.extension('plotly', 'tabulator')

from panel.widgets import FileDownload

from dashboard.io_data import load_data, load_kpis
from dashboard.state import DashboardState
from dashboard.widgets import make_widgets
from dashboard.layout import build_layout
from dashboard.export_pdf import generate_dashboard_pdf
from dashboard.config import KPI_GROUPS
from dashboard.data_access import load_monthly_dividends_tables  # <— canonical monthly sources


# -------- utilities --------
def _ensure_datetime_index(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """
    Ensure df has a DatetimeIndex. If date_col exists, set it as index.
    """
    if df is None or df.empty:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.set_index(date_col).sort_index()
        else:
            # last resort: try to coerce current index
            try:
                df.index = pd.to_datetime(df.index, errors="coerce")
                df = df.sort_index()
            except Exception:
                pass
    # hard assert so we fail fast if something is off
    assert isinstance(df.index, pd.DatetimeIndex), "Index is not datetime!"
    return df


def _month_name_map():
    return {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }


def _prepare_monthly_structures():
    """
    Use dashboard.data_access.load_monthly_dividends_tables() as the single source of truth.
    Returns:
      - monthly_total_tidy: columns [month (timestamp), value]
      - monthly_by_symbol_wide: index month (timestamp), columns = symbols, values = dividend_net
      - monthly_by_symbol_tidy: columns [month (timestamp), symbol, value]
      - calendar_wide: index=year, columns=1..12 (months), values = dividend totals (float)
      - calendar_tidy: columns [year, month, value, month_name]
    """
    monthly_total, monthly_by_symbol, calendar_df = load_monthly_dividends_tables()

    # ------- monthly_total (tidy: month, value) -------
    # Expect columns ["year","month","dividend_net"]
    if not monthly_total.empty:
        mt = monthly_total.copy()
        mt["month_ts"] = pd.to_datetime(
            mt["year"].astype(int).astype(str) + "-" + mt["month"].astype(int).astype(str) + "-01",
            errors="coerce"
        )
        monthly_total_tidy = mt[["month_ts", "dividend_net"]].rename(
            columns={"month_ts": "month", "dividend_net": "value"}
        ).sort_values("month")
    else:
        monthly_total_tidy = pd.DataFrame(columns=["month", "value"])

    # ------- monthly_by_symbol (wide + tidy) -------
    # Expect columns ["year","month","symbol","dividend_net"] (may be empty if no symbol info)
    if isinstance(monthly_by_symbol, pd.DataFrame) and not monthly_by_symbol.empty:
        mbs = monthly_by_symbol.copy()
        mbs["month_ts"] = pd.to_datetime(
            mbs["year"].astype(int).astype(str) + "-" + mbs["month"].astype(int).astype(str) + "-01",
            errors="coerce"
        )
        monthly_by_symbol_tidy = mbs[["month_ts", "symbol", "dividend_net"]].rename(
            columns={"month_ts": "month", "dividend_net": "value"}
        ).dropna(subset=["month"]).sort_values(["month", "symbol"])

        monthly_by_symbol_wide = monthly_by_symbol_tidy.pivot_table(
            index="month", columns="symbol", values="value", aggfunc="sum", fill_value=0.0
        ).sort_index()
    else:
        monthly_by_symbol_tidy = pd.DataFrame(columns=["month", "symbol", "value"])
        monthly_by_symbol_wide = pd.DataFrame()

    # ------- calendar (wide + tidy) -------
    # load_monthly_dividends_tables() returns calendar_df with Year×Month already laid out
    if isinstance(calendar_df, pd.DataFrame) and not calendar_df.empty:
        # calendar_df is returned as tidy with columns: ["year", 1..12] OR already wide.
        # We normalize to: index=year, columns=1..12
        if "year" in calendar_df.columns:
            cal_wide = calendar_df.set_index("year")
        else:
            cal_wide = calendar_df.copy()

        # Ensure months 1..12 exist
        for m in range(1, 13):
            if m not in cal_wide.columns:
                cal_wide[m] = 0.0
        cal_wide = cal_wide.reindex(columns=sorted(cal_wide.columns)).sort_index()

        # Tidy version for some heatmap factories
        cal_tidy = cal_wide.copy()
        cal_tidy = cal_tidy.reset_index().melt(id_vars="year", var_name="month", value_name="value")
        cal_tidy["month_name"] = cal_tidy["month"].map(_month_name_map())
    else:
        cal_wide = pd.DataFrame()
        cal_tidy = pd.DataFrame(columns=["year", "month", "value", "month_name"])

    return monthly_total_tidy, monthly_by_symbol_wide, monthly_by_symbol_tidy, cal_wide, cal_tidy


def initialize_full_history(state: DashboardState):
    """
    Create *_full copies that are never mutated by UI filters.
    Also ensures a monthly-by-symbol matrix exists as *_full if we can derive it.
    """
    # ---------------- 1) Daily full ----------------
    if getattr(state, "daily_df_full", None) is None and isinstance(state.daily_df, pd.DataFrame):
        state.daily_df_full = state.daily_df.copy()
    if getattr(state, "daily_df_full", None) is None:
        state.daily_df_full = pd.DataFrame()

    # ---------------- 2) Monthly dividends by symbol (full) ----------------
    # If we already have a wide (matrix) version from the loader, freeze it.
    if getattr(state, "monthly_div_by_symbol_full", None) is None:
        if isinstance(state.monthly_div_by_symbol, pd.DataFrame) and not state.monthly_div_by_symbol.empty:
            state.monthly_div_by_symbol_full = state.monthly_div_by_symbol.copy()
        else:
            # As a fallback, try to infer from daily_df_full if it contains dividend columns per symbol
            mdbs_full = pd.DataFrame()
            daily = getattr(state, "daily_df_full", pd.DataFrame())
            if isinstance(daily, pd.DataFrame) and not daily.empty:
                div_cols = [c for c in daily.columns if "div" in c.lower()]
                if div_cols:
                    tmp = daily[div_cols].fillna(0.0).copy()
                    if not isinstance(tmp.index, pd.DatetimeIndex):
                        tmp.index = pd.to_datetime(tmp.index, errors="coerce")
                    tmp["month"] = tmp.index.to_period("M").to_timestamp()
                    mdbs_full = tmp.groupby("month").sum()
                    mdbs_full.columns = [c.replace("div_", "").replace("DIV_", "") for c in mdbs_full.columns]
            state.monthly_div_by_symbol_full = mdbs_full

    if getattr(state, "monthly_div_by_symbol_full", None) is None:
        state.monthly_div_by_symbol_full = pd.DataFrame()

    # Debug spans
    print(
        "daily_df_full span:",
        None if state.daily_df_full.empty else (state.daily_df_full.index.min(), state.daily_df_full.index.max())
    )
    print(
        "monthly_div_by_symbol_full span:",
        None if state.monthly_div_by_symbol_full.empty else (state.monthly_div_by_symbol_full.index.min(), state.monthly_div_by_symbol_full.index.max())
    )


def make_app():
    # ---------------- Load core data ----------------
    daily_df, monthly_df, dividends_df, metadata_df = load_data()
    kpis = load_kpis()

    # Enforce datetime index on the main timeseries you chart from
    if isinstance(daily_df, pd.DataFrame) and not daily_df.empty:
        daily_df = _ensure_datetime_index(daily_df, "date")
    if isinstance(monthly_df, pd.DataFrame) and not monthly_df.empty:
        # Monthly df may or may not be indexed by date; keep as is if not needed for charts
        try:
            monthly_df = _ensure_datetime_index(monthly_df, "date")
        except Exception:
            pass
    if isinstance(dividends_df, pd.DataFrame) and not dividends_df.empty:
        try:
            dividends_df = _ensure_datetime_index(dividends_df, "date")
        except Exception:
            pass

    # ---------------- Canonical monthly dividend sources ----------------
    (
        monthly_total_tidy,
        monthly_by_symbol_wide,
        monthly_by_symbol_tidy,
        calendar_wide,
        calendar_tidy,
    ) = _prepare_monthly_structures()

    # ---------------- Create state ----------------
    state = DashboardState(
        daily_df=daily_df,
        monthly_df=monthly_df,
        dividends_df=dividends_df,
        metadata_df=metadata_df,
        kpis=kpis
    )
    state.set_defaults()

    # Attach the prepared monthly/calc artifacts so plots can consume them
    # Wide matrix (index=month, columns=symbol) for symbol heatmaps
    state.monthly_div_by_symbol = monthly_by_symbol_wide

    # Tidy variants if your plot factories expect long format
    state.monthly_div_by_symbol_tidy = monthly_by_symbol_tidy           # [month, symbol, value]
    state.monthly_dividends_total = monthly_total_tidy                   # [month, value]
    state.monthly_dividends_calendar_wide = calendar_wide               # index=year, cols=1..12
    state.monthly_dividends_calendar_tidy = calendar_tidy               # [year, month, value, month_name]

    # Freeze *_full copies
    initialize_full_history(state)

    # ---------------- Widgets & layout ----------------
    widgets = make_widgets(state)
    template, chart_specs = build_layout(state, widgets)

    # ---------------- PDF export button ----------------
    download_pdf_button = FileDownload(
        label="Download PDF Report",
        filename="market_dashboard.pdf",
        callback=lambda: generate_dashboard_pdf(state, chart_specs, KPI_GROUPS, state.kpis),
        button_type="primary"
    )

    # Sidebar structure: ["## Filters", date_range, Spacer, heatmap_palette, Spacer, (button slot), Spacer, view_mode_toggle, Spacer, symbol_selector]
    # The button slot is index 5 (placeholder in layout.py).
    template.sidebar[5] = download_pdf_button

    return template


dashboard = make_app()
dashboard.servable()
