import re
import panel as pn
import pandas as pd
import numpy as np
from dashboard.config import KPI_EXPLANATIONS

# ---------- formatting & parsing helpers ----------
def _num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("€", "").replace("%", "").strip()
    m = re.search(r'[-+]?\d[\d\.\,]*', s)
    if not m:
        return None
    token = m.group(0)
    if "." in token and "," in token:
        token = token.replace(".", "").replace(",", ".")
    else:
        token = token.replace(",", ".")
    try:
        return float(token)
    except Exception:
        return None

def _eur(x):
    if x is None:
        return "N/A"
    s = f"{x:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {s}"

def _pct(x):
    if x is None:
        return "N/A"
    return f"{x:.2f}%"

def _int_str(x):
    if x is None:
        return "N/A"
    try:
        return f"{int(round(x))}"
    except Exception:
        return "N/A"

# ---------- helpers: net-of-contributions gain over monthly_df windows ----------
def _net_gain_months(monthly_df, start_idx, end_idx):
    """
    Net-of-external-contributions absolute gain between month indices (inclusive on end):
    (last_value[end] - last_value[start-1]) - sum(contributions[start..end])
    Requires monthly_df with 'last_value' and 'contributions'.
    Returns float or None.
    """
    if not {"last_value", "contributions"} <= set(monthly_df.columns):
        return None
    if start_idx < 0 or end_idx >= len(monthly_df) or end_idx < start_idx:
        return None
    lv = monthly_df["last_value"].values
    contrib = monthly_df["contributions"].values
    start_base = lv[start_idx - 1] if start_idx - 1 >= 0 else np.nan
    if np.isnan(start_base):
        return None
    delta_val = lv[end_idx] - start_base
    delta_contrib = contrib[start_idx:end_idx + 1].sum()
    return float(delta_val - delta_contrib)

def _max_drawdown(series):
    """Return max drawdown as percent (negative or zero)."""
    x = np.asarray(series, dtype=float)
    if x.size == 0 or np.all(~np.isfinite(x)):
        return None
    peak = -np.inf
    mdd = 0.0
    for v in x:
        if not np.isfinite(v):
            continue
        peak = max(peak, v)
        if peak > 0:
            dd = v / peak - 1.0
            mdd = min(mdd, dd)
    return mdd * 100.0

