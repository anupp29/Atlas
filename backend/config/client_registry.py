"""
Loads and validates the thin ATLAS configuration for every client.
Single source of client-specific behaviour settings.
All other modules read client config from here — never directly from files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)

_KNOWN_FRAMEWORKS = frozenset({"PCI-DSS", "SOX", "GDPR", "ISO-27001", "HIPAA"})
_CLIENTS_DIR = Path(__file__).parent / "clients"

# In-memory registry: client_id → config dict
_REGISTRY: dict[str, dict[str, Any]] = {}


def load_all_clients() -> None:
    """
    Load and validate all client YAML configs from /backend/config/clients/.
    Called once on application startup. Fails loudly on any validation error.
    """
    if not _CLIENTS_DIR.exists():
        raise FileNotFoundError(f"Clients config directory not found: {_CLIENTS_DIR}")

    yaml_files = list(_CLIENTS_DIR.glob("*.yaml"))
    if not yaml_files:
        raise FileNotFoundError(f"No client YAML files found in {_CLIENTS_DIR}")

    for yaml_file in yaml_files:
        with open(yaml_file, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        validated = _validate_client_config(raw, yaml_file.name)
        _REGISTRY[validated["client_id"]] = validated
        logger.info("client_registry.loaded", client_id=validated["client_id"], file=yaml_file.name)

    logger.info("client_registry.all_loaded", count=len(_REGISTRY))


def get_client(client_id: str) -> dict[str, Any]:
    """
    Return the full config for a client.

    Args:
        client_id: The client identifier.

    Returns:
        Client config dict (read-only — do not mutate).

    Raises:
        KeyError: If client_id is not registered.
    """
    if client_id not in _REGISTRY:
        raise KeyError(
            f"Client '{client_id}' is not registered. "
            f"Known clients: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[client_id]


def get_all_client_ids() -> list[str]:
    """Return all registered client IDs."""
    return list(_REGISTRY.keys())


def update_trust_level(client_id: str, new_level: int, sdm_confirmed_by: str) -> None:
    """
    Update the trust_level for a client. Only callable by trust_progression.py.
    Requires SDM confirmation to be recorded.

    Args:
        client_id: Client to update.
        new_level: New trust stage (0–4).
        sdm_confirmed_by: Name/ID of the SDM who confirmed the upgrade.

    Raises:
        KeyError: If client_id not registered.
        ValueError: If new_level is invalid or is a downgrade without explicit flag.
    """
    if client_id not in _REGISTRY:
        raise KeyError(f"Client '{client_id}' not found in registry.")
    if not (0 <= new_level <= 4):
        raise ValueError(f"Invalid trust level: {new_level}. Must be 0–4.")
    if not sdm_confirmed_by:
        raise ValueError("SDM confirmation is required to update trust level.")

    current = _REGISTRY[client_id]["trust_level"]
    _REGISTRY[client_id]["trust_level"] = new_level
    logger.info(
        "client_registry.trust_level_updated",
        client_id=client_id,
        from_level=current,
        to_level=new_level,
        sdm_confirmed_by=sdm_confirmed_by,
    )


def _validate_client_config(raw: dict[str, Any], filename: str) -> dict[str, Any]:
    """
    Validate all required fields in a client config.
    Raises ValueError with a precise message on any violation.
    """
    required_fields = [
        "client_id", "client_name", "auto_execute_threshold",
        "max_action_class", "compliance_frameworks", "business_hours",
        "sla_breach_thresholds", "escalation_matrix", "trust_level", "applications",
    ]
    for field in required_fields:
        if field not in raw:
            raise ValueError(f"[{filename}] Missing required field: '{field}'")

    threshold = raw["auto_execute_threshold"]
    if not (0.5 <= threshold <= 1.0):
        raise ValueError(
            f"[{filename}] auto_execute_threshold must be between 0.5 and 1.0, got {threshold}"
        )

    max_class = raw["max_action_class"]
    if max_class not in (1, 2):
        raise ValueError(
            f"[{filename}] max_action_class must be 1 or 2. "
            f"Value 3 is never permitted — Class 3 actions never auto-execute. Got: {max_class}"
        )

    frameworks = raw["compliance_frameworks"]
    unknown = set(frameworks) - _KNOWN_FRAMEWORKS
    if unknown:
        raise ValueError(
            f"[{filename}] Unknown compliance frameworks: {unknown}. "
            f"Known frameworks: {_KNOWN_FRAMEWORKS}"
        )

    trust = raw["trust_level"]
    if not (0 <= trust <= 4):
        raise ValueError(f"[{filename}] trust_level must be 0–4, got {trust}")

    return raw
