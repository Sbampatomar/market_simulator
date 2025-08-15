# dashboard/plots/heatmaps.py
# Heatmaps com paletas reativas e três fábricas:
# - dividends_by_month_symbol(state, palette)
# - dividends_by_month_total(state, palette)
# - monthly_dividends_calendar(state, palette)  [X=Jan..Dec, Y=Years, FULL PERIOD]

import numpy as np
import pandas as pd
import panel as pn
import plotly.graph_objects as go
import calendar
import re

# Paletas opcionais
try:
    import colorcet as cc
except Exception:
    cc = None

try:
    import cmcrameri.cm as cmc
except Exception:
    cmc = None

# ---------- Paletas: uma única fonte de verdade ----------
PALETTES = {}
# Plotly built-ins (strings aceitas diretamente)
for name in ["Viridis", "Magma", "Inferno", "Plasma", "Cividis", "Turbo", "Icefire"]:
    PALETTES[name] = name

# Colorcet (listas de cores)
if cc is not None:
    PALETTES.update({
        "CET_L17 (cc)": cc.CET_L17,
        "CET_L4 (cc)": cc.CET_L4,
        "CET_D1 (cc)": cc.CET_D1,
        "fire (cc)": cc.fire,
        "kbc (cc)": cc.kbc,
    })

# Crameri (listas de RGBA 0–1)
if cmc is not None:
    def _seq_from_cmap(cmap):
        # converte colormap em lista de 256 cores
        return [cmap(i) for i in range(256)]
    PALETTES.update({
        "roma (cmcrameri)": _seq_from_cmap(cmc.roma),
        "bam (cmcrameri)": _seq_from_cmap(cmc.bam),
        "imola (cmcrameri)": _seq_from_cmap(cmc.imola),
        "vik (cmcrameri)": _seq_from_cmap(cmc.vik),
        "berlin (cmcrameri)": _seq_from_cmap(cmc.berlin),
    })

def _rgba_tuple_to_hex(rgba):
    r, g, b = rgba[:3]
    if isinstance(r, float):  # 0–1
        r = int(round(r * 255))
        g = int(round(g * 255))
        b = int(round(b * 255))
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"#{r:02x}{g:02x}{b:02x}"

def _to_plotly_colorscale(seq):
    if seq is None:
        return "Viridis"
    hexes = []
    for c in seq:
        if isinstance(c, str):
            hexes.append(c)
        elif isinstance(c, (tuple, list)):
            hexes.append(_rgba_tuple_to_hex(c))
        else:
            hexes.append(str(c))
    n = max(1, len(hexes) - 1)
    return [[i / n, color] for i, color in enumerate(hexes)]

def get_colorscale(palette_name: str):
    p = PALETTES.get(palette_name, "Viridis")
    return p if isinstance(p, str) else _to_plotly_colorscale(p)

# ---------- Utilitários ----------
def _coerce_month_index(idx):
    if isinstance(idx, pd.PeriodIndex):
        return idx.to_timestamp()
    return pd.to_datetime(idx)

def _div_value_columns_strict(cols):
    """
    Keep ONLY dividend cash-flow columns (case-insensitive):
      - 'div_<SYM>' or '<SYM>_div'
      - 'dividend_<SYM>' or '<SYM>_dividend'
    Exclude ratio/yield/percent/rate variants.
    """
    out = []
    for c in cols:
        if not isinstance(c, str):
            continue
        lc = c.lower()
        is_div = (
            lc.startswith("div_") or lc.endswith("_div") or
            lc.startswith("dividend_") or lc.endswith("_dividend")
        )
        if is_div and not any(b in lc for b in ("yield", "ratio", "pct", "percent", "rate")):
            out.append(c)
    return out

def _strip_div_prefix_suffix(name: str) -> str:
    s = re.sub(r"^(div_|dividend_)", "", name, flags=re.I)
    s = re.sub(r"(_div|_dividend)$", "", s, flags=re.I)
    return s

