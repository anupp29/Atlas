"""
Internal ATLAS LLM endpoint — powered by Cerebras.
Runs at POST /internal/llm/reason.
Receives the structured context payload from n5_reasoning.py and returns
the validated JSON schema ATLAS expects.

Start with: uvicorn backend.llm.cerebras_server:app --port 8000
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import structlog
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

logger = structlog.get_logger(__name__)

app = FastAPI(title="ATLAS LLM — Cerebras", version="1.0.0")

# ── Cerebras client (initialised once on startup) ─────────────────────────────
_cerebras: Cerebras | None = None


@app.on_event("startup")
def _startup() -> None:
    global _cerebras
    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        raise RuntimeError("CEREBRAS_API_KEY environment variable is not set.")
    _cerebras = Cerebras(api_key=api_key)
    logger.info("cerebras_server.started", model=_get_model())


def _get_model() -> str:
    return os.environ.get("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507")


# ── Request / Response models ─────────────────────────────────────────────────

class ReasonRequest(BaseModel):
    incident_context: dict[str, Any]
    evidence_summary: list[dict[str, Any]]
    blast_radius: list[dict[str, Any]] = []
    recent_deployments: list[dict[str, Any]] = []
    historical_graph_matches: list[dict[str, Any]] = []
    semantic_matches: dict[str, Any] = {}
    compliance_profile: dict[str, Any] = {}
    reasoning_instructions: str = ""


# ── Endpoint ──────────────────────────────────────────────────────────────────

@app.post("/internal/llm/reason")
async def reason(req: ReasonRequest) -> dict[str, Any]:
    """
    Accept ATLAS reasoning context, call Cerebras, return structured JSON.
    """
    if _cerebras is None:
        raise HTTPException(status_code=503, detail="Cerebras client not initialised.")

    prompt = _build_prompt(req)

    logger.info(
        "cerebras_server.reasoning",
        client_id=req.incident_context.get("client_id"),
        incident_id=req.incident_context.get("incident_id"),
        model=_get_model(),
    )

    try:
        response = _cerebras.chat.completions.create(
            model=_get_model(),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ATLAS, an expert AIOps reasoning engine. "
                        "You perform ITIL-structured root cause analysis. "
                        "You MUST respond with valid JSON only — no markdown, no explanation outside the JSON. "
                        "Your response must be a single JSON object matching the required schema exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_completion_tokens=2048,
        )
    except Exception as exc:
        logger.error("cerebras_server.api_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Cerebras API error: {exc}")

    raw_text: str = response.choices[0].message.content or ""
    logger.info(
        "cerebras_server.response_received",
        client_id=req.incident_context.get("client_id"),
        tokens_used=getattr(response.usage, "total_tokens", "?"),
    )

    result = _parse_json_response(raw_text, req.incident_context.get("client_id", ""))
    return result


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(req: ReasonRequest) -> str:
    """Build the ITIL 6-step reasoning prompt from the context payload."""
    ctx = req.incident_context
    evidence = req.evidence_summary
    deployments = req.recent_deployments
    graph_matches = req.historical_graph_matches
    semantic = req.semantic_matches
    compliance = req.compliance_profile

    # Summarise evidence
    evidence_lines = []
    for ep in evidence:
        evidence_lines.append(
            f"  - Agent: {ep.get('agent_id')} | Service: {ep.get('service_name')} | "
            f"Anomaly: {ep.get('anomaly_type')} | Confidence: {ep.get('detection_confidence', 0):.2f} | "
            f"Hypothesis: {ep.get('preliminary_hypothesis', 'N/A')}"
        )

    # Summarise deployments
    deploy_lines = []
    for d in deployments[:3]:
        deploy_lines.append(
            f"  - Change: {d.get('change_id')} | {d.get('description', d.get('change_description', ''))} | "
            f"By: {d.get('deployed_by')} | Risk: {d.get('cab_risk_rating', d.get('risk_rating', 'N/A'))}"
        )

    # Summarise historical matches
    hist_lines = []
    for h in graph_matches[:3]:
        hist_lines.append(
            f"  - Incident: {h.get('incident_id')} | Root cause: {h.get('root_cause')} | "
            f"Resolution: {h.get('resolution')} | MTTR: {h.get('mttr_minutes')} min"
        )

    # Semantic matches
    client_sem = semantic.get("client_specific", [])
    sem_lines = []
    for s in client_sem[:2]:
        sem_lines.append(
            f"  - ID: {s.get('incident_id')} | Similarity: {s.get('similarity_score', 0):.2f} | "
            f"Description: {s.get('description', '')[:100]}"
        )

    # Available playbooks based on anomaly types
    anomaly_types = list({ep.get("anomaly_type", "") for ep in evidence})
    playbook_hint = _get_playbook_hint(anomaly_types)

    prompt = f"""ATLAS ITIL Root Cause Analysis

