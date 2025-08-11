import panel as pn
import plotly.graph_objects as go
import numpy as np

def _allocation_series(state, field, categories=None, min_categories=None):
    latest_values = state.daily_df.iloc[-1]
    mapper = dict(zip(state.metadata_df.symbol, state.metadata_df[field]))
    current = {}
    avg = {}
    all_symbols = sorted([c.replace("val_", "") for c in state.daily_df.columns if c.startswith("val_")])

    for sym in all_symbols:
        col = f"val_{sym}"
        if col in state.daily_df.columns:
            key = mapper.get(sym, "Unknown")
            current[key] = current.get(key, 0.0) + latest_values[col]
            avg[key] = avg.get(key, 0.0) + state.daily_df[col].mean()

    if categories:
        cats = categories
        current = {cat: current.get(cat, 0.0) for cat in cats}
        avg = {cat: avg.get(cat, 0.0) for cat in cats}
    elif min_categories:
        sorted_items = sorted(current.items(), key=lambda x: x[1], reverse=True)
        top_items = sorted_items[:min_categories]
        other_items = sorted_items[min_categories:]
        current = {k: v for k, v in top_items}
        current["Other"] = sum(v for _, v in other_items)

        sorted_avg = sorted(avg.items(), key=lambda x: x[1], reverse=True)
        top_avg = sorted_avg[:min_categories]
        other_avg = sorted_avg[min_categories:]
        avg = {k: v for k, v in top_avg}
        avg["Other"] = sum(v for _, v in other_avg)

        cats = list(current.keys())
    else:
        cats = sorted(set(current) | set(avg))

    def normalize(arr):
        total = float(np.sum(arr))
        return list((arr / total * 100.0) if total > 0 else np.zeros_like(arr))

    current_vals = normalize(np.array([current.get(c, 0.0) for c in cats], dtype=float))
    avg_vals = normalize(np.array([avg.get(c, 0.0) for c in cats], dtype=float))
    return cats, current_vals, avg_vals

def _radar_figure(title_text, categories, current_vals, avg_vals):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=avg_vals + [avg_vals[0]],
                                  theta=categories + [categories[0]],
                                  mode='lines',
                                  name='Average',
                                  line=dict(dash='dot')))
    fig.add_trace(go.Scatterpolar(r=current_vals + [current_vals[0]],
                                  theta=categories + [categories[0]],
                                  mode='lines+markers',
                                  name='Latest',
                                  line=dict(width=3)))
    fig.update_layout(
        title={"text": f"<b>{title_text}</b>", "x": 0.5},
        polar=dict(
            radialaxis=dict(visible=True, gridcolor='lightgray'),
            angularaxis=dict(gridcolor='lightgray'),
            bgcolor='white'
        ),
        height=350,
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color="black", size=12),
        margin=dict(l=40, r=20, t=40, b=40)
    )
    return fig

def sector_allocation(state, fixed_categories=None, min_categories=None):
    cats, cur, avg = _allocation_series(state, "sector", categories=fixed_categories, min_categories=min_categories)
    fig = _radar_figure("Sector Allocation", cats, cur, avg)
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig

def country_allocation(state, fixed_categories=None, min_categories=None):
    cats, cur, avg = _allocation_series(state, "country", categories=fixed_categories, min_categories=min_categories)
    fig = _radar_figure("Country Allocation", cats, cur, avg)
    return pn.pane.Plotly(fig, config={"responsive": True}, sizing_mode="stretch_width"), fig