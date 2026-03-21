"""
Pure confidence scoring functions for the ATLAS confidence engine.
No I/O. No side effects. Fully deterministic. Same inputs always produce same outputs.
Called exclusively by n6_confidence.py.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


def calculate_historical_accuracy(records: list[dict]) -> float:
    """
    Calculate empirical success rate from Decision History records.

    Args:
        records: List of decision history records for this pattern/action/client triple.
                 Each record must have a 'resolution_outcome' field: 'success'|'failure'|'partial'.

    Returns:
        Float 0.0–1.0. Returns 0.50 if fewer than 5 records (cold-start sentinel).
    """
    if len(records) < 5:
        return 0.50

    successes = sum(
        1 for r in records
        if r.get("resolution_outcome") == "success"
        and not r.get("recurrence_within_48h", False)
    )
    rate = successes / len(records)
    assert 0.0 <= rate <= 1.0, f"Historical accuracy out of range: {rate}"
    return rate


def calculate_root_cause_certainty(hypotheses: list[dict]) -> float:
    """
    Measure the gap between the top and second hypothesis confidence scores.
    Wide gap = high certainty. Narrow gap = uncertain, route to human.

    Args:
        hypotheses: List of dicts with 'confidence' float field, sorted descending.

    Returns:
        Float 0.0–1.0. Returns 0.0 if fewer than 2 hypotheses.
    """
    if not hypotheses:
        return 0.0
    if len(hypotheses) == 1:
        top = float(hypotheses[0].get("confidence", 0.0))
        return min(max(top, 0.0), 1.0)

    scores = sorted(
        [float(h.get("confidence", 0.0)) for h in hypotheses],
        reverse=True,
    )
    gap = scores[0] - scores[1]
    # Normalise: a gap of 0.5 or more = full certainty
    certainty = min(gap / 0.5, 1.0)
    assert 0.0 <= certainty <= 1.0, f"Root cause certainty out of range: {certainty}"
    return certainty


def calculate_action_safety(action_class: int) -> float:
    """
    Map action safety class to a confidence factor.

    Args:
        action_class: 1, 2, or 3.

    Returns:
        1.0 for Class 1, 0.6 for Class 2, 0.0 for Class 3.

    Raises:
        ValueError: If action_class is not 1, 2, or 3.
    """
    match action_class:
        case 1:
            return 1.0
        case 2:
            return 0.6
        case 3:
            return 0.0
        case _:
            raise ValueError(f"Invalid action_class: {action_class}. Must be 1, 2, or 3.")


def calculate_evidence_freshness(evidence_timestamp: datetime) -> float:
    """
    Linear decay from 1.0 at 0 minutes to 0.0 at 20 minutes.

    Args:
        evidence_timestamp: UTC datetime of the most recent EvidencePackage.

    Returns:
        Float 0.0–1.0.
    """
    now = datetime.now(timezone.utc)
    if evidence_timestamp.tzinfo is None:
        evidence_timestamp = evidence_timestamp.replace(tzinfo=timezone.utc)

    age_seconds = (now - evidence_timestamp).total_seconds()
    max_age_seconds = 1200.0  # 20 minutes
    freshness = max(0.0, 1.0 - (age_seconds / max_age_seconds))
    assert 0.0 <= freshness <= 1.0, f"Evidence freshness out of range: {freshness}"
    return freshness


def calculate_composite(f1: float, f2: float, f3: float, f4: float) -> float:
    """
    Weighted composite score from four factors.

    Weights:
        F1 Historical Accuracy:  30%
        F2 Root Cause Certainty: 25%
        F3 Action Safety Class:  25%
        F4 Evidence Freshness:   20%

    Args:
        f1: Historical accuracy rate (0.0–1.0)
        f2: Root cause certainty (0.0–1.0)
        f3: Action safety class score (0.0–1.0)
        f4: Evidence freshness (0.0–1.0)

    Returns:
        Float 0.0–1.0, clamped if arithmetic produces otherwise.
    """
    for name, val in (("f1", f1), ("f2", f2), ("f3", f3), ("f4", f4)):
        if not (0.0 <= val <= 1.0):
            raise ValueError(f"Factor {name} out of range: {val}")

    composite = (f1 * 0.30) + (f2 * 0.25) + (f3 * 0.25) + (f4 * 0.20)
    composite = min(max(composite, 0.0), 1.0)
    assert 0.0 <= composite <= 1.0
    return composite