# ---------- Fábricas de figuras ----------
def dividends_by_month_symbol(state, palette: str):
    """
    Heatmap: rows = months (YYYY-MM), columns = symbols, z = monthly dividend totals.
    Respects date_range and selected_symbols (empty list => show nothing).
    Uses strict dividend cash-flow columns only.
    """
    # 1) Prefer precomputed monthly matrix
    df = getattr(state, "monthly_div_by_symbol", None)
    if not (isinstance(df, pd.DataFrame) and not df.empty):
        # 2) Derive from daily_df strictly from dividend flow columns
        daily = getattr(state, "daily_df", None)
        if isinstance(daily, pd.DataFrame) and not daily.empty:
            div_cols = _div_value_columns_strict(daily.columns)
            if div_cols:
                tmp = daily[div_cols].fillna(0.0).copy()
                if not isinstance(tmp.index, pd.DatetimeIndex):
                    tmp.index = pd.to_datetime(tmp.index, errors="coerce")
                tmp["month"] = tmp.index.to_period("M").to_timestamp()
                df = tmp.groupby("month").sum()
                df = df.rename(columns={c: _strip_div_prefix_suffix(c) for c in df.columns})

    # 3) Fallback synthetic if still empty
    if not (isinstance(df, pd.DataFrame) and not df.empty):
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
        df = pd.DataFrame({"AAA.MI": np.linspace(0.0, 10.0, len(idx)),
                           "BBB.DE": np.linspace(1.0, 8.0, len(idx))[::-1],
                           "CCC.PA": np.linspace(0.5, 6.5, len(idx))}, index=idx)

    # Normalize monthly index and clip to selected date range
    df = df.copy()
    df.index = _coerce_month_index(df.index)
    df = df.sort_index()
    start, end = getattr(state, "date_range", (df.index.min(), df.index.max()))
    if start is not None and end is not None:
        df = df.loc[pd.to_datetime(start):pd.to_datetime(end)]

    # Apply symbol selection (accept empty list)
    selected = getattr(state, "selected_symbols", None)
    if selected is not None:
        # case-insensitive mapping from UPPER -> original column
        cmap = {c.upper(): c for c in df.columns if isinstance(c, str)}
        keep = [cmap[s.upper()] for s in selected if s.upper() in cmap]
        df = df[keep] if keep else df.iloc[:, 0:0]

    # Build figure
    z = df.values
    x_labels = list(df.columns)
    y_labels = [d.strftime("%Y-%m") for d in df.index]
    colorscale = get_colorscale(palette)

    fig = go.Figure(data=[go.Heatmap(
        z=z, x=x_labels, y=y_labels, colorscale=colorscale,
        colorbar=dict(title="Dividends"),
        hovertemplate="Month=%{y}<br>Symbol=%{x}<br>Value=%{z:.2f}<extra></extra>",
        zsmooth=False, xgap=2, ygap=2
    )])
    fig.update_layout(
        title={"text":"<b>Monthly Dividends by Symbol</b>", "x":0.5},
        xaxis_title="Symbol", yaxis_title="Month",
        margin=dict(l=10, r=10, t=50, b=70),
    )
    # Place colorbar at bottom for consistency
    fig.update_traces(selector=dict(type="heatmap"),
        colorbar=dict(orientation="h", x=0.5, xanchor="center",
                      y=-0.24, yanchor="top", len=0.90, thickness=12))

    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig


