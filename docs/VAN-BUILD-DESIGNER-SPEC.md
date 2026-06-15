# Van Build Designer — Project Spec & Knowledge Base

**Purpose of this file:** the single source of truth for the larger app. It carries the product vision, the agent/database architecture, the **engineering domain knowledge and rules** learned across the prototype project, the **data model** the agents populate, the **validation rules** the app must enforce, and a list of reference assets already built. Hand this to any new session, agent, or contributor before they touch the project.

-----

## 1. Product vision

A web app where a user:

1. **Picks a van model** (Transit, Sprinter, Promaster, etc. — each with its own dimensions, wheelbase, axle positions, GAWR/GVWR, curb weights).
1. **Customizes a floorplan by drag-and-drop** — cabinets, bed, galley, bath, garage, plus electrical/plumbing components.
1. The app then automatically produces:
- **Weight tracking + warnings** (axle loads vs GAWR, GVWR, balance).
- **Electrical diagram** (one-line) + **plumbing diagram** (schematic).
- **Complete BOM** — structure (t-slot + plywood), enclosure, electrical, plumbing — with a cut list.

The differentiator is that the layout *drives* the engineering: place a box or a battery and the framing, panels, wiring, fusing, and weight all derive automatically, with real warnings (over-axle, voltage drop, full switching channels, etc.).

-----

## 2. Architecture

### 2.1 Agents

- **Sourcing agent** — finds relevant parts/components across suppliers (Victron, Safiery, 80/20, plumbing, etc.) for each category.
- **Spec-collection agent** — takes found parts, extracts and **normalizes** their specs into the standard schema (Section 5), and writes to the database. Must fill *every required field* for that category or flag the part incomplete.
- **(Recommended) Validation/sizing agent** — given a build, applies the rules in Section 6 to size wire/fuses, check axle loads, and emit warnings. Keep sizing logic server-side/agent-side so the front-end stays thin.

### 2.2 Database

- Just built. Schema in Section 5. The catalog is the centerpiece — agents keep it current; the app reads from it.

### 2.3 Front-end

- Prototype is a **self-contained single-file HTML** (no build step, iPhone/Safari-first, `localStorage`). See `van-build-designer.html`. As it scales to multi-van + DB it will likely need an API, but keep the **layout-first, derive-everything-from-geometry** principle.

-----

## 3. The three material layers (core mental model)

The app tracks **three layers**, not one:

1. **Structure** — 10-series t-slot aluminum frame (skeleton).
1. **Enclosure** — Baltic birch plywood panels (boxes, skins, doors, drawers).
1. **Systems** — electrical + plumbing components placed on/in the structure.

**Key principle:** layers 1 and 2 **derive from the box geometry** the user draws (L×W×H + per-face options). Layer 3 is placed components that carry weight, position, and electrical/plumbing attributes.

-----

## 4. Domain knowledge & engineering rules

> This is the accumulated brain. Embed it. Don’t make agents re-derive it.

### 4.1 Electrical — wire sizing & voltage drop

- **Voltage-drop formula (DC, round-trip):**
  `Vdrop = 2 × length_ft × amps × (ohms_per_1000ft / 1000)`
  `%drop = Vdrop / system_volts × 100`
- **Limits:** **3%** for critical/charging runs; **10%** for accessory/lighting. **Size up when borderline** (a run at 3.1% goes to the next gauge).
- **Copper resistance (Ω / 1000 ft):**
  
  |AWG|Ω/1000ft|AWG|Ω/1000ft|
  |---|--------|---|--------|
  |4/0|0.0490  |6  |0.395   |
  |3/0|0.0618  |8  |0.628   |
  |2/0|0.0779  |10 |0.999   |
  |1/0|0.0983  |12 |1.588   |
  |2  |0.156   |14 |2.525   |
  |4  |0.249   |16 |4.016   |
  |   |        |18 |6.385   |
- **Two checks per run, not one:** voltage drop **and** ampacity. A gauge can pass drop but fail ampacity (e.g., 80 A on 6 AWG passes drop on a short run but exceeds 6 AWG ampacity → use 4 AWG). Size to the **larger** of the two.
- **DC-DC (Orion) supply** is fused **both ends** and sized for input drop; run both + and − the full distance (don’t rely on chassis return at 100 A over a long run).
- **Run length comes from the layout**, measured along realistic cable paths (not straight-line). The rear electrical cabinet is the hub; loads measured forward. Mid-roof devices (A/C) have surprisingly long runs to a rear cabinet — this drove the A/C from 2 AWG up to 1/0.

### 4.2 Electrical — Victron Lynx distribution (rules)

- **Lynx Distributor = 4 MEGA-fuse positions**, each fuse **40–400 A**, on a **1000 A busbar**.
- **Rule:** sum of all fuse ratings on a Lynx module **≤ 1000 A** (the bus rating).
- One distributor (4 positions) is **not enough** for a full build — count the fused branches first. A typical build needs ~8 (MultiPlus, MPPT, 2× Orion, A/C, always-hot, STAR-A feed, STAR-B feed) → **two Lynx Distributors**.
- **Lynx Power In** = unfused busbar for the **battery main** connection (battery → Class-T → shunt → Power In, which clicks onto the Distributors).
- **Fuse the right type in the right place:**
  - **Class-T** for the battery main and (optionally) the inverter — high interrupt rating (20 kA) for lithium fault current.
  - **MEGA** in the Lynx Distributor positions.
  - **Blade** fuses for 12 V always-hot loads (sub-block).
  - **Inline** small fuses for valves.

### 4.3 Electrical — STAR digital switching (Safiery)

- **STAR controller = 12 channels (6 × 30 A = 150 A).** Split by **area**: STAR-A front, STAR-B rear.
- Keypads (CAN) + Bluetooth switches **bind straight to STAR** — local switching works with **no GX in the path** (important for lights). Keypads on the CAN bus can address any STAR output (A or B).
- When a STAR runs out of channels, options: **GX IO-Extender 150** (cheap, for screen-operated functions like fills/drains) or a **3rd/2nd STAR controller** (keeps it keypad-native).
- **STAR-Tank** = wireless radar tank sensors → pair to the Safiery STAR hub.

### 4.4 Electrical — key component facts (verified)

- **GX IO-Extender 150:** USB-powered off the GX. Drives loads with **2 latching relays (3 A @ 30 V DC, bi-stable — ideal for motorized valves)** + **1 solid-state switch (4 A @ 70 V DC)**. Its **8 digital I/O and 4 PWM are 5 V / 4 mA logic only** — they need a relay board to drive a 12 V load. So **3 valves direct per unit**; a 4th needs a small relay or gang two.
- **Ekrano GX:** all-in-one GX brain **+ integrated 7” touchscreen** — replaces a Cerbo GX **+** a GX Touch. Has **built-in WiFi but NO built-in Bluetooth** (unlike Cerbo). Anything that needs BT to the GX needs a dongle, or must route through another hub.
- **MultiPlus 12/3000:** ~250 A continuous on the DC/inverter side; Victron recommends ~**400 A** fuse.
- **Orion XS 12/12-50:** 50 A each; mount rear, heavy supply runs forward to the starter battery, fused both ends.
- **Grounding:** **single-point chassis bond** at house battery − (battery side of shunt). Everything shares that one bond. Equipment cases, AC ground bar, solar frames, vehicle 2nd battery − all to chassis.

### 4.5 Plumbing rules

- **Tanks:** fresh (wheel-well/saddle mount common), gray, RO product tank, thermal expansion, cassette toilet. Water weight = **8.34 lb/gal**.
- **Valves — three kinds:** **electric (motorized ball)** for fills/drains, **manual** shutoffs, **check** valves. Only the fills/drains are powered.
- **ShowerMiser is PASSIVE** — thermostatic warm-up recirc, **no power**. Don’t put it on a switching channel.
- **Electric valves drive switching demand** — count them against STAR/IO-Extender capacity. Typical set: city inlet, tank-fill/city-bypass, pump/siphon-fill, fresh drain, gray inlet, gray dump.
- **Galley sink → 5-gal jug** with a purpose-made threaded jug-top hose (no valve, no gray-tank connection) is a valid simple gray solution.
- **Heating is hydronic:** Webasto diesel heater → **calorifier (hot-water HX)** for domestic hot water; hydronic circ pump; cabinet heat (loop + 12 V pad).
- **No double-ordering:** powered plumbing devices (pumps, heater, electric valves) are **bought in the plumbing BOM**; their **wiring/fusing lives in the electrical BOM**.

### 4.6 Structure — 10-series t-slot

- 10-series = 1” × 1” profile, ~**0.30 lb/ft** (single 1010). Lighter than 15-series (good for payload) but **less stiff** — flag unsupported spans over ~30–36” on load frames (bed deck, cantilevers); use closer uprights or doubled rails.
- **Frame derivation per box:** 4 posts @ H, 4 length-rails @ L, 4 width-rails @ (W − 2×profile). Optional shelf/divider support rails.
- **Hardware:** corner brackets/gussets, t-nuts, button-head screws, end caps. (Counts are estimates with adjustable factors; **linear feet is the accurate cost driver**.)

### 4.7 Enclosure — Baltic birch plywood

- Comes in **5×5 sheets (25 sqft)**, not 4×8. Affects nesting/yield.
- Thicknesses & weight: **1/2” ≈ 1.45**, **1/4” ≈ 0.75**, **1/8” ≈ 0.38** lb/sqft.
- **Mounting auto-derives from thickness** (10-series slot fits ~1/4”):
  - **1/8” and 1/4”** → **inset into the slot** (panel cut = face dim − 2×(profile − slot_engage), ≈ −1.5”).
  - **1/2”** → **surface-mount** to the frame face (panel cut = face/frame dimension).
- **Panel cut sizes derive from the frame opening, not the outer box.**
- **Sheet count = area × (1 + waste%) / 25, rounded up.** ~15–20% waste. (Area-based; true 2D nest is a later enhancement — emit the cut list so it can be nested by hand.)
- Default thickness by role: **1/2”** structural (bottoms, fixed sides, shelves, bed deck), **1/4”** backs/drawer bottoms/doors, **1/8”** wall/ceiling skins.

### 4.8 Weight & balance (axle math)

- For a mass at distance `d` **behind the front axle**, on wheelbase `wb`:
  `rear_reaction = W × d / wb`, `front_reaction = W × (wb − d) / wb`.
- Sum every box, panel set, and component reaction onto **base curb weights per axle**, compare to **front GAWR / rear GAWR / GVWR**.
- Interior origin sits some offset behind the front axle (`faOff`, per van model). Get this from the van model record.
- **Transit 350 DRW 148” EL reference:** GVWR **10360**, front GAWR **5103**, rear GAWR **7275**, wheelbase **148”**, interior ≈ **172” L × 70” W**. (Confirm curb weights per axle per actual build/scale.)

-----

## 5. Data model (what the agents populate)

### 5.1 `van_models`

`id, make, model, trim (DRW/SRW, roof, length), wheelbase_in, interior_L_in, interior_W_in, interior_H_in, front_axle_to_interior_front_in, gvwr_lb, gawr_front_lb, gawr_rear_lb, curb_front_lb, curb_rear_lb, wheelwell_cutouts[]`

### 5.2 `components` (universal)

`id, category, subcategory, name, brand, model_no, supplier, supplier_url, price, in_stock, weight_lb, dim_L_in, dim_W_in, dim_H_in, datasheet_url, notes`

**Category-specific spec blocks (required fields the spec agent must fill):**

- **electrical_source/load:** `system_voltage, current_continuous_A, current_peak_A, recommended_fuse_A, fuse_type, min_wire_awg, comms (VE.Direct/VE.Can/CAN/BT/USB/none), switched_by (STAR/IO-Ext/always-hot/AC-panel), terminals (lug/ring/ferrule)`
- **plumbing:** `flow_gpm, connection_size_in, powered (bool), valve_type (electric/manual/check), tank_gal, fluid`
- **structure (t-slot):** `series, profile_w_in, lb_per_ft, slot_width_in`
- **enclosure (ply):** `species, thickness_in, sheet_W_in, sheet_L_in, lb_per_sqft`
- **hardware:** `type (bracket/t-nut/screw/slide/hinge/pull/MC4), fits_series, pack_qty`

### 5.3 `builds`

`id, van_model_id, boxes[], components[], settings (waste%, mat lb/ft & lb/sqft overrides)`

- **box:** `name, x, y, L, W, H, faces{bottom,top,front,back,left,right: {mode: open/panel/door, thickness}}, shelves, dividers, drawers`
- **placed component:** `component_id, x, y, qty`

-----

## 6. Validation rules (warnings the app must emit)

1. **Axle/GVWR:** front > GAWR_F, rear > GAWR_R, or GVW > GVWR → warn; suggest shifting heavy items fore/aft.
1. **Voltage drop:** any run %drop > its limit (3% critical / 10% accessory) → **size up** and warn.
1. **Ampacity:** chosen gauge < load ampacity → size up.
1. **Lynx positions:** fused branches > 4 per Distributor → add a Distributor. Sum of fuses > 1000 A → warn.
1. **STAR channels:** loads on a controller > 12 → suggest IO-Extender (screen functions) or another STAR (keypad functions).
1. **IO-Extender capacity:** > 3 direct valve drives per unit → add a relay or a unit.
1. **Bluetooth path:** BT device + Ekrano GX (no BT) → warn (needs dongle / different hub).
1. **T-slot span:** 10-series unsupported run > ~36” on a load frame → warn (deflection).
1. **Double-order guard:** a powered plumbing device must appear in plumbing BOM (device) AND electrical BOM (circuit) — never the same line twice.
1. **ShowerMiser / passive devices:** never assigned a switching channel.

-----

## 7. Reference assets already built (prototype)

|File                              |What it is                                                                                                                                 |
|----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
|`van-build-designer.html`         |**v1 layout cut engine** — drag boxes, per-face cut list, live t-slot + Baltic + weight/axle. Single-file, localStorage.                   |
|`van-electrical-BOM.xlsx`         |Full electrical BOM (sources, Lynx ×2 + 8 MEGA, STAR-A/B, always-hot, exterior/Garmin, wire by gauge, grounding, terminals).               |
|`van-plumbing-BOM.xlsx`           |Full plumbing BOM (tanks, pumps, hydronic, filtration/RO, fixtures, electric + manual valves, lines/fittings).                             |
|`van-wire-schedule.xlsx`          |Per-run voltage-drop calc (resistance ref + formulas) → buy-footage per gauge. **Feeds the BOM wire section via JSON so they can’t drift.**|
|`van-cable-cutlist.xlsx`          |Per-run cut lengths + terminals, from the wire schedule.                                                                                   |
|`van-switch-map.xlsx`             |Every keypad/BT button → STAR output, two-sided bed logic, scenes (All-Off, Night, Away, Winterize).                                       |
|`van-fuse-schedule.xlsx`          |Every fuse/breaker in the rig (Class-T, 8 MEGA, blade, IO-Ext, AC panel, Garmin).                                                          |
|`van-commissioning-checklist.xlsx`|Safe power-up & test sequence A→I.                                                                                                         |
|`van-wiring-cabinet.html`         |One-line electrical diagram (synced to the BOMs).                                                                                          |
|`van-plumbing.html`               |Plumbing schematic.                                                                                                                        |
|`transit-weight-balance.html`     |Weight/axle/cost tracker with component weights + positions.                                                                               |

**Generators (Python, openpyxl):** `bom.py`, `pbom.py`, `wire.py`, `cutlist.py`, `switchmap.py`, `fuses.py`, `commission.py`. Diagram generators are JS (`build4.js`) rendered to SVG.

-----

## 8. Conventions & lessons learned (rules for building this)

- **Pull from the actual layout/schematic — never invent.** The biggest source of error was filling gaps from generic knowledge (missed valves, wrong wire lengths). If a value isn’t derivable, flag it, don’t guess.
- **Single source of truth.** The wire schedule computes footage; the BOM reads it (JSON link). Never hand-enter a number two places — link them so they can’t drift.
- **Size up when borderline.** Voltage drop and ampacity both rounded toward the safer gauge.
- **Derive from geometry.** Structure, enclosure, and weight all come from the boxes drawn — don’t make the user re-enter material.
- **Verify before showing (diagrams).** Render to PNG, check for label collisions/overlaps, escape `& < >` in SVG text, then publish.
- **Spreadsheet hygiene:** use real formulas (not hard-coded values); price-safe extended cost `=qty*N(price)` to avoid `#VALUE` on empty inputs; money format with dash-for-zero; blue font = user input cell.
- **Platform:** iPhone/Safari-first, single-file HTML, no build step, `localStorage` for persistence, touch via pointer events with `touch-action:none` on the canvas.
- **Two-check sizing, area-based sheets, opening-based cuts** — see Sections 4.1, 4.7.

-----

## 9. Open items / next phases

- **Component → BOM auto-wiring layer:** placing a component should generate its circuit (fuse, gauge, run length from position, switching assignment) and run the Section 6 validations live. This is the configurator on top of the layout engine.
- **Multi-van support:** populate `van_models` (each model’s dims, axles, wheelwell cutouts).
- **True 2D nesting** for plywood cut lists (currently area-based).
- **Diagram auto-generation** from the build graph (one-line + plumbing schematic), not hand-built SVG.
- **Pricing/budget rollup** once the catalog carries live prices.
- **15-series support** (mixed builds) alongside 10-series.

-----

*Keep this file updated as the catalog schema, rules, or assets change. It is the project’s memory.*