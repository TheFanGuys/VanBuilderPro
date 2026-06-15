# Project Status

_One-page snapshot. Counts are from the current `data/` files._

---

## ✅ Finished

- **Layout planner** (`app/VanBuilder.jsx`) — canvas resizes per trim; drag-and-drop;
  per-trim boundary, roof-fit, and wheel-well checks.
- **Database-driven resolution** — placed item = `{id, x, y, rot}`; all specs read
  from `parts-db.json`. BOM, electrical, plumbing, and weight share one record.
- **Parts DB** (`data/parts-db.json`) — 33 components, 6 systems, with electrical/
  plumbing/mounting blocks, confidence, and sources.
- **Van Engineering DB** (`data/van-models.json`) — 59 configs with interior dims,
  wheel wells, door openings, GVWR/GAWR, curb-by-axle, axle geometry, roof load.
- **Live axle-reaction math** (Spec §4.8) — front/rear/GVW vs GAWR/GVWR warnings.
- **Sourcing Queue** (`agents`/`scripts` + `app/sourcing-queue.html`) — self-healing
  gap detection straight from the databases; 393 tasks.
- **Discovery Agent** (`agents/discovery_agent.py` + `app/discovery-queue.html`) —
  full pipeline with source hierarchy, conflict flagging, human-gated apply; 38
  seeded candidates + a live-search connector scaffold (`discovery_sources.py`).
- **Repo + docs** — organized structure, README, architecture/agent/schema/roadmap.

## 🟡 Partially working

- **Axle math is live but data-starved** — engine works; only **1 of 59** trims has
  the inputs to run it (the rest correctly show "pending" with the missing fields).
- **Discovery `discover()` is seeded, not live** — 38 real candidates are hand-seeded;
  the pluggable source layer (`discovery_sources.py`) is in place, but live web
  search needs a search-API key + LLM extraction (see REMAINING-WORK.md A1–A2).
- **`VanPartsDB.jsx` not yet on the shared DB** — the standalone browser still uses
  its own embedded seed instead of reading `data/parts-db.json`.
- **Plumbing view is summary-level** — tanks/fixtures/flow totals only; no line
  routing or fittings modeling.
- **Queue state is per-device** — check-offs and approvals live in `localStorage`,
  not a shared store.

## 🔧 Placeholder / approximate (flagged in data)

- **Transit GVWR estimates** — series-level GVWR from a secondary overview now shows as a flagged estimate (`≈ … est.`) on Transit configs without a verified value; verified rows and the "verify GVWR" tasks are untouched.

- **Reference trim axle inputs** — the Transit 350 EL's axle offset and curb split
  are a labeled `reference_estimate`, present so axle math is demonstrable; queued
  for replacement with sticker/scale values.
- **Door openings & wheel wells** — approximate by make/roof (`confidence: "approx"`).
- **Roof load ratings** — mostly `null` + flagged (one reference value).

## 🔒 Data verified (human-checked or manufacturer-sourced)

- **Parts:** 7 of 33 fully verified with no missing specs.
- **Vans:** GVWR confirmed on 4 configs; payload derivable on 2; **1** config fully
  complete (all required fields).

## ⏳ Data pending (in the queues)

- **Sourcing Queue:** 393 open tasks — 345 van (GVWR/GAWR/curb/axle offset across
  trims) + 48 component (mostly verification + source URLs, a few missing specs).
- **Discovery Queue:** 38 candidates awaiting review — 36 to add, 1 conflict to
  resolve, 1 no-op.

---

## Next 5 priorities

1. **Fill verified van weights for high-value trims** — work the high-priority
   `van_spec` tasks (GVWR, GAWR, curb-by-axle, axle offset) so live axle math runs
   on the trims people actually build on, not just the reference trim.
2. **Complete & verify the 26 flagged parts** — fill missing specs + source URLs in
   `parts-db.json` and flip `verified`; this drains most of the component queue.
3. **Unify on one parts catalog** — migrate `VanPartsDB.jsx` to read
   `data/parts-db.json` so nothing consumes a second component source.
4. **Wire the live discovery hook** — implement per-category web search in
   `discover()` with the existing verification/normalize/merge safety, then run
   discover → approve → apply.
5. **Approve the strongest discovery candidates** — merge high-confidence new parts
   (e.g. Victron Orion XS, Velit 2000R, Epoch) into `parts-db.json`, then let the
   sourcing queue track their remaining gaps.
