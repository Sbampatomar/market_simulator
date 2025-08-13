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

# ---------- Fábricas de figuras ----------
def dividends_by_month_symbol(state, palette: str):
    """
    Heatmap: linhas = meses (YYYY-MM), colunas = símbolos, valores = dividendos.
    Usa state.monthly_div_by_symbol se existir; senão deriva de daily_df.
    Respeita state.date_range e state.selected_symbols.
    Retorna (pane, fig).
    """
    df = getattr(state, "monthly_div_by_symbol", None)

    if df is None or len(df) == 0:
        daily = getattr(state, "daily_df", None)
        if daily is not None and len(daily) > 0:
            div_cols = [c for c in daily.columns if "div" in c.lower()]
            if div_cols:
                tmp = daily[div_cols].fillna(0.0).copy()
                tmp["month"] = tmp.index.to_period("M").dt.to_timestamp()
                df = tmp.groupby("month").sum()
                df.columns = [c.replace("div_", "").replace("DIV_", "") for c in df.columns]

    if df is None or len(df) == 0:
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
        df = pd.DataFrame({
            "AAA.MI": np.linspace(0.0, 10.0, len(idx)),
            "BBB.DE": np.linspace(1.0, 8.0, len(idx))[::-1],
            "CCC.PA": np.linspace(0.5, 6.5, len(idx)),
        }, index=idx)

    # recorte por data selecionada
    start, end = getattr(state, "date_range", (df.index.min(), df.index.max()))
    df = df.copy()
    df.index = _coerce_month_index(df.index)
    df = df.loc[(df.index >= pd.to_datetime(start)) & (df.index <= pd.to_datetime(end))]

    # seleção de símbolos
    selected = getattr(state, "selected_symbols", None)
    if selected:
        keep = [s for s in selected if s in df.columns]
        if keep:
            df = df[keep]

    z = df.values
    x_labels = list(df.columns)
    y_labels = [d.strftime("%Y-%m") for d in df.index]
    colorscale = get_colorscale(palette)

    fig = go.Figure(
        data=[go.Heatmap(
            z=z,
            x=x_labels,
            y=y_labels,
            colorscale=colorscale,
            colorbar=dict(title="Dividends"),
            hovertemplate="Month=%{y}<br>Symbol=%{x}<br>Value=%{z:.2f}<extra></extra>",
            zsmooth=False
        )]
    )
    fig.update_layout(
        title="<b>Monthly Dividends by Symbol</b>",
        xaxis_title="Symbol",
        yaxis_title="Month",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig

def dividends_by_month_total(state, palette: str):
    """
    Heatmap 1xN (ou Nx1) com totais mensais agregados no período do slider.
    Respeita state.date_range.
    """
    start, end = getattr(state, "date_range", (None, None))
    daily = getattr(state, "daily_df", None)
    if daily is None or len(daily) == 0:
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=12, freq="MS")
        s = pd.Series(np.linspace(0.0, 20.0, len(idx)), index=idx)
    else:
        div_cols = [c for c in daily.columns if "div" in c.lower()]
        if div_cols:
            s = daily[div_cols].sum(axis=1).groupby(daily.index.to_period("M")).sum()
            s.index = s.index.to_timestamp()
        else:
            # fallback: usa portfolio_gain como proxy mensal
            s = daily["portfolio_gain"].groupby(daily.index.to_period("M")).sum()
            s.index = s.index.to_timestamp()
        if start is not None and end is not None:
            s = s.loc[pd.to_datetime(start):pd.to_datetime(end)]

    z = s.values.reshape(-1, 1)
    y_labels = [d.strftime("%Y-%m") for d in s.index]
    colorscale = get_colorscale(palette)

    fig = go.Figure(
        data=[go.Heatmap(
            z=z,
            x=["Total"],
            y=y_labels,
            colorscale=colorscale,
            colorbar=dict(title="Total"),
            hovertemplate="Month=%{y}<br>Total=%{z:.2f}<extra></extra>",
            zsmooth=False
        )]
    )
    fig.update_layout(
        title="<b>Monthly Totals (Dividends or Gains)</b>",
        xaxis_title="",
        yaxis_title="Month",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig

def monthly_dividends_calendar(state, palette: str):
    """
    Heatmap: x = months (Jan..Dec), y = years, value = monthly dividends total.
    FULL period (ignores state.date_range). Respects state.selected_symbols.
    Returns (pane, fig).
    """
    # -------- Prefer deriving from the WIDEST daily df --------
    df = None
    daily_full = getattr(state, "daily_df_full", None)
    if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
        div_cols = [c for c in daily_full.columns if "div" in c.lower()]
        if div_cols:
            tmp = daily_full[div_cols].fillna(0.0).copy()
            if not isinstance(tmp.index, pd.DatetimeIndex):
                tmp.index = pd.to_datetime(tmp.index)
            tmp["month"] = tmp.index.to_period("M").to_timestamp()
            df = tmp.groupby("month").sum()
            df.columns = [c.replace("div_", "").replace("DIV_", "") for c in df.columns]

    # -------- Fallbacks --------
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
        df = pd.DataFrame({
            "AAA.MI": np.linspace(0.0, 10.0, len(idx)),
            "BBB.DE": np.linspace(1.0, 8.0, len(idx))[::-1],
        }, index=idx)

    # Optional: filter selected symbols
    selected = getattr(state, "selected_symbols", None)
    if selected:
        keep = [s for s in selected if s in df.columns]
        if keep:
            df = df[keep]

    # Normalize monthly index
    if isinstance(df.index, pd.PeriodIndex):
        df.index = df.index.to_timestamp()
    else:
        df.index = pd.to_datetime(df.index)

    # Total monthly dividends across selected symbols
    s = df.sum(axis=1)

    # -------- CRUCIAL: determine FULL monthly bounds from the widest source --------
    # Prefer bounds from daily_df_full; else from the df we built
    if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
        idx_full = pd.to_datetime(daily_full.index)
        first_m = idx_full.min().to_period("M").to_timestamp()
        last_m  = idx_full.max().to_period("M").to_timestamp()
    else:
        first_m = s.index.min().to_period("M").to_timestamp()
        last_m  = s.index.max().to_period("M").to_timestamp()

    # Reindex to a continuous monthly range across the FULL period
    full_idx = pd.date_range(first_m, last_m, freq="MS")
    s = s.reindex(full_idx, fill_value=0.0)  # use np.nan if you want blank cells

    # Pivot: Years x Months (ensure all years and 12 months exist)
    data = pd.DataFrame({
        "year": s.index.year,
        "month": s.index.month,
        "value": s.values
    })
    pivot = data.pivot(index="year", columns="month", values="value").sort_index()
    min_year, max_year = int(data["year"].min()), int(data["year"].max())
    pivot = pivot.reindex(index=range(min_year, max_year + 1))
    pivot = pivot.reindex(columns=range(1, 13), fill_value=0.0)

    years = list(pivot.index)
    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]
    z = pivot.values

    colorscale = get_colorscale(palette)
    fig = go.Figure(
        data=[go.Heatmap(
            z=z,
            x=month_labels,
            y=[str(y) for y in years],
            colorscale=colorscale,
            colorbar=dict(title="Dividends"),
            hovertemplate="Year=%{y}<br>Month=%{x}<br>Total=%{z:.2f}<extra></extra>",
            zsmooth=False
        )]
    )
    fig.update_layout(
        title="<b>Monthly Dividends (Full Period)</b>",
        xaxis_title="Month",
        yaxis_title="Year",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig

def _get_portfolio_value_series(daily: pd.DataFrame) -> pd.Series | None:
    """
    Extract a portfolio-value time series from a daily dataframe, robustly.
    Preference order:
      (A) single total columns (clear 'portfolio value' signal)
      (B) reconstruct from per-symbol value columns (+ cash if present)
      (C) fallback: None
    """
    if not isinstance(daily, pd.DataFrame) or daily.empty:
        return None

    df = daily.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.sort_index()

    cols = list(df.columns)
    low  = [c.lower() for c in cols]

    # ---- (A) Try obvious single total columns ----
    EXACTS = ['portfolio_value', 'total_value']  # add total_value
    CONTAINS_ALL = [
        ('portfolio', 'value'),
        ('total', 'value'),
        ('portfolio', 'equity'),
        ('account', 'value'),
        ('net', 'worth'),
        ('nav',),  # Net Asset Value
    ]

    # exact match first
    for name in EXACTS:
        if name in low:
            s = pd.to_numeric(df[cols[low.index(name)]], errors='coerce')
            if s.notna().sum() > 0:
                return s

    # contains-all words (case-insensitive)
    def _find_contains_all(words):
        for c in cols:
            lc = c.lower()
            if all(w in lc for w in words):
                s = pd.to_numeric(df[c], errors='coerce')
                if s.notna().sum() > 0:
                    return s
        return None

    for pat in CONTAINS_ALL:
        s = _find_contains_all(pat)
        if s is not None:
            return s

    # invested + gain (common pattern)
    invested = None
    gain = None
    for c in cols:
        lc = c.lower()
        if invested is None and (('invested' in lc or 'invest' in lc) and 'value' in lc or lc == 'invested'):
            invested = pd.to_numeric(df[c], errors='coerce')
        if gain is None and ('gain' in lc and 'portfolio' in lc or lc == 'portfolio_gain'):
            gain = pd.to_numeric(df[c], errors='coerce')
    if invested is not None and gain is not None:
        s = invested + gain
        if s.notna().sum() > 0:
            return s

    # ---- (B) Reconstruct from per-symbol value columns (+ cash) ----
    # heuristics: columns that look like per-symbol market value
    value_like_prefixes = ('value_', 'val_', 'mv_', 'market_value_', 'position_value_', 'holding_value_')
    value_like_suffixes = ('_value', '_val', '_mv')
    candidate_cols = set()

    for c in cols:
        lc = c.lower()
        if lc in ('portfolio_value', 'total_value', 'portfolio_total_value'):
            continue
        starts = any(lc.startswith(p) for p in value_like_prefixes)
        ends   = any(lc.endswith(suf) for suf in value_like_suffixes)
        if starts or ends:
            candidate_cols.add(c)

    # common cash columns to include (optional)
    cash_cols = [c for c in cols if c.lower() in ('cash', 'cash_balance', 'cashvalue', 'available_cash')]

    numeric_parts = []
    for c in sorted(candidate_cols):
        s = pd.to_numeric(df[c], errors='coerce')
        if s.notna().sum() > 0:
            numeric_parts.append(s)
    for c in cash_cols:
        s = pd.to_numeric(df[c], errors='coerce')
        if s.notna().sum() > 0:
            numeric_parts.append(s)

    if numeric_parts:
        # row-wise sum across available parts
        s = pd.concat(numeric_parts, axis=1).sum(axis=1, min_count=1)
        if s.notna().sum() > 0:
            return s

    # ---- (C) Give up ----
    return None

def total_portfolio_value_calendar(state, palette: str):
    """
    Heatmap: x = months (Jan..Dec), y = years, z = TOTAL PORTFOLIO VALUE (EoM).
    FULL period (ignores state.date_range). Uses the widest available data.
    """
    # Prefer the widest daily df
    daily_full = getattr(state, "daily_df_full", None)
    daily_part = getattr(state, "daily_df", None)
    daily = daily_full if (isinstance(daily_full, pd.DataFrame) and not daily_full.empty) else daily_part

    # 1) Extract portfolio value series (daily)
    if not isinstance(daily, pd.DataFrame) or daily.empty:
        # mock (shouldn't be needed for your data)
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=18, freq="D")
        s_daily = pd.Series(np.linspace(10_000, 25_000, len(idx)), index=idx)
    else:
        s_daily = _get_portfolio_value_series(daily)
        if s_daily is None or s_daily.dropna().empty:
            # robust fallback: sum per-symbol value columns if present
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
                # final fallback mock
                idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=18, freq="D")
                s_daily = pd.Series(np.linspace(10_000, 25_000, len(idx)), index=idx)

        # ensure datetime index & sorted
        if not isinstance(s_daily.index, pd.DatetimeIndex):
            s_daily.index = pd.to_datetime(s_daily.index, errors="coerce")
        s_daily = s_daily.sort_index()

    # 2) Monthly END values (EoM)
    s_monthly = s_daily.resample("M").last()

    # 3) Build a FULL month-end index over the widest daily span
    if isinstance(daily_full, pd.DataFrame) and not daily_full.empty:
        idx_full = pd.to_datetime(daily_full.index, errors="coerce")
        first_eom = idx_full.min().to_period("M").to_timestamp('M')  # month END
        last_eom  = idx_full.max().to_period("M").to_timestamp('M')  # month END
    else:
        first_eom = s_monthly.index.min().to_period("M").to_timestamp('M')
        last_eom  = s_monthly.index.max().to_period("M").to_timestamp('M')

    full_months_eom = pd.date_range(first_eom, last_eom, freq="M")  # month END dates
    s_monthly = s_monthly.reindex(full_months_eom)  # keep NaN for missing months (blank cells)

    # 4) Pivot to Year × Month
    data = pd.DataFrame({
        "year": s_monthly.index.year,
        "month": s_monthly.index.month,
        "value": s_monthly.values
    })
    if data.empty:
        # keep a minimal skeleton if no values at all
        years = []
        z = np.empty((0, 12))
    else:
        pivot = data.pivot(index="year", columns="month", values="value").sort_index()
        min_year, max_year = int(data["year"].min()), int(data["year"].max())
        pivot = pivot.reindex(index=range(min_year, max_year + 1))
        pivot = pivot.reindex(columns=range(1, 13))  # months 1..12; NaN stays NaN (blank)
        years = [str(y) for y in pivot.index.tolist()]
        z = pivot.values

    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]
    colorscale = get_colorscale(palette)

    fig = go.Figure(
        data=[go.Heatmap(
            z=z,
            x=month_labels,
            y=years,
            colorscale=colorscale,
            colorbar=dict(title="Portfolio Value"),
            hovertemplate="Year=%{y}<br>Month=%{x}<br>Value=%{z:.2f}<extra></extra>",
            zsmooth=False
        )]
    )
    fig.update_layout(
        title="<b>Total Portfolio Value (Full Period)</b>",
        xaxis_title="Month",
        yaxis_title="Year",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    pane = pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width")
    return pane, fig