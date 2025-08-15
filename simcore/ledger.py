from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_EVEN, getcontext
from pathlib import Path
from typing import List, Optional
from datetime import date as date_cls
import csv

getcontext().prec = 28  # robust precision

def D(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))

def q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

@dataclass
class DividendEvent:
    date: date_cls
    symbol: str
    qty: Decimal
    dividend_per_share_gross: Decimal
    currency: str
    fx_to_base: Decimal
    withholding_rate: Decimal
    domestic_tax_rate: Decimal
    broker_fee: Decimal
    dividend_gross: Optional[Decimal] = None
    withholding_tax: Optional[Decimal] = None
    domestic_tax: Optional[Decimal] = None
    dividend_net: Optional[Decimal] = None
    notes: str = ""

class DividendsLedger:
    def __init__(self, base_currency: str = "EUR"):
        self.base_currency = base_currency
        self._events: List[DividendEvent] = []

    def record(
        self,
        date, symbol, qty, dps_gross, currency,
        fx_to_base=1, withholding_rate=0, domestic_tax_rate=0, broker_fee=0, notes=""
    ):
        ev = DividendEvent(
            date=date,
            symbol=symbol,
            qty=D(qty),
            dividend_per_share_gross=D(dps_gross),
            currency=currency,
            fx_to_base=D(fx_to_base),
            withholding_rate=D(withholding_rate),
            domestic_tax_rate=D(domestic_tax_rate),
            broker_fee=D(broker_fee),
            notes=notes or ""
        )
        self._events.append(ev)

    def finalize(self) -> List[DividendEvent]:
        for ev in self._events:
            gross_local = ev.qty * ev.dividend_per_share_gross
            gross_base  = gross_local * ev.fx_to_base
            wh = gross_base * ev.withholding_rate
            dom = (gross_base - wh) * ev.domestic_tax_rate
            net = gross_base - wh - dom - ev.broker_fee

            ev.dividend_gross   = q2(gross_base)
            ev.withholding_tax  = q2(wh)
            ev.domestic_tax     = q2(dom)
            ev.dividend_net     = q2(net)
            ev.fx_to_base       = q2(ev.fx_to_base)
            ev.dividend_per_share_gross = q2(ev.dividend_per_share_gross)
            ev.qty              = q2(ev.qty)
            ev.broker_fee       = q2(ev.broker_fee)
            ev.withholding_rate = q2(ev.withholding_rate)
            ev.domestic_tax_rate= q2(ev.domestic_tax_rate)
        return self._events

    def to_csv(self, out_path: Path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        events = self.finalize()
        fieldnames = [
            "date","symbol","qty","dividend_per_share_gross","currency","fx_to_base",
            "withholding_rate","domestic_tax_rate","broker_fee",
            "dividend_gross","withholding_tax","domestic_tax","dividend_net","notes"
        ]
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for ev in events:
                row = asdict(ev)
                row["date"] = ev.date.isoformat()
                for k, v in row.items():
                    if isinstance(v, Decimal):
                        row[k] = f"{v:.2f}"
                w.writerow(row)