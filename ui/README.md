# ATLAS UI

The operational frontend for the ATLAS AIOps platform.

Connects to the ATLAS backend via WebSocket and REST. Shows live log streams, real-time incident briefings, pipeline progress, and the L1/L2/L3 human review flow. Every number on screen is live data from the backend — not mock.

## Start

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. Requires the ATLAS backend running on port 8000.

## Environment

Frontend-to-backend connectivity is controlled through Vite environment variables:

- `VITE_ATLAS_API_BASE_URL` (default: `http://localhost:8000`)
- `VITE_ATLAS_WS_BASE_URL` (optional; auto-derived from API base URL when omitted)
- `VITE_ATLAS_POLL_INTERVAL_MS` (default: `10000`)
- `VITE_ATLAS_DEFAULT_CLIENT_ID` (default: `FINCORE_UK_001`)

Use `ui/.env.example` as the reference when setting deployment environments.

## Stack

React 18, TypeScript, Tailwind CSS, Framer Motion, Recharts, React Force Graph 2D.
