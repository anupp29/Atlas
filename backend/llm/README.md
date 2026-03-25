# backend/llm

Internal LLM reasoning server. Runs as a **separate process on port 8001**, independent of the main FastAPI backend on port 8000.

The main backend's N5 node posts incident context to this server at `ATLAS_LLM_ENDPOINT`. This server calls the configured LLM and returns structured JSON reasoning output.

---

## Files

| File | What it does |
|------|-------------|
| `cerebras_server.py` | FastAPI server that receives reasoning context from N5, calls the LLM (Ollama primary, Claude fallback), validates the response schema, and returns structured JSON. |

---

## Why it is a separate process

The LLM server is decoupled from the main backend so that:
- LLM failures never crash the main backend
- The LLM server can be restarted independently without losing active incident state
- Different LLM providers can be swapped by restarting only this process

---

## Starting the LLM server

```bash
# Must be started before the main backend
uvicorn backend.llm.cerebras_server:app --port 8001
```

The main backend reads `ATLAS_LLM_ENDPOINT` from the environment. This must point to port 8001, not port 8000. Port 8000 is the main FastAPI backend — it does not serve the LLM reasoning endpoint.

```
# Correct
ATLAS_LLM_ENDPOINT=http://localhost:8001/internal/llm/reason

# Wrong — port 8000 is the main backend, not the LLM server
ATLAS_LLM_ENDPOINT=http://localhost:8000/internal/llm/reason
```

---

## LLM routing

The server tries LLM providers in this order:

1. Ollama with `OLLAMA_MODEL` (default: `qwen3-coder:480b-cloud`) — requires `ollama serve` running locally
2. Anthropic Claude — requires `ANTHROPIC_API_KEY`
3. OpenAI GPT-4o — requires `OPENAI_API_KEY`

If all three fail, N5 loads the pre-computed fallback from `data/fallbacks/`.

---

## Required output schema

The server must return JSON with all of these fields. N5 validates the response before accepting it.

```json
{
  "root_cause": "string",
  "recommended_action_id": "string (must match a playbook ID in the library)",
  "alternative_hypotheses": [
    {
      "hypothesis": "string",
      "confidence": 0.0,
      "evidence_for": "string",
      "evidence_against": "string"
    }
  ],
  "explanation_for_engineer": "string (minimum 50 characters)",
  "technical_evidence_summary": "string",
  "confidence_factors": {}
}
```

---

## Testing the LLM server

```bash
# Verify Ollama is working before starting the server
python scripts/test_ollama_qwen3.py

# Test the full integration path (LLM server must be running)
python scripts/test_ollama_atlas_integration.py
```
