# docs

Project documentation. Read these before writing any code.

---

## Files

| File | What it contains |
|------|-----------------|
| `MASTER.md` | Complete product specification. The single source of truth. Five flows, full architecture, demo timeline, 7-day sprint plan. Read this first. |
| `ARCHITECTURE.md` | System design. All 6 layers, all components, Neo4j schema, data flow diagram, complete tech stack. |
| `USECASE.md` | User flows for every persona: SDM, L1, L2, L3, client. Nine use cases from onboarding to compliance audit. |
| `PLAN.md` | Build sequence. Every task in order with done conditions. Do not start a new task until the current one is complete. |
| `STRUCTURE.md` | Every file in the repository, its purpose, its responsibilities, its guardrails. Read the relevant section before building any file. |
| `ROLE.md` | AI agent behavioral contract. Hard rules on code quality, security, multi-tenancy, and what production-ready means on this project. |
| `TODO.md` | Outstanding tasks and known issues. |


---

## Reading order

1. `MASTER.md` - understand what ATLAS is and the five flows
2. `ARCHITECTURE.md` - understand how it is built
3. `USECASE.md` - understand who uses it and how
4. `STRUCTURE.md` - understand every file before touching it
5. `PLAN.md` - understand the build sequence

---

## Key numbers

These appear throughout the codebase and documentation:

| Number | What it is |
|--------|-----------|
| 43 minutes | Atlassian 2024 benchmark MTTR for P2 enterprise incidents |
| 0.92 | FinanceCore auto-execute threshold |
| 0.82 | RetailMax auto-execute threshold |
| 0.84 | Expected composite confidence score for the FinanceCore demo scenario |
| 0.91 | ChromaDB similarity score for INC-2024-0847 in the FinanceCore scenario |
| 94% | Conformal confidence on the PostgreSQL detection |
| 90 seconds | Cascade correlation window |
| 60 seconds | Neo4j query result cache TTL |
| 30 minutes | Agent bootstrap period before Alerts are permitted |
| 5 | Minimum historical records before cold-start veto lifts |
| 7 | Number of hard vetoes in the confidence engine (plus 1 cold-start veto = 8 total) |
| 3x | Weight multiplier for L3 corrections in the learning engine |
