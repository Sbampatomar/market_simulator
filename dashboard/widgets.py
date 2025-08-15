# dashboard/widgets.py
import panel as pn
import pandas as pd
from dashboard.plots import heatmaps
import re

def _is_df_nonempty(obj) -> bool:
    return isinstance(obj, pd.DataFrame) and not obj.empty

def _normalize_unique_symbols(symbols):
    """Upper-case, strip, and keep only first occurrence (stable dedupe)."""
    out, seen = [], set()
    for s in symbols:
        if not isinstance(s, str):
            continue
        name = s.strip().upper()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out

def _infer_symbols_from_df(df: pd.DataFrame) -> list[str]:
    """
    Extract symbols from common per-symbol columns:

      qty_<SYM>, val_<SYM>, value_<SYM>, mv_<SYM>,
      market_value_<SYM>, position_value_<SYM>, holding_value_<SYM>, avg_price_<SYM>
      <SYM>_value, <SYM>_val, <SYM>_mv
      or columns that are exactly the ticker (e.g., ENI.MI)

    Excludes aggregates and metrics like total/portfolio/cash/invested/gain/fee/tax/etc.
    """
    candidates = set()

    # prefixes we WANT to strip to get the symbol
    strip_prefix = re.compile(r'^(qty_|val_|value_|mv_|market_value_|position_value_|holding_value_|avg_price_)',
                              re.I)
    # suffixes we WANT to strip to get the symbol
    strip_suffix = re.compile(r'(_qty|_val|_value|_mv)$', re.I)

    # columns we should IGNORE entirely (aggregates/metrics)
    exclude_prefixes = (
        "gain_", "realized_gain", "unrealized_gain", "portfolio_gain",
        "tax_", "fee_", "daily_fee", "cost_", "pnl_", "irr_", "return_",
        "div_", "avg_", "price_", "weighted_", "actions", "cash_", "cash",
    )
    exclude_contains = ("total_", "portfolio_", "cash", "invested", "drawdown")
    exclude_suffixes = ("_gain", "_tax", "_fee", "_pnl", "_irr", "_return", "_yield", "_price", "_avg")

    agg_exact = re.compile(r'^(total_)?(portfolio_)?value$', re.I)

    for col in df.columns:
        if not isinstance(col, str):
            continue
        lc = col.lower()

        # skip obvious aggregates/metrics
        if agg_exact.fullmatch(col):
            continue
        if lc.startswith(exclude_prefixes) or lc.endswith(exclude_suffixes) or any(t in lc for t in exclude_contains):
            continue

        sym = None
        if strip_prefix.match(col):
            sym = strip_prefix.sub("", col)
        elif strip_suffix.search(col):
            sym = strip_suffix.sub("", col)
        else:
            # Only accept "plain ticker columns" if they don't look like metrics
            if "." in col:
                sym = col

        if sym:
            # Require a dot and at least two letters to avoid junk
            if "." in sym and len(re.sub(r'[^A-Za-z]', "", sym)) >= 2:
                candidates.add(sym)

    # Normalize to canonical form and return
    return _normalize_unique_symbols(sorted(candidates))

def make_widgets(state):
    pn.extension()
    # --- Date range (unchanged) ---
    daily = getattr(state, "daily_df", None)
    if _is_df_nonempty(daily):
        idx_min = pd.to_datetime(daily.index.min()); idx_max = pd.to_datetime(daily.index.max())
    else:
        idx_max = pd.Timestamp.today().normalize(); idx_min = idx_max - pd.DateOffset(months=12)

    init_start = max(idx_min, idx_max - pd.DateOffset(months=12)); init_end = idx_max
    date_range = pn.widgets.DateRangeSlider(name="Period", start=idx_min, end=idx_max,
                                            value=(init_start, init_end), step=24*60*60*1000)
    if not hasattr(state, "date_range"):
        state.date_range = (init_start, init_end)
    date_range.param.watch(lambda e: setattr(state, "date_range",
                                             (pd.to_datetime(e.new[0]), pd.to_datetime(e.new[1]))), "value")

    # --- Palette ---
    palette_options = list(heatmaps.PALETTES.keys())
    default_palette = "Viridis" if "Viridis" in heatmaps.PALETTES else (palette_options[0] if palette_options else None)
    heatmap_palette = pn.widgets.Select(name="Color palette", options=palette_options, value=default_palette)

    # --- Symbols (prefer explicit, then fallbacks) ---
    symbols = (getattr(state, "available_symbols", []) or getattr(state, "all_symbols", []) or [])
    if not symbols:
        mdbs_full = getattr(state, "monthly_div_by_symbol_full", None)
        if _is_df_nonempty(mdbs_full):
            symbols = list(mdbs_full.columns)
    if not symbols:
        mdbs = getattr(state, "monthly_div_by_symbol", None)
        if _is_df_nonempty(mdbs):
            symbols = list(mdbs.columns)
    if not symbols:
        df = getattr(state, "daily_df_full", None)
        if not _is_df_nonempty(df):
            df = getattr(state, "daily_df", None)
        if _is_df_nonempty(df):
            symbols = _infer_symbols_from_df(df)

    # Normalize & dedupe robustly
    symbols = _normalize_unique_symbols(symbols)

    # Initial selection (normalized)
    prev = getattr(state, "selected_symbols", [])
    initial = [s for s in _normalize_unique_symbols(prev) if s in symbols]

    symbol_selector = pn.widgets.CheckBoxGroup(
        name="Symbols",
        options=symbols,
        value=initial,
        inline=False,
        sizing_mode="stretch_width",
        height=250,
    )

    # Initialize baseline (optionally “select all” if empty)
    if not hasattr(state, "selected_symbols"):
        if not symbol_selector.value and symbols:
            symbol_selector.value = list(symbol_selector.options)  # comment out if you don’t want select-all default
        state.selected_symbols = _normalize_unique_symbols(symbol_selector.value)

    # Keep state synced (normalized)
    symbol_selector.param.watch(lambda e: setattr(state, "selected_symbols",
                                                  _normalize_unique_symbols(e.new)), "value")

    # Convenience buttons
    select_all_btn = pn.widgets.Button(name="Select all", button_type="primary")
    clear_btn      = pn.widgets.Button(name="Clear",      button_type="warning")
    select_all_btn.on_click(lambda e: setattr(symbol_selector, "value", list(symbol_selector.options)))
    clear_btn.on_click(lambda e: setattr(symbol_selector, "value", []))

    symbols_panel = pn.Column(
        symbol_selector,
        pn.Row(select_all_btn, clear_btn, sizing_mode="stretch_width")
    )
    symbols_panel._checkbox = symbol_selector  # used by layout.py

    # --- View mode ---
    view_mode_toggle = pn.widgets.RadioButtonGroup(name="View mode",
                                                   options=["daily", "monthly"], value="daily",
                                                   button_type="primary")

    return (date_range, heatmap_palette, symbols_panel, view_mode_toggle)
