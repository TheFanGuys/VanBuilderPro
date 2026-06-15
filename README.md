# VanBuilder

A database-driven planning system for DIY camper-van and RV builds. You lay out
a van interior by dragging real components onto a scaled floor plan, and the app
continuously computes electrical loads, plumbing, weight distribution, axle
loads, a bill of materials, and engineering warnings — all resolved from a
single component database. Two agent pipelines keep that database honest and
growing: a **Sourcing Queue** that detects missing specs, and a **Component
Discovery Agent** that finds new real-world parts and proposes them for review.

Built around the principle that **the database is the single source of truth**
and that the system should **flag missing data rather than guess it**.

---

## Architecture at a glance

```
Van Engineering DB ─┐
Parts DB ───────────┼─► Layout Planner ─► Electrical ─► Plumbing
                    │                   └► Weight ─► BOM ─► Engineering Warnings
Discovery Agent ────┘ (feeds new parts in)      ▲
Sourcing Queue ─────────────────────────────────┘ (detects every gap)
```

A placed component stores only `{ id, x, y, rotation }`. Every spec — dimensions,
weight, cost, electrical, plumbing, mounting, verification status, sources — is
read from its Parts DB record. See [SYSTEM-ARCHITECTURE.md](SYSTEM-ARCHITECTURE.md).

---

## Repository layout

```
vanbuilder/
├── README.md                  · this file
├── SYSTEM-ARCHITECTURE.md     · data flow, engines, runtime model
├── AGENT-WORKFLOW.md          · sourcing + discovery agent pipelines
├── DATA-SCHEMA.md             · parts-db / van-models / queue schemas
├── ROADMAP.md                 · phases done + planned
├── PROJECT-STATUS.md          · one-page status (finished / partial / pending)
├── REMAINING-WORK.md          · complete list of what's left to build
├── HOW-TO-RUN.md              · plain-English run guide
├── app/                       · UI (open in a React/artifact runtime or a browser)
│   ├── VanBuilder.jsx           · the planner (React, single file)
│   ├── VanPartsDB.jsx         · standalone parts-database browser (React)
│   ├── van-picker.html        · van catalog browser (single-file)
│   ├── sourcing-queue.html    · sourcing-queue viewer (single-file)
│   ├── discovery-queue.html   · discovery-queue review panel (single-file)
│   └── van-parts-db/          · typed TS data-layer library (alt accessor)
├── data/                      · the databases + generated queues (source of truth)
│   ├── parts-db.json          · canonical component catalog (33 components)
│   ├── van-models.json        · van engineering DB (59 configs)
│   ├── sourcing-queue.json    · detected missing-spec tasks (generated)
│   └── discovery-queue.json   · discovered component candidates (generated)
├── agents/
│   ├── discovery_agent.py     · Component Discovery Agent pipeline
│   ├── discovery_sources.py   · pluggable candidate source (seed default; live scaffold)
│   └── README.md              · agent layer overview
├── scripts/                   · regenerate the data files
│   ├── build_parts_db.py
│   ├── build_van_models.py
│   └── build_sourcing_queue.py
└── docs/
    ├── VAN-BUILD-DESIGNER-SPEC.md   · original domain spec (single source of rules)
    └── van-models-agent-brief.md    · spec-collection brief for the van DB
```

---

## Quick start

> **Not a developer?** Start with [HOW-TO-RUN.md](HOW-TO-RUN.md) — plain-English, click-by-click.


### Run the apps
The four `app/*.html` files are self-contained — open them in any browser.
`VanBuilder.jsx` and `VanPartsDB.jsx` are single-file React components meant to run
in a React/Tailwind runtime (e.g. the Claude artifact sandbox or a Vite/Next app
with Tailwind + `lucide-react`).

### Regenerate the data
The Python scripts have no dependencies beyond the standard library and read/write
`data/` regardless of where you run them from:

```bash
python3 scripts/build_van_models.py        # → data/van-models.json
python3 scripts/build_parts_db.py          # → data/parts-db.json
python3 scripts/build_sourcing_queue.py    # → data/sourcing-queue.json  (reads the two above)
python3 agents/discovery_agent.py          # → data/discovery-queue.json (reads parts-db.json)
```

### Approve discovered parts (human-gated)
```bash
# 1. Review in app/discovery-queue.html, click Approve, "Export approved IDs"
# 2. Save the copied JSON as approvals.json, then:
python3 agents/discovery_agent.py --apply approvals.json   # dry-run by default
```

---

## Conventions

- **Units:** inches, pounds, USD, watts, amps. Capacity carries its own unit.
- **Honesty rule:** any spec that isn't sourced is `null` and flagged — never
  invented. Gaps become tasks in the sourcing or discovery queue.
- **Single source of truth:** `data/parts-db.json` (components) and
  `data/van-models.json` (vans). Nothing downstream redefines a component.

## Status & next steps
See [PROJECT-STATUS.md](PROJECT-STATUS.md) for what's finished, partial, and
pending, plus the next five priorities. Domain rules live in
[docs/VAN-BUILD-DESIGNER-SPEC.md](docs/VAN-BUILD-DESIGNER-SPEC.md).

## License
Not yet chosen — add a `LICENSE` file before publishing publicly.
