# dashboard/plots/heatmaps.py
# Heatmaps fed by the new canonical sources

import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ---------- Palette registry (used by widgets.py) ----------
try:
    import colorcet as cc
except Exception:
    cc = None

try:
    import cmcrameri.cm as cmc
except Exception:
    cmc = None

def _mpl_to_hex_list(cmap, n=256):
    return [
        "#{:02x}{:02x}{:02x}".format(
            int(round(255*r)), int(round(255*g)), int(round(255*b))
        )
        for r, g, b, _ in (cmap(i/(n-1)) for i in range(n))
    ]

PALETTES = {}
for name in ["Viridis", "Magma", "Inferno", "Plasma", "Cividis", "Turbo", "Icefire"]:
    PALETTES[name] = name
if cc is not None:
    PALETTES.update({
        "CET_L17 (cc)": cc.CET_L17,
        "fire (cc)": cc.fire,
        "coolwarm (cc)": cc.coolwarm,
        "linear_kryw_0_100_c71 (cc)": cc.linear_kryw_0_100_c71,
    })
if cmc is not None:
    PALETTES.update({
        "roma (cm)":  _mpl_to_hex_list(cmc.roma),
        "bam (cm)":   _mpl_to_hex_list(cmc.bam),
        "imola (cm)": _mpl_to_hex_list(cmc.imola),
        "vik (cm)":   _mpl_to_hex_list(cmc.vik),
        "berlin (cm)":_mpl_to_hex_list(cmc.berlin),
    })

DEFAULT_SCALE_NAME = "Viridis"

def _colorscale(palette):
    if palette is None:
        return PALETTES.get(DEFAULT_SCALE_NAME, "Viridis")
    if isinstance(palette, str):
        return PALETTES.get(palette, palette)
    return palette

# ---------- Visual style knobs (edit these to tune visuals globally) ----------
STYLE = {
    "cell_w": 46,
    "cell_h": 26,
    "xgap": 2,
    "ygap": 2,
    "margin": dict(l=64, r=24, t=60, b=110),  # a touch more bottom room for the colorbar
    "cbar": dict(
        orientation="h",
        x=0.5, xanchor="center",
        y=-0.20,            # below plot; adjust together with bottom margin if needed
        len=0.60,
        thickness=12,
        # NOTE: no 'titleside' here; title is set per-trace as colorbar.title
    ),
    "title_font": dict(size=16),
    "axes_font": dict(size=11),
}

MONTH_ABBR = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

def _ensure_month_index(index):
    if isinstance(index, pd.PeriodIndex) and index.freqstr == "M":
        return index.astype(str).tolist()
    if isinstance(index, pd.DatetimeIndex):
        return index.to_period("M").astype(str).tolist()
    try:
        dt = pd.to_datetime(index)
        return pd.PeriodIndex(dt, freq="M").astype(str).tolist()
    except Exception:
        return [str(x) for x in index]

def _empty_fig(msg="No data"):
    fig = go.Figure()
    fig.update_layout(
        title={"text": msg, "x": 0.5, "xanchor": "center"},
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=STYLE["margin"],
        height=320,
    )
    return fig

def _apply_heatmap_layout(fig, *, title, ncols, nrows, cbar_title):
    # compute figure size from desired cell size and gaps
    w = STYLE["margin"]["l"] + STYLE["margin"]["r"] + max(1, ncols) * STYLE["cell_w"] + max(0, ncols-1) * STYLE["xgap"]
    h = STYLE["margin"]["t"] + STYLE["margin"]["b"] + max(1, nrows) * STYLE["cell_h"] + max(0, nrows-1) * STYLE["ygap"]

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center", font=STYLE["title_font"]),
        width=w,
        height=h,
        margin=STYLE["margin"],
        xaxis=dict(
            title="Month",
            tickangle=0,
            tickfont=STYLE["axes_font"],
            showgrid=False,
            zeroline=False,
            automargin=True,
        ),
        yaxis=dict(
            tickfont=STYLE["axes_font"],
            showgrid=False,
            zeroline=False,
            automargin=True,
        ),
    )
    # update existing colorbar on the first trace
    if fig.data:
        fig.data[0].update(colorbar=dict(title={"text": cbar_title, "side": "top"}, **STYLE["cbar"]))
    return fig

# ---------------- Heatmaps ----------------

