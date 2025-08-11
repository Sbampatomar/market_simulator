import panel as pn
# from .config import KPI_GROUPS, KPI_EXPLANATIONS
from dashboard.config import KPI_GROUPS, KPI_EXPLANATIONS

def kpi_group_panel(kpi_data, group_name, kpi_labels):
    cards = []
    for label in kpi_labels:
        val = kpi_data.get(label, None)
        if val is None:
            continue
        try:
            numeric_val = float(val.replace("%", "").replace("€", "").replace(",", ""))
        except ValueError:
            numeric_val = 0.0
        color = "red" if numeric_val < 0 else "green"
        explanation = KPI_EXPLANATIONS.get(label, "")
        html = f"""
        <div title='{explanation}' style='display:flex; flex-direction:column; justify-content:center; height:100%;'>
            <div style='text-align:center; font-size:12px;'><b>{label}</b></div>
            <div style='text-align:center; font-size:16pt; color:{color};'>{val}</div>
        </div>
        """
        card = pn.Column(
            pn.pane.HTML(html, sizing_mode='stretch_both'),
            width=180, height=100, margin=5,
            styles={
                'border': '1px solid #ddd',
                'border-radius': '8px',
                'box-shadow': '1px 1px 6px rgba(0,0,0,0.1)',
                'background': 'white',
                'padding': '8px',
                'display': 'flex',
                'justify-content': 'center'
            }
        )
        cards.append(card)
    return pn.Column(pn.pane.Markdown(f"### {group_name}"), pn.GridBox(*cards, ncols=6))

def kpi_date_panel(kpi_data):
    start = kpi_data.get("Start date", "N/A")
    end = kpi_data.get("End date", "N/A")
    return pn.pane.Markdown(f"### Simulation period: **{start} → {end}**")