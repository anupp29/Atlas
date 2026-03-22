"""
Node 5 — Reasoning Engine.

Assembles the complete ITIL 6-step reasoning prompt and calls the internal
ATLAS LLM endpoint (POST /internal/llm/reason). Falls back to pre-computed
responses if the live call fails or exceeds 8 seconds.

Inputs:  all N1–N4 state fields
Outputs: root_cause, recommended_action_id, alternative_hypotheses,
         explanation_for_engineer, technical_evidence_summary,
         confidence_factors, llm_unavailable, audit_trail entry
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import structlog

from backend.config.client_registry import get_client
from backend.execution.playbook_library import validate_action_id
from backend.orchestrator.state import AtlasState, append_audit_entry

logger = structlog.get_logger(__name__)

_LLM_TIMEOUT: float = 8.0
_FALLBACK_DIR = Path(__file__).parent.parent.parent.parent / "data" / "fallbacks"
_MIN_EXPLANATION_CHARS: int = 50


async def run(state: AtlasState) -> dict[str, Any]:
    """
    Node 5: Call the LLM reasoning endpoint and validate the output.

    LangGraph node function — returns a dict slice of fields to update.

    Args:
        state: Current AtlasState.

    Returns:
        Dict slice with reasoning results.
    """
    client_id: str = state["client_id"]
    incident_id: str = state["incident_id"]

    logger.info(
        "n5_reasoning.started",
        client_id=client_id,
        incident_id=incident_id,
    )

    llm_endpoint = os.environ.get("ATLAS_LLM_ENDPOINT", "")
    if not llm_endpoint:
        raise RuntimeError(
            "ATLAS_LLM_ENDPOINT environment variable is not set. "
            "ATLAS cannot start without an LLM endpoint."
        )

    client_config = get_client(client_id)
    context_payload = _build_context_payload(state, client_config)

    # ── Attempt live LLM call ─────────────────────────────────────────────────
    llm_result: dict | None = await _call_llm_endpoint(llm_endpoint, context_payload, client_id)

    # ── Fallback to pre-computed response ─────────────────────────────────────
    if llm_result is None:
        llm_result = _load_fallback(client_id)

    # ── If all fails: route to human review with raw evidence ─────────────────
    if llm_result is None:
        logger.error(
            "n5_reasoning.all_sources_failed",
            client_id=client_id,
            incident_id=incident_id,
        )
        return {
            "llm_unavailable": True,
            "root_cause": "LLM unavailable — raw evidence attached for human review.",
            "recommended_action_id": "",
            "alternative_hypotheses": [],
            "explanation_for_engineer": "LLM endpoint unavailable and no fallback found. Please review raw evidence.",
            "technical_evidence_summary": "",
            "confidence_factors": {},
            "routing_decision": "L2_L3_ESCALATION",
            "audit_trail": append_audit_entry(state, {
                "node": "n5_reasoning",
                "actor": "ATLAS_AUTO",
                "action": "llm_unavailable_escalated",
                "reason": "All LLM sources failed, no fallback available",
            }),
        }

    # ── Validate output ───────────────────────────────────────────────────────
    validated = _validate_and_extract(llm_result, client_id)
    if validated is None:
        # Validation failed — treat as unavailable
        logger.error(
            "n5_reasoning.validation_failed",
            client_id=client_id,
            incident_id=incident_id,
        )
        fallback = _load_fallback(client_id)
        if fallback:
            validated = _validate_and_extract(fallback, client_id)

    if validated is None:
        return {
            "llm_unavailable": True,
            "root_cause": "LLM output validation failed.",
            "recommended_action_id": "",
            "alternative_hypotheses": [],
            "explanation_for_engineer": "LLM output failed validation. Routing to human review.",
            "technical_evidence_summary": "",
            "confidence_factors": {},
            "routing_decision": "L2_L3_ESCALATION",
            "audit_trail": append_audit_entry(state, {
                "node": "n5_reasoning",
                "actor": "ATLAS_AUTO",
                "action": "llm_validation_failed_escalated",
            }),
        }

    logger.info(
        "n5_reasoning.complete",
        client_id=client_id,
        incident_id=incident_id,
        recommended_action=validated["recommended_action_id"],
        hypotheses_count=len(validated["alternative_hypotheses"]),
    )

    return {
        "root_cause": validated["root_cause"],
        "recommended_action_id": validated["recommended_action_id"],
        "alternative_hypotheses": validated["alternative_hypotheses"],
        "explanation_for_engineer": validated["explanation_for_engineer"],
        "technical_evidence_summary": validated["technical_evidence_summary"],
        "confidence_factors": validated.get("confidence_factors", {}),
        "llm_unavailable": False,
        "audit_trail": append_audit_entry(state, {
            "node": "n5_reasoning",
            "actor": "ATLAS_AUTO",
            "action": "reasoning_complete",
            "recommended_action_id": validated["recommended_action_id"],
            "root_cause_summary": validated["root_cause"][:100],
            "hypotheses_count": len(validated["alternative_hypotheses"]),
        }),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LLM call
# ─────────────────────────────────────────────────────────────────────────────

async def _call_llm_endpoint(
    endpoint: str,
    payload: dict[str, Any],
    client_id: str,
) -> dict | None:
    """
    POST to the internal ATLAS LLM endpoint with 8-second timeout.
    Returns parsed JSON dict or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=_LLM_TIMEOUT) as client:
            resp = await client.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(
            "n5_reasoning.llm_bad_status",
            client_id=client_id,
            status=resp.status_code,
            body=resp.text[:200],
        )
        return None
    except httpx.TimeoutException:
        logger.warning(
            "n5_reasoning.llm_timeout",
            client_id=client_id,
            timeout=_LLM_TIMEOUT,
        )
        return None
    except Exception as exc:
        logger.error(
            "n5_reasoning.llm_error",
            client_id=client_id,
            error=str(exc),
        )
        return None


