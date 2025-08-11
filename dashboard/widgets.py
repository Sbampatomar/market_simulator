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

    # --- Heatmap palette: define allowed values, default, then sync state ---
    palette_label_map = {name.capitalize(): name for name in (CRAMERI or [])}
    if palette_label_map:
        palette_values = list(palette_label_map.values())
        default_palette = "imola" if "imola" in palette_values else palette_values[0]
    else:
        # Fallback if CRAMERI is empty
        palette_label_map = {"Viridis": "viridis"}
        palette_values = ["viridis"]
        default_palette = "viridis"

    heatmap_palette = pn.widgets.Select(
        name="Heatmap Palette (Scientific - Crameri)",
        options=palette_label_map,
        value=default_palette
    )

    # IMPORTANT: register allowed values on the Param selector BEFORE setting value
    state.param['heatmap_palette'].objects = palette_values
    state.heatmap_palette = default_palette  # assign a valid default

    # keep state in sync if user changes widget
    heatmap_palette.param.watch(lambda e: setattr(state, "heatmap_palette", e.new), 'value')

    # Symbols
    symbol_selector = pn.widgets.CheckBoxGroup(
        name="Select Symbols",
        options=state.param['symbols'].objects,
        value=state.symbols
    )
    symbol_selector.param.watch(lambda e: setattr(state, 'symbols', e.new), 'value')

    return date_range, heatmap_palette, symbol_selector
