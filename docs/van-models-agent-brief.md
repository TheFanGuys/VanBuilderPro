# Van models — spec-collection agent brief

**Scope:** how agents populate the `van_models` table. This extends **Spec §5.1**
with the configuration axes (roof / designation / body / length) and tells the
sourcing + spec-collection agents exactly what to gather per van, where to get
it, how to normalize it, and when to flag a row incomplete.

Companion files: `van-models.json` (seed catalog, 58 configs) and
`build_van_models.py` (the generator that emits it).

---

## 1. The job

A "van model" row is **one buildable configuration**, not one nameplate. A
Sprinter is not a row; *Sprinter 2500, 170" WB, high roof, cargo* is a row.
Agents enumerate the real configuration matrix per make, then fill each row's
dimensions and weights — or flag what's missing.

Two passes, mirroring §2.1:

1. **Sourcing agent** — confirm which configurations actually ship (the matrix),
   from the manufacturer build/order guide. Don't invent combos.
2. **Spec-collection agent** — for each row, fill every **required** field
   (§3). If a value isn't on an authoritative source, leave it `null` and set
   `provenance.confidence` / `missing_required` — **never guess** (§8 rule).

---

## 2. Configuration axes — the canonical vocabulary

Each make names things differently. Normalize to these tokens; keep the
manufacturer's own label in `roof_label` / `trim` for display.

| Axis | Canonical tokens | Notes |
|---|---|---|
| `roof` | `low`, `medium`, `standard`, `high`, `super_high` | see per-make table below |
| `length_class` | `standard`, `regular`, `long`, `extended`, `long_ext` | |
| `body_style` | `cargo`, `crew`, `passenger`, `window`, `chassis_cab` | |
| `drivetrain` | `RWD`, `AWD`, `FWD` | ProMaster is FWD only |
| `rear_wheels` | `SRW`, `DRW` | DRW on heavy trims |

### Per-make valid values (verified matrices)

**Mercedes-Benz Sprinter**
- Designations: `1500` (144" only), `2500`, `3500`, `3500XD`, `4500` (cab-chassis-heavy).
- Wheelbases / length: `144"` standard, `170"` long, `170"` extended.
- Roofs: `standard`, `high`. (The old **low roof is gone** on current US vans;
  treat "low" only when collecting older model years.)
- Bodies: `cargo`, `crew`, `passenger`, `chassis_cab`.
- Extended length ships **high roof only**. AWD from 2500 up.

**Ford Transit**
- Designations: `150`, `250`, `350`, `350HD`.
- Wheelbases / length: `130"` regular, `148"` long, `148"` long_ext (extended body).
- Roofs: `low`, `medium`, `high`. Availability: 130"→ low/medium; 148"→ low/medium/high;
  extended → **high only**.
- Bodies: `cargo`, `crew`, `passenger` (passenger = 350 / 350HD on 148" & extended).

**Ram ProMaster**
- Designations: `1500`, `2500`, `3500`.
- Wheelbases / length: `118"`, `136"`, `159"`, `159"` extended.
- Roofs: `low` (standard), `high`, `super_high` (super-high from MY2023+).
- Bodies: `cargo`, `window`, `chassis_cab`. **FWD only.**
- Verified combo list is in the Stellantis press kit (see `van-models.json` sources).

> When in doubt about whether a combo ships, the **order guide is authoritative**.
> A dealer "build & price" tool is the fastest live check.

---

## 3. Fields the spec agent must fill

`van_models@2` schema (required marked ★ — a row is `complete` only when all ★ are non-null):

```
id                                  slug, stable
make, model                         ★  Mercedes-Benz / Ford / Ram ; Sprinter / Transit / ProMaster
model_designation                   ★  1500 / 250 / 3500XD ...
body_style, roof, length_class      ★  canonical tokens (§2)
wheelbase_in                        ★
drivetrain, rear_wheels                RWD/AWD/FWD ; SRW/DRW
exterior_height_in
interior_L_in, interior_W_in, interior_H_in   ★  cargo load-area, inches
between_wheelwells_in                  width between the wheel boxes (fitment)
front_axle_to_interior_front_in     ★  "faOff" — drives axle math (§4.8). Geometry, per model.
gvwr_lb                             ★
gawr_front_lb, gawr_rear_lb         ★
curb_front_lb, curb_rear_lb         ★  per-axle, from the door-jamb sticker / scale
payload_lb                             gvwr − curb (derive if both known)
wheelwell_cutouts[]                    {x_from_front_in, width_in, length_in, intrusion_in}
provenance                             {confidence, sources[], last_verified, ...}
complete, missing_required             computed
```

**Why faOff and curb-by-axle stay null in the seed:** they're vehicle/option
specific and feed the GAWR/GVWR safety warnings. They must come from the actual
sticker or upfitter guide — so the seed flags them `needs_verification` rather
than carrying a fabricated number.

---

## 4. Source hierarchy (most → least authoritative)

1. **Manufacturer upfitter / body builder guide** (best for interior dims,
   faOff, wheel-well geometry, GAWR). Ford Pro Upfitter, MB Body & Equipment
   Guide, Ram ProMaster Body Builder Guide.
2. **Order / order guide** — which configs ship; GVWR by designation.
3. **Door-jamb certification label** — the truth for **curb-by-axle, GVWR, GAWR**
   on a *specific* vehicle. Always wins for weights when a real van is in hand.
4. **Dealer spec pages / KBB / Edmunds** — fast for dims and GVWR; treat as
   `manufacturer_approx`, confirm against 1–3 before marking `verified`.

Record each value's origin in `provenance.sources`. If two sources disagree,
keep the more authoritative and note the conflict — don't average.

---

## 5. Normalization rules

- **Units:** inches and pounds. Convert ft/cm/kg at ingest.
- **Roof:** map the manufacturer word to a canonical token (e.g. ProMaster
  "Standard" → `low`; Sprinter "High Roof" → `high`). Keep the original in
  `roof_label`.
- **Interior length** = cargo **load-area** length behind the front seats (use
  the published *load-floor* length where given), not exterior length.
- **Don't collapse** AWD/DRW into the base row silently — if it changes a ★
  weight, it's a **new row**.
- **id** is stable: `{model}-{designation}-{wb}{ext?}-{roof}-{body}`.

---

## 6. Validation the agent runs before writing

1. Combo is in the make's attested matrix (§2) — else reject as not-buildable.
2. All ★ fields non-null → `complete=true`; else list them in `missing_required`.
3. Each weight value has a source in `provenance.sources`.
4. If `gvwr_lb` and per-axle curb are present: `payload_lb = gvwr − curb_total`,
   and sanity-check `curb_front + curb_rear ≤ gvwr`, `front ≤ gawr_front`,
   `rear ≤ gawr_rear`.
5. `interior_H_in` consistent with roof token (high roof shouldn't read 56").

These mirror the build-time checks in Spec §6 — same data, caught earlier.

---

## 7. Seed status (what's already in `van-models.json`)

- **58 configurations**: Sprinter 20, Transit 22, ProMaster 16.
- **Configs**: attested from manufacturer build matrices.
- **Dimensions**: manufacturer-approx, populated.
- **Weights / faOff**: null + `needs_verification`, except four sourced rows
  (Transit 350 ext DRW GVWR/GAWR; Transit 350 passenger GVWR; ProMaster 2500-159
  and 3500-159ext GVWR). **0/58 are fully complete** — that's the honest
  starting point; the spec agent's job is to close `missing_required`, vehicle by
  vehicle, from the sources above.

To extend: add combos to `COMBOS` and verified weights to `VERIFIED` in
`build_van_models.py`, re-run, commit the JSON.
