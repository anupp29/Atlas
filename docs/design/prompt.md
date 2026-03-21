# ATLAS — Lovable UI Design Prompt

## What You Are Building

A professional AIOps operations dashboard called **ATLAS** for a managed service provider (Atos). The dashboard monitors multiple enterprise clients simultaneously, detects infrastructure incidents using AI, and guides engineers through investigation and resolution. Think: Bloomberg Terminal meets modern SRE tooling. Dark theme. Dense but readable. Every number is real. Every indicator means something.

---

## Visual Identity

**Colour palette:**
- Background: `#0A0E1A` (near-black navy)
- Surface / card background: `#111827`
- Surface elevated: `#1F2937`
- Border: `#374151`
- Text primary: `#F9FAFB`
- Text secondary: `#9CA3AF`
- Text muted: `#6B7280`

**Status colours (use these exactly — they carry meaning):**
- Healthy / success: `#10B981` (emerald green)
- Warning: `#F59E0B` (amber)
- Incident / error: `#EF4444` (red)
- Executing / in-progress: `#3B82F6` (blue)
- Resolved: `#10B981` (green)
- Early warning: `#F59E0B` (amber)
- Deployment node: `#EAB308` (yellow)
- Historical incident node: `#8B5CF6` (purple)
- Veto fired: `#EF4444` (red)

**Typography:**
- Font: Inter (system fallback: -apple-system, sans-serif)
- Monospace (for INC numbers, CHG numbers, timestamps, IDs): JetBrains Mono or Fira Code
- Heading sizes: tight, professional — not large decorative headers
- Numbers that matter (MTTR, confidence score, SLA countdown) should be large and prominent

**Motion:**
- Framer Motion for all transitions
- Panel switches: 300ms fade
- Status indicator changes: 200ms colour transition
- SLA timer turning red: pulse animation when under 5 minutes
- Graph animation: sequential, deliberate — each step 1–3 seconds
- No bouncy or playful animations — this is an operations tool

---

## Layout

Three-panel layout. Full viewport height. No scrolling on the outer shell — each panel scrolls internally.

```
┌──────────────┬──────────────────────────────────┬──────────────┐
│              │                                  │              │
│  LEFT PANEL  │         CENTRE PANEL             │ RIGHT PANEL  │
│  w: 288px    │         flex-1                   │  w: 320px    │
│              │                                  │              │
│  Client      │  [Normal mode: log stream]       │  Activity    │
│  Roster      │  [Incident mode: briefing card]  │  Feed        │
│              │                                  │              │
└──────────────┴──────────────────────────────────┴──────────────┘
```

Top bar: thin, `h-12`, contains the ATLAS logo (left), current time UTC (right), and a global connection status indicator (green dot = connected, amber = reconnecting, red = disconnected).

---

## Left Panel — Client Roster

Two client cards stacked vertically. Each card is a clickable surface that selects the active client.

**FinanceCore card (selected state by default):**
```
┌─────────────────────────────────────┐
│  ● FINANCECORE LTD          [● RED] │  ← health dot, red = incident active
│  United Kingdom                     │
│                                     │
│  [Java] [PostgreSQL] [Redis]        │  ← tech stack badges, small pills
│  [PCI-DSS] [SOX] [ISO-27001]       │  ← compliance badges, colour-coded
│                                     │
│  SLA Uptime: 99.94%                 │
│  ████████████████░░  Stage 1 → 2   │  ← trust progress bar
│  L1 Assistance                      │
│                                     │
│  ⚠ 1 Active Incident               │  ← red badge, only shown when > 0
└─────────────────────────────────────┘
```

**RetailMax card (unselected state):**
```
┌─────────────────────────────────────┐
│  ○ RETAILMAX EU             [● GRN] │
│  European Union                     │
│                                     │
│  [Node.js] [Redis] [MongoDB]        │
│  [GDPR]                             │
│                                     │
│  SLA Uptime: 99.97%                 │
│  ████████████████████  Stage 2      │
│  L1 Automation                      │
└─────────────────────────────────────┘
```

