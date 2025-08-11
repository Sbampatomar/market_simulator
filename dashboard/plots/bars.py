import panel as pn
import plotly.graph_objects as go
import plotly.colors as pc

def monthly_irr(state):
    irr_approx = (state.monthly_df["perf_pct"] / 100 + 1) ** 12 - 1
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=state.monthly_df.index,
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
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

def dividends_last_12m_total(state):
    df = state.dividends_df[state.dividends_df.index >= (state.dividends_df.index.max() - pd.DateOffset(months=12))].copy()
    df = df.fillna(0.0)
    monthly = df.groupby(df.index.to_period("M")).sum().sum(axis=1).to_timestamp()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly.index,
        y=monthly.values,
        name="Total Dividends",
        marker_color=pc.qualitative.Dark24[0],
        opacity=0.85
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
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

# Local import to avoid global pd dependency at module import
import pandas as pd
import colorcet as cc

def dividends_by_symbol_last_12m(state):
    df = state.dividends_df[state.dividends_df.index >= (state.dividends_df.index.max() - pd.DateOffset(months=12))].copy()
    df = df.fillna(0.0)
    monthly_symbol = df.groupby(df.index.to_period("M")).sum().to_timestamp()

    fig = go.Figure()
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
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig