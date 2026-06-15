# Van Parts DB — component database

A typed data layer for a DIY van / RV build planner. It models every kind of
build component (electrical, plumbing, HVAC, tanks, appliances, roof, cabinetry,
build materials), flags missing or unverified specs, and imports/exports as JSON
and CSV. The schema is built so a future AI agent can populate rows straight from
manufacturer datasheets, with a human verification step baked in.

There are two pieces in this delivery:

- **`VanPartsDB.jsx`** — a runnable React UI (browse, filter, detail panel,
  warnings, import/export). This is the live demo.
- **`van-parts-db/src/`** — the framework-agnostic TypeScript core below.

## Files

| File | What it holds |
|------|---------------|
| `types.ts` | All interfaces: `VanComponent`, `Dimensions`, `PowerSpec`, `Capacity`, `SourceRef`, `Warning`, `ComponentFilter`, and the `SystemType` / `Voltage` / `ConfidenceLevel` unions. |
| `seed.ts` | `SEED_COMPONENTS` — 30 worked examples across every system. |
| `warnings.ts` | `getWarnings()`, `worstLevel()`, `isClean()` — the data-quality gate. |
| `filter.ts` | `filterComponents()`, `brandsOf()`, `categoriesOf()` — pure filtering. |
| `io.ts` | `exportJSON` / `importJSON`, `exportCSV` / `importCSV`, `importAny`. |
| `index.ts` | Barrel re-export of everything above. |

```ts
import { SEED_COMPONENTS, filterComponents, getWarnings, exportCSV } from "./van-parts-db/src";
```

## The component shape

Every part is one `VanComponent`. Units are fixed so nothing has to guess:
**inches, pounds, USD, watts, amps**; capacity carries its own unit.

```ts
{
  id, name, system, category, brand, model,
  dims: { l, w, h },                 // inches, any axis may be null
  weightLb, costUsd,                 // null when unknown
  power: { voltage, watts, amps, surgeWatts, idleWatts } | null,
  capacity: { value, unit, kind } | null,
  mountingNotes, sources: [{ label, url }],
  confidence, verified, tags, updatedAt
}
```

Two filter levels: **`system`** is the broad bucket (Electrical, Plumbing, …)
and **`category`** is the sub-type within it (Battery, Charge Controller, …).

## For an AI agent populating from datasheets

1. Fill every field you can read off the datasheet. **Leave anything you can't
   verify as `null`** — never invent a number to fill a blank.
2. Add a `sources` entry pointing at the datasheet or product page.
3. Set `confidence` honestly:
   - `manufacturer` — copied from the maker's published figures.
   - `estimated` — typical/approximate, needs confirming.
   - `unverified` — placeholder from an unconfirmed source.
   - `verified` — only after a human checks it.
4. Leave `verified: false`. A person flips it to `true` in the UI after review.

The warning engine then surfaces every gap automatically, so partial data is
safe to commit — it shows up flagged rather than silently wrong.

## Warning rules (severity: error > warn > info)

- **error** — missing dimensions, missing weight, or `confidence: "unverified"`.
- **warn** — no cost, electrical part with no power draw, tank/battery with no
  capacity, no source link.
- **info** — `estimated` confidence, or not yet human-reviewed.

`worstLevel(getWarnings(c))` returns `"ok"` when a part is clean.

## CSV format

`importCSV` / `exportCSV` use one flat row per part. Nested fields collapse into
named columns and expand back on import:

- dimensions → `length_in, width_in, height_in`
- power → `voltage, watts, amps, surge_watts, idle_watts`
- capacity → `capacity_value, capacity_unit, capacity_kind`
- `tags` → semicolon-joined (`lithium;house bank`)
- `sources` → semicolon-joined `label|url` pairs

`importAny(text)` auto-detects JSON vs CSV. Importing merges by `id`, so an
agent can re-import an updated sheet without creating duplicates.

## Note on the seed data

Figures are realistic but approximate, and several rows are intentionally left
incomplete or unverified to exercise the warning system. Always confirm against
the real datasheet and your van's payload sticker before buying or building.
