# --- bootstrap import path so "dashboard" is importable when run by panel ---
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ---------------------------------------------------------------------------

import panel as pn
pn.extension('plotly', 'tabulator')

# from .io_data import load_data, load_kpis
# from .state import DashboardState
# from .widgets import make_widgets
# from .layout import build_layout
# from .export_pdf import generate_dashboard_pdf
# from .config import KPI_GROUPS
from dashboard.io_data import load_data, load_kpis
from dashboard.state import DashboardState
from dashboard.widgets import make_widgets
from dashboard.layout import build_layout
from dashboard.export_pdf import generate_dashboard_pdf
from dashboard.config import KPI_GROUPS

from panel.widgets import FileDownload

def make_app():
    daily_df, monthly_df, dividends_df, metadata_df = load_data()
    kpis = load_kpis()

    state = DashboardState(
        daily_df=daily_df,
        monthly_df=monthly_df,
        dividends_df=dividends_df,
        metadata_df=metadata_df,
        kpis=kpis
    )
    state.set_defaults()

    widgets = make_widgets(state)
    template, chart_specs = build_layout(state, widgets)

    download_pdf_button = FileDownload(
        label="Download PDF Report",
        filename="market_dashboard.pdf",
        callback=lambda: generate_dashboard_pdf(state, chart_specs, KPI_GROUPS, state.kpis),
        button_type="primary"
    )

    # Insert into sidebar after palette selector
    # Sidebar structure: ["## Filters", date_range, Spacer, heatmap_palette, Spacer, (button slot), Spacer, symbol_selector]
    # The button slot is index 5 in our layout builder.
    template.sidebar[5] = download_pdf_button

    return template

dashboard = make_app()
dashboard.servable()