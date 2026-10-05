"""Run:  python diagnose.py   (from the project root, venv activated)"""
import traceback

def step(name, fn):
    try:
        print(f"[ .. ] {name}"); r = fn(); print(f"[ OK ] {name} -> {r}\n"); return True
    except Exception:
        print(f"[FAIL] {name}\n{traceback.format_exc()}\n"); return False

def api():
    import httpx
    r = httpx.get("https://api.frankfurter.dev/v1/latest?base=USD", timeout=20, follow_redirects=True)
    return r.status_code, r.json()["date"]

def db():
    from app.database import engine, init_db
    init_db()
    with engine.connect() as c:
        return str(c.exec_driver_sql("select version()").scalar())[:60]

def sync():
    from app.database import SessionLocal, Rate
    from app import fx
    s = SessionLocal()
    n = fx.sync(s, 30)
    return f"{n} new rows, total {s.query(Rate).count()}"

if step("1. Python can reach the FX API", api) and step("2. PostgreSQL connection + tables", db):
    step("3. Download + save 30 days of rates", sync)