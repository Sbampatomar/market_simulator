import panel as pn
import pandas as pd
import re
import numpy as np
import plotly.graph_objects as go
import colorcet as cc
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

def portfolio_value_with_symbols(state, palette: str = "glasbey"):
    """
    Line chart: Total portfolio value + each symbol's value over time.
    Respects state.daily_df (already filtered by date range) and state.selected_symbols.
    Excludes aggregate columns (e.g., total_value) from the per-symbol traces.
    """
    daily = getattr(state, "daily_df", None)
    if not isinstance(daily, pd.DataFrame) or daily.empty:
        return pn.pane.Markdown("No data available for portfolio value."), None

    df = daily.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()

    # --- helpers -----------------------------------------------------------
    def _is_value_col(c: str) -> bool:
        lc = c.lower()
        return (
            lc.startswith(("value_", "val_", "mv_", "market_value_", "position_value_", "holding_value_"))
            or lc.endswith(("_value", "_val", "_mv"))
        )

    # columns that represent aggregates or non-symbol series we must exclude
    AGG_KEYWORDS = {"total", "portfolio", "cash", "invested"}
    AGG_REGEX = re.compile(r"^(?:total_)?portfolio_?value$", re.I)

    def _looks_like_aggregate(col: str) -> bool:
        lc = col.lower()
        if lc in {"total_value", "portfolio_value", "total_portfolio_value"}:
            return True
        if AGG_REGEX.fullmatch(col):
            return True
        # also exclude names containing these aggregates outright
        return any(k in lc for k in AGG_KEYWORDS)

    def _col_to_symbol(col: str) -> str:
        s = re.sub(r'^(value_|val_|mv_|market_value_|position_value_|holding_value_)', '', col, flags=re.I)
        s = re.sub(r'(_value|_val|_mv)$', '', s, flags=re.I)
        return s

    def _find_total_series(df_: pd.DataFrame) -> pd.Series | None:
        # 1) explicit columns, case-insensitive
        candidates = []
        for c in df_.columns:
            lc = c.lower()
            if lc in {"total_value", "portfolio_value", "total_portfolio_value"} or AGG_REGEX.fullmatch(c):
                candidates.append(c)
        if candidates:
            s = pd.to_numeric(df_[candidates[0]], errors="coerce")
            if not s.dropna().empty:
                return s

        # 2) fallback: None
        return None

    # --- compute total -----------------------------------------------------
    total = _find_total_series(df)
    if total is None or total.dropna().empty:
        # Sum the per-symbol value columns (excluding aggregates)
        parts = []
        for c in df.columns:
            if _is_value_col(c) and not _looks_like_aggregate(c):
                parts.append(pd.to_numeric(df[c], errors="coerce"))
        if parts:
            total = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
        else:
            # last resort: try project helper if available
            try:
                total = _get_portfolio_value_series(df)  # provided elsewhere
            except Exception:
                total = None
        if total is None or total.dropna().empty:
            return pn.pane.Markdown("No value columns found to compute total portfolio value."), None

    # --- choose symbol value columns (exclude aggregates) ------------------
    value_cols = [c for c in df.columns if _is_value_col(c) and not _looks_like_aggregate(c)]
    symbol_map = {c: _col_to_symbol(c) for c in value_cols}

    # Optional: filter by selected symbols
    selected = getattr(state, "selected_symbols", None)
    if selected is not None:  # <-- accept empty list as 'show none'
        sel = {str(s).upper() for s in selected}
        value_cols = [c for c in value_cols if symbol_map.get(c, "").upper() in sel]

    # --- build figure ------------------------------------------------------
    fig = go.Figure()

    # Total line (thicker)
    fig.add_trace(go.Scatter(
        x=total.index,
        y=total.values,
        mode="lines",
        name="Total Portfolio Value",
        line=dict(width=3),
        hovertemplate="Date=%{x|%Y-%m-%d}<br>Total=%{y:,.2f}<extra></extra>",
    ))

    # Color palette for symbols
    colors = list(cc.glasbey) if palette == "glasbey" else list(cc.glasbey)

    # Per-symbol lines
    for i, c in enumerate(sorted(value_cols, key=lambda x: symbol_map[x])):
        sym = symbol_map[c]
        s = pd.to_numeric(df[c], errors="coerce")
        if s.dropna().empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            name=sym,
            line=dict(width=1.5, color=colors[i % len(colors)]),
            opacity=0.95,
            hovertemplate="Date=%{x|%Y-%m-%d}<br>" + sym + "=%{y:,.2f}<extra></extra>",
        ))

    # Legend at bottom (consistent with your other charts)
    BOTTOM_EXTRA_LEGEND = 84
    fig.update_layout(
        title={"text": "<b>Portfolio Value + Individual Symbols Value</b>", "x": 0.5},
        xaxis_title="Date",
        yaxis_title="€",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black", size=12),
        margin=dict(l=50, r=20, t=50, b=BOTTOM_EXTRA_LEGEND),
        height=420,
        xaxis=dict(gridcolor="lightgray"),
        yaxis=dict(gridcolor="lightgray", tickprefix="€", tickformat=",.0f"),
        legend=dict(
            orientation="h",
            x=0.5, xanchor="center",
            y=-0.20, yanchor="top",
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            itemsizing="constant",
            traceorder="normal",
        ),
    )

    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig