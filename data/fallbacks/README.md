# fallbacks

Pre-computed LLM responses for demo reliability. N5 loads these in under 200ms if the live LLM call exceeds 8 seconds or fails.

These files are committed to the repository. Regenerate them if you change the seed data, the reasoning prompt, or the playbook IDs — otherwise N5 will load a fallback with a mismatched `recommended_action_id` and the validation will fail.

---

## Files

| File | Client | Expected action ID |
|------|--------|-------------------|
| `financecore_incident_response.json` | FinanceCore | `connection-pool-recovery-v2` |
| `retailmax_incident_response.json` | RetailMax | `redis-memory-policy-rollback-v1` |

---

## When to regenerate

Regenerate both files if any of the following change:
- The Neo4j seed data (different deployment IDs, different historical incidents)
- The ChromaDB seed data (different similarity scores)
- A playbook ID in `playbook_library.py`
- The reasoning prompt structure in `n5_reasoning.py`

To regenerate, make a real LLM call with the incident context and save the response:

```bash
# Start the LLM server
uvicorn backend.llm.cerebras_server:app --port 8001

# Trigger the FinanceCore scenario and capture the LLM response
python scripts/trigger_financecore_e2e.py
# The LLM server logs the full response — copy it to data/fallbacks/financecore_incident_response.json
```

After regenerating, verify the files pass validation:

```bash
python data/phase7_verify.py
# Section 2 checks both fallback files — must show all PASS
```

---

## Required schema

Each file must contain valid JSON with all required fields:

```json
{
  "root_cause": "string describing the root cause",
  "recommended_action_id": "connection-pool-recovery-v2",
  "alternative_hypotheses": [
    {
      "hypothesis": "string",
      "confidence": 0.38,
      "evidence_for": "string",
      "evidence_against": "string"
    }
  ],
  "explanation_for_engineer": "string, minimum 50 characters",
  "technical_evidence_summary": "string",
  "confidence_factors": {}
}
```

`recommended_action_id` must match a real playbook ID in the library. N5 validates this before accepting the fallback.

---

## Generating fallbacks

Make a real LLM call with the incident context before the demo and save the response:

```python
# Assemble the FinanceCore incident context (blast radius, deployments, historical matches)
# Call the LLM endpoint with the 6-step ITIL reasoning prompt
# Save the complete response to this directory
```

These files are not committed to the repository. Generate them fresh before each demo run to ensure they reflect the current seed data.
