"""
ATLAS Health Check — verifies all services are reachable before a demo.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --wait   # poll until all services are up
    python scripts/health_check.py --client-id FINCORE_UK_001
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_FRONTEND_URL = "http://localhost:5173"
DEFAULT_PAYMENT_API_URL = "http://localhost:8001"
DEFAULT_CLIENT_ID = "FINCORE_UK_001"


def build_services(
    backend_url: str,
    frontend_url: str,
    payment_api_url: str,
    client_id: str,
) -> list[dict]:
    """Build service checks using the current API surface."""
    return [
        {
            "name": "ATLAS API Docs",
            "url": f"{backend_url}/docs",
            "method": "GET",
            "expect_status": 200,
            "critical": True,
        },
        {
            "name": "Active Incidents API",
            "url": f"{backend_url}/api/incidents/active?client_id={client_id}",
            "method": "GET",
            "expect_status": 200,
            "critical": True,
        },
        {
            "name": "Playbook Library API",
            "url": f"{backend_url}/api/playbooks",
            "method": "GET",
            "expect_status": 200,
            "critical": True,
        },
        {
            "name": "Trust API",
            "url": f"{backend_url}/api/trust/{client_id}",
            "method": "GET",
            "expect_status": 200,
            "critical": True,
        },
        {
            "name": "Internal LLM Route",
            "url": f"{backend_url}/internal/llm/reason",
            "method": "POST",
            # Empty object should fail validation quickly if route is present.
            "body": {},
            "expect_status": 422,
            "critical": False,
        },
        {
            "name": "Mock PaymentAPI",
            "url": f"{payment_api_url}/actuator/health",
            "method": "GET",
            "expect_status": 200,
            "critical": False,
        },
        {
            "name": "Frontend (Vite)",
            "url": frontend_url,
            "method": "GET",
            "expect_status": 200,
            "critical": False,
        },
    ]

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def check_service(svc: dict) -> tuple[bool, str]:
    """Return (ok, detail_message)."""
    url = svc["url"]
    method = svc.get("method", "GET")
    body = svc.get("body")
    expected = svc.get("expect_status", 200)
    if isinstance(expected, int):
        expected = [expected]

    try:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            if status in expected:
                return True, f"HTTP {status}"
            return False, f"HTTP {status} (expected {expected})"
    except urllib.error.HTTPError as e:
        if e.code in expected:
            return True, f"HTTP {e.code}"
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"Connection refused — {e.reason}"
    except Exception as e:
        return False, str(e)


def _status_icon(ok: bool, critical: bool, wait_mode: bool = False) -> str:
    """Render service status icon for normal and wait modes."""
    if ok:
        return f"{GREEN}✓{RESET}"
    if wait_mode:
        return f"{YELLOW}…{RESET}"
    if critical:
        return f"{RED}✗{RESET}"
    return f"{YELLOW}⚠{RESET}"


def _run_once(services: list[dict]) -> bool:
    """Execute one pass of checks and print status lines."""
    all_ok = True
    for svc in services:
        ok, detail = check_service(svc)
        icon = _status_icon(ok, svc["critical"])
        label = svc["name"].ljust(24)
        print(f"  {icon}  {label}  {GRAY}{detail}{RESET}")
        if not ok and svc["critical"]:
            all_ok = False
    print()
    return all_ok


def _run_wait_loop(services: list[dict], timeout_s: int) -> bool:
    """Poll checks until all critical services are up or timeout expires."""
    deadline = time.monotonic() + timeout_s
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        all_critical_ok = True
        results: list[tuple[dict, bool, str]] = []

        for svc in services:
            ok, detail = check_service(svc)
            results.append((svc, ok, detail))
            if not ok and svc["critical"]:
                all_critical_ok = False

        # Print status on first attempt and every ~30s (10 x 3s poll)
        if attempt == 1 or attempt % 10 == 0:
            print(f"\n  {GRAY}Attempt {attempt} — {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}{RESET}")
            for svc, ok, detail in results:
                icon = _status_icon(ok, svc["critical"], wait_mode=True)
                print(f"  {icon}  {svc['name'].ljust(24)}  {GRAY}{detail}{RESET}")

        if all_critical_ok:
            print(f"\n  {GREEN}{BOLD}All critical services are up.{RESET}\n")
            return True

        time.sleep(3)

    print(f"\n  {RED}Timeout after {timeout_s}s — some services did not start.{RESET}\n")
    return False


def run_checks(
    wait: bool = False,
    timeout_s: int = 120,
    backend_url: str = DEFAULT_BACKEND_URL,
    frontend_url: str = DEFAULT_FRONTEND_URL,
    payment_api_url: str = DEFAULT_PAYMENT_API_URL,
    client_id: str = DEFAULT_CLIENT_ID,
) -> bool:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    print(f"\n  {CYAN}{BOLD}ATLAS Health Check{RESET}  {GRAY}{ts}{RESET}")
    print(f"  {'─' * 50}")
    services = build_services(
        backend_url=backend_url,
        frontend_url=frontend_url,
        payment_api_url=payment_api_url,
        client_id=client_id,
    )

    if not wait:
        return _run_once(services)

    # Wait mode — poll until all critical services are up or timeout.
    return _run_wait_loop(services, timeout_s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATLAS service health check")
    parser.add_argument("--wait", action="store_true", help="Poll until all critical services are up (max 120s)")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds for --wait mode")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL, help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})")
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL, help=f"Frontend URL (default: {DEFAULT_FRONTEND_URL})")
    parser.add_argument("--payment-api-url", default=DEFAULT_PAYMENT_API_URL, help=f"Mock PaymentAPI base URL (default: {DEFAULT_PAYMENT_API_URL})")
    parser.add_argument("--client-id", default=DEFAULT_CLIENT_ID, help=f"Client ID used by client-scoped endpoints (default: {DEFAULT_CLIENT_ID})")
    args = parser.parse_args()

    ok = run_checks(
        wait=args.wait,
        timeout_s=args.timeout,
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        payment_api_url=args.payment_api_url,
        client_id=args.client_id,
    )
    sys.exit(0 if ok else 1)
