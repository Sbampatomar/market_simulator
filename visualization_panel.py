# Unified and complete visualization_panel.py with improved layout and chart grouping

import pandas as pd
import panel as pn
import plotly.graph_objects as go
import plotly.colors as pc
from pathlib import Path
import param
import numpy as np
from sklearn.linear_model import LinearRegression
from plotly.colors import qualitative
import colorcet as cc
import io
import tempfile
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from panel.widgets import FileDownload
from reportlab.platypus import PageBreak

pn.extension('plotly', 'tabulator')

# ---------------- CONFIG ----------------
DATA_DIR = Path("output")
daily_df = pd.read_csv(DATA_DIR / "daily_portfolio.csv", parse_dates=["date"], index_col="date")
monthly_df = pd.read_csv(DATA_DIR / "monthly_stats.csv", parse_dates=["month"], index_col="month")
dividends_df = pd.read_csv(DATA_DIR / "monthly_dividends.csv", index_col=0)
dividends_df.index = pd.to_datetime(dividends_df.index)
assert isinstance(dividends_df.index, pd.DatetimeIndex), "Index is not datetime!"
metadata_df = pd.read_csv(Path("input") / "symbol_metadata.csv")
kpi_file = DATA_DIR / "output_kpis.txt"

# ---------------- KPI GROUPING AND DESCRIPTIONS ----------------
KPI_GROUPS = {
    "Capital KPIs": [
        "Initial investment",
        "Total investments (initial + investment_plan)",
        "Final portfolio value",
        "Final total stocks count",
        "Final gain/loss absolute",
        "Final gain/loss percentual",
        "Capital gain if realized (last date)",
        "Capital gain tax if realized",
        "Capital gain (net)",
        "Total broker fees paid",
        "Max Drawdown"
    ],
    "Dividend KPIs": [
        "Total dividends generated (gross)",
        "Total dividends generated (net)",
        "Total dividends reinvested",
        "Remaining dividend pot",
        "Last year generated dividend (net)",
        "YTD generated dividend (net)",
        "Total payed taxes on dividends",
        "Dividend payed tax / gain ratio"
    ],
    "Performance KPIs": [
        "Portfolio XIRR",
        "YTD gain/loss absolute",
        "Last month gain/loss absolute"
    ]
}

KPI_EXPLANATIONS = {
    "Initial investment": "The initial capital invested at simulation start.",
    "Total investments (initial + investment_plan)": "Sum of initial and scheduled investments.",
    "Final portfolio value": "Portfolio value at simulation end.",
    "Final total stocks count": "Total shares held across all stocks.",
    "Final gain/loss absolute": "Net profit or loss in euros.",
    "Final gain/loss percentual": "Net profit or loss in percent.",
    "Capital gain if realized (last date)": "Unrealized gain if all sold at final date.",
    "Capital gain tax if realized": "Estimated taxes on full liquidation.",
    "Capital gain (net)": "Gain after taxes if realized.",
    "Total broker fees paid": "Sum of all broker commissions.",
    "Max Drawdown": "Largest observed portfolio value drop.",
    
    "Total dividends generated (gross)": "Total dividends before tax.",
    "Total dividends generated (net)": "Total dividends after tax.",
    "Total dividends reinvested": "Portion of dividends reinvested.",
    "Remaining dividend pot": "Undeployed dividends left at end.",
    "Last year generated dividend (net)": "Dividends received in the last year.",
    "YTD generated dividend (net)": "Dividends received year-to-date.",
    "Total payed taxes on dividends": "Cumulative dividend taxes.",
    "Dividend payed tax / gain ratio": "Tax on dividends over total gain (%).",

    "Portfolio XIRR": "Annualized internal rate of return.",
    "YTD gain/loss absolute": "Net profit/loss from January 1st to end date.",
    "Last month gain/loss absolute": "Net profit/loss of the last month."
}


# ---------------- Color Palette Setup ----------------
all_colorcet_palettes = {
    name: getattr(cc.cm, name) for name in dir(cc.cm)
    if not name.startswith('_') and callable(getattr(cc.cm, name))
}

crameri_palettes = sorted([
    name for name in all_colorcet_palettes
    if 'glasbey' not in name and 'rainbow' not in name
])

