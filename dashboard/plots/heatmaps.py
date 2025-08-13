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
    Retorna (pane, fig).
    """
    # Fonte preferida: mensal por símbolo pré-agregado
    df = getattr(state, "monthly_div_by_symbol", None)

    # Deriva de daily se necessário
    if df is None or len(df) == 0:
        daily = getattr(state, "daily_df", None)
        if daily is not None and len(daily) > 0:
            div_cols = [c for c in daily.columns if "div" in c.lower()]
            if div_cols:
                tmp = daily[div_cols].fillna(0.0).copy()
                tmp["month"] = tmp.index.to_period("M").dt.to_timestamp()
                df = tmp.groupby("month").sum()
                df.columns = [c.replace("div_", "").replace("DIV_", "") for c in df.columns]

    # Mock estável se ainda não houver dados
    if df is None or len(df) == 0:
        idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=18, freq="MS")
        df = pd.DataFrame({
            "AAA.MI": np.linspace(0.0, 10.0, len(idx)),
            "BBB.DE": np.linspace(1.0, 8.0, len(idx))[::-1],
        }, index=idx)

    # Filtro opcional por símbolos
    selected = getattr(state, "selected_symbols", None)
    if selected:
        keep = [s for s in selected if s in df.columns]
        if keep:
            df = df[keep]

    # Normaliza o índice para início do mês
    df = df.copy()
    if isinstance(df.index, pd.PeriodIndex):
        df.index = df.index.to_timestamp()
    else:
        df.index = pd.to_datetime(df.index)

    # Total mensal (série por mês)
    s = df.sum(axis=1)

    # EXPANSÃO: índice mensal contínuo cobrindo todo o período
    first_m = s.index.min().to_period("M").to_timestamp()
    last_m  = s.index.max().to_period("M").to_timestamp()
    full_idx = pd.date_range(first_m, last_m, freq="MS")
    s = s.reindex(full_idx, fill_value=0.0)  # troque para np.nan se preferir “célula em branco”

    # Tabela Year x Month (todas os anos e 12 meses)
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
    month_labels = [calendar.month_abbr[m] for m in range(1, 13)]  # Jan..Dec
    z = pivot.values  # shape (n_years, 12)

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