def _load_fallback(client_id: str) -> dict | None:
    """
    Load pre-computed fallback response from /data/fallbacks/.
    Tries two filename conventions:
      1. {client_id_lower}_incident_response.json  (e.g. fincore_uk_001_incident_response.json)
      2. {client_name_slug}_incident_response.json  (e.g. financecore_incident_response.json)
    Returns None if no file exists or the file is malformed.
    """
    # Build candidate filenames — most specific first
    slug = client_id.lower().replace("-", "_")
    candidates = [
        _FALLBACK_DIR / f"{slug}_incident_response.json",
    ]
    # Also try a short-name variant by taking the first segment before the first underscore
    # e.g. FINCORE_UK_001 → fincore, RETAILMAX_EU_002 → retailmax
    short = slug.split("_")[0]
    candidates.append(_FALLBACK_DIR / f"{short}_incident_response.json")

    # Scan the fallback directory for any file containing the short name
    if _FALLBACK_DIR.exists():
        for f in _FALLBACK_DIR.glob("*_incident_response.json"):
            if short in f.stem and f not in candidates:
                candidates.append(f)

    for path in candidates:
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            logger.info("n5_reasoning.fallback_loaded", path=str(path), client_id=client_id)
            return data
        except Exception as exc:
            logger.error("n5_reasoning.fallback_load_error", path=str(path), error=str(exc))

    logger.warning(
        "n5_reasoning.fallback_not_found",
        tried=[str(c) for c in candidates],
        client_id=client_id,
    )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def _validate_and_extract(raw: dict, client_id: str) -> dict | None:
    """
    Validate all required fields in the LLM output.
    Returns cleaned dict or None if validation fails.
    """
    required = {
        "root_cause", "recommended_action_id", "alternative_hypotheses",
        "explanation_for_engineer", "technical_evidence_summary",
    }
    missing = required - raw.keys()
    if missing:
        logger.error("n5_reasoning.missing_fields", missing=list(missing), client_id=client_id)
        return None

    # Validate recommended_action_id against playbook library
    action_id: str = raw["recommended_action_id"]
    if action_id and not validate_action_id(action_id):
        logger.error(
            "n5_reasoning.invalid_action_id",
            action_id=action_id,
            client_id=client_id,
        )
        return None

    # Validate explanation length
    explanation: str = raw["explanation_for_engineer"]
    if len(explanation) < _MIN_EXPLANATION_CHARS:
        logger.error(
            "n5_reasoning.explanation_too_short",
            length=len(explanation),
            minimum=_MIN_EXPLANATION_CHARS,
            client_id=client_id,
        )
        return None

    # Validate alternative_hypotheses structure
    hypotheses = raw["alternative_hypotheses"]
    if not isinstance(hypotheses, list):
        logger.error("n5_reasoning.hypotheses_not_list", client_id=client_id)
        return None

    return {
        "root_cause": str(raw["root_cause"]),
        "recommended_action_id": action_id,
        "alternative_hypotheses": hypotheses,
        "explanation_for_engineer": explanation,
        "technical_evidence_summary": str(raw["technical_evidence_summary"]),
        "confidence_factors": raw.get("confidence_factors", {}),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Prompt assembly
# ─────────────────────────────────────────────────────────────────────────────

def _build_context_payload(state: AtlasState, client_config: dict[str, Any]) -> dict[str, Any]:
    """
    Assemble the complete reasoning context payload for the LLM endpoint.
    Follows the ITIL 6-step structure from ARCHITECTURE.md.
    """
    evidence_packages = state["evidence_packages"]
    blast_radius = state.get("blast_radius", [])
    deployments = state.get("recent_deployments", [])
    graph_matches = state.get("historical_graph_matches", [])
    semantic_matches = state.get("semantic_matches", [])
    priority = state.get("incident_priority", "P3")
    situation_summary = state.get("situation_summary", "")

    # Separate client-specific from cross-client semantic matches
    client_matches = [m for m in semantic_matches if m.get("source") != "cross_client_anonymised"]
    cross_matches = [m for m in semantic_matches if m.get("source") == "cross_client_anonymised"]

    return {
        "incident_context": {
            "client_id": state["client_id"],
            "incident_id": state["incident_id"],
            "priority": priority,
            "correlation_type": state.get("correlation_type", "ISOLATED_ANOMALY"),
            "situation_summary": situation_summary,
        },
        "evidence_summary": [
            {
                "agent_id": p.get("agent_id"),
                "service_name": p.get("service_name"),
                "anomaly_type": p.get("anomaly_type"),
                "detection_confidence": p.get("detection_confidence"),
                "shap_feature_values": p.get("shap_feature_values", {}),
                "preliminary_hypothesis": p.get("preliminary_hypothesis"),
                "severity_classification": p.get("severity_classification"),
                "supporting_log_samples": p.get("supporting_log_samples", [])[:3],
            }
            for p in evidence_packages
        ],
        "blast_radius": blast_radius[:10],  # cap to avoid context overflow
        "recent_deployments": deployments[:5],
        "historical_graph_matches": graph_matches[:5],
        "semantic_matches": {
            "client_specific": client_matches[:3],
            "cross_client_anonymised": cross_matches[:3],
        },
        "compliance_profile": {
            "frameworks": client_config.get("compliance_frameworks", []),
            "max_action_class": client_config.get("max_action_class", 1),
            "trust_level": client_config.get("trust_level", 0),
        },
        "reasoning_instructions": (
            "Perform ITIL-structured root cause analysis in 6 steps: "
            "1) Symptom characterisation — what exactly is failing and how. "
            "2) Impact assessment — which services and users are affected. "
            "3) Change correlation — does any recent deployment explain this. "
            "4) Historical match validation — does this match a known pattern. "
            "5) Hypothesis ranking — rank all plausible causes with evidence for and against. "
            "6) Resolution recommendation — recommend the most appropriate playbook action. "
            "Return structured JSON with all required fields."
        ),
    }
