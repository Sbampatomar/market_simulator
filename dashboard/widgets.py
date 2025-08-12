import panel as pn
from dashboard.config import CRAMERI

def make_widgets(state):
    # Date range
    date_range = pn.widgets.DateRangeSlider(
        name='Date Range',
        start=state.daily_df.index.min(),
        end=state.daily_df.index.max(),
        value=state.date_range
    )
    date_range.param.watch(lambda e: setattr(state, "date_range", e.new), 'value')

    # Heatmap palette (robust defaults)
    palette_label_map = {name.capitalize(): name for name in (CRAMERI or [])}
    if palette_label_map:
        palette_values = list(palette_label_map.values())
        default_palette = "imola" if "imola" in palette_values else palette_values[0]
    else:
        palette_label_map = {"Viridis": "viridis"}
        palette_values = ["viridis"]
        default_palette = "viridis"

    heatmap_palette = pn.widgets.Select(
        name="Heatmap Palette (Scientific - Crameri)",
        options=palette_label_map,
        value=default_palette
    )
    state.param['heatmap_palette'].objects = palette_values
    state.heatmap_palette = default_palette
    heatmap_palette.param.watch(lambda e: setattr(state, "heatmap_palette", e.new), 'value')

    # Symbols
    symbol_selector = pn.widgets.CheckBoxGroup(
        name="Select Symbols",
        options=state.param['symbols'].objects,
        value=state.symbols
    )
    symbol_selector.param.watch(lambda e: setattr(state, 'symbols', e.new), 'value')

    # NEW: Daily/Monthly toggle for the "Invested vs Value" chart
    view_mode_toggle = pn.widgets.RadioButtonGroup(
        name="Portfolio View Mode",
        options=["daily", "monthly"],
        value="daily",
        button_type="primary"
    )

    # Return all widgets (note: layout.py expects 4 items now)
    return date_range, heatmap_palette, symbol_selector, view_mode_toggle