# ---------------- Load KPI Data ----------------
def load_kpis():
    lines = kpi_file.read_text(encoding="utf-8").splitlines()
    kpis = {}
    for line in lines:
        if ':' in line:
            key, val = line.split(':', 1)
            kpis[key.strip()] = val.strip()
    return kpis

kpi_data = load_kpis()

# ---------------- Widgets ----------------
all_symbols = sorted([col.replace("val_", "") for col in daily_df.columns if col.startswith("val_")])
symbol_selector = pn.widgets.CheckBoxGroup(name="Select Symbols", options=all_symbols, value=all_symbols[:5])

date_range = pn.widgets.DateRangeSlider(
    name='Date Range', start=daily_df.index.min(), end=daily_df.index.max(),
    value=(daily_df.index.min(), daily_df.index.max())
)

# Create label → value mapping (capitalize names for display)
palette_label_map = {name.capitalize(): name for name in crameri_palettes}

heatmap_palette = pn.widgets.Select(
    name="Heatmap Palette (Scientific - Crameri)",
    options=palette_label_map,
    value="imola"
)

def get_colorscale():
    selected_key = heatmap_palette.value
    try:
        cmap = cc.cm[selected_key]  # This is a callable (matplotlib colormap)
        if callable(cmap):
            # Sample 256 evenly spaced points and convert to Plotly-compatible rgb strings
            colors = [
                f'rgb({int(r*255)},{int(g*255)},{int(b*255)})'
                for r, g, b, _ in [cmap(i) for i in np.linspace(0, 1, 256)]
            ]
            return [[i / (len(colors) - 1), color] for i, color in enumerate(colors)]
        else:
            raise ValueError("Selected colormap is not callable.")
    except Exception as e:
        print(f"[ColorScale Error] {e}")
        return [[0, 'rgb(0,0,0)'], [1, 'rgb(255,255,255)']]  # Fallback

# ---------------- KPI Panels ----------------
def make_kpi_group_panel(group_name, kpi_labels):
    cards = []
    for label in kpi_labels:
        val = kpi_data.get(label, None)
        if val is None:
            continue
        try:
            numeric_val = float(val.replace("%", "").replace("€", "").replace(",", ""))
        except ValueError:
            numeric_val = 0
        color = "red" if numeric_val < 0 else "green"
        explanation = KPI_EXPLANATIONS.get(label, "")
        html = f"""
        <div title='{explanation}' style='display:flex; flex-direction:column; justify-content:center; height:100%;'>
            <div style='text-align:center; font-size:12px;'><b>{label}</b></div>
            <div style='text-align:center; font-size:16pt; color:{color};'>{val}</div>
        </div>
        """
        card = pn.Column(pn.pane.HTML(html, sizing_mode='stretch_both'), width=180, height=100, margin=5,
                         styles={
                             'border': '1px solid #ddd',
                             'border-radius': '8px',
                             'box-shadow': '1px 1px 6px rgba(0,0,0,0.1)',
                             'background': 'white',
                             'padding': '8px',
                             'display': 'flex',
                             'justify-content': 'center'
                         })
        cards.append(card)
    return pn.Column(pn.pane.Markdown(f"### {group_name}"), pn.GridBox(*cards, ncols=6))

def kpi_date_panel():
    start = kpi_data.get("Start date", "N/A")
    end = kpi_data.get("End date", "N/A")
    return pn.pane.Markdown(f"### Simulation period: **{start} → {end}**")

# ---------------- Styled Plot Wrapper ----------------
def styled_plotly_figure(title, x, y_series_dict, yaxis_title="€"):
    fig = go.Figure()
    palette = pc.qualitative.Dark24
    for i, (name, y) in enumerate(y_series_dict.items()):
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name=name,
                                 line=dict(color=palette[i % len(palette)], width=2)))
    fig.update_layout(
        title={"text": title, "x": 0.5},
        yaxis_title=yaxis_title,
        height=350,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        hovermode='x unified',
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray')
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")

# ---------------- Plot Functions ----------------
@pn.depends(symbol_selector, date_range)
def plot_symbol_values(symbols, date_range):
    start, end = date_range
    df = daily_df.loc[start:end]
    series = {sym: df[f"val_{sym}"] for sym in symbols if f"val_{sym}" in df.columns}
    return styled_plotly_figure("<b>Symbol Value Over Time</b>", df.index, series)

def plot_total_portfolio_value():
    return styled_plotly_figure("<b>Total Portfolio Value Over Time</b>", daily_df.index, {"Total Portfolio": daily_df["total_value"]})

def plot_capital_vs_value():
    invested = monthly_df["contributions"].cumsum()
    value = monthly_df["last_value"]
    return styled_plotly_figure("<b>Total Invested vs Portfolio Value</b>", monthly_df.index, {
        "Invested Capital": invested,
        "Portfolio Value": value
    })

def plot_monthly_irr():
    irr_approx = (monthly_df["perf_pct"] / 100 + 1) ** 12 - 1
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_df.index,
        y=irr_approx,
        name="Monthly IRR",
        marker_color=pc.qualitative.Dark24[1],
        opacity=0.85
    ))
    fig.update_layout(
        title={"text": "<b>Monthly IRR Approximation</b>", "x": 0.5},
        xaxis_title="Month",
        yaxis_title="IRR",
        height=350,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        barmode='group',
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray')
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")

def plot_cumulative_dividends():
    total = dividends_df.sum(axis=1).cumsum()
    return styled_plotly_figure("<b>Cumulative Dividends Over Time</b>", total.index, {"Cumulative Dividends": total})

def make_radar_allocation(title_text, field, fixed_categories=None, min_categories=None):
    latest_values = daily_df.iloc[-1]
    mapper = dict(zip(metadata_df.symbol, metadata_df[field]))
    current = {}
    avg = {}
    for sym in all_symbols:
        col = f"val_{sym}"
        if col in daily_df.columns:
            key = mapper.get(sym, "Unknown")
            current[key] = current.get(key, 0) + latest_values[col]
            avg[key] = avg.get(key, 0) + daily_df[col].mean()

    if fixed_categories:
        categories = fixed_categories
        current = {cat: current.get(cat, 0.0) for cat in categories}
        avg = {cat: avg.get(cat, 0.0) for cat in categories}
    elif min_categories:
        sorted_items = sorted(current.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_items[:min_categories]
        other_items = sorted_items[min_categories:]
        current = {k: v for k, v in top_items}
        current["Other"] = sum(v for _, v in other_items)

        sorted_avg = sorted(avg.items(), key=lambda x: x[1], reverse=True)
        top_avg = sorted_avg[:min_categories]
        other_avg = sorted_avg[min_categories:]
        avg = {k: v for k, v in top_avg}
        avg["Other"] = sum(v for _, v in other_avg)

        categories = list(current.keys())
    else:
        categories = sorted(set(current) | set(avg))

    current_vals = np.array([current.get(c, 0) for c in categories], dtype=float)
    avg_vals = np.array([avg.get(c, 0) for c in categories], dtype=float)

    # Normalização
    def normalize(x):
        total = np.sum(x)
        return list((x / total * 100) if total > 0 else np.zeros_like(x))

    current_vals = normalize(current_vals)
    avg_vals = normalize(avg_vals)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=avg_vals + [avg_vals[0]],
                                  theta=categories + [categories[0]],
                                  mode='lines',
                                  name='Average',
                                  line=dict(dash='dot')))
    fig.add_trace(go.Scatterpolar(r=current_vals + [current_vals[0]],
                                  theta=categories + [categories[0]],
                                  mode='lines+markers',
                                  name='Latest',
                                  line=dict(width=3)))
    fig.update_layout(
        title={"text": f"<b>{title_text}</b>", "x": 0.5},
        polar=dict(
            radialaxis=dict(visible=True, gridcolor='lightgray'),
            angularaxis=dict(gridcolor='lightgray'),
            bgcolor='white'
        ),
        height=350,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        margin=dict(l=40, r=20, t=40, b=40)
    )

    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")

@pn.depends(heatmap_palette)
def plot_dividend_heatmap_full(palette):
    colorscale = get_colorscale()
    df = dividends_df.copy()
    df["Year"] = df.index.year
    df["Month"] = df.index.strftime("%b")
    pivot = df.groupby(["Year", "Month"]).sum().sum(axis=1).unstack(fill_value=0)
    months_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    valid_months = [m for m in months_order if m in pivot.columns]
    pivot = pivot[valid_months]

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=colorscale,
        hovertemplate='Year %{y}, %{x}<br>€ %{z:.2f}<extra></extra>'
    ))
    fig.update_layout(
        title={"text": "<b>Dividend Heatmap - Full Period</b>", "x": 0.5},
        xaxis_title="Month",
        yaxis_title="Year",
        height=350,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        margin=dict(l=40, r=20, t=40, b=40)
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")

@pn.depends(heatmap_palette)
def plot_dividend_heatmap_recent(palette):
    colorscale = get_colorscale()
    df = dividends_df[dividends_df.index >= (dividends_df.index.max() - pd.DateOffset(months=12))].copy()
    df = df.fillna(0.0)
    monthly = df.groupby(df.index.to_period("M")).sum().sum(axis=1).to_timestamp()
    fig = go.Figure(data=go.Heatmap(z=[monthly.values], x=monthly.index.strftime("%b %y"), y=["Total"], colorscale=colorscale))
    fig.update_layout(
        title={"text": "<b>Dividend Heatmap - Last 12 Months</b>", "x": 0.5},
        height=120,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12)
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")

# ---------------- Additional Bar Plots ----------------
def plot_dividends_by_symbol_last_12_months():
    df = dividends_df[dividends_df.index >= (dividends_df.index.max() - pd.DateOffset(months=12))].copy()
    df = df.fillna(0.0)
    monthly_symbol = df.groupby(df.index.to_period("M")).sum().to_timestamp()

    fig = go.Figure()
    #palette = pc.qualitative.Safe
    palette = cc.glasbey[:len(monthly_symbol.columns)]
    for i, sym in enumerate(monthly_symbol.columns):
        fig.add_trace(go.Bar(
            x=monthly_symbol.index,
            y=monthly_symbol[sym],
            name=sym,
            marker_color=palette[i % len(palette)],
            opacity=0.85
        ))

    fig.update_layout(
        barmode='group',
        title={"text": "<b>Dividends by Symbol - Last 12 Months</b>", "x": 0.5},
        xaxis_title="Month",
        yaxis_title="€",
        height=350,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray')
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")

def plot_dividends_last_12_months():
    df = dividends_df[dividends_df.index >= (dividends_df.index.max() - pd.DateOffset(months=12))].copy()
    df = df.fillna(0.0)
    monthly = df.groupby(df.index.to_period("M")).sum().sum(axis=1).to_timestamp()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly.index,
        y=monthly.values,
        name="Total Dividends",
        marker_color=pc.qualitative.Dark24[0],
        opacity=0.85
        # → Do not use `width` here; it's incompatible with period-based index
    ))

    fig.update_layout(
        title={"text": "<b>Total Dividends - Last 12 Months</b>", "x": 0.5},
        xaxis_title="Month",
        yaxis_title="€",
        height=350,
        barmode='group',
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray')
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")


# ---------------- Raw Chart Accessors ----------------
def raw_symbol_value_over_time(symbols, date_range):
    return plot_symbol_values(symbols, date_range).object

def raw_total_portfolio_value():
    return plot_total_portfolio_value().object

def raw_capital_vs_value():
    return plot_capital_vs_value().object

def raw_cumulative_dividends():
    return plot_cumulative_dividends().object

def raw_monthly_irr():
    return plot_monthly_irr().object

def raw_dividends_last_12_months():
    return plot_dividends_last_12_months().object

def raw_dividends_by_symbol_last_12_months():
    return plot_dividends_by_symbol_last_12_months().object

def raw_dividend_heatmap_full():
    return plot_dividend_heatmap_full().object

def raw_dividend_heatmap_recent():
    return plot_dividend_heatmap_recent().object

def raw_sector_allocation():
    return make_radar_allocation("Sector Allocation", "sector", fixed_categories=fixed_sectors).object

def raw_country_allocation():
    return make_radar_allocation("Country Allocation", "country", fixed_categories=fixed_countries).object

# ---------------- PDF Export Function ----------------
def generate_dashboard_pdf():
    selected_symbols = symbol_selector.value
    start_date, end_date = date_range.value

    with tempfile.TemporaryDirectory() as tmpdir:
        chart_fns = [
            ("Symbol Value Over Time", lambda: raw_symbol_value_over_time(selected_symbols, (start_date, end_date))),
            ("Total Portfolio Value", raw_total_portfolio_value),
            ("Invested vs Portfolio Value", raw_capital_vs_value),
            ("Cumulative Dividends", raw_cumulative_dividends),
            ("Monthly IRR", raw_monthly_irr),
            ("Total Dividends - Last 12 Months", raw_dividends_last_12_months),
            ("Dividends by Symbol - Last 12 Months", raw_dividends_by_symbol_last_12_months),
            ("Dividend Heatmap - Full Period", raw_dividend_heatmap_full),
            ("Dividend Heatmap - Last 12 Months", raw_dividend_heatmap_recent),
            ("Sector Allocation", raw_sector_allocation),
            ("Country Allocation", raw_country_allocation),
        ]

        images = []
        for name, fn in chart_fns:
            try:
                fig = fn()
                image_path = f"{tmpdir}/{name.replace(' ', '_')}.png"
                fig.write_image(image_path, width=1000, height=600, scale=2)
                images.append((name, image_path))
            except Exception as e:
                print(f"[PDF Export] Failed to render {name}: {e}")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        elements = []

        start = kpi_data.get("Start date", "N/A")
        end = kpi_data.get("End date", "N/A")

        elements.append(Paragraph("<b>Market Simulation Dashboard Report</b>", styles['Title']))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(f"Simulation Period: {start} → {end}", styles['Normal']))
        elements.append(Paragraph(f"Filtered Range: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}", styles['Normal']))
        elements.append(Paragraph(f"Symbols: {', '.join(selected_symbols)}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

        kpi_rows = []
        for group_name, labels in KPI_GROUPS.items():
            kpi_rows.append([Paragraph(f"<b>{group_name}</b>", styles['Heading4']), ""])
            for label in labels:
                val = kpi_data.get(label, "N/A")
                kpi_rows.append([label, val])

        kpi_table = Table(kpi_rows, hAlign='LEFT')
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), '#CCCCCC'),
            ('GRID', (0, 0), (-1, -1), 0.5, 'black'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 0.4 * inch))

        for name, path in images:
            img = Image(path, width=10.5 * inch, height=6.5 * inch)  # ocupa ~100% da página útil em A4 paisagem
            elements.append(Paragraph(f"<b>{name}</b>", styles['Heading3']))
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(img)
            elements.append(PageBreak())

        doc.build(elements)
        buffer.seek(0)
        return buffer

