# kpi_exporter.py
import pandas as pd
from decimal import Decimal
from config import OUTPUT_FOLDER, TAX_RATE_DEFAULT
from utils import calculate_drawdown, calculate_xirr
import logging

def export_allocation(allocation_dict, name):
    df = pd.DataFrame(allocation_dict).T.fillna(0.0)
    df.index.name = 'month'
    df = df.sort_index()
    df.to_csv(OUTPUT_FOLDER / f"monthly_{name}_allocation.csv", float_format="%.4f")

def generate_dividend_yield_by_symbol(daily_df, monthly_dividends_by_symbol):
    daily_df = daily_df.copy()
    daily_df['quarter'] = daily_df.index.to_period("Q")
    daily_df['year'] = daily_df.index.to_period("Y")

    symbols = [col.replace("val_", "") for col in daily_df.columns if col.startswith("val_")]
    results = []

    for sym in symbols:
        val_col = f"val_{sym}"
        if val_col not in daily_df.columns:
            logging.warning(f"Missing column for symbol value: {val_col}, skipping symbol {sym}")
            continue

        for period_type in ['quarter', 'year']:
            grouped = daily_df.groupby(period_type)
            for period, group in grouped:
                avg_value = Decimal(str(group[val_col].mean()))
                if avg_value == 0:
                    logging.info(f"Average value for {sym} in {period_type} {period} is zero. Skipping yield calc.")
                    continue

                period_str = str(period)
                valid_months = []
                for month in monthly_dividends_by_symbol:
                    try:
                        parsed_period = pd.to_datetime(month).to_period("Q" if period_type == 'quarter' else "Y")
                        if parsed_period == period:
                            valid_months.append(month)
                    except Exception:
                        logging.warning(f"Skipping invalid month entry in monthly_dividends_by_symbol: {month}")
                        continue

                dividends = sum(
                    (monthly_dividends_by_symbol.get(month, {}).get(sym, Decimal("0.0")) for month in valid_months),
                    start=Decimal("0.0")
                )

                if dividends == 0:
                    logging.info(f"No dividends found for {sym} in {period_type} {period}")

                results.append({
                    'symbol': sym,
                    'period_type': period_type,
                    'period': period_str,
                    'net_dividends': float(dividends),
                    'average_value': float(avg_value),
                    'net_yield_pct': float(dividends / avg_value * 100) if avg_value > 0 else None
                })

    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FOLDER / "dividend_yield_by_symbol.csv", index=False, float_format="%.4f")

    total = df[df['period_type'] == 'year'].groupby('period').agg({
        'net_dividends': 'sum',
        'average_value': 'sum'
    }).reset_index()
    total['net_yield_pct'] = total['net_dividends'] / total['average_value'] * 100
    total.to_csv(OUTPUT_FOLDER / "annual_summary.csv", index=False, float_format="%.4f")

