"""
Step 1 — Verify Ollama + qwen3-coder:480b-cloud works before wiring into ATLAS.

Run:
    python scripts/test_ollama_qwen3.py

Exit 0 = model responds correctly, safe to wire into main.py.
Exit 1 = something is wrong, do not proceed.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

OLLAMA_BASE = "http://localhost:11434"
MODEL = "qwen3-coder:480b-cloud"


def _post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def check_ollama_running() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5) as r:
            json.loads(r.read())
        print("  PASS  Ollama server is running at localhost:11434")
        return True
    except Exception as exc:
        print(f"  FAIL  Ollama server not reachable: {exc}")
        print("        Start it with: ollama serve")
        return False


def pull_model() -> bool:
    """Pull the model if not already present."""
    # Check if already pulled
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=5) as r:
            tags = json.loads(r.read())
        names = [m["name"] for m in tags.get("models", [])]
        if MODEL in names or MODEL.split(":")[0] in names:
            print(f"  PASS  Model '{MODEL}' already present")
            return True
    except Exception:
        pass

    print(f"  INFO  Pulling '{MODEL}' — this routes to Alibaba Cloud, should be fast...")
    try:
        payload = {"name": MODEL, "stream": False}
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/pull",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        status = result.get("status", "")
        print(f"  PASS  Pull complete — status: {status}")
        return True
    except Exception as exc:
        print(f"  FAIL  Pull failed: {exc}")
        return False


def test_basic_completion() -> bool:
    """Send a simple prompt and verify we get a coherent response."""
    print(f"  INFO  Sending test prompt to {MODEL}...")
    t0 = time.perf_counter()
    try:
        result = _post("/api/generate", {
            "model": MODEL,
            "prompt": "Reply with exactly: ATLAS_OK",
            "stream": False,
            "options": {"temperature": 0, "num_predict": 20},
        })
        elapsed = time.perf_counter() - t0
        response_text = result.get("response", "").strip()
        print(f"  INFO  Response ({elapsed:.1f}s): '{response_text}'")
        if not response_text:
            print("  FAIL  Empty response from model")
            return False
        print(f"  PASS  Model responded in {elapsed:.1f}s")
        return True
    except Exception as exc:
        print(f"  FAIL  Completion failed: {exc}")
        return False


def test_json_output() -> bool:
    """Verify the model can produce structured JSON — critical for ATLAS reasoning."""
    print("  INFO  Testing JSON output capability...")
    t0 = time.perf_counter()
    try:
        result = _post("/api/generate", {
            "model": MODEL,
            "prompt": (
                'Return ONLY valid JSON, no explanation: '
                '{"status": "ok", "model": "qwen3-coder", "ready": true}'
            ),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_predict": 50},
        })
        elapsed = time.perf_counter() - t0
        raw = result.get("response", "").strip()
        parsed = json.loads(raw)
        print(f"  PASS  JSON output valid in {elapsed:.1f}s — keys: {list(parsed.keys())}")
        return True
    except json.JSONDecodeError as exc:
        print(f"  FAIL  Model returned invalid JSON: {exc}")
        print(f"        Raw response: {result.get('response', '')[:200]}")
        return False
    except Exception as exc:
        print(f"  FAIL  JSON test failed: {exc}")
        return False


def test_chat_api() -> bool:
    """Test the /api/chat endpoint — this is what ATLAS will use."""
    print("  INFO  Testing /api/chat endpoint...")
    t0 = time.perf_counter()
    try:
        result = _post("/api/chat", {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are ATLAS, an AIOps assistant."},
                {"role": "user", "content": "Say: ATLAS_CHAT_OK"},
            ],
            "stream": False,
            "options": {"temperature": 0, "num_predict": 20},
        })
        elapsed = time.perf_counter() - t0
        content = result.get("message", {}).get("content", "").strip()
        print(f"  INFO  Chat response ({elapsed:.1f}s): '{content}'")
        if not content:
            print("  FAIL  Empty chat response")
            return False
        print(f"  PASS  Chat API works in {elapsed:.1f}s")
        return True
    except Exception as exc:
        print(f"  FAIL  Chat API failed: {exc}")
        return False


if __name__ == "__main__":
    print("\n  Ollama + qwen3-coder:480b-cloud — Connection Test")
    print("  " + "─" * 50)

    if not check_ollama_running():
        sys.exit(1)

    if not pull_model():
        sys.exit(1)

    results = [
        test_basic_completion(),
        test_json_output(),
        test_chat_api(),
    ]

    print("\n  " + "─" * 50)
    if all(results):
        print("  RESULT: ALL TESTS PASSED — safe to wire into ATLAS")
        sys.exit(0)
    else:
        failed = results.count(False)
        print(f"  RESULT: {failed} test(s) FAILED — do not wire into ATLAS yet")
        sys.exit(1)
