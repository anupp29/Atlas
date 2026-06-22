# Frontend Reference — `ui/`

The frontend is a **React 18 + TypeScript** single-page application built with
Vite, styled with Tailwind CSS and shadcn/ui (Radix primitives), with
TanStack Query handling all server-state synchronisation against the FastAPI
backend over REST and WebSocket.

## Technology Stack

| Concern | Library |
|---|---|
| Framework | React 18.3 + TypeScript, built by Vite |
| Routing | `react-router-dom` v6 |
| Server state / data fetching | `@tanstack/react-query` v5 |
| Styling | Tailwind CSS + `tailwindcss-animate` |
| Component primitives | shadcn/ui on Radix UI (accordion, dialog, dropdown, tabs, tooltip, etc.) |
| Charts | `recharts` |
| Forms | `react-hook-form` + `zod` validation |
| Icons | `lucide-react` |
| Toasts / notifications | `sonner` |
| Testing | Vitest + Testing Library (unit) · Playwright (E2E, see `playwright.config.ts`) |

## Directory Layout

```text
ui/src/
├── App.tsx                  Route definitions and top-level providers
├── main.tsx                 Vite/React entry point
├── pages/                   One file per route (see table below)
├── layouts/
│   └── AtlasLayout.tsx       Shared shell: sidebar, top bar, activity drawer
├── components/
│   ├── atlas/                Domain-specific ATLAS components
│   └── ui/                   Generic shadcn/ui primitives (button, dialog, table, …)
├── contexts/
│   ├── AuthContext.tsx        Session/role state (L1 / L2 / L3 / SDM / CLIENT)
│   └── AtlasDataContext.tsx   Shared incident/activity data provider
├── hooks/
│   ├── use-atlas-data.ts      All TanStack Query hooks against the backend
│   └── use-mobile.tsx         Responsive breakpoint hook
├── lib/
│   ├── atlas-api.ts           Typed fetch/WebSocket client for every backend endpoint
│   ├── atlas-config.ts        Runtime config: API base URL, poll interval, default client
│   └── atlas-adapters.ts      Maps raw backend payloads to frontend view models
├── data/
│   └── mock.ts                 Fallback/demo data when the backend is unreachable
└── types/
    └── atlas.ts                 Shared TypeScript types mirroring backend schemas
```

## Pages

| Route file | Role | Purpose |
|---|---|---|
| `pages/Landing.tsx` | Public | Marketing/landing page — capabilities, intelligence, roles. |
| `pages/Login.tsx` | Public | Authentication entry point. |
| `pages/Onboarding.tsx` | SDM | No-code client onboarding wizard (Layer 0 configuration UI). |
| `pages/Portfolio.tsx` | SDM / L1 | Multi-client portfolio overview — SLA, active/resolved counts, MTTR. |
| `pages/Incidents.tsx` | L1 / L2 / L3 | The incident briefing and approval workspace — renders the tier-appropriate view described in the [escalation chain](../escalation/human-workflow.md). |
| `pages/Playbooks.tsx` | L2 / L3 | Read-only view of the registered playbook library. |
| `pages/AuditLog.tsx` | SDM / Compliance | Immutable audit trail browser and compliance export. |
| `pages/ClientPortal.tsx` | Client | The client-facing transparency portal (Output D). |
| `pages/Settings.tsx` | All roles | Account and notification preferences. |
| `pages/NotFound.tsx` | — | 404 fallback. |

## Key Library Files

=== "`lib/atlas-api.ts`"

    The single typed client for every backend call: `fetchActiveIncidents`,
    `fetchIncidentDetails`, `approveIncident`, `rejectIncident`,
    `modifyIncident`, `fetchAuditLog`, `fetchTrustLevel`, `confirmTrustUpgrade`,
    `fetchPlaybookLibrary`, and `buildWsUrl()` for the three WebSocket channels.
    Session identity (`role`, `name`, `email`) is read from a typed session
    object validated against the known role set
    (`L1 | L2 | L3 | SDM | CLIENT`).

=== "`lib/atlas-config.ts`"

    Centralises runtime configuration so nothing is hardcoded across
    components: API base URL (default `http://localhost:8000`), derived
    WebSocket base URL (`http:` → `ws:`, `https:` → `wss:`), poll interval
    (default 10s), and default demo client ID.

=== "`hooks/use-atlas-data.ts`"

    The data layer every page consumes. Wraps `atlas-api.ts` calls in
    `useQuery` / `useMutation` / `useQueries`, applies `atlas-adapters.ts` to
    normalise backend payloads into frontend view models, and falls back to
    `data/mock.ts` fixtures when the backend is unreachable — so the UI
    remains demonstrable even with the API offline.

=== "`lib/atlas-adapters.ts`"

    Pure mapping functions (`adaptActiveIncident`, `adaptActivityEvent`,
    `adaptAuditRecord`, …) that translate raw backend JSON into the
    strongly-typed shapes defined in `types/atlas.ts`. Keeping this mapping in
    one place means a backend field rename only requires one file to change.

## ATLAS-Specific Components (`components/atlas/`)

| Component | Renders |
|---|---|
| `IncidentBriefing.tsx` | The L2/L3 six-section briefing card. |
| `AIReasoningPanel.tsx` | The confidence debug panel — factor scores, vetoes, reasoning chain. |
| `ExecutionTrace.tsx` | The five-step execution timeline for a running or completed playbook. |
| `PipelineIndicator.tsx` | Visual progress through the N1–N7 orchestrator pipeline. |
| `ActivityFeed.tsx` / `ActivityDrawer.tsx` | The live, portfolio-wide activity stream seen on every dashboard. |
| `CountdownTimer.tsx` | SLA breach countdown, used across L1/L2/L3 views. |
| `PriorityBadge.tsx` / `StatusIndicator.tsx` | Shared P1–P4 and status visual indicators. |
| `ConfirmationDialog.tsx` | Approve / Modify / Reject confirmation flow, including the dual-token compliance gate. |
| `AppSidebar.tsx` / `TopBar.tsx` | Shared navigation chrome inside `AtlasLayout.tsx`. |

## Live Data: WebSocket Channels

The frontend subscribes to the three WebSocket channels exposed by the backend
(see [API Reference](../api/reference.md#websocket-channels)) through
`buildWsUrl()` in `atlas-api.ts`, giving every dashboard — Portfolio, Incidents,
and the Client Portal — real-time updates without polling for the common case.

[:octicons-arrow-right-24: Scripts & seed data](scripts-and-data.md){ .md-button .md-button--primary }