INCIDENT CONTEXT:
  Priority: {ctx.get('priority', 'P3')}
  Correlation Type: {ctx.get('correlation_type', 'ISOLATED_ANOMALY')}
  Summary: {ctx.get('situation_summary', 'N/A')}
  Client: {ctx.get('client_id')}

EVIDENCE FROM SPECIALIST AGENTS:
{chr(10).join(evidence_lines) if evidence_lines else '  None'}

RECENT DEPLOYMENTS (last 7 days):
{chr(10).join(deploy_lines) if deploy_lines else '  None'}

HISTORICAL GRAPH MATCHES:
{chr(10).join(hist_lines) if hist_lines else '  None'}

SEMANTIC SIMILARITY MATCHES:
{chr(10).join(sem_lines) if sem_lines else '  None'}

COMPLIANCE PROFILE:
  Frameworks: {', '.join(compliance.get('frameworks', []))}
  Max Action Class: {compliance.get('max_action_class', 1)}
  Trust Level: {compliance.get('trust_level', 0)}

AVAILABLE PLAYBOOKS:
{playbook_hint}

TASK: Perform ITIL root cause analysis in 6 steps and return ONLY this JSON:

{{
  "root_cause": "<concise root cause statement>",
  "confidence_factors": {{
    "deployment_correlation": <0.0-1.0>,
    "historical_match": <0.0-1.0>,
    "evidence_strength": <0.0-1.0>
  }},
  "recommended_action_id": "<exact playbook id from available playbooks above>",
  "alternative_hypotheses": [
    {{
      "hypothesis": "<hypothesis text>",
      "evidence_for": "<supporting evidence>",
      "evidence_against": "<contradicting evidence>",
      "confidence": <0.0-1.0>
    }}
  ],
  "explanation_for_engineer": "<minimum 80 character L2-level explanation of what happened, why, and what the recommended action will do>",
  "technical_evidence_summary": "<technical summary of all evidence reviewed>"
}}

Return ONLY the JSON object. No markdown. No preamble."""

    return prompt


def _get_playbook_hint(anomaly_types: list[str]) -> str:
    """
    Return relevant playbook IDs based on detected anomaly types.
    Queries the playbook library directly — never hardcoded.
    """
    from backend.execution.playbook_library import get_playbooks_for_anomaly, list_playbooks

    seen: set[str] = set()
    hints: list[str] = []

    for anomaly_type in anomaly_types:
        for pb in get_playbooks_for_anomaly(anomaly_type):
            if pb.playbook_id not in seen and pb.auto_execute_eligible:
                seen.add(pb.playbook_id)
                hints.append(
                    f"  - {pb.playbook_id} "
                    f"({pb.name}, Class {pb.action_class}, "
                    f"target: {pb.target_technology})"
                )

    # If no anomaly-specific match, list all auto-eligible playbooks as fallback
    if not hints:
        for pb in list_playbooks():
            if pb.auto_execute_eligible and pb.playbook_id not in seen:
                seen.add(pb.playbook_id)
                hints.append(
                    f"  - {pb.playbook_id} "
                    f"({pb.name}, Class {pb.action_class}, "
                    f"target: {pb.target_technology})"
                )

    return "\n".join(hints) if hints else "  - No eligible playbooks found"


# ── JSON parser ───────────────────────────────────────────────────────────────

def _parse_json_response(raw: str, client_id: str) -> dict[str, Any]:
    """
    Extract and parse JSON from the model response.
    Handles cases where the model wraps JSON in markdown code fences.
    """
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Find the outermost JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        logger.error("cerebras_server.no_json_found", client_id=client_id, raw=raw[:200])
        raise HTTPException(status_code=502, detail="Model did not return valid JSON.")

    json_str = text[start:end]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.error(
            "cerebras_server.json_parse_error",
            client_id=client_id,
            error=str(exc),
            raw=json_str[:300],
        )
        raise HTTPException(status_code=502, detail=f"JSON parse error: {exc}")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": _get_model()}
