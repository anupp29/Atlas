# mock_services

Lightweight mock services for local testing. These simulate the real services that playbooks interact with during development and demo runs.

---

## Files

| File | What it simulates |
|------|-----------------|
| `mock_payment_api.py` | Java Spring Boot PaymentAPI with Spring Boot Actuator endpoints |

---

## mock_payment_api.py

Simulates the FinanceCore PaymentAPI for local playbook testing. Exposes the endpoints that `connection_pool_recovery_v2.py` calls:

| Endpoint | Method | What it does |
|----------|--------|-------------|
| `/actuator/health` | GET | Returns 503 when fault is active, 200 when healthy |
| `/actuator` | GET | Returns available actuator endpoints |
| `/actuator/env` | POST | Accepts pool size configuration changes |
| `/actuator/refresh` | POST | Applies configuration changes |
| `/metrics/connections` | GET | Returns current connection count (decreases after pool size is restored) |

### Fault simulation

The mock starts in a faulted state (connection pool exhausted, returning 503). After receiving a valid pool size update via `/actuator/env` + `/actuator/refresh`, it transitions to recovery mode and the connection count metric starts decreasing.

### Running

```bash
python data/mock_services/mock_payment_api.py
# Starts on http://localhost:8080
```

The playbook's `target_service_url` must point to `http://localhost:8080` for local testing. In the real demo, this points to the actual PaymentAPI health endpoint configured in `financecore.yaml`.
