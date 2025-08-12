# simulation.py
import pandas as pd
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import logging

from config import (START_DATE, END_DATE, BROKER_FEE, ENABLE_MONTHLY_REINVESTMENT,
                    TRANSACTION_FILE, INVESTMENT_PLAN_FILE, OUTPUT_FOLDER,
                    TAX_RATES, TAX_RATE_DEFAULT, REINVESTMENT_THRESHOLD)
from data_loader import load_price_data, load_symbol_metadata, load_reinvestment_targets
from utils import align_to_trading_day
from kpi_exporter import (generate_dividend_yield_by_symbol,
                           generate_additional_kpis,
                           export_allocation)

def get_dividend_tax_rate(country):
    return TAX_RATES.get(country, TAX_RATE_DEFAULT)

def run_simulation(start_date=None, end_date=None, reinvestment_threshold=None):
    logging.info("Starting simulation")

    start_date = pd.to_datetime(start_date if start_date else START_DATE)
    end_date = pd.to_datetime(end_date if end_date else END_DATE)
    reinvestment_threshold = Decimal(reinvestment_threshold if reinvestment_threshold else REINVESTMENT_THRESHOLD)

    tx_df = pd.read_csv(TRANSACTION_FILE, parse_dates=['date'])
    tx_df['price'] = tx_df.get('price', pd.NA)
    if 'fee' not in tx_df.columns:
        tx_df['fee'] = BROKER_FEE

    plan_df = pd.read_csv(INVESTMENT_PLAN_FILE, parse_dates=['start_date'])
    plan_df['fee'] = plan_df['fee'].apply(lambda x: Decimal(str(x)) if pd.notna(x) else BROKER_FEE) if 'fee' in plan_df.columns else BROKER_FEE

    reinvest_weights = load_reinvestment_targets()
    price_data = load_price_data()
    symbol_metadata = load_symbol_metadata()

    if ENABLE_MONTHLY_REINVESTMENT and not reinvest_weights:
        logging.warning("Monthly reinvestment is enabled, but no reinvestment targets were provided.")

    all_symbols = sorted(set(tx_df['symbol']) | set(plan_df['symbol']) | set(reinvest_weights.keys()))

    trading_days = pd.DatetimeIndex(sorted(set.union(*(set(df.index) for df in price_data.values()))))
    trading_days = trading_days[(trading_days >= start_date) & (trading_days <= end_date)]
    full_index = pd.date_range(start=start_date, end=end_date, freq="B")

    filled_price_data = {sym: df[['Close']].reindex(full_index).ffill() for sym, df in price_data.items()}

    tx_df['aligned_date'] = tx_df['date'].apply(lambda d: align_to_trading_day(d, trading_days))
    tx_df = tx_df.dropna(subset=['aligned_date'])
    tx_by_day = tx_df.groupby('aligned_date')

    scheduled = []
    for _, row in plan_df.iterrows():
        symbol = row['symbol']
        interval = int(row['interval_months'])
        start = row['start_date']
        amount = Decimal(str(row['amount_per_cycle']))
        fee = Decimal(str(row['fee'])) if 'fee' in row and pd.notna(row['fee']) else BROKER_FEE
        current = start
        while current <= end_date:
            aligned = align_to_trading_day(current, trading_days)
            if pd.notna(aligned):
                scheduled.append({'symbol': symbol, 'date': current, 'aligned_date': aligned, 'amount': amount, 'fee': fee})
            current += relativedelta(months=interval)

    scheduled_df = pd.DataFrame(scheduled)
    plan_df_expanded = scheduled_df.groupby('aligned_date') if not scheduled_df.empty else {}

    held = {sym: 0 for sym in all_symbols}
    avg_price = {sym: Decimal("0.0") for sym in all_symbols}
    cash_buffers = {sym: Decimal("0.0") for sym in all_symbols}
    dividend_buffers = {sym: Decimal("0.0") for sym in all_symbols}
    realized_gains = {sym: Decimal("0.0") for sym in all_symbols}

    rows = []
    monthly_stats = {}
    monthly_dividends_by_symbol = {}
    current_month = None
    reinvest_day_triggered = False
    sector_exposure = {}
    country_exposure = {}
    gross_dividends = {}
    net_dividends = {}
    dividend_taxes_paid = Decimal("0.0")

    for day in trading_days:
        actions = []
        month_str = day.strftime("%Y-%m")
        if month_str not in monthly_stats:
            monthly_stats[month_str] = {'first_value': Decimal("0.0"), 'last_value': Decimal("0.0"),
                                        'dividends': Decimal("0.0"), 'contributions': Decimal("0.0"),
                                        'reinvested': Decimal("0.0"), 'realized_gain': Decimal("0.0"),
                                        'fees': Decimal("0.0")}

        if day in tx_by_day.groups:
            for tx in tx_by_day.get_group(day).itertuples():
                symbol = tx.symbol
                if symbol not in price_data or day not in price_data[symbol].index:
                    continue
                qty = int(tx.quantity)
                price = Decimal(str(tx.price)) if pd.notna(tx.price) else Decimal(str(price_data[symbol].loc[day, 'Close']))
                try:
                    fee = Decimal(str(tx.fee)) if pd.notna(tx.fee) else BROKER_FEE
                except (AttributeError, ValueError, TypeError):
                    fee = BROKER_FEE
                action = tx.type
                if action == 'buy':
                    held_before = held[symbol]
                    held[symbol] += qty
                    avg_price[symbol] = ((avg_price[symbol] * held_before + price * qty) / held[symbol]) if held[symbol] > 0 else price
                    monthly_stats[month_str]['contributions'] += qty * price
                    monthly_stats[month_str]['fees'] += fee
                    actions.append(f"buy {qty} {symbol} @ {price:.2f}")
                elif action == 'sell':
                    if held[symbol] >= qty:
                        proceeds = price * qty
                        cost_basis = avg_price[symbol] * qty
                        gain = proceeds - cost_basis
                        realized_gains[symbol] += gain
                        monthly_stats[month_str]['realized_gain'] += gain
                        held[symbol] -= qty
                        monthly_stats[month_str]['fees'] += fee
                        actions.append(f"sell {qty} {symbol} @ {price:.2f} (gain {gain:.2f})")

        if hasattr(plan_df_expanded, 'groups') and day in plan_df_expanded.groups:
            for tx in plan_df_expanded.get_group(day).itertuples():
                symbol = tx.symbol
                if symbol not in price_data or day not in price_data[symbol].index:
                    continue
                amount = Decimal(str(tx.amount))
                fee = Decimal(str(tx.fee)) if pd.notna(tx.fee) else BROKER_FEE
                price = Decimal(str(price_data[symbol].loc[day, 'Close']))
                qty = int((amount - fee) // price)
                leftover = amount - qty * price - fee
                if qty > 0:
                    held_before = held[symbol]
                    held[symbol] += qty
                    avg_price[symbol] = ((avg_price[symbol] * held_before + price * qty) / held[symbol]) if held[symbol] > 0 else price
                    monthly_stats[month_str]['contributions'] += qty * price
                    monthly_stats[month_str]['fees'] += fee
                    cash_buffers[symbol] += leftover
                    actions.append(f"plan buy {qty} {symbol} @ {price:.2f}")

        if ENABLE_MONTHLY_REINVESTMENT:
            if day.month != current_month:
                current_month = day.month
                reinvest_day_triggered = False

            if not reinvest_day_triggered and day.day > 11:
                reinvest_day_triggered = True
                total = sum(dividend_buffers[s] + cash_buffers[s] for s in all_symbols)
                if total >= REINVESTMENT_THRESHOLD:
                    queue = sorted(reinvest_weights.items(), key=lambda x: -x[1])
                    for tgt, _ in queue:
                        if tgt in price_data and day in price_data[tgt].index:
                            price = Decimal(str(price_data[tgt].loc[day, 'Close']))
                            reinvest_fee = Decimal(str(reinvest_weights.get(f"fee_{tgt}", BROKER_FEE)))
                            share_alloc = total * reinvest_weights[tgt]
                            qty = int((share_alloc - reinvest_fee) // price)
                            cost = qty * price + reinvest_fee
                            if qty > 0 and share_alloc > cost:
                                held_before = held[tgt]
                                held[tgt] += qty
                                avg_price[tgt] = ((avg_price[tgt] * held_before + price * qty) / held[tgt]) if held[tgt] > 0 else price
                                monthly_stats[month_str]['reinvested'] += cost
                                monthly_stats[month_str]['fees'] += reinvest_fee
                                total -= cost
                                cash_buffers[tgt] = share_alloc - cost
                                actions.append(f"reinvest {qty} {tgt} @ {price:.2f}")
                    dividend_buffers = {s: Decimal("0.0") for s in all_symbols}

        values = {s: held[s] * Decimal(str(filled_price_data[s].loc[day, 'Close'])) if s in filled_price_data and day in filled_price_data[s].index and not pd.isna(filled_price_data[s].loc[day, 'Close']) else Decimal("0.0") for s in all_symbols}
        unrealized = {s: values[s] - (avg_price[s] * held[s]) for s in all_symbols}
        total_value = sum(values.values())
        total_unrealized = sum(unrealized.values())
        total_realized = sum(realized_gains.values())
        total_gain = total_realized + total_unrealized

        if monthly_stats[month_str]['first_value'] == Decimal("0.0"):
            monthly_stats[month_str]['first_value'] = total_value
        monthly_stats[month_str]['last_value'] = total_value

        rows.append({
            'date': day,
            'total_value': float(total_value),
            'portfolio_gain': float(total_gain),
            'realized_gain': float(total_realized),
            'unrealized_gain': float(total_unrealized),
            'daily_fee': float(monthly_stats[month_str]['fees']) if actions else 0.0,
            **{f"qty_{s}": held[s] for s in all_symbols},
            **{f"avg_price_{s}": float(avg_price[s]) for s in all_symbols},
            **{f"val_{s}": float(values[s]) for s in all_symbols},
            **{f"gain_{s}": float(unrealized[s]) for s in all_symbols},
            'actions': '; '.join(actions)
        })
        if actions:
            logging.info(f"{day.date()}: {'; '.join(actions)}")

    result_df = pd.DataFrame(rows).set_index('date')
    result_df.to_csv(OUTPUT_FOLDER / "daily_portfolio.csv", float_format="%.4f")

    monthly_df = pd.DataFrame([{
        'month': k,
        'first_value': float(v['first_value']),
        'last_value': float(v['last_value']),
        'perf_abs': float(v['last_value'] - v['first_value']),
        'perf_pct': float(((v['last_value'] - v['first_value']) / v['first_value'] * 100)) if v['first_value'] > 0 else None,
        'dividends': float(v['dividends']),
        'contributions': float(v['contributions']),
        'reinvested': float(v['reinvested']),
        'realized_gain': float(v['realized_gain']),
        'fees': float(v['fees']),
        'total_stocks_held': sum(held.values())
    } for k, v in monthly_stats.items()])
    monthly_df['month'] = pd.to_datetime(monthly_df['month'])
    monthly_df = monthly_df.sort_values('month').set_index('month')
    monthly_df.to_csv(OUTPUT_FOLDER / "monthly_stats.csv", float_format="%.4f")

    dividend_df = pd.DataFrame.from_dict(monthly_dividends_by_symbol, orient='index')
    dividend_df.index = pd.to_datetime(dividend_df.index)
    dividend_df = dividend_df.sort_index().fillna(0.0).astype(float)
    dividend_df["total_dividends"] = dividend_df.sum(axis=1)
    dividend_df.to_csv(OUTPUT_FOLDER / "monthly_dividends.csv", float_format="%.4f")

    export_allocation(sector_exposure, 'sector')
    export_allocation(country_exposure, 'country')
    generate_dividend_yield_by_symbol(result_df, monthly_dividends_by_symbol)

    daily_df = pd.read_csv(OUTPUT_FOLDER / "daily_portfolio.csv", parse_dates=['date'], index_col='date')
    monthly_df = pd.read_csv(OUTPUT_FOLDER / "monthly_stats.csv", parse_dates=['month'], index_col='month')
    generate_additional_kpis(
        daily_df, monthly_df,
        start_date, end_date,
        gross_dividends, net_dividends,
        dividend_taxes_paid, dividend_buffers
    )

    logging.info("Simulation completed successfully")