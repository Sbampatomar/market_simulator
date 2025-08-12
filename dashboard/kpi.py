import panel as pn
# from .config import KPI_GROUPS, KPI_EXPLANATIONS
from dashboard.config import KPI_GROUPS, KPI_EXPLANATIONS
import pandas as pd
from decimal import Decimal, InvalidOperation

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

def _num(x):
    """Parse a number that may come from kpi_data (with %, €, commas) or native numeric."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("€", "").replace("%", "").replace(",", "").strip()
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, InvalidOperation):
        return None

def _eur(x):
    if x is None:
        return "N/A"
    return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _pct(x):
    if x is None:
        return "N/A"
    return f"{x:.2f}%"

def compute_custom_kpis(state, original_kpis: dict):
    """
    Builds the new KPI dict you requested, using:
      - DataFrames in `state` when reliable
      - Fallbacks to original_kpis when needed
    Assumptions:
      - monthly_df['contributions'] is external capital injected (initial+plan)
      - dividends_df is NET amounts (per symbol) by date index (monthly resolution is fine)
    """
    # --- Capital block ---
    # [A] External capital only (initial + plan), excluding reinvestments
    if "contributions" in state.monthly_df.columns:
        money_invested = float(state.monthly_df["contributions"].sum())
    else:
        # Fallback to original KPI if contributions not available
        money_invested = _num(original_kpis.get("Total investments (initial + investment_plan)"))

    # [H] Reinvested dividends
    reinvested_divs = _num(original_kpis.get("Total dividends reinvested")) or 0.0

    # [B] Total invested = external capital + reinvested dividends
    total_invested = (money_invested or 0.0) + reinvested_divs

    # [C] Final portfolio value (prefer data frame)
    if "total_value" in state.daily_df.columns:
        portfolio_final = float(state.daily_df["total_value"].iloc[-1])
    else:
        portfolio_final = _num(original_kpis.get("Final portfolio value"))

    # [D] Absolute P/L
    if total_invested is None or portfolio_final is None:
        pl_abs = None
    else:
        pl_abs = portfolio_final - total_invested

    # [E] Percent P/L
    if (pl_abs is None) or (total_invested is None) or total_invested == 0:
        pl_pct = None
    else:
        pl_pct = pl_abs / total_invested * 100.0

    # --- Dividends block ---
    # [F] gross, [G] net, [I] pot
    total_div_gross = _num(original_kpis.get("Total dividends generated (gross)"))
    total_div_net   = _num(original_kpis.get("Total dividends generated (net)"))
    dividend_pot    = _num(original_kpis.get("Remaining dividend pot"))

    # [J] prior full calendar year (net)
    # We derive from dividends_df (assumed NET). If your dividends_df is gross, switch to total_div_gross sources or provide a net frame.
    try:
        end_date = state.daily_df.index.max()
        prior_year = (end_date - pd.DateOffset(years=1)).year  # the calendar year before end_date.year
        df_div = state.dividends_df.copy()
        # If dividends_df is monthly with index at month-end/begin, grouping by year is fine:
        last_year_net = float(df_div[df_div.index.year == (end_date.year - 1)].sum(axis=1).sum())
    except Exception:
        last_year_net = _num(original_kpis.get("Last year generated dividend (net)"))

    # [K] trailing 365 days (net)
    try:
        start_365 = end_date - pd.Timedelta(days=365)
        trailing_365_net = float(state.dividends_df.loc[start_365:end_date].sum(axis=1).sum())
    except Exception:
        # Fallback: use existing YTD metric if available (note: semantics differ)
        trailing_365_net = _num(original_kpis.get("YTD generated dividend (net)"))

    # [H] already computed above as reinvested_divs

    # Format for display
    k = {
        "[A] Money invested": _eur(money_invested),
        "[B] Total invested": _eur(total_invested),
        "[C] Portfolio final value": _eur(portfolio_final),
        "[D] Portfolio gain/loss (absolute)": _eur(pl_abs),
        "[E] Portfolio gain/loss (percentual)": _pct(pl_pct),

        "[F] Total generated dividends (gross)": _eur(total_div_gross),
        "[G] Total income dividends (net)": _eur(total_div_net),
        "[H] Reinvested dividends": _eur(reinvested_divs),
        "[I] Remaining dividend pot": _eur(dividend_pot),
        "[J] Last year dividends (net)": _eur(last_year_net),
        "[K] YTD dividends (net, trailing 365 days)": _eur(trailing_365_net),
    }
    return k