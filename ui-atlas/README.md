# ui-atlas

Standalone presentation UI for ATLAS. Pre-built demo screens that do not require a live backend connection. Use this for presentations where running the full backend stack is not practical.

---

## What it is

A React 19 + TypeScript application with a complete set of demo screens covering every stage of the ATLAS incident lifecycle. Each screen is a self-contained page with realistic data baked in. No backend connection required.

This is not the operational dashboard. For the live dashboard that connects to the real backend, use `frontend/`.

---

## Pages

| Route | Page | What it shows |
|-------|------|--------------|
| `/` | Dashboard | Client roster, health status, activity feed |
| `/detection` | DetectionPhase | Chronos-Bolt and SHAP detection in progress |
| `/incidents` | IncidentIntelligence | Active incident list |
| `/incidents/briefing` | IncidentBriefing | Full L2 six-section briefing card |
| `/incidents/l1-command` | L1CommandInterface | L1 two-sentence summary and approve/escalate buttons |
| `/incidents/approval` | ApprovalWorkflow | Dual cryptographic approval flow |
| `/incidents/playbook` | PlaybookExecution | Playbook execution with live progress |
| `/incidents/resolved` | PostResolution | MTTR counter, metric recovery chart, benchmark line |
| `/incidents/veto` | VetoWarning | Veto fired screen with plain-English explanation |
| `/network` | NetworkOverview | Neo4j knowledge graph visualisation |
| `/finance` | FinanceCore | FinanceCore client deep-dive |

---

## Stack

- React 19 + TypeScript
- Tailwind CSS 4
- React Router 7
- Vite 8
- Node.js 18 or 20 required

---

## Running

```bash
cd ui-atlas
npm install
npm run dev    # http://localhost:5174
```

To build for static hosting:

```bash
npm run build
# Output in dist/
```

---

## Relationship to frontend/

| | `frontend/` | `ui-atlas/` |
|--|-------------|-------------|
| React version | 18 | 19 |
| Backend required | Yes (WebSocket) | No |
| Data source | Live backend | Baked-in demo data |
| Use case | Live operational demo | Presentation without backend |
| Recharts / Force Graph | Yes | No |
| React Router | No | Yes |