Compliance badge colours:
- PCI-DSS: red background `#7F1D1D`, text `#FCA5A5`
- SOX: amber background `#78350F`, text `#FCD34D`
- GDPR: blue background `#1E3A5F`, text `#93C5FD`
- ISO-27001: grey background `#1F2937`, text `#9CA3AF`

Tech stack badges: small rounded pills, dark grey background, white text, tiny icon if possible.

Trust progress bar: thin `h-1.5` bar, green fill, shows progress toward next stage. Label below: "Stage 1 — L1 Assistance" with "→ Stage 2" in muted text.

---

## Centre Panel — Two States

### State 1: Normal Mode (no active incident)

A scrolling log stream. Monospace font, small (`text-xs`). Lines scroll upward, newest at bottom. Auto-scroll enabled, pauses if user scrolls up.

Each log line has a left-border colour based on severity:
- `INFO`: no border, muted text
- `WARN`: amber left border `border-l-2 border-amber-500`
- `ERROR`: red left border `border-l-2 border-red-500`
- `FATAL`: red left border, red text, slightly brighter

Example lines:
```
09:23:12.441  INFO  [PaymentAPI] HikariCP - Pool stats: total=40, active=12, idle=28
09:23:18.203  INFO  [TransactionDB] checkpoint complete: wrote 847 buffers
09:23:31.887  WARN  [PaymentAPI] HikariCP - Connection acquisition timeout after 30002ms
09:23:44.112  ERROR [TransactionDB] FATAL: remaining connection slots are reserved
```

A thin header bar above the log stream: "LIVE LOG STREAM — FINANCECORE" with a pulsing green dot.

### State 2: Incident Mode (active incident)

The log stream fades out (Framer Motion, 300ms) and the ATLAS Briefing Card fades in.

A thin banner at the very top of the centre panel (always visible in incident mode):
```
┌─────────────────────────────────────────────────────────────────┐
│  🔴 INCIDENT ACTIVE — INC0089247 — PaymentAPI / TransactionDB  │
│  SLA Breach: 21:34 remaining          Confidence: 0.84         │
└─────────────────────────────────────────────────────────────────┘
```
Banner background: `#1F0A0A` (very dark red). Text: white. SLA time in large monospace. When under 5 minutes: the SLA time pulses red.

Below the banner: the full briefing card, scrollable.

---

## Briefing Card — Six Sections

Each section is a card with `bg-[#111827]` background, `border border-[#374151]`, `rounded-lg`, `p-4`, `mb-3`.

### Section 1 — Situation Summary

```
SITUATION SUMMARY
─────────────────────────────────────────────────────
Affected Services:  PaymentAPI (P1) · TransactionDB (P1) · AuthService (P2)
Business Impact:    Core payment processing degraded. Estimated 2,400 transactions/min affected.
                    HikariCP connection pool at 94% capacity. HTTP 503 errors at 340% above baseline.

SLA Breach:  ┌──────────────────┐
             │    21:34         │  ← large monospace, green → amber → red
             └──────────────────┘
             ServiceNow: INC0089247
```

The SLA countdown is the most prominent element in this section. Large font (`text-4xl`), monospace, centred in its box. Colour transitions automatically.

### Section 2 — Blast Radius

Header: "BLAST RADIUS — DEPENDENCY GRAPH"

The graph visualisation occupies this section. See Graph Visualisation section below for full spec.

Below the graph: a flat list of downstream services:
```
● PaymentAPI        P1  ████ Critical
● TransactionDB     P1  ████ Critical  
● AuthService       P2  ███  High       ⚠ Early Warning: 1.8σ
● NotificationSvc   P3  ██   Medium
```

### Section 3 — Deployment Correlation

```
DEPLOYMENT CORRELATION
─────────────────────────────────────────────────────
Change ID:     CHG0089234                    ← monospace, amber colour
Description:   Reduced HikariCP maxPoolSize from 100 → 40 (cost optimisation)
Deployed by:   raj.kumar@atos.com
Timestamp:     3 days ago  (2026-03-18 14:23 UTC)  ← "3 days ago" large, exact on hover
CAB Risk:      LOW  ← green badge
```

