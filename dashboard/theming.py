import plotly.graph_objects as go
import plotly.colors as pc
import numpy as np
import colorcet as cc

def styled_plotly_figure(title, x, series_dict, yaxis_title="€"):
    # (unchanged)
    fig = go.Figure()
    palette = pc.qualitative.Dark24
    for i, (name, y) in enumerate(series_dict.items()):
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
    return fig

def styled_plotly_figure(title, x, series_dict, yaxis_title="€"):
    fig = go.Figure()
    palette = pc.qualitative.Dark24
    for i, (name, y) in enumerate(series_dict.items()):
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
    return fig

def _hex_to_rgb_string(h):
    h = h.lstrip('#')
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgb({r},{g},{b})"
    # Unexpected format → fallback to black
    return "rgb(0,0,0)"

def colorscale_from_cmap(name):
    """
    Return a Plotly-compatible colorscale for 'name'.
    Priority:
      1) colorcet.palette[name]  -> list of hex colors
      2) known Plotly named scales ('Viridis', 'Cividis', etc.)  -> return the string
      3) fallback: 'Viridis'
    """
    # Try colorcet palette registry (hex list)
    try:
        pal = getattr(cc, "palette", {}).get(name)
        if pal:
            # Convert list of hex colors to evenly spaced stops
            n = len(pal)
            if n >= 2:
                colors = [_hex_to_rgb_string(c) for c in pal]
                return [[i / (n - 1), c] for i, c in enumerate(colors)]
    except Exception:
        pass

    # Accept Plotly’s built-in names directly
    plotly_named = {"Viridis", "Cividis", "Magma", "Inferno", "Plasma", "Turbo", "Bluered", "RdBu", "RdYlBu"}
    if name in plotly_named or name.capitalize() in plotly_named:
        return name if name in plotly_named else name.capitalize()

    # Last resort fallback
    return "Viridis"