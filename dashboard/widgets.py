# dashboard/widgets.py
# Cria os widgets e conecta seus valores ao "state" (date_range, selected_symbols).
# Retorna: (date_range, heatmap_palette, symbol_selector, view_mode_toggle)

import panel as pn
import pandas as pd
from dashboard.plots import heatmaps

def _detect_symbol_list(state):
    # Preferência: state.symbols (se você já popula isso no State)
    symbols = getattr(state, "symbols", None)
    if symbols:
        return list(symbols)

    # Tenta monthly_div_by_symbol
    mdbs = getattr(state, "monthly_div_by_symbol", None)
    if mdbs is not None and len(mdbs) > 0:
        return list(mdbs.columns)

    # Tenta daily_df por colunas qty_*
    daily = getattr(state, "daily_df", None)
    if daily is not None and len(daily) > 0:
        qty_cols = [c for c in daily.columns if c.startswith("qty_")]
        if qty_cols:
            return [c.replace("qty_", "") for c in qty_cols]

    return []

def make_widgets(state):
    pn.extension()

    # ---------------- Date range slider ----------------
    daily = getattr(state, "daily_df", None)
    if daily is not None and len(daily) > 0:
        idx_min = pd.to_datetime(daily.index.min())
        idx_max = pd.to_datetime(daily.index.max())
    else:
        idx_max = pd.Timestamp.today().normalize()
        idx_min = idx_max - pd.DateOffset(months=12)

    # valor inicial: últimos 12 meses (ou todo o período, se preferir)
    init_start = max(idx_min, idx_max - pd.DateOffset(months=12))
    init_end = idx_max

    date_range = pn.widgets.DateRangeSlider(
        name="Period",
        start=idx_min,
        end=idx_max,
        value=(init_start, init_end),
        step=24*60*60*1000,  # 1 dia em ms
    )

    # Sincroniza no state
    if not hasattr(state, "date_range"):
        state.date_range = (init_start, init_end)

    def _on_date_change(event):
        state.date_range = (pd.to_datetime(event.new[0]), pd.to_datetime(event.new[1]))

    date_range.param.watch(_on_date_change, "value")

    # ---------------- Palette Select ----------------
    palette_options = list(heatmaps.PALETTES.keys())
    default_palette = "Viridis" if "Viridis" in heatmaps.PALETTES else (palette_options[0] if palette_options else None)

    heatmap_palette = pn.widgets.Select(
        name="Color palette",
        options=palette_options,
        value=default_palette,
    )

    # ---------------- Symbols selector ----------------
    symbols = _detect_symbol_list(state)
    default_symbols = symbols[: min(8, len(symbols))] if symbols else []

    symbol_selector = pn.widgets.CheckButtonGroup(
        name="Symbols",
        options=symbols,
        value=default_symbols,
        button_type="default",
        orientation="vertical",
        sizing_mode="stretch_width",
    )

    # Propaga para o state
    if not hasattr(state, "selected_symbols"):
        state.selected_symbols = list(default_symbols)

    def _on_symbols_change(event):
        state.selected_symbols = list(event.new)

    symbol_selector.param.watch(_on_symbols_change, "value")

    # ---------------- View mode (overview charts) ----------------
    # Valores usados diretamente pelo módulo lines: "daily" ou "monthly"
    view_mode_toggle = pn.widgets.RadioButtonGroup(
        name="View mode",
        options=["daily", "monthly"],
        value="daily",
        button_type="primary"
    )

    return date_range, heatmap_palette, symbol_selector, view_mode_toggle