The CHG number should be visually prominent — monospace, amber (`#F59E0B`), slightly larger than surrounding text. This is the smoking gun. It should look like one.

### Section 4 — Historical Match

```
HISTORICAL MATCH
─────────────────────────────────────────────────────
┌──────────┐
│   91%    │  ← large, green, prominent similarity score badge
│ MATCH    │
└──────────┘
  ✓ DOUBLE-CONFIRMED  ← green badge, shown when match appears in both Neo4j and ChromaDB

Incident:    INC-2024-0847  (November 2024)
Root Cause:  HikariCP maxPoolSize reduced via deployment CHG0071892
Resolution:  Restored pool size to 150, restarted connection manager
MTTR:        23 minutes
```

The 91% badge should be a large rounded square, green background, white text, prominent. This number is a key demo moment.

### Section 5 — Alternative Hypotheses

```
ALTERNATIVE HYPOTHESES
─────────────────────────────────────────────────────
▼ Memory pressure on RDS instance                    38% confidence
  ✓ Evidence for:    Memory metrics elevated in last 2 hours
  ✗ Evidence against: Memory within normal range for this time of day

▼ Traffic spike causing natural exhaustion           27% confidence  
  ✓ Evidence for:    Request rate 12% above baseline
  ✗ Evidence against: Insufficient to explain 94% pool utilisation with original pool size
```

Collapsed by default, expandable on click. Evidence for: green text with ✓. Evidence against: red text with ✗.

### Section 6 — Recommended Action

```
RECOMMENDED ACTION
─────────────────────────────────────────────────────
Playbook:     connection-pool-recovery-v2
Action:       Restore HikariCP maxPoolSize to 150. Restart connection manager pod.
Est. Time:    4–6 minutes
Risk Class:   ● Class 1  ← green badge
Rollback:     ✓ Auto-rollback available (connection-pool-restore-v2)
```

### Veto Panel (shown below Section 6 when vetoes are active)

```
┌─────────────────────────────────────────────────────────────────┐
│  ⛔ ACTIVE VETO CONDITIONS — AUTO-EXECUTE BLOCKED              │
│                                                                 │
│  PCI-DSS: Production configuration changes during business     │
│  hours require dual engineer sign-off per compliance policy.   │
│                                                                 │
│  Business Hours: Action requested during trading hours         │
│  (08:00–18:00 GMT). PCI-DSS enforcement active.               │
└─────────────────────────────────────────────────────────────────┘
```

Background: `#1F0A0A`. Border: `#7F1D1D`. Text: `#FCA5A5`. This panel must be visually alarming — it is blocking autonomous action.

---

## Graph Visualisation

Uses React Force Graph 2D. Embedded within Section 2 of the briefing card. Height: `400px`.

**Node visual spec:**
- Normal service: grey circle, `r=8`, label below in small white text
- Warning service: amber circle, `r=8`, amber glow (`box-shadow` equivalent)
- Affected service: red circle, `r=10`, red glow, slightly larger
- Deployment node: yellow diamond shape (or yellow circle with ⚙ icon), `r=10`
- Historical incident node: purple circle, `r=8`, `INC-XXXX` label

**Edge visual spec:**
- `DEPENDS_ON`: white line, `strokeWidth: 1.5`, directional arrow
- `MODIFIED_CONFIG_OF`: amber dashed line, `strokeWidth: 2`, directional arrow
- `AFFECTED`: red line, `strokeWidth: 1.5`

**Animation sequence (plays automatically when briefing card appears):**
1. All nodes render in grey/default state
2. Deployment node (CHG0089234) pulses yellow — 3 second pulse animation
3. `MODIFIED_CONFIG_OF` edge from CHG0089234 to TransactionDB animates (stroke-dashoffset sweep, 1 second)
4. TransactionDB transitions from grey to orange (1 second)
5. `DEPENDS_ON` edge from TransactionDB to PaymentAPI animates (1 second)
6. PaymentAPI transitions to red (1 second)
7. AuthService and NotificationService glow amber (early warning state, 1 second)
8. Animation complete — graph remains fully interactive

