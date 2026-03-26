"""
ATLAS Health Check — verifies all services are reachable before a demo.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --wait   # poll until all services are up
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone

SERVICES = [
    {
        "name": "ATLAS Backend",
        "url": "http://localhost:8000/docs",
        "method": "GET",
        "expect_status": 200,
        "critical": True,
    },
    {
        "name": "LLM Endpoint",
        "url": "http://localhost:8000/docs",
        "method": "GET",
        # Just verify the server is up — actual LLM call requires Cerebras key
        "expect_status": 200,
        "critical": False,
    },
    {
        "name": "Mock PaymentAPI",
        "url": "http://localhost:8001/actuator/health",
        "method": "GET",
        "expect_status": 200,
        "critical": False,
    },
    {
        "name": "Frontend (Vite)",
        "url": "http://localhost:5173",
        "method": "GET",
        "expect_status": 200,
        "critical": False,
    },
    {
        "name": "Active Incidents API",
        "url": "http://localhost:8000/api/incidents/active",
        "method": "GET",
        "expect_status": 200,
        "critical": True,
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


def run_checks(wait: bool = False, timeout_s: int = 120) -> bool:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    print(f"\n  {CYAN}{BOLD}ATLAS Health Check{RESET}  {GRAY}{ts}{RESET}")
    print(f"  {'─' * 50}")

    if not wait:
        all_ok = True
        for svc in SERVICES:
            ok, detail = check_service(svc)
            icon = f"{GREEN}✓{RESET}" if ok else (f"{YELLOW}⚠{RESET}" if not svc["critical"] else f"{RED}✗{RESET}")
            label = svc["name"].ljust(24)
            print(f"  {icon}  {label}  {GRAY}{detail}{RESET}")
            if not ok and svc["critical"]:
                all_ok = False
        print()
        return all_ok

    # Wait mode — poll until all critical services are up or timeout
    deadline = time.monotonic() + timeout_s
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        all_critical_ok = True
        results = []
        for svc in SERVICES:
            ok, detail = check_service(svc)
            results.append((svc, ok, detail))
            if not ok and svc["critical"]:
                all_critical_ok = False

        # Print status on first attempt and every 10s
        if attempt == 1 or attempt % 10 == 0:
            print(f"\n  {GRAY}Attempt {attempt} — {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}{RESET}")
            for svc, ok, detail in results:
                icon = f"{GREEN}✓{RESET}" if ok else f"{YELLOW}…{RESET}"
                print(f"  {icon}  {svc['name'].ljust(24)}  {GRAY}{detail}{RESET}")

        if all_critical_ok:
            print(f"\n  {GREEN}{BOLD}All critical services are up.{RESET}\n")
            return True

        time.sleep(3)

    print(f"\n  {RED}Timeout after {timeout_s}s — some services did not start.{RESET}\n")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATLAS service health check")
    parser.add_argument("--wait", action="store_true", help="Poll until all critical services are up (max 120s)")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout in seconds for --wait mode")
    args = parser.parse_args()

    ok = run_checks(wait=args.wait, timeout_s=args.timeout)
    sys.exit(0 if ok else 1)
