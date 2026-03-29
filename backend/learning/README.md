# learning

Continuous learning engine. Every resolved incident, every human correction, every approval and rejection feeds back into the confidence engine and trust model.

---

## Files

| File | What it does |
|------|-------------|
| `decision_history.py` | SQLite database of every decision ATLAS has made. Immutable records. Provides accuracy rate queries for the confidence engine. |
| `recalibration.py` | Recalculates Factor 1 (Historical Accuracy Rate) after every resolution. Maintains an in-memory accuracy cache that N6 reads at decision time. |
| `weight_correction.py` | Accumulates L2 parameter modification diffs. After 3 same-direction diffs, adjusts the playbook default for that client. Parses L3 rejection reasons to update hypothesis weights. |
| `trust_progression.py` | Evaluates whether a client has met the criteria to advance to the next trust stage. Writes recommendations to the audit trail. Never auto-upgrades. |

---

## decision_history.py

One record per incident resolution. Separate from `audit_db.py`:
- `audit_db.py` is the compliance audit trail (regulatory, immutable, exportable)
- `decision_history.py` is the learning memory (pattern matching, accuracy rates)

### Record schema

```
client_id                   mandatory
incident_id
anomaly_type                e.g. "CONNECTION_POOL_EXHAUSTED"
service_class               e.g. "java-spring-boot"
recommended_action_id       e.g. "connection-pool-recovery-v2"
confidence_score_at_decision
routing_tier                auto / L1 / L2 / L3
human_action                approved / modified / rejected / escalated
modification_diff           JSON, what parameter changed and in what direction
rejection_reason            free text from L2/L3 engineer
resolution_outcome          success / failure / partial
actual_mttr                 seconds
recurrence_within_48h       boolean - symptomatic fix detection
```

Recurrence within 48 hours counts as a negative outcome even if immediate metrics recovered. The learning engine is honest about this.

No `update_record()` or `delete_record()` methods exist. Corrections are made by writing a new record.

### Key queries

```python
# Accuracy rate for a pattern triple
rate, count = get_accuracy_rate(client_id, anomaly_type, service_class, action_id)

# All records for a pattern
records = get_records_for_pattern(client_id, anomaly_type, service_class, action_id)

# All patterns for a client (used by recalibration on startup)
patterns = get_all_patterns_for_client(client_id)
```

---

## recalibration.py

Owns the in-memory accuracy cache. N6 reads from this cache at decision time (no I/O, must be fast).

After every resolution, `recalibrate_after_resolution()` queries decision history and updates the cache. Runs asynchronously, never blocks the resolution confirmation.

On startup, `force_recalculate_all()` rebuilds the entire cache from decision history so the confidence engine has real priors immediately.

Cold-start threshold: fewer than 5 records returns 0.50 (neutral prior). When a pattern crosses 5 records, the cold-start veto in N6 is automatically lifted.

```python
# Read (called by N6, no I/O)
accuracy, count = get_cached_accuracy(client_id, anomaly_type, service_class, action_id)

# Write (called after resolution, async)
await recalibrate_after_resolution(client_id, incident_id, anomaly_type, service_class, action_id)
```

---

## weight_correction.py

Two types of corrections:

**Parameter defaults (from L2 modifications)**
When an L2 engineer modifies a playbook parameter (e.g. increases `maxPoolSize` from 150 to 200), the diff is recorded. After 3 diffs in the same direction on the same client, the adjusted value becomes the new default for that action on that client. Bounded at ±50% of the playbook default. If the ceiling is reached, a human review flag is written to the audit log.

**Hypothesis weights (from L3 rejections)**
When an L3 engineer rejects a recommendation, the rejection reason is parsed for hypothesis type keywords (connection pool, memory, deadlock, deployment regression, etc.). The matching hypothesis type receives a -0.05 weight adjustment, capped at -0.50. N5 reads these weights when assembling the reasoning prompt.

```python
# Called by main.py after a Modify action
record_modification_diff(client_id, incident_id, action_id, modification_diff, playbook_defaults)

# Called by pipeline after a rejection
record_rejection(client_id, incident_id, action_id, rejection_reason)

# Available for N5 to read when assembling the reasoning prompt
# (functions exist in weight_correction.py but are not yet called by n5_reasoning.py)
adjusted = get_adjusted_default(client_id, action_id, "target_pool_size")
weights = get_hypothesis_weights(client_id)
```

---

## trust_progression.py

Five evidence-gated trust stages:

| Stage | Name | Requirement |
|-------|------|-------------|
| 0 | Observation | Default for new clients |
| 1 | L1 Assistance | 30 incidents + >80% confirmed correct reasoning |
| 2 | L1 Automation | 30 more incidents + >85% auto-resolution success |
| 3 | L2 Assistance | Demonstrated Stage 2 accuracy |
| 4 | L2 Automation | SDM explicit enablement required |

Class 3 actions never auto-execute at any trust level. Permanent. Non-configurable.

`evaluate_progression()` is called after every resolution. If criteria are met, it writes a recommendation to the audit trail and returns it for SDM notification. It does not automatically upgrade the trust level.

`confirm_upgrade()` is the only path through which trust level changes. It requires an SDM confirmation string and can only advance one stage at a time.

```python
# Called after every resolution (async background task)
result = await evaluate_progression(client_id, incident_id)
# result["recommendation"] is non-None if criteria are met

# Called by SDM via API after reviewing the recommendation
confirm_upgrade(client_id, new_stage=2, sdm_confirmed_by="sdm@atos.com")
```
