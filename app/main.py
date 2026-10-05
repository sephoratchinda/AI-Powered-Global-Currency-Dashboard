"""FastAPI application: REST API + static dashboard.  Run: uvicorn app.main:app --reload"""
import threading, time, logging
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import analytics as an, fx, ml
from .database import Alert, SessionLocal, get_db, init_db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fx")
LAST_ERROR = {"msg": None}
CUR = fx.CURRENCIES


def _sync_job():
    while True:
        db = SessionLocal()
        ok = False
        try:
            n = fx.sync(db, 400)
            LAST_ERROR["msg"], ok = None, True
            log.info("Synced %s new rows", n)
        except Exception as e:  # network down -> keep serving cached data
            LAST_ERROR["msg"] = repr(e)
            log.error("Sync failed: %r", e)
        finally:
            db.close()
        time.sleep(1800 if ok else 15)   # retry quickly until the first sync works


@asynccontextmanager
async def lifespan(app):
    init_db()
    threading.Thread(target=_sync_job, daemon=True).start()
    yield


app = FastAPI(title="AI Global Currency Intelligence API", lifespan=lifespan)


def check_pair(*codes):
    for c in codes:
        if c not in CUR:
            raise HTTPException(400, f"Unsupported currency '{c}'. Use one of {CUR}")


def series(db, base, quote, days):
    check_pair(base, quote)
    ds, vals = fx.pair_series(db, base, quote, days)
    if len(vals) < 3:
                raise HTTPException(503, f"No rate data yet. Last sync error: {LAST_ERROR['msg'] or 'none - first sync still running'}")
    return ds, vals

@app.get("/api/status")
def status(db=Depends(get_db)):
    from .database import Rate
    return {"rate_rows": db.query(Rate).count(), "last_sync_error": LAST_ERROR["msg"]}

@app.get("/api/currencies")
def currencies():
    return CUR


@app.get("/api/latest")
def latest(base: str = "USD", db=Depends(get_db)):
    check_pair(base)
    out = []
    for q in CUR:
        if q == base:
            continue
        ds, v = series(db, base, q, 5)
        out.append({"quote": q, "rate": v[-1], "change_pct": an.pct_change(v[-1], v[-2]), "date": str(ds[-1])})
    return {"base": base, "rates": out}


@app.get("/api/convert")
def convert(amount: float = Query(ge=0), from_: str = Query(alias="from"), to: str = "INR", db=Depends(get_db)):
    ds, v = series(db, from_, to, 3)
    return {"amount": amount, "from": from_, "to": to, "rate": v[-1], "result": amount * v[-1], "date": str(ds[-1])}


@app.get("/api/history")
def history(base: str = "USD", quote: str = "INR", days: int = Query(30, ge=2, le=365), db=Depends(get_db)):
    ds, v = series(db, base, quote, days)
    gl = [an.pct_change(b, a) for a, b in zip(v, v[1:])]
    vol = an.volatility(v)
    return {"dates": [str(d) for d in ds], "values": v, "daily_change_pct": gl,
            "volatility": vol, "volatility_label": an.vol_label(vol),
            "period_change_pct": an.pct_change(v[-1], v[0])}


@app.get("/api/forecast")
def forecast(base: str = "USD", quote: str = "INR", horizon: int = Query(7, ge=1, le=30), db=Depends(get_db)):
    ds, v = series(db, base, quote, 365)
    try:
        res = ml.forecast(v, horizon)
    except ValueError as e:
        raise HTTPException(422, str(e))
    d, dates = ds[-1], []
    while len(dates) < horizon:
        d += timedelta(days=1)
        if d.weekday() < 5:
            dates.append(str(d))
    return {**res, "dates": dates, "last_value": v[-1]}


@app.get("/api/heatmap")
def heatmap(days: int = Query(30, ge=2, le=365), db=Depends(get_db)):
    ds, m = fx.load(db, days)
    if len(ds) < 3:
        raise HTTPException(503, "No rate data yet")
    mat = {a: {b: (an.pct_change((m[b][-1] / m[a][-1]), (m[b][0] / m[a][0])) if a != b else None) for b in CUR} for a in CUR}
    strength = {a: sum(x for x in mat[a].values() if x is not None) / (len(CUR) - 1) for a in CUR}
    return {"currencies": CUR, "matrix": mat, "strength": dict(sorted(strength.items(), key=lambda kv: -kv[1]))}


SAMPLE = ["Dollar gains as US growth beats expectations", "Euro slips on weak industrial output and recession fears",
          "Sterling rallies on strong services data", "Aussie dollar drops on China slowdown fear"]


@app.get("/api/sentiment")
def sentiment():
    live, titles = True, []
    try:
        r = httpx.get("https://news.google.com/rss/search?q=forex+currency+markets&hl=en-US&gl=US&ceid=US:en", timeout=10)
        r.raise_for_status()
        titles = [i.findtext("title") for i in ET.fromstring(r.text).iter("item")][:12]
    except Exception:
        live, titles = False, SAMPLE
    items = [{"headline": t, "score": an.score_headline(t)} for t in titles if t]
    tot = sum(i["score"] for i in items)
    return {"live": live, "overall": "Positive" if tot > 0 else "Negative" if tot < 0 else "Neutral", "items": items}


class AlertIn(BaseModel):
    pair: str = Field(pattern=r"^[A-Z]{3}/[A-Z]{3}$")
    direction: Literal["above", "below"]
    threshold: float = Field(gt=0)


@app.get("/api/alerts")
def list_alerts(db=Depends(get_db)):
    return [{"id": a.id, "pair": a.pair, "direction": a.direction, "threshold": a.threshold} for a in db.query(Alert).filter_by(active=True)]


@app.post("/api/alerts", status_code=201)
def add_alert(a: AlertIn, db=Depends(get_db)):
    check_pair(*a.pair.split("/"))
    row = Alert(**a.model_dump())
    db.add(row); db.commit()
    return {"id": row.id}


@app.delete("/api/alerts/{aid}")
def del_alert(aid: int, db=Depends(get_db)):
    row = db.get(Alert, aid)
    if not row:
        raise HTTPException(404, "Alert not found")
    db.delete(row); db.commit()
    return {"deleted": aid}


@app.get("/api/alerts/check")
def check_alerts(db=Depends(get_db)):
    hits = []
    for a in db.query(Alert).filter_by(active=True):
        b, q = a.pair.split("/")
        _, v = series(db, b, q, 3)
        if (a.direction == "above" and v[-1] > a.threshold) or (a.direction == "below" and v[-1] < a.threshold):
            hits.append(f"{a.pair} = {v[-1]:.4f} is {a.direction} {a.threshold}")
    moves = []
    for i, a in enumerate(CUR):
        for b in CUR[i + 1:]:
            _, v = series(db, a, b, 3)
            c = an.pct_change(v[-1], v[-2])
            if abs(c) > 1:
                moves.append(f"{a}/{b} moved {c:+.2f}% in a day")
    return {"threshold_alerts": hits, "significant_moves": moves}


@app.post("/api/sync")
def manual_sync(db=Depends(get_db)):
    try:
        return {"new_rows": fx.sync(db, 400)}
    except Exception as e:
        raise HTTPException(502, f"Upstream API error: {e}")


app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True), name="ui")
