# --- bootstrap import path so "dashboard" is importable when run by panel ---
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ---------------------------------------------------------------------------

import pandas as pd
from pathlib import Path

import panel as pn
pn.extension('plotly', 'tabulator')

from dashboard.io_data import load_data, load_kpis
from dashboard.state import DashboardState
from dashboard.widgets import make_widgets
from dashboard.layout import build_layout
from dashboard.export_pdf import generate_dashboard_pdf
from dashboard.config import KPI_GROUPS

from panel.widgets import FileDownload


def initialize_full_history(state):
    """
    Create *_full copies that are never mutated by UI filters.
    Also ensures a monthly-by-symbol matrix exists as *_full if we can derive it.
    """

    # ---------------- 1) Daily full ----------------
    if getattr(state, "daily_df_full", None) is None and getattr(state, "daily_df", None) is not None:
        state.daily_df_full = state.daily_df.copy()

    # ---------------- 2) Monthly dividends by symbol (full) ----------------
    if getattr(state, "monthly_div_by_symbol_full", None) is None:
        mdbs = getattr(state, "monthly_div_by_symbol", None)

        if isinstance(mdbs, pd.DataFrame) and not mdbs.empty:
            # Already have the monthly matrix -> freeze a full copy
            state.monthly_div_by_symbol_full = mdbs.copy()
        else:
            # Prefer the widest daily df available (full if present and non-empty, else partial)
            daily_full = getattr(state, "daily_df_full", None)
            daily_part = getattr(state, "daily_df", None)

            if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
                daily = daily_full
            else:
                daily = daily_part if isinstance(daily_part, pd.DataFrame) else None

            if isinstance(daily, pd.DataFrame) and not daily.empty:
                div_cols = [c for c in daily.columns if "div" in c.lower()]
                if div_cols:
                    tmp = daily[div_cols].fillna(0.0).copy()
                    # ensure DatetimeIndex at month start
                    if not isinstance(tmp.index, pd.DatetimeIndex):
                        tmp.index = pd.to_datetime(tmp.index)
                    tmp["month"] = tmp.index.to_period("M").to_timestamp()
                    mdbs_full = tmp.groupby("month").sum()
                    # normalize column names: drop "div_" prefix if present
                    mdbs_full.columns = [c.replace("div_", "").replace("DIV_", "") for c in mdbs_full.columns]
                    state.monthly_div_by_symbol_full = mdbs_full

    # ---------------- 3) Optional: load from file if you persist it ----------------
    if getattr(state, "monthly_div_by_symbol_full", None) is None:
        monthly_file = Path("output") / "monthly_dividends_by_symbol.csv"
        if monthly_file.exists():
            m = pd.read_csv(monthly_file, index_col=0)
            try:
                m.index = pd.to_datetime(m.index).to_period("M").to_timestamp()
            except Exception:
                pass
            state.monthly_div_by_symbol_full = m

    # ---------------- 4) Guarantee attributes exist ----------------
    if getattr(state, "daily_df_full", None) is None:
        state.daily_df_full = pd.DataFrame()
    if getattr(state, "monthly_div_by_symbol_full", None) is None:
        state.monthly_div_by_symbol_full = pd.DataFrame()

    print("daily_df_full span:", 
      None if state.daily_df_full.empty else (state.daily_df_full.index.min(), state.daily_df_full.index.max()))
    print("monthly_div_by_symbol_full span:", 
        None if state.monthly_div_by_symbol_full.empty else (state.monthly_div_by_symbol_full.index.min(), state.monthly_div_by_symbol_full.index.max()))


def make_app():
    # Carrega dados do disco
    daily_df, monthly_df, dividends_df, metadata_df = load_data()
    kpis = load_kpis()

    # Cria o state
    state = DashboardState(
        daily_df=daily_df,
        monthly_df=monthly_df,
        dividends_df=dividends_df,
        metadata_df=metadata_df,
        kpis=kpis
    )
    state.set_defaults()

    # Congela cópias "full" que não serão afetadas por filtros da UI
    initialize_full_history(state)

    # Widgets e layout
    widgets = make_widgets(state)
    template, chart_specs = build_layout(state, widgets)

    # Botão PDF
    download_pdf_button = FileDownload(
        label="Download PDF Report",
        filename="market_dashboard.pdf",
        callback=lambda: generate_dashboard_pdf(state, chart_specs, KPI_GROUPS, state.kpis),
        button_type="primary"
    )

    # Sidebar structure: ["## Filters", date_range, Spacer, heatmap_palette, Spacer, (button slot), Spacer, view_mode_toggle, Spacer, symbol_selector]
    # O slot do botão é o índice 5 (placeholder em layout.py).
    template.sidebar[5] = download_pdf_button

    return template


dashboard = make_app()
dashboard.servable()
