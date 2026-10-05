# AI-Powered Global Currency Intelligence Dashboard

FastAPI + SQLAlchemy + scikit-learn backend, Chart.js dashboard. Data: Frankfurter API (ECB reference rates,
updated once per working day – "live" here means latest published ECB rate).

## Features

Live rates · converter · interactive charts (7D/30D/90D/1Y) · daily gain/loss · volatility indicator ·
AI forecast (Linear Regression vs Random Forest, auto-selected, 95% band) · strength heatmap ·
news sentiment · threshold + big-move alerts · responsive layout · DB cache (works offline after first sync).

## Install & run (VS Code)

```bash
python -m venv venv
venv\Scripts\activate          # Windows      |  source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 (first start downloads ~1 year of rates – wait ~10 s).
Interactive API docs: http://127.0.0.1:8000/docs · Tests: `pytest -v`

### PostgreSQL (pgAdmin4)

Copy `.env.example` to `.env` and set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD (the same
credentials you use to log in to pgAdmin4). The app creates the database and tables itself; refresh
pgAdmin (Servers → Databases → Refresh) to see `fx_dashboard` with tables `rates` and `alerts`.
Set `DB_TYPE=sqlite` to run without PostgreSQL.

## Architecture

Browser (frontend/) ⇄ FastAPI (app/main.py) ⇄ {fx.py → Frankfurter API, database.py → SQLite/PostgreSQL,
analytics.py, ml.py}. See docs/UML.md and docs/schema.sql.

## API reference

| Endpoint                                                             | Purpose                                               |
| -------------------------------------------------------------------- | ----------------------------------------------------- |
| GET /api/latest?base=USD                                             | latest rate + daily % change for all quotes           |
| GET /api/convert?amount=100&from=USD&to=INR                          | conversion                                            |
| GET /api/history?base&quote&days                                     | series, daily gain/loss, volatility                   |
| GET /api/forecast?base&quote&horizon                                 | AI forecast, band, model metrics                      |
| GET /api/heatmap?days=30                                             | strength matrix + ranking                             |
| GET /api/sentiment                                                   | headline sentiment (Google News RSS, sample fallback) |
| GET/POST /api/alerts, DELETE /api/alerts/{id}, GET /api/alerts/check | alert CRUD + evaluation                               |
| POST /api/sync                                                       | force data refresh                                    |

Errors: 400 bad currency · 422 bad input/not enough data · 502 upstream API failed · 503 no data yet.

## User manual

1. Choose a **Base** currency; cards show rates and daily change. Click a card to chart it.
2. Pick the pair and timeframe above the chart; dashed green line = 7-day AI forecast with shaded 95% band.
3. **Converter**: type an amount, choose currencies, ⇅ swaps them.
4. **Volatility/forecast panel**: compare model errors with the naive baseline – if the model doesn't beat it, say so in your report.
5. **Alerts**: choose pair, above/below, threshold → Add. A pop-up appears when triggered (checked every 60 s).

## Limitations (mention in your viva)

ECB rates are daily, not tick-by-tick; FX is near a random walk so forecast accuracy is modest; sentiment is lexicon-based.
Possible upgrades: LSTM with TensorFlow, VADER/FinBERT sentiment, email/SMS alerts, user accounts.

# Running Procee of System

python -m venv venv
venv\Scripts\activate

      pip install -r requirements.txt

            venv\Scripts\activate        # activate virtual environment first
         uvicorn app.main:app --reload    # just run this to open project on local browser

         Run the automated tests with    python -m pytest -v
