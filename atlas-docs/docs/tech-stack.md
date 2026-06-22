# Technology Stack

Exact, pinned dependency versions as declared in `requirements.txt` and
`ui/package.json` — not approximations.

## Backend (Python 3.11)

=== "Web & API"

    | Package | Version | Role |
    |---|---|---|
    | `fastapi` | 0.111.0 | API framework |
    | `uvicorn[standard]` | 0.29.0 | ASGI server |
    | `websockets` | 12.0 | WebSocket transport |
    | `httpx` | 0.27.0 | Outbound HTTP (ServiceNow, LLM calls) |
    | `pydantic` | 2.7.1 | Request/response validation |

=== "Orchestration"

    | Package | Version | Role |
    |---|---|---|
    | `langgraph` | 0.2.28 | 7-node state-machine orchestration |
    | `langchain-core` | 0.2.39 | Shared LangChain primitives used by LangGraph |

=== "Data Layer"

    | Package | Version | Role |
    |---|---|---|
    | `neo4j` | 5.20.0 | Knowledge graph driver |
    | `chromadb` | 0.5.3 | Vector store for semantic incident matching |
    | `aiosqlite` | 0.20.0 | Async SQLite — audit log, decision history |

=== "Detection / ML"

    | Package | Version | Role |
    |---|---|---|
    | `scikit-learn` | 1.4.2 | Isolation Forest |
    | `shap` | 0.45.1 | Feature-contribution explainability |
    | `torch` | 2.3.0 | Chronos-Bolt model runtime |
    | `transformers` | 4.41.2 | HuggingFace model loading |
    | `chronos-forecasting` | 1.3.0 | Chronos-Bolt time-series foundation model |
    | `numpy` / `pandas` | 1.26.4 / 2.2.2 | Numerical and tabular processing |

=== "Utilities"

    | Package | Version | Role |
    |---|---|---|
    | `python-dotenv` | 1.0.1 | `.env` loading |
    | `pyyaml` | 6.0.1 | Client configuration files |
    | `structlog` | 24.1.0 | Structured, queryable logging |
    | `cryptography` | 42.0.7 | Dual-approval cryptographic tokens |
    | `pytest` / `pytest-asyncio` | 8.2.0 / 0.23.6 | Backend test suite |

## Frontend (`ui/`)

| Package | Version | Role |
|---|---|---|
| `react` / `react-dom` | 18.3.1 | UI framework |
| `typescript` (via Vite) | — | Static typing across the app |
| `@tanstack/react-query` | 5.83.0 | Server-state synchronisation |
| `react-router-dom` | 6.30.1 | Client-side routing |
| `recharts` | 2.15.4 | Charts (SHAP waterfalls, trend lines) |
| `react-hook-form` + `zod` | 7.61.1 / 3.25.76 | Form state and schema validation |
| `@radix-ui/*` (via shadcn/ui) | various | Accessible component primitives |
| `lucide-react` | 0.462.0 | Icon set |
| `sonner` | 1.7.4 | Toast notifications |
| `@playwright/test` | 1.57.0 | End-to-end test runner |

## External Services

| Service | Role |
|---|---|
| **Neo4j Aura Serverless** | Knowledge graph — service topology, deployments, incident history |
| **ChromaDB** | Namespaced per-client vector store for semantic incident search |
| **ServiceNow** | ITSM ticketing and CMDB source of truth, synced via push webhook |
| **Cerebras** | Primary hosted LLM inference (`qwen-3-235b-a22b-instruct-2507` by default) |
| **Ollama (local)** | Offline LLM fallback (`qwen3-coder:480b-cloud` by default) |
| **Anthropic / OpenAI** | Optional further LLM fallbacks |
| **Slack** | Dual-approval notification channel for compliance-gated actions |

## Documentation Site

| Package | Role |
|---|---|
| `mkdocs-material` | Site generator and theme — tabs, search, dark mode |
| `mkdocs-mermaid2-plugin` | Renders the diagrams throughout this documentation |
| GitHub Actions | Automated build and GitHub Pages deployment on every push to `docs/` |
