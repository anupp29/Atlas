# config

Client configuration system. Loads and validates YAML configs for every client. All other modules read client config from here.

---

## Files

| File | What it does |
|------|-------------|
| `client_registry.py` | Loads all YAML files from `clients/`, validates every field, stores them in an in-memory registry. Provides `get_client()`, `get_all_client_ids()`, and `update_trust_level()`. |
| `clients/financecore.yaml` | FinanceCore Ltd config. UK bank. PCI-DSS, SOX, ISO-27001. Trust level 1. Auto-execute threshold 0.92. |
| `clients/retailmax.yaml` | RetailMax EU config. E-commerce. GDPR only. Trust level 2. Auto-execute threshold 0.82. |

---

## What the config holds

Only what CMDB cannot provide:

| Field | Purpose |
|-------|---------|
| `client_id` | Unique identifier used as the multi-tenancy key everywhere |
| `auto_execute_threshold` | Minimum confidence score for autonomous execution (0.5 to 1.0) |
| `max_action_class` | Highest action class eligible for automation. Must be 1 or 2. Never 3. |
| `compliance_frameworks` | PCI-DSS, SOX, GDPR, ISO-27001, HIPAA. Controls veto behaviour. |
| `business_hours` | Start/end hour, weekdays only, timezone. Used by the PCI-DSS/SOX veto. |
| `change_freeze_windows` | Recurring daily or absolute datetime ranges. No automation during these. |
| `sla_breach_thresholds` | Minutes to breach per priority (P1/P2/P3/P4). |
| `escalation_matrix` | L1/L2/L3/SDM contact and Slack channel per tier. |
| `trust_level` | Current trust stage (0-4). Only `trust_progression.py` may update this. |
| `applications` | List of services with tech type, version, criticality, compliance sensitivity. |

---

## Adding a new client

Create a new YAML file in `clients/` following the same structure as `financecore.yaml`. The registry loads all `.yaml` files in the directory on startup. No code changes required.

`load_all_clients()` is called once by `main.py` during the startup lifespan. If you add a new YAML file while the server is running, you must restart the server for it to take effect. `get_client()` will raise `KeyError` for any client that was not loaded at startup.

---

## Validation

`client_registry.py` validates every field on load and raises `ValueError` with a precise message on any violation. The application refuses to start if any client config is invalid.

Key rules enforced:
- `auto_execute_threshold` must be between 0.5 and 1.0
- `max_action_class` must be 1 or 2 (never 3 - Class 3 actions never auto-execute)
- `compliance_frameworks` must be from the known set
- `trust_level` must be 0 to 4

---

## Trust level updates

Only `backend/learning/trust_progression.py` may call `update_trust_level()`. It requires an SDM confirmation string. Trust level can only advance one stage at a time. Downgrades are blocked without an explicit override.
