# Roadmap

A history of what's been built and where it goes next. Detailed current state is
in [PROJECT-STATUS.md](PROJECT-STATUS.md).

---

## Done

**Phase 0 — Planner foundation**
- Drag-and-drop floor-plan planner with materials, electrical, plumbing, and
  weight views.

**Phase 1 — Databases as the source of truth**
- Parts DB (`parts-db.json`, `parts_db@2`) with electrical/plumbing/mounting spec
  blocks, verification status, and sources.
- Van Engineering DB (`van-models.json`, `van_models@3`): interior dims, wheel
  wells, door openings, GVWR/GAWR, curb-by-axle, axle geometry, roof load.
- Planner rewired so a placed item is just `{id, x, y, rot}`; all specs resolve
  from the database. BOM, electrical, plumbing, and weight all read one record.

**Phase 2 — Engineering analysis**
- Live axle-reaction math (Spec §4.8) with front/rear/GVW vs GAWR/GVWR warnings.
- Roof-fit, wheel-well overlap, and roof-load checks.
- Missing/unverified specs surfaced as warnings throughout the UI.

**Phase 3 — Self-healing data pipeline**
- Sourcing Queue that detects gaps directly from the databases (no hand-kept
  list) and turns each into a prioritized task with a source hint.

**Phase 4 — Discovery**
- Component Discovery Agent: discover → extract → verify (source hierarchy) →
  normalize → merge-plan → human-gated apply, with a Discovery Queue review panel.
- Catalog expanded to 33 components; 33 real discovery candidates seeded.

**Phase 5 — Repo hygiene (this pass)**
- Organized into a GitHub-ready structure with full documentation. Feature freeze.

---

## Next

**Near term — fill verified data (no new features)**
- Work the high-priority `van_spec` tasks: enter verified GVWR/GAWR/curb-by-axle
  and axle offsets for high-value trims so live axle math runs beyond the single
  reference trim.
- Fill the 26 `needsReview` parts (specs + sources) and mark verified.
- Consolidate: migrate `VanPartsDB.jsx` to read `data/parts-db.json` so the
  standalone browser and the planner share one catalog.

**Mid term — close the discovery loop**
- Replace the seeded `discover()` with live per-category web search, keeping the
  same verification/normalize/merge safety.
- Run discovery → approve → apply into `parts-db.json`; let the sourcing queue
  track each new part's remaining gaps.
- Broaden van coverage (more configurations; optionally more platforms) on the
  honest null-weights pattern.

**Longer term — deeper modeling & persistence (feature work)**
- Run-length-based wire sizing and voltage-drop checks (Spec §4.4) using actual
  layout distances instead of nominal gauges.
- Plumbing line routing and fittings, not just tanks/fixtures.
- Optional shared persistence (replace per-device `localStorage` for queue state).
- Export: cut sheets, wiring schedule, and a printable BOM.
