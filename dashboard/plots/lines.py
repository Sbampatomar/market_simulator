import panel as pn
# from ..theming import styled_plotly_figure
from dashboard.theming import styled_plotly_figure

def symbol_values(state):
    start, end = state.date_range
    df = state.daily_df.loc[start:end]
    series = {s: df[f"val_{s}"] for s in state.symbols if f"val_{s}" in df.columns}
    fig = styled_plotly_figure("<b>Symbol Value Over Time</b>", df.index, series)
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

def total_portfolio_value(state):
    fig = styled_plotly_figure("<b>Total Portfolio Value Over Time</b>",
                               state.daily_df.index, {"Total Portfolio": state.daily_df["total_value"]})
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

def invested_vs_value(state):
    invested = state.monthly_df["contributions"].cumsum()
    value = state.monthly_df["last_value"]
    fig = styled_plotly_figure("<b>Total Invested vs Portfolio Value</b>",
                               state.monthly_df.index, {"Invested Capital": invested, "Portfolio Value": value})
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig