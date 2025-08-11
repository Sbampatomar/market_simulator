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


# KPI groupings (moved verbatim)
KPI_GROUPS = {
    "Capital KPIs": [
        "Initial investment",
        "Total investments (initial + investment_plan)",
        "Final portfolio value",
        "Final total stocks count",
        "Final gain/loss absolute",
        "Final gain/loss percentual",
        "Capital gain if realized (last date)",
        "Capital gain tax if realized",
        "Capital gain (net)",
        "Total broker fees paid",
        "Max Drawdown"
    ],
    "Dividend KPIs": [
        "Total dividends generated (gross)",
        "Total dividends generated (net)",
        "Total dividends reinvested",
        "Remaining dividend pot",
        "Last year generated dividend (net)",
        "YTD generated dividend (net)",
        "Total payed taxes on dividends",
        "Dividend payed tax / gain ratio"
    ],
    "Performance KPIs": [
        "Portfolio XIRR",
        "YTD gain/loss absolute",
        "Last month gain/loss absolute"
    ]
}

KPI_EXPLANATIONS = {
    "Initial investment": "The initial capital invested at simulation start.",
    "Total investments (initial + investment_plan)": "Sum of initial and scheduled investments.",
    "Final portfolio value": "Portfolio value at simulation end.",
    "Final total stocks count": "Total shares held across all stocks.",
    "Final gain/loss absolute": "Net profit or loss in euros.",
    "Final gain/loss percentual": "Net profit or loss in percent.",
    "Capital gain if realized (last date)": "Unrealized gain if all sold at final date.",
    "Capital gain tax if realized": "Estimated taxes on full liquidation.",
    "Capital gain (net)": "Gain after taxes if realized.",
    "Total broker fees paid": "Sum of all broker commissions.",
    "Max Drawdown": "Largest observed portfolio value drop.",

    "Total dividends generated (gross)": "Total dividends before tax.",
    "Total dividends generated (net)": "Total dividends after tax.",
    "Total dividends reinvested": "Portion of dividends reinvested.",
    "Remaining dividend pot": "Undeployed dividends left at end.",
    "Last year generated dividend (net)": "Dividends received in the last year.",
    "YTD generated dividend (net)": "Dividends received year-to-date.",
    "Total payed taxes on dividends": "Cumulative dividend taxes.",
    "Dividend payed tax / gain ratio": "Tax on dividends over total gain (%).",

    "Portfolio XIRR": "Annualized internal rate of return.",
    "YTD gain/loss absolute": "Net profit/loss from January 1st to end date.",
    "Last month gain/loss absolute": "Net profit/loss of the last month."
}