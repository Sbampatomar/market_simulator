# dashboard/layout.py
import panel as pn
from dashboard.kpi import kpi_group_panel, kpi_date_panel, compute_custom_kpis
from dashboard.config import KPI_GROUPS
from dashboard.plots import lines, bars, heatmaps, radars
from dashboard.plots.lines import portfolio_value_with_symbols

def build_layout(state, widgets):
    # Unpack widgets (widgets is a tuple)
    date_range, heatmap_palette, symbol_selector, view_mode_toggle = widgets

    # ---------------- Overview ----------------
    total_value_pane, _ = lines.total_portfolio_value(state, mode=view_mode_toggle.value)
    inv_vs_val_pane, _  = lines.invested_vs_value(state, mode=view_mode_toggle.value)
    pv_sym_pane, _      = portfolio_value_with_symbols(state)

    # Toggle daily/monthly for overview charts
    def _on_mode_change(event):
        _, fig1 = lines.total_portfolio_value(state, mode=event.new)
        total_value_pane.object = fig1
        _, fig2 = lines.invested_vs_value(state, mode=event.new)
        inv_vs_val_pane.object = fig2
    view_mode_toggle.param.watch(_on_mode_change, "value")

    # ---------------- Bars ----------------
    monthly_irr_pane, _   = bars.monthly_irr(state)
    ltm_total_div_pane, _ = bars.dividends_last_12m_total(state)
    ltm_by_symbol_pane, _ = bars.dividends_by_symbol_last_12m(state)

    # ---------------- Heatmaps (palette-bound) ----------------
    # monthly_dividends_calendar returns a single go.Figure
    calendar_div_view = pn.bind(
        lambda palette: heatmaps.monthly_dividends_calendar(state, palette),
        palette=heatmap_palette
    )
    # If your total_portfolio_value_calendar still returns (title, fig), keep [1]
    calendar_val_view = pn.bind(
        lambda palette: heatmaps.total_portfolio_value_calendar(state, palette),
        palette=heatmap_palette
    )

    calendar_div_pane = pn.pane.Plotly(calendar_div_view, config={"responsive": True}, sizing_mode="stretch_width")
    calendar_val_pane = pn.pane.Plotly(calendar_val_view, config={"responsive": True}, sizing_mode="stretch_width")

    # ---------------- Radars ----------------
    sector_alloc_pane, sector_alloc_fig   = radars.sector_allocation(state)
    country_alloc_pane, country_alloc_fig = radars.country_allocation(state)

    # ---------------- KPIs ----------------
    custom_kpis = compute_custom_kpis(state, state.kpis)

    # --------- Unified rebuild for symbol/date dependent charts ----------
    def _rebuild_symbol_dependent():
        # Portfolio value + individual symbols
        _, fig_comp = portfolio_value_with_symbols(state)
        pv_sym_pane.object = fig_comp

        # Dividends by Symbol – Last 12 Months
        _, fig_ltm_sym = bars.dividends_by_symbol_last_12m(state)
        ltm_by_symbol_pane.object = fig_ltm_sym

        # Monthly Dividends (Full Period) calendar (returns a single Figure)
        fig_div_cal = heatmaps.monthly_dividends_calendar(state, palette=heatmap_palette.value)
        calendar_div_pane.object = fig_div_cal

        # Total Portfolio Value (Full Period) calendar (keep [1] if function returns (title, fig))
        fig_val_cal = heatmaps.total_portfolio_value_calendar(state, palette=heatmap_palette.value)
        calendar_val_pane.object = fig_val_cal

    # Watch symbol selection — update state THEN rebuild
    raw_checkbox = getattr(symbol_selector, "_checkbox", None) or symbol_selector
    def _on_symbols_change(event):
        state.selected_symbols = [str(s).upper() for s in event.new]
        _rebuild_symbol_dependent()
    raw_checkbox.param.watch(_on_symbols_change, "value")

    # Watch date range (these charts read state and should honor the range)
    date_range.param.watch(lambda e: _rebuild_symbol_dependent(), "value")

    # ---------------- Template ----------------
    template = pn.template.FastListTemplate(
        title="Market Simulation Dashboard",
        sidebar=[
            "## Filters",
            date_range,
            pn.Spacer(height=32),
            heatmap_palette,
            pn.Spacer(height=32),
            pn.pane.Markdown(""),    # placeholder for FileDownload (set in app.py)
            pn.Spacer(height=32),
            view_mode_toggle,
            pn.Spacer(height=16),
            symbol_selector,         # panel with checkbox + buttons
        ],
        main=[
            # KPIs
            lambda: kpi_date_panel(state.kpis),
            lambda: kpi_group_panel(custom_kpis, "General KPIs",     KPI_GROUPS["General KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Capital KPIs",     KPI_GROUPS["Capital KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Dividend KPIs",    KPI_GROUPS["Dividend KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Taxes/Fees KPIs",  KPI_GROUPS["Taxes/Fees KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Performance KPIs", KPI_GROUPS["Performance KPIs"]),

            # Overview
            pn.Column(
                pn.pane.Markdown("### Portfolio Overview"),
                total_value_pane,
                inv_vs_val_pane,
                pv_sym_pane,
            ),

            # Dividends
            pn.Column(
                pn.pane.Markdown("### Dividend Metrics"),
                monthly_irr_pane,
                ltm_total_div_pane,
                ltm_by_symbol_pane,
                calendar_div_pane,
                calendar_val_pane,
            ),

            # Allocations
            pn.Column(
                pn.pane.Markdown("### Allocation Charts"),
                pn.Row(sector_alloc_pane, country_alloc_pane),
            ),
        ],
    )

    # ---------------- Export (PDF, etc.) ----------------
    chart_specs = [
        ("Symbol Value Over Time",               lambda: lines.symbol_values(state)[1]),
        ("Total Portfolio Value",                lambda: lines.total_portfolio_value(state, mode=view_mode_toggle.value)[1]),
        ("Invested vs Portfolio Value",          lambda: lines.invested_vs_value(state, mode=view_mode_toggle.value)[1]),
        ("Portfolio Value + Individual Symbols", lambda: portfolio_value_with_symbols(state)[1]),
        ("Monthly IRR",                          lambda: bars.monthly_irr(state)[1]),
        ("Total Dividends - Last 12 Months",     lambda: bars.dividends_last_12m_total(state)[1]),
        ("Dividends by Symbol - Last 12 Months", lambda: bars.dividends_by_symbol_last_12m(state)[1]),
        ("Monthly Dividends (Full Period)",      lambda: heatmaps.monthly_dividends_calendar(state, palette=heatmap_palette.value)),
        ("Total Portfolio Value (Full Period)",  lambda: heatmaps.total_portfolio_value_calendar(state, palette=heatmap_palette.value)),
        ("Sector Allocation",                    lambda: sector_alloc_fig),
        ("Country Allocation",                   lambda: country_alloc_fig),
    ]

    return template, chart_specs