def dividends_by_month_symbol(state, palette=None):
    """
    Heatmap: X = months, Y = symbols, Z = dividend_net
    Consumes: state.monthly_div_by_symbol (wide; index=month Timestamp, columns=symbols)
    """
    m = getattr(state, "monthly_div_by_symbol", pd.DataFrame())
    if not isinstance(m, pd.DataFrame) or m.empty:
        return _empty_fig("No symbol-level dividends")

    df = m.copy()
    if not isinstance(df.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            pass

    x = _ensure_month_index(df.index)
    y = list(df.columns)
    z = df.T.values

    trace = go.Heatmap(
        x=x, y=y, z=z,
        colorscale=_colorscale(palette),
        xgap=STYLE["xgap"], ygap=STYLE["ygap"],
        colorbar=dict(title={"text": "Net", "side": "top"}, **STYLE["cbar"]),
        hovertemplate="Symbol: %{y}<br>Month: %{x}<br>Net: %{z:.2f}<extra></extra>",
    )
    fig = go.Figure(data=trace)
    fig = _apply_heatmap_layout(fig, title="Dividends by Month and Symbol (Net)",
                                ncols=len(x), nrows=len(y), cbar_title="Net")
    fig.update_layout(yaxis_title="Symbol")
    return fig

def dividends_by_month_total(state, palette=None):
    """
    Heatmap with a single row 'Total' across months.
    Consumes: state.monthly_dividends_total (tidy: [month, value])
    """
    mt = getattr(state, "monthly_dividends_total", pd.DataFrame())
    if not isinstance(mt, pd.DataFrame) or mt.empty:
        return _empty_fig("No monthly totals")

    df = mt.copy()
    if "month" not in df.columns and "Month" in df.columns:
        df = df.rename(columns={"Month": "month"})
    if "value" not in df.columns and "dividend_net" in df.columns:
        df = df.rename(columns={"dividend_net": "value"})

    try:
        x = pd.to_datetime(df["month"]).to_period("M").astype(str).tolist()
    except Exception:
        x = df["month"].astype(str).tolist()

    z = np.array([df["value"].values.tolist()])  # 1 × n
    trace = go.Heatmap(
        x=x, y=["Total"], z=z,
        colorscale=_colorscale(palette),
        xgap=STYLE["xgap"], ygap=STYLE["ygap"],
        colorbar=dict(title={"text": "Net", "side": "top"}, **STYLE["cbar"]),
        hovertemplate="Month: %{x}<br>Total: %{z:.2f}<extra></extra>",
    )
    fig = go.Figure(data=trace)
    fig = _apply_heatmap_layout(fig, title="Monthly Dividends (Total, Net)",
                                ncols=len(x), nrows=1, cbar_title="Net")
    fig.update_layout(yaxis_title="")
    return fig

def monthly_dividends_calendar(state, palette=None):
    """
    Calendar heatmap: X=Jan..Dec, Y=years. Consumes:
    state.monthly_dividends_calendar_wide (index=year or 'year' col, cols=1..12)
    """
    cal = getattr(state, "monthly_dividends_calendar_wide", pd.DataFrame())
    if not isinstance(cal, pd.DataFrame) or cal.empty:
        return _empty_fig("No calendar data")

    df = cal.copy()
    if "year" in df.columns:
        df = df.set_index("year")
    for mth in range(1, 13):
        if mth not in df.columns:
            df[mth] = 0.0
    df = df.reindex(columns=sorted(df.columns)).sort_index()

    x = MONTH_ABBR
    y = df.index.astype(int).tolist()
    z = df[[1,2,3,4,5,6,7,8,9,10,11,12]].values

    trace = go.Heatmap(
        x=x, y=y, z=z,
        colorscale=_colorscale(palette),
        xgap=STYLE["xgap"], ygap=STYLE["ygap"],
        colorbar=dict(title={"text": "Net", "side": "top"}, **STYLE["cbar"]),
        hovertemplate="Year: %{y}<br>Month: %{x}<br>Net: %{z:.2f}<extra></extra>",
    )
    fig = go.Figure(data=trace)
    fig = _apply_heatmap_layout(fig, title="Dividends Calendar (Net)",
                                ncols=12, nrows=len(y), cbar_title="Net")
    fig.update_layout(yaxis_title="Year")
    return fig

def total_portfolio_value_calendar(state, palette=None):
    """
    Calendar heatmap for month-end portfolio value: X=Jan..Dec, Y=years.
    Consumes: state.daily_df (index DatetimeIndex, column 'total_value')
    """
    df = getattr(state, "daily_df", pd.DataFrame())
    if not isinstance(df, pd.DataFrame) or df.empty:
        return _empty_fig("No portfolio value data")

    if "date" in df.columns and not isinstance(df.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        try:
            df = df.set_index(pd.to_datetime(df["date"], errors="coerce")).sort_index()
        except Exception:
            pass
    if not isinstance(df.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        try:
            df.index = pd.to_datetime(df.index, errors="coerce")
            df = df.sort_index()
        except Exception:
            return _empty_fig("Invalid date index")

    col = "total_value"
    if col not in df.columns:
        candidates = [c for c in df.columns if "value" in c.lower() and "total" in c.lower()]
        if candidates:
            col = candidates[0]
        else:
            return _empty_fig("No 'total_value' column")

    try:
        month_end = df[[col]].resample("M").last().dropna()
    except Exception:
        g = df[[col]].groupby([df.index.to_period("M")]).last()
        g.index = g.index.to_timestamp(how="end")
        month_end = g

    if month_end.empty:
        return _empty_fig("No month-end values")

    month_end["year"] = month_end.index.year
    month_end["m"] = month_end.index.month
    mat = month_end.pivot(index="year", columns="m", values=col).fillna(0.0)
    for mth in range(1, 13):
        if mth not in mat.columns:
            mat[mth] = 0.0
    mat = mat.reindex(columns=sorted(mat.columns)).sort_index()

    x = MONTH_ABBR
    y = mat.index.astype(int).tolist()
    z = mat[[1,2,3,4,5,6,7,8,9,10,11,12]].values

    trace = go.Heatmap(
        x=x, y=y, z=z,
        colorscale=_colorscale(palette),
        xgap=STYLE["xgap"], ygap=STYLE["ygap"],
        colorbar=dict(title={"text": "Value", "side": "top"}, **STYLE["cbar"]),
        hovertemplate="Year: %{y}<br>Month: %{x}<br>Value: %{z:.2f}<extra></extra>",
    )
    fig = go.Figure(data=trace)
    fig = _apply_heatmap_layout(fig, title="Portfolio Value Calendar (Month-end)",
                                ncols=12, nrows=len(y), cbar_title="Value")
    fig.update_layout(yaxis_title="Year")
    return fig