def dividends_by_month_total(state, palette: str):
    """
    Heatmap 1xN (or Nx1) with monthly total dividends (cash flows only).
    Respects date_range and selected_symbols (empty list => zeroed series).
    """
    daily = getattr(state, "daily_df", None)

    if isinstance(daily, pd.DataFrame) and not daily.empty:
        div_cols = _div_value_columns_strict(daily.columns)
        if div_cols:
            df = daily[div_cols].fillna(0.0).copy()
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, errors="coerce")
            # Optional symbol filter BEFORE monthly aggregation
            selected = getattr(state, "selected_symbols", None)
            if selected is not None:
                sel = {str(s).upper() for s in selected}
                keep_cols = []
                for c in div_cols:
                    sym = _strip_div_prefix_suffix(c)
                    if isinstance(sym, str) and sym.upper() in sel:
                        keep_cols.append(c)
                df = df[keep_cols] if keep_cols else df.iloc[:, 0:0]

            s = df.sum(axis=1).groupby(df.index.to_period("M")).sum()
            s.index = s.index.to_timestamp()
        else:
            # No dividend flow columns found -> produce an empty series over the date range
            s = pd.Series(dtype=float)
    else:
        s = pd.Series(dtype=float)

    # Clip to date range (and if empty, synthesize last 12 months of zeros to keep the plot stable)
    start, end = getattr(state, "date_range", (None, None))
    if s.empty:
        base_end = pd.Timestamp.today().normalize()
        base_idx = pd.date_range(base_end - pd.DateOffset(months=11), base_end, freq="MS")
        s = pd.Series(0.0, index=base_idx)
    if start is not None and end is not None:
        s = s.loc[pd.to_datetime(start):pd.to_datetime(end)]
        if s.empty:
            # keep structure (zeros) so the heatmap renders
            rng = pd.date_range(pd.to_datetime(start).to_period("M").to_timestamp(),
                                pd.to_datetime(end).to_period("M").to_timestamp(), freq="MS")
            s = pd.Series(0.0, index=rng)

    # Build figure (vertical 1-column heatmap with bottom colorbar)
    z = s.values.reshape(-1, 1)
    y_labels = [d.strftime("%Y-%m") for d in s.index]
    colorscale = get_colorscale(palette)

    fig = go.Figure(data=[go.Heatmap(
        z=z, x=["Total"], y=y_labels, colorscale=colorscale,
        colorbar=dict(title="Total"),
        hovertemplate="Month=%{y}<br>Total=%{z:.2f}<extra></extra>",
        zsmooth=False, xgap=2, ygap=2
    )])
    fig.update_traces(selector=dict(type="heatmap"),
        colorbar=dict(orientation="h", x=0.5, xanchor="center",
                      y=-0.24, yanchor="top", len=0.70, thickness=12))
    fig.update_layout(
        title={"text":"<b>Monthly Dividends Total</b>", "x":0.5},
        xaxis_title="", yaxis_title="Month",
        margin=dict(l=10, r=10, t=50, b=70),
    )

    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig

