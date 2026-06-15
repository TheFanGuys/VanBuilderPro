# Agent Workflow

VanBuilder has two cooperating agent pipelines. Both treat `data/parts-db.json`
(and `data/van-models.json`) as the single source of truth, both keep a human in
the loop, and neither ever invents or silently overwrites data.

```
            ┌──────────────────────── Component Discovery Agent ───────────────────────┐
            │  find new real parts → verify sources → normalize → propose for approval  │
            └───────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼ (approve)
   ┌──────────────┐   add / update      ┌──────────────────┐   detect gaps   ┌──────────────────┐
   │   Discovery  │ ──────────────────► │    Parts DB      │ ──────────────► │  Sourcing Queue  │
   │    Queue     │                     │  parts-db.json   │                 │ (missing specs)  │
   └──────────────┘                     └──────────────────┘ ◄────────────── └──────────────────┘
        ▲ approve/reject                          ▲                fill              │ collect
        │                                         └──────────────── verify ─────────┘
```

---

## 1. Sourcing Queue — self-healing gap detection

**Script:** `scripts/build_sourcing_queue.py`
**Output:** `data/sourcing-queue.json` → viewed in `app/sourcing-queue.html`

Reads the live database records and **detects** missing specs. There is no
hand-maintained list; fill a field and regenerate, and the task disappears.

```
Parts DB ─► Missing-Spec Detection ─► Sourcing Queue ─► Verification ─► Parts DB Update
   ▲                                                                          │
   └──────────────────────────────────────────────────────────────────────────┘
```

**Two streams**

- `component_spec` — per `parts-db.json` record: flags missing dimensions,
  weight, cost, electrical specs (role-aware: a busbar isn't asked for a fuse;
  AC loads ask for a breaker), plumbing fluid, mounting, source URL, and human
  verification.
- `van_spec` — per `van-models.json` record: flags missing GVWR, front/rear GAWR,
  curb-by-axle, axle offset, and interior dimensions.

**Priority:** high = safety-relevant (weights, GAWR, wire/fuse); medium = accuracy;
low = provenance/verification. Each task carries a source hint (e.g. "door-jamb
label or corner-scale the van," "manufacturer datasheet").

Current output: **393 tasks** (48 component, 345 van).

---

## 2. Component Discovery Agent — finding new parts

**Script:** `agents/discovery_agent.py`
**Output:** `data/discovery-queue.json` → reviewed in `app/discovery-queue.html`

```
Discovery ─► Candidate List ─► Spec Extraction ─► Source Verification
          ─► Normalize Units ─► Merge Plan ─► Add/Update parts-db.json ─► Missing-Spec Tasks
```

| Stage | Function | What it does |
|---|---|---|
| Discovery | `discover()` | returns candidate components. **Currently seeded** with 33 real high-value parts; in production this is where per-category web search plugs in. |
| Spec extraction | `extract_specs()` | attaches/parses specs; strips spec authority from community-only sources. |
| Source verification | `verify_sources()` | applies the hierarchy → `confidence`. |
| Normalize units | `normalize_units()` | mm→in, kg→lb, price range → single USD estimate. |
| Missing detection | `detect_missing()` | same field set as the sourcing queue. |
| Merge plan | `plan_merge()` | matches by brand+model vs Parts DB → `add` / `update` / `conflict` / `noop`. |
| Apply (gated) | `apply_approved()` | merges **approved** candidates into `parts-db.json`. |

### Source hierarchy (authoritative → weakest)

| Kind | May set specs? | May set price/availability? | Role |
|---|---|---|---|
| `datasheet` / `manual` | ✅ | ✅ | authoritative — confidence `manufacturer` |
| `supplier` | ✅ (if no datasheet) | ✅ | confidence `manufacturer`/`estimated` |
| `retailer` | ❌ | ✅ | price + availability — confidence `estimated` |
| `community` (forum/YouTube/Reddit/blog) | ❌ | ❌ | **popularity signal only** |

### Safety rules (enforced in code)

1. **Never overwrite a verified spec** with unverified data.
2. If a discovered value disagrees with an existing value → **flag a conflict**,
   do not overwrite, do not guess. Conflicts are locked from approval until
   resolved.
3. Discovered parts land as `pending`; **a human approves** (in the Discovery
   Queue) before anything is written to `parts-db.json`.
4. `parts-db.json` stays the single source of truth.

Current output: **33 candidates** — 31 new (add), 1 conflict (a verified price
mismatch, correctly blocked), 1 no-op; 4 flagged as new releases.

### Human-in-the-loop

Both queues are review surfaces. The Sourcing Queue is a check-off worklist; the
Discovery Queue has Approve/Reject per card and an "Export approved IDs" button
that produces the `approvals.json` consumed by `--apply`. Approval state is stored
per-device in `localStorage`.

---

## The loop

A spec gap anywhere becomes a task; collecting it and marking the record verified
removes the task; a discovered part flows through verification and, once a human
approves it, becomes a first-class database record whose own remaining gaps the
sourcing queue then tracks. The system trends toward more complete, more verified
data over time without ever guessing.
