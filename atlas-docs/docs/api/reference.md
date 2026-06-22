# API Reference

All routes are defined in `backend/main.py`. The base URL in local development is
`http://localhost:8000`; WebSocket channels use the same host with `ws://` (or
`wss://` behind TLS), derived automatically by the frontend's
[`atlas-config.ts`](../codebase/frontend-reference.md#key-library-files).

## Authentication Model

ATLAS uses a lightweight, header-based role model rather than a login session for
its mutation endpoints — deliberately simple for an MVP while still enforcing who
is allowed to do what:

| Header | Required on | Purpose |
|---|---|---|
| `X-ATLAS-ROLE` | All mutation and detail endpoints | One of `L1`, `L2`, `L3`, `SDM`, `CLIENT`. Rejected with `403` if missing or unrecognised. |
| `X-ATLAS-USER` | Approve / Reject / Modify | The acting engineer's identity. Must match the `approver` / `rejector` / `modifier` field in the request body — a mismatch is rejected with `403`, preventing one user from submitting an action under another's name. |

| Endpoint | Roles allowed |
|---|---|
| `POST /api/incidents/approve` | `L1`, `L2`, `L3`, `SDM` |
| `POST /api/incidents/reject` | `L1`, `L2`, `L3`, `SDM` |
| `POST /api/incidents/modify` | `L2`, `L3`, `SDM` (L1 cannot modify parameters) |
| `POST /api/trust/{client_id}/confirm-upgrade` | `SDM` only |

---

## REST Endpoints

=== "Webhook"

    #### `POST /webhook/cmdb`
    Receives a ServiceNow change-record webhook and writes/merges a
    `Deployment` node into Neo4j, linked to the affected `Service` via
    `MODIFIED_CONFIG_OF`. This is the mechanism that keeps the
    [knowledge graph](../architecture/graph-schema.md) seconds-fresh. Broadcasts
    a `cmdb_change` event to the global activity feed on success.

    **Request body:** `client_id`, `change_id`, `change_description`,
    `deployed_by`, `timestamp`, `risk_rating`, `cab_approved_by`,
    `affected_service`.

    | Status | Meaning |
    |---|---|
    | `200` | Accepted, graph updated |
    | `422` | `client_id` missing |
    | `503` | Neo4j write failed |

=== "Incident Actions"

    #### `POST /api/incidents/approve`
    Resumes a suspended pipeline with `human_action: "approved"`. If a
    cryptographic `token` is supplied (PCI-DSS/SOX dual sign-off — see
    [Compliance Gate](../escalation/human-workflow.md#compliance-gate-dual-cryptographic-approval)),
    it is validated against the incident ID before resuming; an invalid or
    mismatched token returns `403`.

    #### `POST /api/incidents/reject`
    Resumes the pipeline with `human_action: "rejected"` and a mandatory
    `reason`. The reason is fed to the
    [weight-correction learning signal](../architecture/learning-engine.md#weight-correction).

    #### `POST /api/incidents/modify`
    Resumes the pipeline with `human_action: "modified"` and a
    `modified_parameters` diff. The diff is recorded via
    `record_modification_diff()` against the playbook's default parameters —
    the input to the "3+ times same direction" default-update rule.

    All three endpoints validate `client_id`, broadcast an `incident_updated`
    event over the client's incident WebSocket, and (for approve/reject) an
    activity-feed event.

=== "Incident Queries"

    #### `GET /api/incidents/active`
    Returns all in-flight incidents, optionally filtered by `?client_id=`.

    #### `GET /api/incidents/details/{thread_id}`
    Returns a full state snapshot for one incident, including audit trail
    count and last-updated timestamp. Falls back to durable LangGraph
    checkpoint storage (`get_incident_state`) if the incident is no longer in
    the in-memory active set. Returns `404` if the thread truly doesn't exist,
    `403` if a `client_id` filter is supplied that doesn't match the
    incident's actual tenant.

=== "Audit & Trust"

    #### `GET /api/audit`
    Queries the immutable audit log for a `client_id` within an optional
    `from_time` / `to_time` ISO-8601 window (defaults to "today" through now).

    #### `GET /api/trust/{client_id}`
    Returns the client's current trust stage, progression metrics toward the
    next stage, and SLA uptime percentage — the read-only endpoint clients can
    surface in their own dashboards (see
    [Trust Progression](../architecture/learning-engine.md#trust-progression)).

    #### `POST /api/trust/{client_id}/confirm-upgrade`
    **SDM only.** Advances a client exactly one trust stage, writes an
    immutable audit record, and broadcasts a `trust_upgrade` activity event.
    Returns `400` if the client is already at Stage 4.

=== "Playbooks & Ingestion"

    #### `GET /api/playbooks`
    Returns the complete registered playbook library — see
    [Execution Engine](../architecture/execution-engine.md#the-playbook-library-mvp).

    #### `POST /api/logs/ingest`
    The entry point used by fault-injection scripts (and any external log
    source) to push raw events into the ingestion pipeline — the route
    `scripts/trigger_financecore_e2e.py` calls to exercise the full pipeline
    end to end.

=== "Internal"

    #### `POST /internal/llm/reason`
    The reasoning endpoint called exclusively by
    [Node 5](../architecture/orchestrator.md#node-5-reasoning-engine). Not
    intended for direct external use — documented here for completeness, since
    it can also run as a standalone service (`backend/llm/cerebras_server.py`).

---

## WebSocket Channels

| Channel | Scope | Behaviour |
|---|---|---|
| `WS /ws/logs/{client_id}` | Per client | Live log stream, pushed by the background log generator. Sends a `ping` keepalive every 30s. |
| `WS /ws/incidents/{client_id}` | Per client | Sends the client's current active incidents immediately on connect, then pushes `incident_updated` events as the pipeline progresses. |
| `WS /ws/activity` | Global | The portfolio-wide activity feed consumed by every dashboard — `cmdb_change`, `human_action`, `trust_upgrade`, and incident lifecycle events. |

All three channels reject an unknown `client_id` at connection time with WebSocket
close code `4403`, rather than accepting the connection and silently sending
nothing.

[:octicons-arrow-right-24: See how the frontend consumes these endpoints](../codebase/frontend-reference.md){ .md-button }