def monthly_dividends_calendar(state, palette: str):
    """
    Heatmap: x = months (Jan..Dec), y = years, z = monthly dividends total.
    FULL period (ignores state.date_range). Respects state.selected_symbols (empty list => show none).
    Visual matches total_portfolio_value_calendar.
    """
    # Prefer the widest daily df for full bounds and reliable flows
    df = None
    daily_full = getattr(state, "daily_df_full", None)

    if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
        div_cols = _div_value_columns_strict(daily_full.columns)  # strict: div_/dividend_ and suffixes
        if div_cols:
            tmp = daily_full[div_cols].fillna(0.0).copy()
            if not isinstance(tmp.index, pd.DatetimeIndex):
                tmp.index = pd.to_datetime(tmp.index, errors="coerce")
            tmp["month"] = tmp.index.to_period("M").to_timestamp()
            df = tmp.groupby("month").sum()
            # normalize to pure symbols (case preserved from source)
            df = df.rename(columns={c: _strip_div_prefix_suffix(c) for c in df.columns})

    # Fallback to precomputed monthly matrices
    if (df is None) or df.empty:
        mdbs_full = getattr(state, "monthly_div_by_symbol_full", None)
        if isinstance(mdbs_full, pd.DataFrame) and not mdbs_full.empty:
            df = mdbs_full.copy()
    if (df is None) or df.empty:
        mdbs_part = getattr(state, "monthly_div_by_symbol", None)
        if isinstance(mdbs_part, pd.DataFrame) and not mdbs_part.empty:
            df = mdbs_part.copy()
    if (df is None) or df.empty:
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=18, freq="MS")
        df = pd.DataFrame({"AAA.MI": np.linspace(0.0, 10.0, len(idx)),
                           "BBB.DE": np.linspace(1.0, 8.0, len(idx))[::-1]}, index=idx)

    # Case-insensitive symbol filter (accept empty list => show none)
    selected = getattr(state, "selected_symbols", None)
    if selected is not None:
        cmap = {c.upper(): c for c in df.columns if isinstance(c, str)}
        keep = [cmap[s.upper()] for s in selected if isinstance(s, str) and s.upper() in cmap]
        df = df[keep] if keep else df.iloc[:, 0:0]

    # Normalize to month starts
    if isinstance(df.index, pd.PeriodIndex):
        df.index = df.index.to_timestamp()
    else:
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()

    # Total per month
    s = df.sum(axis=1)

    # FULL span (from widest daily if available)
    if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
        idx_full = pd.to_datetime(daily_full.index, errors="coerce")
        first_m = idx_full.min().to_period("M").to_timestamp()
        last_m  = idx_full.max().to_period("M").to_timestamp()
    else:
        first_m = s.index.min().to_period("M").to_timestamp()
        last_m  = s.index.max().to_period("M").to_timestamp()

    full_idx = pd.date_range(first_m, last_m, freq="MS")
    s = s.reindex(full_idx, fill_value=0.0)

    # Pivot to Years x Months (12 cols)
    data = pd.DataFrame({"year": s.index.year, "month": s.index.month, "value": s.values})
    if data.empty:
        years, z = [], np.empty((0, 12))
    else:
        pivot = data.pivot(index="year", columns="month", values="value").sort_index()
        yr_min, yr_max = int(data["year"].min()), int(data["year"].max())
        pivot = pivot.reindex(index=range(yr_min, yr_max + 1))
        pivot = pivot.reindex(columns=range(1, 13), fill_value=0.0)
        years = [str(y) for y in pivot.index.tolist()]
        z = pivot.values

    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]
    colorscale = get_colorscale(palette)

    # Visual (spaced tiles, bottom colorbar, centered title)
    YGAP = 6; XGAP = YGAP
    ROW_PX = 32; GAP_PX = YGAP
    TOP_EXTRA = 50; BOTTOM_EXTRA = 90

    n_rows = max(1, len(years))
    plot_area_h = n_rows * ROW_PX + max(0, n_rows - 1) * GAP_PX
    target_height = max(240, plot_area_h + TOP_EXTRA + BOTTOM_EXTRA)

    fig = go.Figure(data=[go.Heatmap(
        z=z, x=month_labels, y=years, colorscale=colorscale,
        colorbar=dict(title="Dividends"),
        xgap=XGAP, ygap=YGAP, zsmooth=False,
        hovertemplate="Year=%{y}<br>Month=%{x}<br>Total=%{z:.2f}<extra></extra>",
    )])
    fig.update_traces(selector=dict(type="heatmap"),
        colorbar=dict(orientation="h", x=0.5, xanchor="center",
                      y=-0.24, yanchor="top", len=0.90, thickness=12))
    fig.update_layout(
        title="<b>Monthly Dividends (Full Period)</b>", title_x=0.5,
        xaxis=dict(title="", side="top", showgrid=False, ticks="", showline=False, zeroline=False),
        yaxis=dict(title="", showgrid=False, ticks="", showline=False, zeroline=False),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        margin=dict(l=10, r=10, t=TOP_EXTRA, b=BOTTOM_EXTRA),
        height=target_height,
    )
    if n_rows <= 15:
        fig.update_yaxes(tickfont=dict(size=12))

    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig


