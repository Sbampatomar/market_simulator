# dashboard/layout.py
# Template principal com heatmaps reativos via pn.bind (sem mutação in-place)

import panel as pn
from dashboard.kpi import kpi_group_panel, kpi_date_panel, compute_custom_kpis
from dashboard.config import KPI_GROUPS
from dashboard.plots import lines, bars, heatmaps, radars

def build_layout(state, widgets):
    """
    widgets.make_widgets(state) deve retornar, nesta ordem:
        (date_range, heatmap_palette, symbol_selector, view_mode_toggle)
    """
    date_range, heatmap_palette, symbol_selector, view_mode_toggle = widgets

    # ---------------------------------------------------------------------
    # Overview charts (reativos ao toggle daily/monthly)
    # ---------------------------------------------------------------------
    total_value_pane, _ = lines.total_portfolio_value(state, mode=view_mode_toggle.value)
    inv_vs_val_pane, _ = lines.invested_vs_value(state, mode=view_mode_toggle.value)

    def _on_mode_change(event):
        _, total_fig = lines.total_portfolio_value(state, mode=event.new)
        total_value_pane.object = total_fig
        _, inv_fig = lines.invested_vs_value(state, mode=event.new)
        inv_vs_val_pane.object = inv_fig

    view_mode_toggle.param.watch(_on_mode_change, "value")

    # ---------------------------------------------------------------------
    # Barras (mantidos como estão)
    # ---------------------------------------------------------------------
    monthly_irr_pane, _ = bars.monthly_irr(state)
    ltm_total_div_pane, _ = bars.dividends_last_12m_total(state)
    ltm_by_symbol_pane, _ = bars.dividends_by_symbol_last_12m(state)

    # ---------------------------------------------------------------------
    # HEATMAPS reativos à paleta — via pn.bind
    #   1) Monthly Dividends (calendar, full period)
    #   2) Total Portfolio Value (calendar, full period)
    # ---------------------------------------------------------------------
    calendar_div_view = pn.bind(
        lambda palette: heatmaps.monthly_dividends_calendar(state, palette)[1],
        palette=heatmap_palette
    )
    calendar_val_view = pn.bind(
        lambda palette: heatmaps.total_portfolio_value_calendar(state, palette)[1],
        palette=heatmap_palette
    )

    calendar_div_pane = pn.pane.Plotly(calendar_div_view, config={"responsive": True}, sizing_mode="stretch_width")
    calendar_val_pane = pn.pane.Plotly(calendar_val_view, config={"responsive": True}, sizing_mode="stretch_width")

    # ---------------------------------------------------------------------
    # Radars / alocações
    # ---------------------------------------------------------------------
    sector_alloc_pane, sector_alloc_fig = radars.sector_allocation(state)
    country_alloc_pane, country_alloc_fig = radars.country_allocation(state)

    # ---------------------------------------------------------------------
    # KPIs
    # ---------------------------------------------------------------------
    custom_kpis = compute_custom_kpis(state, state.kpis)

    template = pn.template.FastListTemplate(
        title="Market Simulation Dashboard",
        sidebar=[
            "## Filters",
            date_range,
            pn.Spacer(height=32),
            heatmap_palette,         # <- o mesmo widget usado no bind
            pn.Spacer(height=32),
            pn.pane.Markdown(""),    # placeholder para FileDownload (setado em app.py)
            pn.Spacer(height=32),
            view_mode_toggle,        # Daily/Monthly para os overview charts
            pn.Spacer(height=16),
            symbol_selector
        ],
        main=[
            # KPIs (lazy via lambda para refletir filtros atuais)
            lambda: kpi_date_panel(state.kpis),
            lambda: kpi_group_panel(custom_kpis, "General KPIs", KPI_GROUPS["General KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Capital KPIs", KPI_GROUPS["Capital KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Dividend KPIs", KPI_GROUPS["Dividend KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Taxes/Fees KPIs", KPI_GROUPS["Taxes/Fees KPIs"]),
            lambda: kpi_group_panel(custom_kpis, "Performance KPIs", KPI_GROUPS["Performance KPIs"]),

            # Overview
            pn.Column(
                pn.pane.Markdown("### Portfolio Overview"),
                total_value_pane,
                inv_vs_val_pane
            ),

            # Dividendos (barras + heatmaps)
            pn.Column(
                pn.pane.Markdown("### Dividend Metrics"),
                monthly_irr_pane,
                ltm_total_div_pane,
                ltm_by_symbol_pane,
                calendar_div_pane,   # Monthly Dividends (Full Period)
                calendar_val_pane    # Total Portfolio Value (Full Period)
            ),

            # Alocações
            pn.Column(
                pn.pane.Markdown("### Allocation Charts"),
                pn.Row(sector_alloc_pane, country_alloc_pane)
            ),
        ]
    )

    # ---------------------------------------------------------------------
    # Exportação (PDF etc.). Use lambdas que reconstroem as figuras no estado atual.
    # ---------------------------------------------------------------------
    chart_specs = [
        ("Symbol Value Over Time", lambda: lines.symbol_values(state)[1]),
        ("Total Portfolio Value", lambda: lines.total_portfolio_value(state, mode=view_mode_toggle.value)[1]),
        ("Invested vs Portfolio Value", lambda: lines.invested_vs_value(state, mode=view_mode_toggle.value)[1]),
        ("Monthly IRR", lambda: bars.monthly_irr(state)[1]),
        ("Total Dividends - Last 12 Months", lambda: bars.dividends_last_12m_total(state)[1]),
        ("Dividends by Symbol - Last 12 Months", lambda: bars.dividends_by_symbol_last_12m(state)[1]),
        ("Monthly Dividends (Full Period)", lambda: heatmaps.monthly_dividends_calendar(state, palette=heatmap_palette.value)[1]),
        ("Total Portfolio Value (Full Period)", lambda: heatmaps.total_portfolio_value_calendar(state, palette=heatmap_palette.value)[1]),
        ("Sector Allocation", lambda: sector_alloc_fig),
        ("Country Allocation", lambda: country_alloc_fig),
    ]

    return template, chart_specs
