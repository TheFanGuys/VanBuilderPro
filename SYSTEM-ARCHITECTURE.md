# System Architecture

VanBuilder is a **data-driven** system: two databases describe the world (parts and
vans), a planner consumes them, and a set of analysis engines derive everything
else. Two agent pipelines keep the databases current. There is **no backend** —
the JSON files in `data/` are the store, and the apps are single-file
React/HTML clients.

---

## 1. Data flow

```
                ┌─────────────────────┐     ┌──────────────────┐
                │  Van Engineering DB │     │     Parts DB     │
                │   van-models.json   │     │   parts-db.json  │
                └──────────┬──────────┘     └────────┬─────────┘
                           │                         │
                           ▼                         ▼
                     ┌───────────────────────────────────┐
                     │          Layout Planner            │
                     │            (VanBuilder.jsx)          │
                     │  placed item = { id, x, y, rot }   │
                     └───────────────────────────────────┘
                           │        │        │        │
              ┌────────────┘   ┌────┘   ┌────┘   └─────────────┐
              ▼                ▼        ▼                      ▼
        ┌───────────┐  ┌────────────┐ ┌──────────┐   ┌──────────────────┐
        │ Electrical│  │  Plumbing  │ │  Weight  │   │ BOM (materials)  │
        └─────┬─────┘  └─────┬──────┘ └────┬─────┘   └────────┬─────────┘
              └──────────────┴─────────────┴──────────────────┘
                                   ▼
                       ┌────────────────────────┐
                       │  Engineering Warnings  │  axle/GVWR, roof-fit,
                       │                        │  wheel-well, wire/fuse,
                       └────────────────────────┘  missing-spec flags
```

Feeding the databases:

```
Component Discovery Agent ─► discovery-queue.json ─►(approve)─► parts-db.json
Sourcing Queue (detection) ◄────────────────────────────────── parts-db.json
                                                                van-models.json
```

---

## 2. Single source of truth

Every component is defined exactly once, in `data/parts-db.json`. When a part is
placed in the planner, the placement record is only an id plus geometry; all
specs are looked up from the database record at render time. This means:

- The Materials/BOM, Electrical tab, Plumbing tab, and Weight analysis all read
  the same record — they can never disagree.
- Updating a spec in the database updates every consumer at once.
- Missing/unverified specs surface as warnings everywhere the part appears.

Vans work the same way via `data/van-models.json`: interior dimensions, wheel
wells, door openings, GVWR/GAWR, curb-by-axle and axle geometry all come from the
selected configuration.

---

## 3. The planner (`app/VanBuilder.jsx`)

- **Canvas** is sized from the selected trim's interior length × width (`PX_PER_IN`
  scale). Changing the van resizes the canvas, repositions wheel wells, and
  re-bases every boundary and weight check.
- **Resolution layer:** `partView()` maps a raw Parts DB record into the planner's
  working shape; `vanView()` does the same for a van record. These are the only
  places the database schema is interpreted.
- **Placement model:** `placed = [{ iid, cid, x, y, rot }]`. `items` resolves each
  to its database record plus per-trim flags (`outside`, `tooTall`, `onWell`).

### Engines (all pure functions of the placed items + selected van)

| Engine | What it computes | Source |
|---|---|---|
| `systemElec()` | battery Ah/Wh, daily draw, autonomy, DC/AC load totals, inverter capacity checks | `electrical` block |
| `elecWarnings()` | per-circuit wire/fuse/ampacity checks, confidence/source flags | `electrical` block |
| `computeAxle()` | live front/rear axle reactions + GVW vs GAWR/GVWR (Spec §4.8: `W×d/wheelbase`) | van axle geometry + curb + part weights |
| `roofLoad()` | roof component weight vs roof-load rating | roof-category weights + van rating |
| weight / balance | dry weight, water weight, side balance, payload headroom | `weightLb`, tank `plumbing.tankGal` |
| BOM | grouped quantities, unit weight/cost, verify status | full record |

If a required input is missing (e.g. a trim has no axle offset/curb), the engine
returns a "pending" state naming the missing fields rather than guessing.

---

## 4. Units & conventions

Inches, pounds, USD, watts, amps. Capacity (`{value, unit, kind}`) carries its own
unit. Water weight uses 8.34 lb/gal. Wire ampacity uses a lookup table; axle
reaction uses distance-behind-front-axle `d = axle_offset + (y + length/2)`.

---

## 5. Runtime model

- **Clients:** `VanBuilder.jsx` / `VanPartsDB.jsx` are single-file React components
  (Tailwind classes, `lucide-react` icons). The three `*.html` viewers are
  self-contained (vanilla JS + inline CSS, `localStorage` for check-off/approval
  state).
- **No server:** databases are flat JSON; agents are Python scripts run on demand.
  This keeps the system portable and inspectable, at the cost of no multi-user
  sync (queue state is per-device in `localStorage`).
- **Generated vs authored:** `van-models.json` and `parts-db.json` are authored
  through their `build_*.py` generators (so provenance and computed flags stay
  consistent). `sourcing-queue.json` and `discovery-queue.json` are fully derived.

See [DATA-SCHEMA.md](DATA-SCHEMA.md) for record shapes and
[AGENT-WORKFLOW.md](AGENT-WORKFLOW.md) for the pipelines.
