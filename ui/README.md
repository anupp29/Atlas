# ATLAS UI

The operational frontend for the ATLAS AIOps platform.

Connects to the ATLAS backend via WebSocket and REST. Shows live log streams, real-time incident briefings, pipeline progress, and the L1/L2/L3 human review flow. Every number on screen is live data from the backend — not mock.

## Start

```bash
npm install
npm run dev
```

Runs on `http://localhost:5173`. Requires the ATLAS backend running on port 8000.

## Stack

React 18, TypeScript, Tailwind CSS, Framer Motion, Recharts, React Force Graph 2D.