def write_kpis_to_file(start_date, end_date, max_drawdown, xirr,
                        monthly_df, daily_df,
                        gross_dividends_dict, net_dividends_dict,
                        dividend_taxes_paid,
                        ytd_gain, last_month_gain,
                        dividend_buffers):
    output_file = OUTPUT_FOLDER / "output_kpis.txt"
    start_date_str = str(start_date.date())
    end_date_str = str(end_date.date())

    start_investment = Decimal(monthly_df['contributions'].iloc[0])
    total_contributions = Decimal(monthly_df['contributions'].sum())
    total_fees = Decimal(monthly_df['fees'].sum())
    total_invested = total_contributions + total_fees

    total_gross_dividends = sum(gross_dividends_dict.values())
    total_net_dividends = sum(net_dividends_dict.values())
    total_reinvested = Decimal(monthly_df['reinvested'].sum())
    remaining_pot = sum(dividend_buffers.values())

    final_value = Decimal(daily_df['total_value'].iloc[-1])
    final_gain = final_value - total_invested
    final_gain_pct = (final_gain / total_invested * 100) if total_invested > 0 else Decimal("0.0")

    total_stock_count = daily_df.iloc[-1].filter(like="qty_").sum()
    last_year = daily_df.index[-1].year
    last_year_dividends = Decimal(monthly_df[monthly_df.index.year == last_year]['dividends'].sum())
    ytd_dividends = Decimal(monthly_df[monthly_df.index.year == end_date.year]['dividends'].sum())

    realized = Decimal(daily_df['realized_gain'].iloc[-1])
    unrealized = Decimal(daily_df['unrealized_gain'].iloc[-1])
    capital_gain = realized + unrealized
    capital_gain_tax = capital_gain * TAX_RATE_DEFAULT
    net_capital_gain = capital_gain - capital_gain_tax

    div_tax_ratio = (dividend_taxes_paid / final_gain) if final_gain > 0 else Decimal("0.0")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Start date: {start_date_str}\n")
        f.write(f"End date: {end_date_str}\n")
        f.write(f"Max Drawdown: {max_drawdown:.2%}\n")
        f.write(f"Portfolio XIRR: {xirr:.2%}\n" if xirr is not None else "Portfolio XIRR: Calculation failed\n")

        f.write(f"Total dividends generated (gross): €{total_gross_dividends:.2f}\n")
        f.write(f"Total dividends generated (net): €{total_net_dividends:.2f}\n")
        f.write(f"Total dividends reinvested: €{total_reinvested:.2f}\n")
        f.write(f"Remaining dividend pot: €{remaining_pot:.2f}\n")
        f.write(f"Last year generated dividend (net): €{last_year_dividends:.2f}\n")
        f.write(f"YTD generated dividend (net): €{ytd_dividends:.2f}\n")

        f.write(f"Total broker fees paid: €{total_fees:.2f}\n")
        f.write(f"Final gain/loss absolute: €{final_gain:.2f}\n")
        f.write(f"Final gain/loss percentual: {final_gain_pct:.2f}%\n")
        f.write(f"YTD gain/loss absolute: €{ytd_gain:.2f}\n")
        f.write(f"Last month gain/loss absolute: €{last_month_gain:.2f}\n")

        f.write(f"Initial investment: €{start_investment:.2f}\n")
        f.write(f"Total investments (initial + investment_plan): €{total_invested:.2f}\n")
        f.write(f"Final portfolio value: €{final_value:.2f}\n")
        f.write(f"Final total stocks count: {int(total_stock_count)}\n")

        f.write(f"Capital gain if realized (last date): €{capital_gain:.2f}\n")
        f.write(f"Capital gain tax if realized: €{capital_gain_tax:.2f}\n")
        f.write(f"Capital gain (net): €{net_capital_gain:.2f}\n")

        f.write(f"Total payed taxes on dividends: €{dividend_taxes_paid:.2f}\n")
        f.write(f"Dividend payed tax / gain ratio: {div_tax_ratio:.2%}\n")

    logging.info("Written updated KPIs to output_kpis.txt")

def generate_additional_kpis(daily_df, monthly_df, start_date, end_date, gross_dividends, net_dividends, dividend_taxes_paid, dividend_buffers):
    drawdowns = calculate_drawdown(daily_df['total_value'])
    daily_df['drawdown'] = drawdowns
    daily_df['drawdown'].to_csv(OUTPUT_FOLDER / "daily_drawdown.csv", float_format="%.4f")
    max_drawdown = drawdowns.min()

    flows = []
    for idx, row in monthly_df.iterrows():
        date = pd.to_datetime(idx)
        if row['contributions'] != 0:
            flows.append((date, -row['contributions']))
        if row['dividends'] != 0:
            flows.append((date, row['dividends']))

    final_value = daily_df['total_value'].iloc[-1]
    final_date = daily_df.index[-1]
    flows.append((final_date, float(final_value)))

    xirr = calculate_xirr(flows)

    today = end_date
    daily_ytd = daily_df[daily_df.index.year == today.year]
    ytd_gain = Decimal("0.0")
    if not daily_ytd.empty:
        ytd_gain = Decimal(daily_ytd['total_value'].iloc[-1]) - Decimal(daily_ytd['total_value'].iloc[0])

    last_month = today - pd.DateOffset(months=1)
    last_month_df = daily_df[(daily_df.index.month == last_month.month) & (daily_df.index.year == last_month.year)]
    last_month_gain = Decimal("0.0")
    if not last_month_df.empty:
        last_month_gain = Decimal(last_month_df['total_value'].iloc[-1]) - Decimal(last_month_df['total_value'].iloc[0])

    write_kpis_to_file(
        start_date, end_date, max_drawdown, xirr,
        monthly_df, daily_df,
        gross_dividends, net_dividends,
        dividend_taxes_paid,
        ytd_gain, last_month_gain,
        dividend_buffers
    )

    logging.info("KPIs generated and exported successfully")