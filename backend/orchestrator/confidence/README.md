# confidence

Pure Python confidence scoring. No I/O. No LLM. Deterministic. Same inputs always produce the same output.

---

## Files

| File | What it does |
|------|-------------|
| `scorer.py` | Four factor calculation functions. Called exclusively by N6. |
| `vetoes.py` | Eight independent veto check functions. `run_all_vetoes()` returns the complete list. |

---

## scorer.py

### calculate_historical_accuracy(records)

Empirical success rate from Decision History records for a pattern/action/client triple.

- Fewer than 5 records: returns 0.50 (cold-start sentinel, neutral prior)
- Recurrence within 48 hours counts as failure even if immediate metrics recovered
- Returns float 0.0 to 1.0

### calculate_root_cause_certainty(hypotheses)

Gap between top and second hypothesis confidence scores, normalised to 0-1.

- Wide gap (0.5+): returns 1.0 (certain)
- Tied hypotheses: returns 0.0 (uncertain, route to human)
- Single hypothesis: returns that hypothesis's confidence score

### calculate_action_safety(action_class)

Maps action class to a factor score:
- Class 1: 1.0
- Class 2: 0.6
- Class 3: 0.0

Raises `ValueError` for any other value.

### calculate_evidence_freshness(evidence_timestamp)

Linear decay from 1.0 at 0 minutes to 0.0 at 20 minutes. Evidence older than 20 minutes returns 0.0.

### calculate_composite(f1, f2, f3, f4)

Weighted combination:
- F1 Historical Accuracy: 30%
- F2 Root Cause Certainty: 25%
- F3 Action Safety Class: 25%
- F4 Evidence Freshness: 20%

All inputs must be 0.0 to 1.0. Raises `ValueError` otherwise. Output is clamped to [0.0, 1.0].

---

## vetoes.py

Eight independent checks. Each returns `None` (no veto) or a plain-English string (veto fired). All vetoes always run. `run_all_vetoes()` returns the complete list, not just the first.

| Veto | Condition |
|------|-----------|
| 1 | Active change freeze window (recurring daily or absolute datetime range) |
| 2 | Business hours + PCI-DSS or SOX compliance |
| 3 | Class 3 action type (runs first per spec) |
| 4 | P1 severity |
| 5 | Compliance-sensitive services touched (GDPR or PCI-DSS) |
| 6 | Same action on same service within last 2 hours |
| 7 | Knowledge graph stale over 24 hours |
| 8 | Fewer than 5 historical records (cold start) |

Every veto string is user-facing and display-ready. Engineers see exactly why ATLAS stopped.

### run_all_vetoes()

```python
fired = run_all_vetoes(
    client_config=client_config,
    current_time=datetime.now(timezone.utc),
    action_class=1,
    incident_priority="P2",
    evidence_packages=[...],
    client_id="FINCORE_UK_001",
    action_id="connection-pool-recovery-v2",
    service_name="PaymentAPI",
    last_2_hours_actions=[...],
    last_graph_update_timestamp=datetime(...),
    historical_record_count=5,
)
# fired is a list of plain-English strings, one per fired veto
# Empty list means no vetoes fired
```