**Hover tooltip** (appears on node hover, dark card):
```
PaymentAPI
Type: Java Spring Boot 3.1
Criticality: P1
Version: 3.1.4
Last Deployed: 3 days ago
```

**Click on deployment node** — expands an overlay panel:
```
CHG0089234
HikariCP maxPoolSize: 100 → 40
Deployed by: raj.kumar@atos.com
2026-03-18 14:23 UTC
CAB Risk: LOW
```

**Fallback:** If the graph fails to render, show a pre-recorded 15-second video of the animation (`/graph_animation_fallback.mp4`). The fallback must be indistinguishable in quality from the live render.

---

## SHAP Feature Attribution Chart

Horizontal bar chart. Embedded in the briefing card between Section 1 and Section 2, or as a collapsible panel.

```
DETECTION FEATURE ATTRIBUTION (SHAP)
─────────────────────────────────────────────────────
connection_count    ████████████████████████████  67%  ← red bar
query_latency       ████████████                  21%  ← orange bar
error_rate          ████████                      12%  ← red bar
─────────────────────────────────────────────────────
                                                 100%
```

Bars are horizontal. Features sorted by value (highest at top). Percentage label at the right end of each bar. Chart title above. Recharts `BarChart` with `layout="vertical"`.

Bar colours:
- `connection_count`, `error_rate`, `rejection_rate`: `#EF4444` (red)
- `query_latency`, `response_time`: `#F97316` (orange)
- `memory_usage`, `resource_utilisation`: `#EAB308` (yellow)
- All others: `#6B7280` (grey)

---

## Approval Flow

Shown at the bottom of the briefing card. Three buttons.

**Default state (L2 view):**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   APPROVE    │  │    MODIFY    │  │    REJECT    │
│   (green)    │  │   (amber)    │  │    (red)     │
└──────────────┘  └──────────────┘  └──────────────┘
```

**After Approve click (dual approval required):**
```
┌─────────────────────────────────────────────────────────────────┐
│  ✓ Primary approval recorded — raj.kumar@atos.com              │
│                                                                 │
│  ⏳ Awaiting secondary approval                                │
│     Slack notification sent to: sarah.chen@atos.com (SDM)     │
│     Token expires in: 29:47                                    │
└─────────────────────────────────────────────────────────────────┘
```

**After both approvals:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ✓ Both approvals confirmed                                    │
│  ▶ Executing: connection-pool-recovery-v2                      │
│  ████████████████░░░░░░░░  Step 2/5: Updating HikariCP config  │
└─────────────────────────────────────────────────────────────────┘
```

**Modify panel (opens when Modify is clicked):**
```
MODIFY PARAMETERS
─────────────────────────────────────────────────────
maxPoolSize:    [  150  ]  ← editable input, pre-filled with ATLAS recommendation
                Recommended: 150

─────────────────────────────────────────────────────
DIFF:  maxPoolSize  150 → 200  ← shown in amber when value is changed

[SUBMIT MODIFICATION]  ← disabled until a value is actually changed
```

**Reject panel (opens when Reject is clicked):**
```
REJECTION REASON (required, minimum 20 characters)
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
Characters: 0/20 minimum

[SUBMIT REJECTION]  ← disabled until 20+ characters entered
```

---

## Early Warning Card

Appears below the briefing card when adjacent services are trending upward (between 1.5σ and 2.5σ).

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠ EARLY WARNING — ADJACENT SERVICES                          │
│                                                                 │
│  AuthService        1.8σ  ↑  Trending upward  (detected 2m ago)│
│  NotificationSvc    1.6σ  ↑  Trending upward  (detected 4m ago)│
│                                                                 │
│  These services are below alert threshold but showing          │
│  deviation from baseline. Monitoring elevated.                 │
└─────────────────────────────────────────────────────────────────┘
```

Left border: amber `border-l-4 border-amber-500`. Background: `#1C1500`. This card is a key demo moment — it appears at T+95 and represents ATLAS predicting the next incident before it exists.

---

## Post-Resolution View

Replaces the briefing card when the incident is resolved. Framer Motion slide-up transition.

```
┌─────────────────────────────────────────────────────────────────┐
│  ✓ INCIDENT RESOLVED — INC0089247                              │
└─────────────────────────────────────────────────────────────────┘

MTTR
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│              4:12                                            │
│         ← large, green, monospace                           │
│                                                              │
│  ──────────────────────────────── 43:00  Industry median    │
│  ↓ 38 min 48 sec faster than Atlassian 2024 benchmark       │
└──────────────────────────────────────────────────────────────┘

METRIC RECOVERY — TransactionDB Connection Count
[Recharts LineChart]
  Y-axis: connection count (0 to max_connections)
  X-axis: last 15 minutes
  Line: actual connection count over time
  Red dashed reference line: alert threshold (85% of max)
  Green dashed reference line: normal baseline
  The line shows the spike and then the drop after playbook execution

RESOLUTION SUMMARY
  Playbook:          connection-pool-recovery-v2  ✓ Executed successfully
  ServiceNow:        INC0089247  ✓ Resolved
  Audit record:      AUD-2026-03-21-0847  ✓ Written
  Knowledge base:    ✓ Neo4j updated  ✓ ChromaDB updated
  Trust progression: FinanceCore — 1 incident closer to Stage 2
```

---

## Right Panel — Activity Feed

Timestamped feed of every ATLAS action. Newest at top. Scrollable. Last 100 entries.

Each entry is a single line with a left-border colour:

```
09:24:01  ● PostgreSQL-Agent: HikariCP anomaly detected — confidence 94%, SHAP: connection_count 67%
09:24:03  ● Cascade confirmed via Neo4j DEPENDS_ON — CASCADE_INCIDENT packaged
09:24:04  ● N1-Classifier: Priority P2 assigned — SLA breach in 23:00
09:24:05  ● N2-ITSM: ServiceNow INC0089247 created
09:24:08  ● N3-Graph: CHG0089234 found — MODIFIED_CONFIG_OF PaymentAPI (3 days ago)
09:24:09  ● N4-Semantic: INC-2024-0847 matched at 91% similarity — double-confirmed
09:24:11  ● N5-Reasoning: Claude tool_use response received — root cause identified
09:24:12  ● N6-Confidence: Score 0.84 — PCI-DSS veto fired — routing to L2
09:24:13  ● N7-Router: Routed to L2_L3_ESCALATION — briefing card dispatched
09:24:47  ● Early-Warning: AuthService at 1.8σ — elevated monitoring activated
09:31:22  ● Human-Action: raj.kumar@atos.com approved — awaiting secondary
09:31:58  ● Human-Action: sarah.chen@atos.com confirmed (token validated)
09:31:59  ● Execution: connection-pool-recovery-v2 started
09:35:44  ● Resolution: Success — connection count below threshold — MTTR 4:12
```

Entry type → left border colour:
- `agent_detection` (PostgreSQL-Agent, Java-Agent, etc.): `border-orange-500`
- `orchestrator_node` (N1 through N7): `border-blue-500`
- `human_action`: `border-green-500`
- `veto_fired`: `border-red-500`
- `resolution`: `border-teal-500`
- `early_warning`: `border-amber-500`
- `execution`: `border-blue-400`

Feed header: "ATLAS ACTIVITY FEED" with a pulsing green dot when connected.

---

## L1 Interface (simplified view)

Accessible via a toggle in the top-right of the centre panel: `[L1 View] [L2 View]` — pill toggle, L2 selected by default.

When L1 is selected, the full briefing card is replaced with:

