from pathlib import Path
import colorcet as cc

# Paths
DATA_DIR  = Path("output")
INPUT_DIR = Path("input")
KPI_FILE  = DATA_DIR / "output_kpis.txt"

# Fixed categories (keep your current lists)
FIXED_SECTORS = [
    "Energy", "Materials", "Industrials", "Consumer-Discretionary", "Consumer-Staples",
    "HealthCare", "Financials", "Information-Technology", "Communication-Services", "Utilities"
]
FIXED_COUNTRIES = [
    "Italy", "Germany", "Spain", "France", "Portugal",
    "United Kingdom", "USA", "Belgium", "Switzerland", "Austria"
]

# Color maps
#ALL_CMAPS = {n: getattr(cc.cm, n) for n in dir(cc.cm) if not n.startswith("_") and callable(getattr(cc.cm, n))}
#CRAMERI = sorted([n for n in ALL_CMAPS if "rainbow" not in n and "glasbey" not in n])

#ALL_CMAPS = [n for n in dir(cc.cm) if not n.startswith("_")]
# Exclude only obvious families; leave the rest
#CRAMERI = sorted([n for n in ALL_CMAPS if "glasbey" not in n and "rainbow" not in n])
# Prefer the stable palette registry (hex lists), then filter
try:
    PALETTE_REGISTRY = dict(getattr(cc, "palette", {}))
except Exception:
    PALETTE_REGISTRY = {}

# Keep only scientific, non-glasbey, non-rainbow
CRAMERI = sorted([
    name for name in PALETTE_REGISTRY.keys()
    if "glasbey" not in name.lower() and "rainbow" not in name.lower()
])


# --- NEW KPI GROUPS (phase 1) ---
KPI_GROUPS = {
    "Capital KPIs": [
        "[A] Money invested",
        "[B] Total invested",
        "[C] Portfolio final value",
        "[D] Portfolio gain/loss (absolute)",
        "[E] Portfolio gain/loss (percentual)"
    ],
    "Dividend KPIs": [
        "[F] Total generated dividends (gross)",
        "[G] Total income dividends (net)",
        "[H] Reinvested dividends",
        "[I] Remaining dividend pot",
        "[J] Last year dividends (net)",
        "[K] YTD dividends (net, trailing 365 days)"
    ]
}

KPI_EXPLANATIONS = {
    "[A] Money invested": "External capital only (initial + investment plan), excluding fees/taxes and excluding reinvestments.",
    "[B] Total invested": "External capital plus dividend reinvestments.",
    "[C] Portfolio final value": "Sum of the market value of all shares at the last simulation date.",
    "[D] Portfolio gain/loss (absolute)": "C − B.",
    "[E] Portfolio gain/loss (percentual)": "(D / B) × 100%.",

    "[F] Total generated dividends (gross)": "Sum of all gross dividends generated.",
    "[G] Total income dividends (net)": "Sum of all net dividends received (after dividend taxes).",
    "[H] Reinvested dividends": "Total amount of dividends used to buy shares.",
    "[I] Remaining dividend pot": "Dividends received but not reinvested by the end.",
    "[J] Last year dividends (net)": "Net dividends in the prior full calendar year (Jan–Dec).",
    "[K] YTD dividends (net, trailing 365 days)": "Net dividends over the last 365 days ending at the final simulation date."
}