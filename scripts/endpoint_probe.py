"""
ATLAS endpoint probe.

Validates core backend endpoints with expected status-code contracts.

Usage:
    python scripts/endpoint_probe.py
    python scripts/endpoint_probe.py --base-url http://localhost:8000 --client-id FINCORE_UK_001
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

CONTENT_TYPE_JSON = "application/json"
L2_ACTOR = "Atlas L2"


def _request(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: dict | None = None,
    timeout_s: int = 12,
) -> tuple[int | None, str]:
    """Issue a request and return (status_code, detail)."""
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url=url,
        data=payload,
        headers=headers or {},
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.status, "ok"
    except urllib.error.HTTPError as exc:
        return exc.code, "http_error"
    except urllib.error.URLError as exc:
        return None, f"transport_error: {exc.reason}"
    except Exception as exc:  # pragma: no cover
        return None, f"unexpected_error: {exc}"


def run_probe(base_url: str, client_id: str) -> int:
    tests = [
        {
            "name": "GET /api/incidents/active",
            "method": "GET",
            "url": f"{base_url}/api/incidents/active?client_id={client_id}",
            "headers": {},
            "body": None,
            "accept": {200},
        },
        {
            "name": "GET /api/playbooks",
            "method": "GET",
            "url": f"{base_url}/api/playbooks",
            "headers": {},
            "body": None,
            "accept": {200},
        },
        {
            "name": "GET /api/trust/{client_id}",
            "method": "GET",
            "url": f"{base_url}/api/trust/{client_id}",
            "headers": {},
            "body": None,
            "accept": {200},
        },
        {
            "name": "GET /api/audit",
            "method": "GET",
            "url": f"{base_url}/api/audit?client_id={client_id}",
            "headers": {},
            "body": None,
            "accept": {200},
        },
        {
            "name": "GET /api/incidents/details/{thread_id}",
            "method": "GET",
            "url": f"{base_url}/api/incidents/details/does-not-exist?client_id={client_id}",
            "headers": {"X-ATLAS-ROLE": "L2", "X-ATLAS-USER": L2_ACTOR},
            "body": None,
            "accept": {404, 403},
        },
        {
            "name": "POST /api/logs/ingest",
            "method": "POST",
            "url": f"{base_url}/api/logs/ingest",
            "headers": {"Content-Type": CONTENT_TYPE_JSON},
            "body": {
                "client_id": client_id,
                "source": "PaymentAPI",
                "severity": "ERROR",
                "line": "endpoint probe line",
                "timestamp": "2026-03-30T00:00:00Z",
            },
            "accept": {200, 422},
        },
        {
            "name": "POST /internal/llm/reason",
            "method": "POST",
            "url": f"{base_url}/internal/llm/reason",
            "headers": {"Content-Type": CONTENT_TYPE_JSON},
            "body": {},
            "accept": {422},
        },
        {
            "name": "POST /api/incidents/approve",
            "method": "POST",
            "url": f"{base_url}/api/incidents/approve",
            "headers": {"Content-Type": CONTENT_TYPE_JSON, "X-ATLAS-ROLE": "L2", "X-ATLAS-USER": L2_ACTOR},
            "body": {},
            "accept": {422},
        },
        {
            "name": "POST /api/incidents/reject",
            "method": "POST",
            "url": f"{base_url}/api/incidents/reject",
            "headers": {"Content-Type": CONTENT_TYPE_JSON, "X-ATLAS-ROLE": "L2", "X-ATLAS-USER": L2_ACTOR},
            "body": {},
            "accept": {422},
        },
        {
            "name": "POST /api/incidents/modify",
            "method": "POST",
            "url": f"{base_url}/api/incidents/modify",
            "headers": {"Content-Type": CONTENT_TYPE_JSON, "X-ATLAS-ROLE": "L2", "X-ATLAS-USER": L2_ACTOR},
            "body": {},
            "accept": {422},
        },
        {
            "name": "POST /api/trust/{client_id}/confirm-upgrade",
            "method": "POST",
            "url": f"{base_url}/api/trust/{client_id}/confirm-upgrade",
            "headers": {
                "Content-Type": CONTENT_TYPE_JSON,
                "X-ATLAS-ROLE": "SDM",
                "X-ATLAS-USER": "Atlas Manager",
            },
            "body": {},
            "accept": {200, 400, 403, 422, 500},
        },
        {
            "name": "POST /webhook/cmdb",
            "method": "POST",
            "url": f"{base_url}/webhook/cmdb",
            "headers": {"Content-Type": CONTENT_TYPE_JSON},
            "body": {},
            "accept": {422},
        },
    ]

    failures = 0
    for test in tests:
        status, detail = _request(
            method=test["method"],
            url=test["url"],
            headers=test["headers"],
            body=test["body"],
        )

        if status is None:
            failures += 1
            print(f"FAIL {test['name']} -> {detail}")
            continue

        if status in test["accept"]:
            print(f"PASS {test['name']} -> HTTP {status}")
        else:
            failures += 1
            expected = ",".join(str(code) for code in sorted(test["accept"]))
            print(f"FAIL {test['name']} -> HTTP {status} (expected one of: {expected})")

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ATLAS endpoint probe")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--client-id", default="FINCORE_UK_001", help="Client ID for scoped endpoints")
    args = parser.parse_args()
    return run_probe(base_url=args.base_url.rstrip("/"), client_id=args.client_id)


if __name__ == "__main__":
    raise SystemExit(main())
