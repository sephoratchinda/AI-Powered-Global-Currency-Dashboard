"""Exchange-rate integration (Frankfurter API, ECB reference rates) + DB cache."""
from datetime import date, timedelta
import httpx
from .database import Rate

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "INR", "AED", "CHF", "CNY", "AUD", "CAD"]
HOSTS = ["https://api.frankfurter.dev/v1", "https://api.frankfurter.app"]  # 2nd = legacy fallback
PEGGED = {"AED": 3.6725}  # ECB publishes no AED rate; the dirham is pegged to the USD



def _fetch_range(start, end, symbols: str) -> dict:
    last = None
    for host in HOSTS:
        try:
            r = httpx.get(f"{host}/{start}..{end}", params={"base": "USD", "symbols": symbols},
                          timeout=30, follow_redirects=True)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # try next host
            last = e
    raise RuntimeError(f"All FX API hosts failed: {last!r}")


def sync(db, days: int = 400) -> int:
    """Download history in <=80-day chunks (the API aggregates longer ranges) and upsert."""
    symbols = ",".join(c for c in CURRENCIES if c != "USD" and c not in PEGGED)
    existing = {(r.day, r.currency) for r in db.query(Rate.day, Rate.currency).all()}
    end, cur, saved = date.today(), date.today() - timedelta(days=days), 0
    while cur <= end:
        chunk_end = min(cur + timedelta(days=80), end)
        data = _fetch_range(cur, chunk_end, symbols)
        for d, rates in data["rates"].items():
            day = date.fromisoformat(d)
            for c, v in {"USD": 1.0, **PEGGED, **rates}.items():
                if (day, c) not in existing:
                    db.add(Rate(day=day, currency=c, per_usd=v))
                    existing.add((day, c))
                    saved += 1
        db.commit()
        cur = chunk_end + timedelta(days=1)
    return saved


def load(db, days: int):
    """Return (dates, {currency: [per_usd,...]}) for the last `days`+1 complete days."""
    by = {}
    for r in db.query(Rate).order_by(Rate.day).all():
        by.setdefault(r.day, {})[r.currency] = r.per_usd
    ds = [d for d in sorted(by) if len(by[d]) == len(CURRENCIES)][-(days + 1):]
    return ds, {c: [by[d][c] for d in ds] for c in CURRENCIES}


def pair_series(db, base: str, quote: str, days: int):
    ds, m = load(db, days)
    return ds, [q / b for b, q in zip(m[base], m[quote])]