def _get_portfolio_value_series(daily: pd.DataFrame) -> pd.Series | None:
    """
    Extract a portfolio-value time series from a daily dataframe, robustly.
    Preference order:
      (A) obvious total columns (e.g. 'total_value', 'portfolio_value')
      (B) regex-like matches ('portfolio value', 'total value', etc.)
      (C) invested + portfolio_gain
      (D) reconstruct from per-symbol value columns (+ cash)
      (E) None
    """
    if not isinstance(daily, pd.DataFrame) or daily.empty:
        return None

    df = daily.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()

    cols = list(df.columns)
    low  = [c.lower() for c in cols]

    # (A) exact matches (your data has 'total_value')
    EXACTS = ['portfolio_value', 'total_value']
    for name in EXACTS:
        if name in low:
            s = pd.to_numeric(df[cols[low.index(name)]], errors='coerce')
            if s.notna().any():
                return s

    # (B) contains-all words (case-insensitive)
    def _find_contains_all(words):
        for c in cols:
            lc = c.lower()
            if all(w in lc for w in words):
                s = pd.to_numeric(df[c], errors='coerce')
                if s.notna().any():
                    return s
        return None

    for pat in [('portfolio','value'), ('total','value'), ('portfolio','equity'),
                ('account','value'), ('net','worth'), ('nav',)]:
        s = _find_contains_all(pat)
        if s is not None:
            return s

    # (C) invested + portfolio_gain
    invested, gain = None, None
    for c in cols:
        lc = c.lower()
        if invested is None and (('invested' in lc or 'invest' in lc) and ('value' in lc or lc == 'invested')):
            invested = pd.to_numeric(df[c], errors='coerce')
        if gain is None and (lc == 'portfolio_gain' or ('gain' in lc and 'portfolio' in lc)):
            gain = pd.to_numeric(df[c], errors='coerce')
    if invested is not None and gain is not None:
        s = invested + gain
        if s.notna().any():
            return s

    # (D) reconstruct from per-symbol value columns (+ cash)
    value_like_prefixes = ('value_', 'val_', 'mv_', 'market_value_', 'position_value_', 'holding_value_')
    value_like_suffixes = ('_value', '_val', '_mv')
    parts = []

    for c in cols:
        lc = c.lower()
        if lc in ('portfolio_value', 'total_value'):
            continue
        if any(lc.startswith(p) for p in value_like_prefixes) or any(lc.endswith(s) for s in value_like_suffixes):
            s = pd.to_numeric(df[c], errors='coerce')
            if s.notna().any():
                parts.append(s)

    for c in cols:
        if c.lower() in ('cash', 'cash_balance', 'cashvalue', 'available_cash'):
            s = pd.to_numeric(df[c], errors='coerce')
            if s.notna().any():
                parts.append(s)

    if parts:
        s = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
        if s.notna().any():
            return s

    # (E) give up
    return None

