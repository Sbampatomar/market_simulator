import panel as pn
import pandas as pd
from dashboard.theming import styled_plotly_figure

def symbol_values(state):
    start, end = state.date_range
    df = state.daily_df.loc[start:end]
    series = {s: df[f"val_{s}"] for s in state.symbols if f"val_{s}" in df.columns}
    fig = styled_plotly_figure("<b>Symbol Value Over Time</b>", df.index, series)
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

def total_portfolio_value(state, mode: str = "daily"):
    """
    Plot total portfolio value over time.
    mode: "daily" or "monthly"
    """
    mode = (mode or "daily").lower()
    start, end = state.date_range

    if mode == "monthly":
        # Resample daily values to month-end, then clip to selected range
        val_daily = state.daily_df["total_value"].loc[start:end]
        value = val_daily.resample("M").last()
        idx = value.index
        title = "<b>Total Portfolio Value Over Time (Monthly)</b>"
        xaxis_format = "%b-%Y"
    else:
        value = state.daily_df["total_value"].loc[start:end]
        idx = value.index
        title = "<b>Total Portfolio Value Over Time (Daily)</b>"
        xaxis_format = "%d-%b-%Y"

    fig = styled_plotly_figure(title, idx, {"Total Portfolio": value})

    # Legend below + dynamic x-axis tick format
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        xaxis=dict(tickformat=xaxis_format)
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig


def invested_vs_value(state, mode: str = "daily"):
    """
    Plot portfolio value vs. invested capital (external cash).
    mode: "daily" or "monthly"
    """
    mode = (mode or "daily").lower()
    start, end = state.date_range

    if mode == "monthly":
        # Value: one point per month (month-end)
        val_daily = state.daily_df["total_value"].loc[start:end]
        value = val_daily.resample("M").last()
        idx = value.index

        # Invested: sum contributions per month, cumsum, align to month-end index
        if "contributions" in state.monthly_df.columns and len(state.monthly_df) > 0:
            m = state.monthly_df.copy()
            mi = m.index
            # Normalize monthly_df index to Timestamp (month-end), then group by period
            if isinstance(mi, pd.PeriodIndex):
                mi = mi.to_timestamp("M")
            else:
                mi = pd.to_datetime(mi)
                # ensure month-end alignment for grouping
                mi = mi.to_period("M").to_timestamp("M")
            m.index = mi
            contrib_per_month = m["contributions"].groupby(m.index.to_period("M")).sum()
            contrib_per_month.index = contrib_per_month.index.to_timestamp("M")
            invested = contrib_per_month.cumsum()

            # Reindex to the value's month-end index (one point per month), ffill, and clip
            invested = invested.reindex(idx, method="ffill").fillna(0.0)
        else:
            invested = pd.Series(0.0, index=idx)

        title = "<b>Total Invested vs Portfolio Value (Monthly)</b>"
        xaxis_format = "%b-%Y"

    else:
        # Daily mode: align monthly cumulative contributions forward-filled to daily index
        idx = state.daily_df.index
        if "contributions" in state.monthly_df.columns and len(state.monthly_df) > 0:
            m = state.monthly_df.copy()
            mi = m.index
            if isinstance(mi, pd.PeriodIndex):
                mi = mi.to_timestamp("M")
            else:
                mi = pd.to_datetime(mi)
                mi = mi.to_period("M").to_timestamp("M")
            m.index = mi
            invested_monthly = m["contributions"].groupby(m.index).sum().cumsum()
            invested = invested_monthly.reindex(idx, method="ffill").fillna(0.0)
        else:
            invested = pd.Series(0.0, index=idx)

        value = state.daily_df["total_value"]
        # Apply date range to both series in daily mode
        invested = invested.loc[start:end]
        value = value.loc[start:end]
        idx = value.index

        title = "<b>Total Invested vs Portfolio Value (Daily)</b>"
        xaxis_format = "%d-%b-%Y"

    fig = styled_plotly_figure(
        title,
        idx,
        {"Invested Capital": invested, "Portfolio Value": value}
    )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
        xaxis=dict(tickformat=xaxis_format)
    )
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig