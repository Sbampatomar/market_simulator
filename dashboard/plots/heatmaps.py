import panel as pn
import plotly.graph_objects as go
from dashboard.theming import colorscale_from_cmap
import pandas as pd

def dividends_full(state):
    colorscale = colorscale_from_cmap(state.heatmap_palette)
    df = state.dividends_df.copy()
    df["Year"] = df.index.year
    df["Month"] = df.index.strftime("%b")
    pivot = df.groupby(["Year", "Month"]).sum().sum(axis=1).unstack(fill_value=0)
    months_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    valid_months = [m for m in months_order if m in pivot.columns]
    pivot = pivot[valid_months]

    fig = go.Figure(go.Heatmap(
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
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

def dividends_recent(state):
    colorscale = colorscale_from_cmap(state.heatmap_palette)
    df = state.dividends_df[state.dividends_df.index >= (state.dividends_df.index.max() - pd.DateOffset(months=12))].copy()
    df = df.fillna(0.0)
    monthly = df.groupby(df.index.to_period("M")).sum().sum(axis=1).to_timestamp()
    fig = go.Figure(go.Heatmap(
        z=[monthly.values],
        x=monthly.index.strftime("%b %y"),
        y=["Total"],
        colorscale=colorscale
    ))
    fig.update_layout(
        title={"text": "<b>Dividend Heatmap - Last 12 Months</b>", "x": 0.5},
        height=120,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12)
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig