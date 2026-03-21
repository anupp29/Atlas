"""
Mock PaymentAPI — Spring Boot Actuator stub for ATLAS demo.

Simulates a Java Spring Boot service with HikariCP connection pool exhaustion.
Exposes the exact Actuator endpoints that connection_pool_recovery_v2.py calls.

Endpoints:
    GET  /actuator/health
    GET  /actuator
    GET  /actuator/metrics/hikaricp.connections.active
    GET  /actuator/metrics/hikaricp.connections.max
    GET  /actuator/env/spring.datasource.hikari.maximum-pool-size
    POST /actuator/env
    POST /actuator/refresh

State machine:
    - Starts in FAULT state: active=38, max=40 (95% utilisation — above 85% threshold)
    - After POST /actuator/env + POST /actuator/refresh: transitions to RECOVERING
    - After 60 seconds in RECOVERING: transitions to HEALTHY (active=12, max=150)

Run with:
    python data/mock_services/mock_payment_api.py
    (listens on port 8001 by default — matches ATLAS_MOCK_SERVICE_URL)
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Mock PaymentAPI", description="ATLAS demo stub — Spring Boot Actuator")

# ─────────────────────────────────────────────────────────────────────────────
# Mutable service state
# ─────────────────────────────────────────────────────────────────────────────

_state: dict[str, Any] = {
    "phase": "FAULT",           # FAULT | RECOVERING | HEALTHY
    "active_connections": 38,
    "max_connections": 40,
    "pool_size_override": None,
    "refresh_time": None,
    "env_overrides": {},
}


def _get_current_metrics() -> dict[str, float]:
    """Return current connection metrics based on service phase."""
    phase = _state["phase"]
    if phase == "FAULT":
        return {"active": 38.0, "max": 40.0}
    if phase == "RECOVERING":
        # Linearly recover over 60 seconds after refresh
        elapsed = time.monotonic() - (_state["refresh_time"] or time.monotonic())
        if elapsed >= 60:
            _state["phase"] = "HEALTHY"
            return {"active": 12.0, "max": _state["pool_size_override"] or 150.0}
        # Interpolate: active drops from 38 → 12 over 60 seconds
        progress = min(elapsed / 60.0, 1.0)
        active = 38.0 - (26.0 * progress)
        return {"active": round(active, 1), "max": _state["pool_size_override"] or 150.0}
    # HEALTHY
    return {"active": 12.0, "max": _state["pool_size_override"] or 150.0}


# ─────────────────────────────────────────────────────────────────────────────
# Actuator endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/actuator/health")
async def health() -> dict[str, Any]:
    """Health endpoint — returns 200 even in fault state (service is up, just degraded)."""
    phase = _state["phase"]
    status = "UP" if phase == "HEALTHY" else "DEGRADED"
    return {
        "status": status,
        "components": {
            "db": {"status": "DEGRADED" if phase == "FAULT" else "UP"},
            "hikaricp": {"status": "DEGRADED" if phase == "FAULT" else "UP"},
        },
    }


@app.get("/actuator")
async def actuator_root() -> dict[str, Any]:
    """Actuator root — confirms management endpoints are accessible."""
    return {
        "_links": {
            "health": {"href": "/actuator/health"},
            "env": {"href": "/actuator/env"},
            "refresh": {"href": "/actuator/refresh"},
            "metrics": {"href": "/actuator/metrics"},
        }
    }


@app.get("/actuator/metrics/hikaricp.connections.active")
async def hikari_active() -> dict[str, Any]:
    """HikariCP active connection count."""
    metrics = _get_current_metrics()
    return {
        "name": "hikaricp.connections.active",
        "measurements": [{"statistic": "VALUE", "value": metrics["active"]}],
    }


@app.get("/actuator/metrics/hikaricp.connections.max")
async def hikari_max() -> dict[str, Any]:
    """HikariCP maximum pool size."""
    metrics = _get_current_metrics()
    return {
        "name": "hikaricp.connections.max",
        "measurements": [{"statistic": "VALUE", "value": metrics["max"]}],
    }


@app.get("/actuator/env/spring.datasource.hikari.maximum-pool-size")
async def env_pool_size() -> dict[str, Any]:
    """Current effective pool size property."""
    override = _state["env_overrides"].get("spring.datasource.hikari.maximum-pool-size")
    sources = []
    if override:
        sources.append({
            "name": "configurationProperties",
            "properties": {
                "spring.datasource.hikari.maximum-pool-size": {"value": override}
            },
        })
    sources.append({
        "name": "applicationConfig",
        "properties": {
            "spring.datasource.hikari.maximum-pool-size": {"value": "40"}
        },
    })
    return {
        "property": "spring.datasource.hikari.maximum-pool-size",
        "propertySources": sources,
    }


class EnvOverrideRequest(BaseModel):
    name: str
    value: str


@app.post("/actuator/env")
async def set_env(body: EnvOverrideRequest) -> dict[str, str]:
    """Override an environment property."""
    _state["env_overrides"][body.name] = body.value
    if body.name == "spring.datasource.hikari.maximum-pool-size":
        try:
            _state["pool_size_override"] = int(body.value)
        except ValueError:
            pass
    return {"status": "accepted", "name": body.name, "value": body.value}


@app.post("/actuator/refresh")
async def refresh() -> list[str]:
    """Trigger @RefreshScope rebind — applies env overrides to beans."""
    changed = list(_state["env_overrides"].keys())
    if _state["pool_size_override"] and _state["phase"] == "FAULT":
        _state["phase"] = "RECOVERING"
        _state["refresh_time"] = time.monotonic()
    return changed


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("MOCK_PAYMENT_API_PORT", "8001"))
    print(f"Mock PaymentAPI starting on port {port}")
    print("State: FAULT (active=38, max=40 — 95% utilisation)")
    print("POST /actuator/env + POST /actuator/refresh to trigger recovery")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
