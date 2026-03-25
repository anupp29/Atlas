# clients

YAML configuration files for each managed client. One file per client.

---

## Files

| File | Client | Compliance | Trust level |
|------|--------|-----------|-------------|
| `financecore.yaml` | FinanceCore Ltd (UK bank) | PCI-DSS, SOX, ISO-27001 | 1 (L1 Assistance) |
| `retailmax.yaml` | RetailMax EU (e-commerce) | GDPR | 2 (L1 Automation) |

---

## Adding a new client

Copy either YAML file and fill in the values. The registry loads all `.yaml` files in this directory on startup. No code changes required.

Required fields: `client_id`, `client_name`, `auto_execute_threshold`, `max_action_class`, `compliance_frameworks`, `business_hours`, `sla_breach_thresholds`, `escalation_matrix`, `trust_level`, `applications`.

`max_action_class` must be 1 or 2. Never 3. Class 3 actions never auto-execute regardless of this setting.

`auto_execute_threshold` must be between 0.5 and 1.0. Higher means ATLAS requires more confidence before acting autonomously.
