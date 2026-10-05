"""Pure analytics helpers (easy to unit-test)."""
import math

POS = {"rally", "gain", "gains", "strong", "surge", "growth", "optimism", "rise", "rises", "beat", "boost", "steady", "recovers"}
NEG = {"fall", "falls", "slump", "weak", "recession", "inflation", "risk", "drop", "drops", "fear", "fears", "cut", "slides", "tumbles"}


def pct_change(new: float, old: float) -> float:
    return (new / old - 1) * 100


def volatility(values) -> float:
    """Annualised volatility (%) from daily log returns (252 trading days)."""
    r = [math.log(b / a) for a, b in zip(values, values[1:])]
    if len(r) < 2:
        return 0.0
    m = sum(r) / len(r)
    sd = math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))
    return sd * math.sqrt(252) * 100


def vol_label(v: float) -> str:
    return "Low" if v < 5 else "Moderate" if v < 10 else "High"


def score_headline(text: str) -> int:
    words = [w.strip(".,:;!?'\"()").lower() for w in text.split()]
    s = sum(w in POS for w in words) - sum(w in NEG for w in words)
    return 1 if s > 0 else -1 if s < 0 else 0
