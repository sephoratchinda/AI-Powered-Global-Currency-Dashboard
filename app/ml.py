"""AI forecasting: Linear Regression vs Random Forest on lagged log-returns.
The better model on a chronological hold-out (lower MAE) is refit on all data and
used for a recursive multi-day forecast. FX is close to a random walk, so results
are reported next to a naive 'tomorrow = today' baseline for honesty."""
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

LAGS, WARM = 5, 10


def _feat(ret):
    return np.concatenate([ret[-LAGS:], [ret[-10:].mean(), ret[-10:].std()]])


def forecast(values, horizon: int = 7):
    v = np.asarray(values, float)
    ret = np.diff(np.log(v))
    if len(ret) < 40:
        raise ValueError("Not enough history to train (need 40+ days)")
    idx = np.arange(WARM, len(ret))
    X = np.array([_feat(ret[:i]) for i in idx])
    y = ret[idx]
    split = int(len(X) * 0.8)
    prev, actual = v[idx[split:]], v[idx[split:] + 1]
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=5, random_state=42),
    }
    metrics = {}
    for name, m in models.items():
        m.fit(X[:split], y[:split])
        p = m.predict(X[split:])
        pred = prev * np.exp(p)
        metrics[name] = {
            "mae_pct": float(np.mean(np.abs(pred - actual) / actual) * 100),
            "rmse": float(np.sqrt(np.mean((pred - actual) ** 2))),
            "direction_acc": float(np.mean(np.sign(p) == np.sign(y[split:])) * 100),
        }
    naive = float(np.mean(np.abs(prev - actual) / actual) * 100)
    best = min(metrics, key=lambda k: metrics[k]["mae_pct"])
    model = models[best].fit(X, y)
    r, price, out, lo, hi = list(ret), v[-1], [], [], []
    sd = float(ret.std())
    for h in range(1, horizon + 1):
        rp = float(model.predict([_feat(np.array(r))])[0])
        price *= np.exp(rp)
        r.append(rp)
        out.append(float(price))
        band = 1.96 * sd * np.sqrt(h) * price
        lo.append(float(price - band)); hi.append(float(price + band))
    return {"model": best, "metrics": metrics, "naive_mae_pct": naive,
            "forecast": out, "lower": lo, "upper": hi, "train_days": len(v)}
