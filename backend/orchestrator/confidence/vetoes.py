"""
Hard veto conditions for the ATLAS confidence engine.
Each function returns None (no veto) or a plain-English string (veto fired).
All vetoes run independently. run_all_vetoes returns the complete list.
Called exclusively by n6_confidence.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def check_change_freeze_window(
    client_config: dict[str, Any],
    current_time: datetime,
) -> str | None:
    """
    Veto 1: Fire if current time falls within a configured change freeze window.

    Supports two window formats:
    1. Absolute range: {"start": "2026-12-24T00:00:00", "end": "2027-01-02T23:59:59"}
    2. Recurring daily: {"start": "09:00", "end": "17:00", "weekdays_only": true, "recurring_daily": true}

    Args:
        client_config: Client configuration dict with 'change_freeze_windows' list.
        current_time: Current UTC datetime.

    Returns:
        Veto explanation string or None.
    """
    freeze_windows: list[dict] = client_config.get("change_freeze_windows", [])
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    for window in freeze_windows:
        start_raw = window.get("start")
        end_raw = window.get("end")
        if not start_raw or not end_raw:
            continue

        # Recurring daily window (time-only strings like "09:00")
        if window.get("recurring_daily"):
            try:
                start_time = datetime.strptime(str(start_raw), "%H:%M").time()
                end_time = datetime.strptime(str(end_raw), "%H:%M").time()
            except ValueError:
                continue
            weekdays_only = window.get("weekdays_only", False)
            if weekdays_only and current_time.weekday() >= 5:
                # Weekend — window does not apply
                continue
            current_tod = current_time.time().replace(tzinfo=None)
            if start_time <= current_tod <= end_time:
                label = window.get("label", "recurring daily freeze window")
                return (
                    f"Change freeze window active ({label}: {start_raw}–{end_raw}). "
                    "No automated actions are permitted during this period."
                )
            continue

        # Absolute datetime range
        if isinstance(start_raw, str):
            try:
                start = datetime.fromisoformat(start_raw)
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        else:
            start = start_raw

        if isinstance(end_raw, str):
            try:
                end = datetime.fromisoformat(end_raw)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        else:
            end = end_raw

        if start <= current_time <= end:
            label = window.get("label", "")
            label_str = f" ({label})" if label else ""
            return (
                f"Change freeze window{label_str} is active until {end.isoformat()}. "
                "No automated actions are permitted during this period."
            )
    return None


def check_business_hours_compliance(
    client_config: dict[str, Any],
    current_time: datetime,
    action_class: int,
) -> str | None:
    """
    Veto 2: Fire if PCI-DSS or SOX client AND current time is within business hours.
    Only applies to Class 1 and Class 2 actions (Class 3 has its own veto).

    Args:
        client_config: Client config with 'compliance_frameworks' and 'business_hours'.
        current_time: Current UTC datetime.
        action_class: Action safety class (1, 2, or 3).

    Returns:
        Veto explanation string or None.
    """
    frameworks: list[str] = client_config.get("compliance_frameworks", [])
    regulated = any(f in frameworks for f in ("PCI-DSS", "SOX"))
    if not regulated:
        return None

    business_hours: dict = client_config.get("business_hours", {})
    if not business_hours:
        return None

    start_hour: int = business_hours.get("start_hour", 8)
    end_hour: int = business_hours.get("end_hour", 18)
    weekdays_only: bool = business_hours.get("weekdays_only", True)

    if weekdays_only and current_time.weekday() >= 5:
        return None

    if start_hour <= current_time.hour < end_hour:
        frameworks_str = " and ".join(f for f in frameworks if f in ("PCI-DSS", "SOX"))
        return (
            f"{frameworks_str} compliance requires dual engineer sign-off for production "
            "configuration changes during business hours. Human approval is mandatory."
        )
    return None


def check_action_class_three(action_class: int) -> str | None:
    """
    Veto 3: Fire unconditionally if action class is 3.
    Class 3 actions never auto-execute. Permanent ceiling. Non-configurable.

    Args:
        action_class: Action safety class integer.

    Returns:
        Veto explanation string or None.
    """
    if action_class == 3:
        return (
            "Class 3 action detected (database operations, network changes, or production data). "
            "Class 3 actions never auto-execute under any circumstances. "
            "This is a permanent architectural constraint, not a configuration setting."
        )
    return None


def check_p1_severity(incident_priority: str) -> str | None:
    """
    Veto 4: Fire if incident priority is P1.
    P1 incidents always require human review regardless of confidence score.

    Args:
        incident_priority: Priority string e.g. "P1", "P2", "P3", "P4".

    Returns:
        Veto explanation string or None.
    """
    if incident_priority == "P1":
        return (
            "P1 severity incident requires immediate human escalation. "
            "Automated execution is not permitted for P1 incidents regardless of confidence score."
        )
    return None


def check_compliance_data_touched(
    evidence_packages: list[dict],
    client_config: dict[str, Any],
) -> str | None:
    """
    Veto 5: Fire if any evidence involves services flagged as compliance-sensitive.

    Args:
        evidence_packages: List of EvidencePackage dicts from the incident.
        client_config: Client config with 'compliance_frameworks' and 'applications'.

    Returns:
        Veto explanation string or None.
    """
    frameworks: list[str] = client_config.get("compliance_frameworks", [])
    gdpr_active = "GDPR" in frameworks
    pci_active = "PCI-DSS" in frameworks

    if not (gdpr_active or pci_active):
        return None

    compliance_services: set[str] = set()
    for app in client_config.get("applications", []):
        if app.get("compliance_sensitive", False):
            compliance_services.add(app.get("name", ""))

    affected_services = {ep.get("service_name", "") for ep in evidence_packages}
    touched = affected_services & compliance_services

    if touched:
        frameworks_str = ", ".join(f for f in frameworks if f in ("GDPR", "PCI-DSS"))
        return (
            f"Compliance-sensitive services affected: {', '.join(sorted(touched))}. "
            f"{frameworks_str} data handling requirements mandate human review "
            "before any automated action on these services."
        )
    return None


def check_duplicate_action(
    client_id: str,
    action_id: str,
    service_name: str,
    last_2_hours_actions: list[dict],
) -> str | None:
    """
    Veto 6: Fire if the same action was attempted on the same service within the last 2 hours.
    Prevents repeated automated attempts that may indicate a deeper unresolved issue.

    Args:
        client_id: Client identifier.
        action_id: Playbook action ID being considered.
        service_name: Target service name.
        last_2_hours_actions: List of recent audit records for this client.

    Returns:
        Veto explanation string or None.
    """
    for action in last_2_hours_actions:
        if (
            action.get("client_id") == client_id
            and action.get("action_id") == action_id
            and action.get("service_name") == service_name
        ):
            executed_at = action.get("timestamp", "unknown time")
            return (
                f"Action '{action_id}' was already executed on '{service_name}' "
                f"at {executed_at} (within the last 2 hours). "
                "Repeated automated execution may indicate a symptomatic fix. "
                "Human review required to assess root cause."
            )
    return None


def check_graph_freshness(last_graph_update_timestamp: datetime | None) -> str | None:
    """
    Veto 7: Fire if the knowledge graph has not been updated in more than 24 hours.
    Stale graph means blast radius and deployment correlation data cannot be trusted.

    Args:
        last_graph_update_timestamp: UTC datetime of last Neo4j webhook update, or None.

    Returns:
        Veto explanation string or None.
    """
    if last_graph_update_timestamp is None:
        return (
            "Knowledge graph has never been updated via CMDB webhook. "
            "Graph data cannot be trusted for structural reasoning. Human review required."
        )

    now = datetime.now(timezone.utc)
    if last_graph_update_timestamp.tzinfo is None:
        last_graph_update_timestamp = last_graph_update_timestamp.replace(tzinfo=timezone.utc)

    age_hours = (now - last_graph_update_timestamp).total_seconds() / 3600
    if age_hours > 24:
        return (
            f"Knowledge graph is {age_hours:.1f} hours stale (last update: "
            f"{last_graph_update_timestamp.isoformat()}). "
            "Blast radius and deployment correlation data may be inaccurate. "
            "Human review required until graph is refreshed."
        )
    return None


def check_cold_start(historical_record_count: int) -> str | None:
    """
    Veto 8: Fire if fewer than 5 historical records exist for this pattern/action/client triple.
    Insufficient precedent to trust automated execution.

    Args:
        historical_record_count: Number of matching Decision History records.

    Returns:
        Veto explanation string or None.
    """
    if historical_record_count < 5:
        return (
            f"Insufficient historical precedent: only {historical_record_count} resolved cases "
            "match this pattern/action/client combination (minimum 5 required). "
            "This decision will be captured as seed data to build future confidence."
        )
    return None


def run_all_vetoes(
    client_config: dict[str, Any],
    current_time: datetime,
    action_class: int,
    incident_priority: str,
    evidence_packages: list[dict],
    client_id: str,
    action_id: str,
    service_name: str,
    last_2_hours_actions: list[dict],
    last_graph_update_timestamp: datetime | None,
    historical_record_count: int,
) -> list[str]:
    """
    Run all 8 veto checks. Returns the complete list of fired veto explanations.
    check_action_class_three runs first per spec, but ALL vetoes always run.
    Empty list means no vetoes fired.

    Returns:
        List of plain-English veto explanation strings (user-facing, display-ready).
    """
    fired: list[str] = []

    # Veto 3 runs first per spec
    v = check_action_class_three(action_class)
    if v:
        fired.append(v)

    checks = [
        check_change_freeze_window(client_config, current_time),
        check_business_hours_compliance(client_config, current_time, action_class),
        check_p1_severity(incident_priority),
        check_compliance_data_touched(evidence_packages, client_config),
        check_duplicate_action(client_id, action_id, service_name, last_2_hours_actions),
        check_graph_freshness(last_graph_update_timestamp),
        check_cold_start(historical_record_count),
    ]

    for result in checks:
        if result is not None:
            fired.append(result)

    return fired
