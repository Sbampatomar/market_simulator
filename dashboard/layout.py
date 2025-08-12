# dashboard/layout.py
import panel as pn
from dashboard.kpi import kpi_group_panel, kpi_date_panel, compute_custom_kpis
from dashboard.config import KPI_GROUPS
from dashboard.plots import lines, bars, heatmaps, radars

def build_layout(state, widgets):
    # Unpack widgets (order must match widgets.make_widgets)
    date_range, heatmap_palette, symbol_selector, view_mode_toggle = widgets

    # --- Charts that depend on the toggle (both overview charts) ---
    total_value_pane, total_value_fig = lines.total_portfolio_value(state, mode=view_mode_toggle.value)
    inv_vs_val_pane, inv_vs_val_fig = lines.invested_vs_value(state, mode=view_mode_toggle.value)

    def _on_mode_change(event):
        # Rebuild both overview charts in the selected mode
        _, total_fig = lines.total_portfolio_value(state, mode=event.new)
        total_value_pane.object = total_fig

        _, inv_fig = lines.invested_vs_value(state, mode=event.new)
        inv_vs_val_pane.object = inv_fig

    view_mode_toggle.param.watch(_on_mode_change, "value")

    # --- Other charts (unchanged) ---
    monthly_irr_pane, monthly_irr_fig = bars.monthly_irr(state)
    ltm_total_div_pane, ltm_total_div_fig = bars.dividends_last_12m_total(state)
    ltm_by_symbol_pane, ltm_by_symbol_fig = bars.dividends_by_symbol_last_12m(state)

    heatmap_full_pane, heatmap_full_fig = heatmaps.dividends_full(state)
    heatmap_recent_pane, heatmap_recent_fig = heatmaps.dividends_recent(state)

    sector_alloc_pane, sector_alloc_fig = radars.sector_allocation(state)
    country_alloc_pane, country_alloc_fig = radars.country_allocation(state)

    # --- KPIs ---
    custom_kpis = compute_custom_kpis(state, state.kpis)

    template = pn.template.FastListTemplate(
        title="Market Simulation Dashboard",
        sidebar=[
            "## Filters",
            date_range,
            pn.Spacer(height=32),
            heatmap_palette,
            pn.Spacer(height=32),
            pn.pane.Markdown(""),   # placeholder for FileDownload button (app.py sets sidebar[5])
            pn.Spacer(height=32),
            view_mode_toggle,       # Daily/Monthly toggle for overview charts
            pn.Spacer(height=16),
            symbol_selector
        ],
        main=[
            lambda: kpi_date_panel(state.kpis),
            lambda: kpi_group_panel(custom_kpis, "General KPIs", KPI_GROUPS["General KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Capital KPIs", KPI_GROUPS["Capital KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Dividend KPIs", KPI_GROUPS["Dividend KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Taxes/Fees KPIs", KPI_GROUPS["Taxes/Fees KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Performance KPIs", KPI_GROUPS["Performance KPIs"]),
            pn.Column(
                pn.pane.Markdown("### Portfolio Overview"),
                total_value_pane,
                inv_vs_val_pane
            ),
            pn.Column(
                pn.pane.Markdown("### Dividend Metrics"),
                # (keeping these as-is; we can also toggle them later if you want)
                monthly_irr_pane,
                ltm_total_div_pane,
                ltm_by_symbol_pane,
                heatmap_full_pane,
                heatmap_recent_pane
            ),
            pn.Column(
                pn.pane.Markdown("### Allocation Charts"),
                pn.Row(sector_alloc_pane, country_alloc_pane)
            ),
        ]
    )

    # Export: render overview charts with the currently selected mode
    chart_specs = [
        ("Symbol Value Over Time", lambda: lines.symbol_values(state)[1]),
        ("Total Portfolio Value", lambda: lines.total_portfolio_value(state, mode=view_mode_toggle.value)[1]),
        ("Invested vs Portfolio Value", lambda: lines.invested_vs_value(state, mode=view_mode_toggle.value)[1]),
        ("Monthly IRR", lambda: monthly_irr_fig),
        ("Total Dividends - Last 12 Months", lambda: ltm_total_div_fig),
        ("Dividends by Symbol - Last 12 Months", lambda: ltm_by_symbol_fig),
        ("Dividend Heatmap - Full Period", lambda: heatmap_full_fig),
        ("Dividend Heatmap - Last 12 Months", lambda: heatmap_recent_fig),
        ("Sector Allocation", lambda: sector_alloc_fig),
        ("Country Allocation", lambda: country_alloc_fig),
    ]

    return template, chart_specs