def total_portfolio_value_calendar(state, palette: str):
    """
    Heatmap: x = months (Jan..Dec), y = years, z = EoM total portfolio value.
    FULL period (ignores state.date_range). Colors + colorbar unchanged; with spacing.
    """
    daily_full = getattr(state, "daily_df_full", None)
    daily_part = getattr(state, "daily_df", None)
    daily = daily_full if (isinstance(daily_full, pd.DataFrame) and not daily_full.empty) else daily_part

    # Extract total value series (handles 'total_value' explicitly)
    if not isinstance(daily, pd.DataFrame) or daily.empty:
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=18, freq="D")
        s_daily = pd.Series(np.linspace(10_000, 25_000, len(idx)), index=idx)
    else:
        s_daily = _get_portfolio_value_series(daily)
        if s_daily is None or s_daily.dropna().empty:
            # Fallback: sum per-symbol value columns if present
            df = daily.copy()
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, errors="coerce")
            df = df.sort_index()
            parts = []
            for c in df.columns:
                lc = c.lower()
                if lc.startswith(("value_", "val_", "mv_", "market_value_", "position_value_", "holding_value_")) \
                   or lc.endswith(("_value", "_val", "_mv")):
                    parts.append(pd.to_numeric(df[c], errors="coerce"))
            if parts:
                s_daily = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
            else:
                idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=18, freq="D")
                s_daily = pd.Series(np.linspace(10_000, 25_000, len(idx)), index=idx)

        if not isinstance(s_daily.index, pd.DatetimeIndex):
            s_daily.index = pd.to_datetime(s_daily.index, errors="coerce")
        s_daily = s_daily.sort_index()

    # Month-end values
    s_monthly = s_daily.resample("M").last()

    # FULL month-end span from widest daily
    if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
        idx_full = pd.to_datetime(daily_full.index, errors="coerce")
        first_eom = idx_full.min().to_period("M").to_timestamp('M')
        last_eom  = idx_full.max().to_period("M").to_timestamp('M')
    else:
        first_eom = s_monthly.index.min().to_period("M").to_timestamp('M')
        last_eom  = s_monthly.index.max().to_period("M").to_timestamp('M')

    full_months_eom = pd.date_range(first_eom, last_eom, freq="M")
    s_monthly = s_monthly.reindex(full_months_eom)  # NaN -> blank cells

    # Pivot Year × Month
    data = pd.DataFrame({"year": s_monthly.index.year, "month": s_monthly.index.month, "value": s_monthly.values})
    if data.empty:
        years, z = [], np.empty((0, 12))
    else:
        pivot = data.pivot(index="year", columns="month", values="value").sort_index()
        min_year, max_year = int(data["year"].min()), int(data["year"].max())
        pivot = pivot.reindex(index=range(min_year, max_year + 1))
        pivot = pivot.reindex(columns=range(1, 13))  # keep NaN (blank)
        years = [str(y) for y in pivot.index.tolist()]
        z = pivot.values

    colorscale = get_colorscale(palette)
    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]

    # ---- layout/spacing constants ----
    YGAP = 6            # must match heatmap ygap
    XGAP = YGAP
    ROW_PX = 32         # pixels per year row; increase for taller rows
    GAP_PX = YGAP       # keep equal to YGAP for accurate sizing
    TOP_EXTRA = 50      # title + top padding (pairs with margin.t below)
    BOTTOM_EXTRA = 90   # space for horizontal colorbar (pairs with margin.b)

    n_rows = max(1, len(years))
    plot_area_h = n_rows * ROW_PX + max(0, n_rows - 1) * GAP_PX
    target_height = max(240, plot_area_h + TOP_EXTRA + BOTTOM_EXTRA)

    fig = go.Figure(data=[go.Heatmap(
        z=z,
        x=month_labels,
        y=years,
        colorscale=colorscale,
        colorbar=dict(title="Portfolio Value"),
        xgap=XGAP,
        ygap=YGAP,
        zsmooth=False,
        hovertemplate="Year=%{y}<br>Month=%{x}<br>Value=%{z:.2f}<extra></extra>",
    )])

    # Horizontal, centered colorbar just below plot
    fig.update_traces(
        selector=dict(type="heatmap"),
        colorbar=dict(
            orientation="h",
            x=0.5, xanchor="center",
            y=-0.24, yanchor="top",
            len=0.90,
            thickness=12,
        ),
    )

    fig.update_layout(
        title="<b>Total Portfolio Value (Full Period)</b>",
        title_x=0.5,  # <-- center the title
        xaxis=dict(title="", side="top", showgrid=False, ticks="", showline=False, zeroline=False),
        yaxis=dict(title="", showgrid=False, ticks="", showline=False, zeroline=False),
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        margin=dict(l=10, r=10, t=TOP_EXTRA, b=BOTTOM_EXTRA),
        height=target_height,
    )

    # (Optional) improve legibility at taller row heights
    if n_rows <= 15:
        fig.update_yaxes(tickfont=dict(size=12))

    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig
