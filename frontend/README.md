# frontend

React 18 dashboard. Three-panel layout. Real-time via WebSocket. All data is live from the backend.

---

## Stack

- React 18 + TypeScript
- Tailwind CSS
- Framer Motion (animations)
- Recharts (timeseries charts, SHAP waterfall)
- React Force Graph 2D (knowledge graph visualisation)
- Vite (build tool)
- Node.js 18 or 20 required

---

## Structure

```
frontend/
  src/
    App.tsx               Root component, three-panel layout
    components/           All UI components
    hooks/
      useWebSocket.ts     WebSocket connection management
      useIncident.ts      Incident state management
      useSLACountdown.ts  SLA breach countdown timer
    types/                TypeScript type definitions
    lib/                  Shared utilities
  index.html
  package.json
  vite.config.ts
  tailwind.config.ts
```

---

## Three-panel layout

**Left panel - Client roster**
- FinanceCore and RetailMax client cards
- Real health status via WebSocket
- SLA uptime counter
- Compliance badges (PCI-DSS, SOX, GDPR)
- Trust level indicator with progress to next stage

**Centre panel - Active state**
- Normal mode: live log stream scrolling via WebSocket
- Incident mode: ATLAS briefing card with six sections
  1. Situation summary (affected services, SLA countdown, business impact)
  2. Blast radius (React Force Graph 2D, animated traversal)
  3. Deployment correlation (change ID, description, timestamp from Neo4j)
  4. Historical match (similarity score, link to full record from ChromaDB)
  5. Alternative hypotheses (ranked, evidence for and against each)
  6. Recommended action (playbook details, risk class, rollback status)
- SHAP waterfall chart (Recharts, real feature contribution percentages)
- Post-resolution: metric recovery timeseries with Atlassian 43-minute benchmark line

**Right panel - Activity feed**
- Real-time log of every LangGraph node transition
- Every line is real system output from the backend WebSocket

---

## WebSocket connections

Three connections per session:

| Endpoint | What it receives |
|----------|----------------|
| `/ws/logs/{client_id}` | Live log lines from the event queue |
| `/ws/incidents/{client_id}` | Incident state updates (briefing card data) |
| `/ws/activity` | Global activity feed (all node transitions) |

---

## Running

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` by default. The backend must be running on port 8000.

To build for production:
```bash
npm run build
```

---

## Environment

The frontend expects the backend at `http://localhost:8000`. To change this, update the WebSocket URLs in `src/hooks/useWebSocket.ts`.

The backend's CORS configuration allows `http://localhost:5173` by default. Change `ATLAS_FRONTEND_ORIGIN` in the backend `.env` if you deploy to a different origin.

The WebSocket connections use the native browser WebSocket API, not socket.io. The `useWebSocket.ts` hook implements exponential backoff reconnection with a configurable `MAX_RETRIES` limit.
