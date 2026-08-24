"""Deterministic risk score calculation.

Algorithm (documented per §13 of context.md):
    Score = 100 − sum(weight per finding), clamped to [0, 100].
    Weights: critical=10, high=7, medium=4, low=1.
"""

SEVERITY_WEIGHTS: dict[str, int] = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 1,
}


def calculate_score(severities: list[str]) -> float:
    """Return a risk score from 0 (worst) to 100 (best).

    Accepts severity strings or FindingSeverity enum instances (which are strings).
    """
    total_deduction = sum(SEVERITY_WEIGHTS.get(str(s), 0) for s in severities)
    return max(0.0, 100.0 - float(total_deduction))