```
┌─────────────────────────────────────────────────────────────────┐
│  INCIDENT: FinanceCore — PaymentAPI / TransactionDB            │
│  Priority: P2    SLA Breach: 21:34                             │
└─────────────────────────────────────────────────────────────────┘

WHAT IS HAPPENING:
PaymentAPI is returning HTTP 503 errors. TransactionDB connection pool
is at 94% capacity. HikariCP is timing out on new connections.

ATLAS RECOMMENDS:
  1. Restore HikariCP maxPoolSize to 150
  2. Restart connection manager pod
  3. Monitor connection count for recovery over next 5 minutes

┌──────────────────────────┐  ┌──────────────────────────┐
│        APPROVE           │  │     ESCALATE TO L2       │
│  (large, green, full)    │  │  (large, amber, full)    │
└──────────────────────────┘  └──────────────────────────┘
```

Clean. Minimal. Two buttons. Nothing else. This is for L1 engineers who need to act fast.

---

## Top Bar

```
┌─────────────────────────────────────────────────────────────────┐
│  ◈ ATLAS                    ● Connected    09:24:13 UTC        │
└─────────────────────────────────────────────────────────────────┘
```

- Logo: `◈ ATLAS` in white, slightly larger, left-aligned
- Connection status: green dot + "Connected" text, or amber "Reconnecting..." or red "Disconnected"
- Current time UTC: right-aligned, monospace, updates every second
- Background: `#0D1117` (slightly darker than main background)
- Height: `h-12`

---

## Responsive Behaviour

This dashboard is designed for a 1920×1080 presentation screen. It does not need to be mobile-responsive. It must look perfect at exactly 1920×1080. If the viewport is smaller, the panels can scroll horizontally — do not collapse the layout.

---

## States to Design

Design all of these states — the demo transitions through all of them:

1. **Normal state** — all green, log stream scrolling, no incident
2. **Detection state** — health indicator turning amber/red, activity feed lighting up
3. **Incident active** — briefing card visible, all six sections populated, SLA counting down
4. **Graph animation playing** — traversal sequence in progress
5. **Veto panel visible** — red veto banner below Section 6
6. **Early warning card visible** — amber card below briefing card
7. **Awaiting secondary approval** — after primary approve click
8. **Playbook executing** — progress indicator, step counter
9. **Post-resolution** — MTTR counter, recovery chart, green resolution summary
10. **L1 view** — simplified interface, two buttons

---

## What Makes This Look Real (Not a Mock)

Every number in the UI must look like it came from a real system:
- Confidence score: `0.84` — not `85%` or `High`
- Similarity score: `91%` — not `Similar` or `High Match`
- SHAP values: `connection_count: 67%, query_latency: 21%, error_rate: 12%` — not generic bars
- CHG number: `CHG0089234` — real format, monospace
- INC number: `INC0089247` — real ServiceNow format
- MTTR: `4:12` — not "4 minutes"
- SLA countdown: `21:34` — counting down in real time
- Timestamps: `09:24:13` — real time, updating

The UI should feel like a real operations tool that engineers would actually use under pressure. Not a demo mockup. Not a slide. A real product.

---

## Component Summary

| Component | Location | Key Data |
|---|---|---|
| ClientRoster | Left panel | Health status, trust level, compliance badges |
| ActivityFeed | Right panel | Real-time ATLAS action log |
| BriefingCard | Centre (incident mode) | All 6 sections, real pipeline data |
| GraphViz | Inside BriefingCard Section 2 | Neo4j traversal, animated |
| SHAPChart | Inside BriefingCard | Feature attribution percentages |
| ApprovalFlow | Bottom of BriefingCard | Approve / Modify / Reject + dual sign-off |
| EarlyWarning | Below BriefingCard | Adjacent service σ values |
| PostResolution | Centre (resolved mode) | MTTR, recovery chart, summary |
| L1Interface | Centre (L1 toggle) | Simplified 2-button view |
| TopBar | Top of viewport | Logo, connection status, UTC clock |

---

*Build this exactly. Every colour, every number format, every state. This is a live demo for enterprise judges. It must look like a product that already exists in production.*