# ---------- KPI computations ----------
def compute_custom_kpis(state, original_kpis: dict):
    # [A] External cash invested
    if "contributions" in state.monthly_df.columns:
        external_cash = float(state.monthly_df["contributions"].sum())
    else:
        external_cash = _num(original_kpis.get("Total investments (initial + investment_plan)"))

    # [H] Reinvested dividends
    reinvested_divs = _num(original_kpis.get("Total dividends reinvested")) or 0.0
    # [B] Capital deployed
    capital_deployed = (external_cash or 0.0) + reinvested_divs

    # [C] Final portfolio value
    if "total_value" in state.daily_df.columns:
        portfolio_final = float(state.daily_df["total_value"].iloc[-1])
    else:
        portfolio_final = _num(original_kpis.get("Final portfolio value"))

    # [D] Portfolio gain/loss combined
    if (external_cash is None) or (portfolio_final is None):
        pl_abs = None
        pl_pct = None
    else:
        pl_abs = portfolio_final - external_cash
        pl_pct = (pl_abs / external_cash * 100.0) if external_cash != 0 else None
    pl_combined = "N/A" if (pl_abs is None or pl_pct is None) else f"{_eur(pl_abs)} ({pl_pct:.2f}%)"

    # Dividends [F][G][I]
    total_div_gross = _num(original_kpis.get("Total dividends generated (gross)"))
    total_div_net   = _num(original_kpis.get("Total dividends generated (net)"))
    dividend_pot    = _num(original_kpis.get("Remaining dividend pot"))

    # [J] last year net
    try:
        end_date = state.daily_df.index.max()
        last_year = end_date.year - 1
        last_year_net = float(state.dividends_df[state.dividends_df.index.year == last_year].sum(axis=1).sum())
    except Exception:
        last_year_net = _num(original_kpis.get("Last year generated dividend (net)"))

    # [K] trailing 365d
    try:
        start_365 = end_date - pd.Timedelta(days=365)
        trailing_365_net = float(state.dividends_df.loc[start_365:end_date].sum(axis=1).sum())
    except Exception:
        trailing_365_net = _num(original_kpis.get("YTD generated dividend (net)"))

    # Taxes/Fees
    realized_cg_tax = (max(pl_abs, 0.0) * 0.26) if (pl_abs is not None) else None
    dividends_tax = _num(original_kpis.get("Total payed taxes on dividends"))
    tax_div_ratio = (dividends_tax / total_div_gross * 100.0) if (dividends_tax is not None and total_div_gross and total_div_gross > 0) else None
    broker_fees = _num(original_kpis.get("Total broker fees paid"))

    # General
    total_stocks = _num(original_kpis.get("Final total stocks count"))
    Q_total_invested = capital_deployed
    R_final_value = portfolio_final
    S_total_income_div_net = total_div_net
    T_investment_gains = None
    if (portfolio_final is not None) and (capital_deployed is not None) and (dividend_pot is not None) and (broker_fees is not None):
        T_investment_gains = (portfolio_final - capital_deployed) + dividend_pot - broker_fees
    U_ratio = (T_investment_gains / Q_total_invested * 100.0) if (T_investment_gains is not None and Q_total_invested and Q_total_invested > 0) else None

    # -------- Performance KPIs --------
    # Prefer KPI-file values when present
    xirr = original_kpis.get("Portfolio XIRR", None)
    ytd_abs = _num(original_kpis.get("YTD gain/loss absolute"))
    last_month_abs = _num(original_kpis.get("Last month gain/loss absolute"))
    # Max Drawdown
    mdd = _num(original_kpis.get("Max Drawdown"))
    if mdd is None:
        try:
            mdd = _max_drawdown(state.daily_df["total_value"])
        except Exception:
            mdd = None

    # Compute last quarter absolute (and fallbacks) from monthly_df if needed
    try:
        mdf = state.monthly_df.sort_index()
        n = len(mdf)
        # last index
        j = n - 1
        # Last month absolute (fallback)
        if last_month_abs is None and n >= 2:
            last_month_abs = _net_gain_months(mdf, j, j)
        # Last quarter absolute
        if n >= 4:
            pq = _net_gain_months(mdf, j - 2, j)  # last 3 months
        else:
            pq = None
        # YTD absolute (fallback): from first month of end.year to last
        if ytd_abs is None:
            end_year = mdf.index[j].year
            # find first month index in the same end_year
            candidates = np.where(np.array([d.year for d in mdf.index]) == end_year)[0]
            if candidates.size > 0:
                i = candidates.min()
                ytd_abs = _net_gain_months(mdf, i, j)
    except Exception:
        pq = pq if 'pq' in locals() else None

    # Format performance values
    perf_kpis = {
        "[PX] Portfolio XIRR": xirr if xirr is not None else "N/A",
        "[PY] YTD gain/loss absolute": _eur(ytd_abs),
        "[PQ] Last quarter gain/loss absolute": _eur(pq),
        "[PM] Last month gain/loss absolute": _eur(last_month_abs),
        "[PD] Max Drawdown": _pct(mdd),
    }

    # Assemble all
    out = {
        # General
        "[P] Portfolio total stocks": _int_str(total_stocks),
        "[Q] Total invested [B]": _eur(Q_total_invested),
        "[R] Portfolio final value [C]": _eur(R_final_value),
        "[S] Total income dividends (net) [G]": _eur(S_total_income_div_net),
        "[T] Investment Gains (net)": _eur(T_investment_gains),
        "[U] Investment Gains / Total Invested": _pct(U_ratio),

        # Capital
        "[A] External cash invested": _eur(external_cash),
        "[B] Capital deployed (A + H)": _eur(capital_deployed),
        "[C] Portfolio final value": _eur(portfolio_final),
        "[D] Portfolio gain/loss": pl_combined,

        # Dividends
        "[F] Total generated dividends (gross)": _eur(total_div_gross),
        "[G] Total income dividends (net)": _eur(total_div_net),
        "[H] Reinvested dividends": _eur(reinvested_divs),
        "[I] Remaining dividend pot": _eur(dividend_pot),
        "[J] Last year dividends (net)": _eur(last_year_net),
        "[K] YTD dividends (net, trailing 365 days)": _eur(trailing_365_net),

        # Taxes/Fees
        "[L] Realized capital gain tax (26%)": _eur(realized_cg_tax),
        "[M] Total dividends tax": _eur(dividends_tax),
        "[N] Dividend tax / total dividends": _pct(tax_div_ratio),
        "[O] Total broker fees paid": _eur(broker_fees),
    }
    out.update(perf_kpis)
    return out

# ---------- Rendering ----------
def kpi_group_panel(kpi_data, group_name, kpi_labels):
    cards = []
    for label in kpi_labels:
        val = kpi_data.get(label, None)
        if val is None:
            continue
        # Coloring:
        # Taxes/Fees → neutral; Performance and others use sign coloring when a numeric is present,
        # except Max Drawdown which is typically negative -> will naturally be red.
        if group_name == "Taxes/Fees KPIs":
            color = "black"
        else:
            numeric_val = _num(val)
            color = "green" if (numeric_val is not None and numeric_val >= 0) else "red"

        explanation = KPI_EXPLANATIONS.get(label, "")
        html = f"""
        <div title="{explanation}" style="display:flex; flex-direction:column; justify-content:center; height:100%;">
            <div style="text-align:center; font-size:12px;"><b>{label}</b></div>
            <div style="text-align:center; font-size:16pt; color:{color};">{val}</div>
        </div>
        """
        card = pn.Column(
            pn.pane.HTML(html, sizing_mode='stretch_both'),
            width=220 if label in ("[D] Portfolio gain/loss", "[T] Investment Gains (net)") else 180,
            height=100,
            margin=5,
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
