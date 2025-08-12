from pathlib import Path
import colorcet as cc

# Paths
DATA_DIR  = Path("output")
INPUT_DIR = Path("input")
KPI_FILE  = DATA_DIR / "output_kpis.txt"

# Palette registry (robust across colorcet versions)
try:
    PALETTE_REGISTRY = dict(getattr(cc, "palette", {}))
except Exception:
    PALETTE_REGISTRY = {}

CRAMERI = sorted([
    name for name in PALETTE_REGISTRY.keys()
    if "glasbey" not in name.lower() and "rainbow" not in name.lower()
])

# --- KPI GROUPS (adds Performance KPIs) ---
KPI_GROUPS = {
    "General KPIs": [
        "[P] Portfolio total stocks",
        "[Q] Total invested [B]",
        "[R] Portfolio final value [C]",
        "[S] Total income dividends (net) [G]",
        "[T] Investment Gains (net)",
        "[U] Investment Gains / Total Invested"
    ],
    "Capital KPIs": [
        "[A] External cash invested",
        "[B] Capital deployed (A + H)",
        "[C] Portfolio final value",
        "[D] Portfolio gain/loss"
    ],
    "Dividend KPIs": [
        "[F] Total generated dividends (gross)",
        "[G] Total income dividends (net)",
        "[H] Reinvested dividends",
        "[I] Remaining dividend pot",
        "[J] Last year dividends (net)",
        "[K] YTD dividends (net, trailing 365 days)"
    ],
    "Taxes/Fees KPIs": [
        "[L] Realized capital gain tax (26%)",
        "[M] Total dividends tax",
        "[N] Dividend tax / total dividends",
        "[O] Total broker fees paid"
    ],
    "Performance KPIs": [
        "[PX] Portfolio XIRR",
        "[PY] YTD gain/loss absolute",
        "[PQ] Last quarter gain/loss absolute",
        "[PM] Last month gain/loss absolute",
        "[PD] Max Drawdown"
    ]
}

KPI_EXPLANATIONS = {
    # General
    "[P] Portfolio total stocks": "Total number of shares at the final simulation date (sum across symbols).",
    "[Q] Total invested [B]": "Capital deployed = external cash + reinvested dividends.",
    "[R] Portfolio final value [C]": "Market value of all holdings at the final date.",
    "[S] Total income dividends (net) [G]": "Net dividends received across the full simulation.",
    "[T] Investment Gains (net)": "((C − B) + I) − O: net portfolio gain after dividend pot and broker fees.",
    "[U] Investment Gains / Total Invested": "T divided by B, expressed in percent.",

    # Capital
    "[A] External cash invested": "Out-of-pocket capital (initial + plan), excludes dividend reinvestments.",
    "[B] Capital deployed (A + H)": "External cash plus reinvested dividends used to buy shares.",
    "[C] Portfolio final value": "Market value of all holdings at the final date.",
    "[D] Portfolio gain/loss": "Absolute gain/loss with percentage in parentheses, calculated vs external cash invested.",

    # Dividends
    "[F] Total generated dividends (gross)": "Sum of gross dividends.",
    "[G] Total income dividends (net)": "Sum of net dividends received.",
    "[H] Reinvested dividends": "Dividends used to buy shares.",
    "[I] Remaining dividend pot": "Unreinvested dividends at the end.",
    "[J] Last year dividends (net)": "Net dividends in the prior full calendar year (Jan–Dec).",
    "[K] YTD dividends (net, trailing 365 days)": "Net dividends over the last 365 days.",

    # Taxes/Fees
    "[L] Realized capital gain tax (26%)": "Hypothetical tax at 26% applied to positive portfolio gain/loss.",
    "[M] Total dividends tax": "Cumulative taxes paid on dividends.",
    "[N] Dividend tax / total dividends": "Dividend-tax-to-gross-dividends ratio.",
    "[O] Total broker fees paid": "Sum of all broker commissions.",

    # Performance
    "[PX] Portfolio XIRR": "Annualized internal rate of return for the whole simulation.",
    "[PY] YTD gain/loss absolute": "Year-to-date absolute P/L (net of external contributions).",
    "[PQ] Last quarter gain/loss absolute": "Absolute P/L over the last 3 full months (net of external contributions).",
    "[PM] Last month gain/loss absolute": "Absolute P/L over the last full month (net of external contributions).",
    "[PD] Max Drawdown": "Largest peak-to-trough drop over the period."
}
