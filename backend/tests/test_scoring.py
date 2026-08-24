"""Unit tests for the deterministic risk scoring algorithm."""

from app.services.scoring import SEVERITY_WEIGHTS, calculate_score


def test_perfect_score_with_no_findings() -> None:
    assert calculate_score([]) == 100.0


def test_single_critical_deducts_correctly() -> None:
    assert calculate_score(["critical"]) == 90.0


def test_single_high_deducts_correctly() -> None:
    assert calculate_score(["high"]) == 93.0


def test_single_medium_deducts_correctly() -> None:
    assert calculate_score(["medium"]) == 96.0


def test_single_low_deducts_correctly() -> None:
    assert calculate_score(["low"]) == 99.0


def test_mixed_severities() -> None:
    # critical=10, high=7, medium=4, low=1 → deduction=22
    result = calculate_score(["critical", "high", "medium", "low"])
    assert result == 78.0


def test_score_clamps_at_zero() -> None:
    assert calculate_score(["critical"] * 20) == 0.0


def test_unknown_severity_is_ignored() -> None:
    assert calculate_score(["unknown_severity"]) == 100.0


def test_weights_match_spec() -> None:
    assert SEVERITY_WEIGHTS["critical"] == 10
    assert SEVERITY_WEIGHTS["high"] == 7
    assert SEVERITY_WEIGHTS["medium"] == 4
    assert SEVERITY_WEIGHTS["low"] == 1