# ---------------- Export Button ----------------
download_pdf_button = FileDownload(
    label="📄 Download PDF Report",
    filename="market_dashboard.pdf",
    callback=generate_dashboard_pdf,
    button_type="primary"
)

# ---------------- Layout ----------------
fixed_sectors = ["Energy", "Materials", "Industrials", "Consumer-Discretionary", "Consumer-Staples", "HealthCare", "Financials", "Information-Technology", "Communication-Services", "Utilities"]
fixed_countries = ["Italy", "Germany", "Spain", "France", "Portugal", "United Kingdom", "USA", "Belgium", "Switzerland", "Austria"]

dashboard = pn.template.FastListTemplate(
    
    title="Market Simulation Dashboard",
    
    sidebar=[
        "## Filters",
        date_range,
        pn.Spacer(height=32),
        heatmap_palette,
        pn.Spacer(height=32),
        download_pdf_button,
        pn.Spacer(height=32),
        symbol_selector
    ],

    main=[
        kpi_date_panel,
        make_kpi_group_panel("Capital KPIs", KPI_GROUPS["Capital KPIs"]),
        make_kpi_group_panel("Dividend KPIs", KPI_GROUPS["Dividend KPIs"]),
        make_kpi_group_panel("Performance KPIs", KPI_GROUPS["Performance KPIs"]),
        pn.Column(
            pn.pane.Markdown("### Portfolio Overview"),
            plot_total_portfolio_value(),
            plot_capital_vs_value()
        ),
        pn.Column(
            pn.pane.Markdown("### Dividend Metrics"),
            plot_cumulative_dividends(),
            plot_monthly_irr(),
            plot_dividends_last_12_months(),
            plot_dividends_by_symbol_last_12_months(),
            plot_dividend_heatmap_full,
            plot_dividend_heatmap_recent
        ),
        pn.Column(
            pn.pane.Markdown("### Allocation Charts"),
            pn.Row(
                make_radar_allocation("Sector Allocation", "sector", fixed_categories=fixed_sectors),
                make_radar_allocation("Country Allocation", "country", fixed_categories=fixed_countries)
            )
        ),
        plot_symbol_values
    ]
)

dashboard.servable()