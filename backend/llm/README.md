# backend/llm

Optional standalone LLM service for ATLAS.

The default runtime mode is **single-service**: `backend.main` serves `POST /internal/llm/reason` directly on port 8000.

Use this folder only if you explicitly want to run the LLM endpoint as a separate process.

---

## Files

| File | What it does |
|------|-------------|
| `cerebras_server.py` | FastAPI server that receives reasoning context from N5, calls the LLM (Ollama primary, Claude fallback), validates the response schema, and returns structured JSON. |

---

## Runtime modes

### Default: single-service

- Start only `backend.main`
- Keep `ATLAS_LLM_ENDPOINT` pointed to the backend URL, for example:

```
ATLAS_LLM_ENDPOINT=http://localhost:8000/internal/llm/reason
```

### Optional: standalone LLM service

- Run `backend.llm.cerebras_server` separately
- Point `ATLAS_LLM_ENDPOINT` to that standalone service URL

---

## Starting the standalone LLM server

```bash
# Optional mode only
uvicorn backend.llm.cerebras_server:app --port 8001
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

# Test the full integration path (backend.main must be running)
python scripts/test_ollama_atlas_integration.py
```
