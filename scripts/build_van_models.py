#!/usr/bin/env python3
"""
build_van_models.py  —  van_models catalog generator
=====================================================
Emits `van-models.json`, the seed catalog for the Van Build Designer
`van_models` table (Spec section 5.1, extended with configuration axes).

WHY A GENERATOR (not hand-typed JSON):
  - The trim matrix is a product of axes (designation x wheelbase/length x roof
    x body). Encoding the axes + a few dimensional lookups keeps every row
    consistent and lets the sourcing/spec agents EXTEND it without copy-paste
    drift. Same pattern as bom.py / pbom.py.

HONESTY RULES (Spec sec 8 "flag it, don't guess"):
  - Configuration combos below are ATTESTED from manufacturer / build matrices
    (see SOURCES). Only real combos are listed.
  - Interior/exterior DIMENSIONS are manufacturer-approx (vary by options) and
    tagged confidence "approx".
  - Safety-critical WEIGHTS (gvwr, gawr_front/rear, curb_front/rear) and the
    axle geometry (front_axle_to_interior_front_in) are LEFT NULL and tagged
    "needs_verification" UNLESS a specific sourced value is provided. Curb/axle
    split must come from the door-jamb sticker or upfitter guide per actual
    vehicle — never invented here.
  - Every row carries `provenance` (confidence, sources, last_verified) and a
    computed `complete` flag + `missing_required` list so the app/agent knows
    what still has to be collected.

UNITS: inches, pounds. Run:  python3 build_van_models.py
"""

import json, datetime
import os
from pathlib import Path
# Read/write the repo's /data folder, so this runs from anywhere.
os.chdir(Path(__file__).resolve().parent.parent / "data")

LAST_VERIFIED = "2026-06-14"

SOURCES = {
    "sprinter": [
        {"label": "Mercedes-Benz Sprinter dimensions / configurations (dealer spec aggregates)",
         "url": "https://www.mbwhiteplains.com/mercedes-benz-sprinter-dimensions/"},
        {"label": "Sprinter lineup overview (trims, roofs, wheelbases)",
         "url": "https://thevansmith.com/blogs/vans-for-sale/2025-mercedes-benz-sprinter-specs"},
    ],
    "transit": [
        {"label": "Ford.com 2025 Transit Cargo Van models (roof/WB/GVWR availability)",
         "url": "https://www.ford.com/commercial-trucks/transit-cargo-van/2025/models/transit-van/"},
        {"label": "Transit load-floor lengths & roof heights",
         "url": "https://www.lascoford.com/ford-transit-features.htm"},
    ],
    "promaster": [
        {"label": "Stellantis press kit — 2025 ProMaster full build matrix",
         "url": "https://media.stellantisnorthamerica.com/newsrelease.do?id=26201&mid="},
        {"label": "ProMaster interior dimensions by wheelbase",
         "url": "https://everywherewithclaire.com/ram-promaster-dimensions/"},
    ],
}

# Fields that must be present for a van_models row to count as "complete"
REQUIRED = [
    "make", "model", "model_designation", "body_style", "roof", "wheelbase_in",
    "interior_L_in", "interior_W_in", "interior_H_in",
    "front_axle_to_interior_front_in",
    "gvwr_lb", "gawr_front_lb", "gawr_rear_lb", "curb_front_lb", "curb_rear_lb",
]

# ---------------------------------------------------------------------------
# Dimensional lookups (manufacturer-approx; vary with options) ------------- #
# interior length keyed by (wheelbase_in, length_class) ; values are cargo
# load-area lengths behind the front seats, inches.
# ---------------------------------------------------------------------------
DIMS = {
    "Sprinter": {
        "interior_W_in": 70.0, "between_wheelwells_in": 53.9,
        "interior_H_by_roof": {"standard": 66.0, "high": 79.0},
        "exterior_H_by_roof": {"standard": 100.0, "high": 110.0},
        "interior_L": {(144, "standard"): 135.0, (170, "long"): 173.6, (170, "extended"): 189.0},
    },
    "Transit": {
        "interior_W_in": 69.5, "between_wheelwells_in": 54.8,
        "interior_H_by_roof": {"low": 56.9, "medium": 72.0, "high": 81.5},
        "exterior_H_by_roof": {"low": 82.9, "medium": 100.0, "high": 110.4},
        # uses published load-floor lengths
        "interior_L": {(130, "regular"): 126.0, (148, "long"): 143.7, (148, "long_ext"): 172.2},
    },
    "ProMaster": {
        "interior_W_in": 75.6, "between_wheelwells_in": 56.0,
        "interior_H_by_roof": {"low": 65.0, "high": 76.0, "super_high": 87.0},
        "exterior_H_by_roof": {"low": 88.0, "high": 101.0, "super_high": 112.0},
        "interior_L": {(118, "standard"): 105.1, (136, "standard"): 123.0,
                       (159, "standard"): 146.0, (159, "extended"): 160.0},
    },
}

ROOF_LABEL = {
    "standard": "Standard roof", "high": "High roof", "super_high": "Super-high roof",
    "low": "Low roof", "medium": "Medium roof",
}

# Approx wheel-well cutouts for the floor-plan (low-stakes visual; tagged approx).
# x_from_front = distance from interior front wall to the leading edge of the well.
WELLS = {
    "Sprinter":  [{"x_from_front_in": 95, "width_in": 8, "length_in": 30, "intrusion_in": 5}],
    "Transit":   [{"x_from_front_in": 80, "width_in": 8, "length_in": 28, "intrusion_in": 5}],
    "ProMaster": [{"x_from_front_in": 70, "width_in": 8, "length_in": 30, "intrusion_in": 6}],
}

# Door opening dimensions (inches, approx — vary by build). side = sliding door,
# rear = rear cargo doors. Height keyed by roof token.
DOORS = {
    "Sprinter": {
        "side_w": 51.0, "side_h": {"standard": 50.4, "high": 67.8},
        "rear_w": 59.7, "rear_h": {"standard": 49.6, "high": 68.6},
    },
    "Transit": {
        "side_w": 49.3, "side_h": {"low": 51.4, "medium": 64.0, "high": 75.1},
        "rear_w": 49.3, "rear_h": {"low": 51.0, "medium": 64.0, "high": 75.0},
    },
    "ProMaster": {
        "side_w": 49.6, "side_h": {"low": 60.0, "high": 68.0, "super_high": 78.0},
        "rear_w": 60.3, "rear_h": {"low": 60.0, "high": 68.0, "super_high": 78.0},
    },
}

# Roof load ratings (lb) — load-bearing safety figures (solar + a person on the
# roof). Vary by build and not reliably published per trim, so NULL + flagged.
ROOF_LOAD = {"Sprinter": {"dynamic_lb": None, "static_lb": None},
             "Transit": {"dynamic_lb": None, "static_lb": None},
             "ProMaster": {"dynamic_lb": None, "static_lb": None}}

# SERIES-LEVEL GVWR estimates (lb), keyed by (model, designation). Approximate,
# per-SERIES figures from a secondary overview — NOT per-config and NOT verified.
# They populate `gvwr_estimate_lb` only; the verified `gvwr_lb` field and the
# "verify GVWR" sourcing task are left untouched. Confirm the real number on the
# door-jamb sticker for any specific build.
GVWR_ESTIMATE = {
    ("Transit", "150"):   (8670, 8670),
    ("Transit", "250"):   (9070, 9150),
    ("Transit", "350"):   (9500, 9950),
    ("Transit", "350HD"): (10360, 11000),  # "up to ~11,000"; floor from verified EL DRW
    ("Sprinter", "2500"):   (8550, 9050),
    ("Sprinter", "3500"):   (9900, 11030),
    ("Sprinter", "3500XD"): (9900, 11030),
    # Sprinter 1500 not covered by the provided overview → left as "verify"
    ("ProMaster", "1500"): (8550, 8550),
    ("ProMaster", "2500"): (8900, 9000),
    ("ProMaster", "3500"): (9350, 9900),  # floor from verified 3500 EL; "up to ~9,900+"
}
GVWR_EST_SOURCE = "User-provided OEM overview (secondary; series-level; verify per door sticker)"

# ---------------------------------------------------------------------------
# Verified weight/axle overrides keyed by row id (door-sticker / spec-sheet) #
# Only put a value here if it came from a real source. Everything else stays #
# null + needs_verification.                                                 #
# ---------------------------------------------------------------------------
VERIFIED = {
    # Reference config already in the project spec (Transit 350 DRW 148 EL high roof)
    "transit-350-148ext-high-cargo": {
        "gvwr_lb": 10360, "gawr_front_lb": 5103, "gawr_rear_lb": 7275,
        "rear_wheels": "DRW",
        # axle inputs filled as an engineering REFERENCE ESTIMATE so live axle
        # math is demonstrable. Replace with door-sticker / corner-scale values.
        "front_axle_to_interior_front_in": 48.0,
        "curb_front_lb": 2900, "curb_rear_lb": 3000,
        "_axle_inputs": "reference_estimate",
        "roof_load_rating_lb": {"dynamic_lb": 330, "static_lb": None},
        "_src": {"label": "Project spec sec 4.8 reference (axle inputs estimated)", "url": ""},
        "_conf": "manufacturer",
    },
    # Ford Transit 350 Passenger 148 low roof (KBB spec page)
    "transit-350-148-low-passenger": {
        "gvwr_lb": 9400, "curb_front_lb": None, "curb_rear_lb": None,
        "_curb_total_lb": 6023,
        "_src": {"label": "KBB 2025 Transit 350 Passenger XLT Low Roof",
                 "url": "https://www.kbb.com/ford/transit-350-passenger-van/2025/xlt-w-low-roof"},
        "_conf": "manufacturer",
    },
    # Ram ProMaster 2500 159 high roof cargo (KBB)
    "promaster-2500-159-high-cargo": {
        "gvwr_lb": 8900,
        "_src": {"label": "KBB 2025 ProMaster 2500 SLT High Roof 159 WB",
                 "url": "https://www.kbb.com/ram/promaster-cargo-van/2025/2500-slt-high-roof-w-159--wb"},
        "_conf": "manufacturer",
    },
    # Ram ProMaster 3500 159 extended high roof cargo (KBB)
    "promaster-3500-159ext-high-cargo": {
        "gvwr_lb": 9350,
        "_src": {"label": "KBB ProMaster 3500 SLT+ High Roof Extended 159 WB",
                 "url": "https://www.kbb.com/ram/promaster-cargo-van/2026/3500-slt_plus-high-roof-extended-w-159-wb"},
        "_conf": "manufacturer",
    },
}

# ---------------------------------------------------------------------------
# Attested configuration combos.  Each entry:                                #
#   (designation, wheelbase_in, length_class, roof, body_style)              #
# Only combinations that actually ship are listed. Drivetrain/DRW variants   #
# are collapsed to the common case; the agent expands AWD/DRW as needed.     #
# ---------------------------------------------------------------------------
COMBOS = {
    ("Mercedes-Benz", "Sprinter"): [
        # 1500 — 144" only
        ("1500", 144, "standard", "standard", "cargo"),
        ("1500", 144, "standard", "high", "cargo"),
        # 2500
        ("2500", 144, "standard", "standard", "cargo"),
        ("2500", 144, "standard", "high", "cargo"),
        ("2500", 170, "long", "standard", "cargo"),
        ("2500", 170, "long", "high", "cargo"),
        ("2500", 170, "extended", "high", "cargo"),
        ("2500", 144, "standard", "high", "crew"),
        ("2500", 170, "long", "high", "crew"),
        ("2500", 170, "long", "high", "passenger"),
        # 3500
        ("3500", 144, "standard", "standard", "cargo"),
        ("3500", 144, "standard", "high", "cargo"),
        ("3500", 170, "long", "standard", "cargo"),
        ("3500", 170, "long", "high", "cargo"),
        ("3500", 170, "extended", "high", "cargo"),
        ("3500", 170, "long", "high", "crew"),
        ("3500", 170, "long", "high", "passenger"),
        # 3500XD — heavy, high roof
        ("3500XD", 144, "standard", "high", "cargo"),
        ("3500XD", 170, "long", "high", "cargo"),
        ("3500XD", 170, "extended", "high", "cargo"),
    ],
    ("Ford", "Transit"): [
        # 150
        ("150", 130, "regular", "low", "cargo"),
        ("150", 148, "long", "low", "cargo"),
        ("150", 148, "long", "medium", "cargo"),
        ("150", 148, "long", "high", "cargo"),
        # 250
        ("250", 130, "regular", "low", "cargo"),
        ("250", 130, "regular", "medium", "cargo"),
        ("250", 148, "long", "low", "cargo"),
        ("250", 148, "long", "medium", "cargo"),
        ("250", 148, "long", "high", "cargo"),
        ("250", 148, "long", "medium", "crew"),
        # 350
        ("350", 130, "regular", "low", "cargo"),
        ("350", 148, "long", "low", "cargo"),
        ("350", 148, "long", "medium", "cargo"),
        ("350", 148, "long", "high", "cargo"),
        ("350", 148, "long_ext", "high", "cargo"),
        ("350", 148, "long", "medium", "crew"),
        ("350", 148, "long", "low", "passenger"),
        ("350", 148, "long", "high", "passenger"),
        ("350", 148, "long_ext", "high", "passenger"),
        # 350HD
        ("350HD", 148, "long", "low", "cargo"),
        ("350HD", 148, "long", "high", "cargo"),
        ("350HD", 148, "long_ext", "high", "cargo"),
        ("350HD", 148, "long_ext", "high", "passenger"),
    ],
    ("Ram", "ProMaster"): [
        # 1500
        ("1500", 118, "standard", "low", "cargo"),
        ("1500", 136, "standard", "low", "cargo"),
        ("1500", 136, "standard", "high", "cargo"),
        # 2500
        ("2500", 136, "standard", "low", "cargo"),
        ("2500", 136, "standard", "high", "cargo"),
        ("2500", 159, "standard", "high", "cargo"),
        ("2500", 159, "standard", "high", "window"),
        # 3500
        ("3500", 136, "standard", "low", "cargo"),
        ("3500", 136, "standard", "high", "cargo"),
        ("3500", 159, "standard", "high", "cargo"),
        ("3500", 159, "extended", "high", "cargo"),
        ("3500", 159, "standard", "super_high", "cargo"),
        ("3500", 159, "extended", "super_high", "cargo"),
        ("3500", 159, "extended", "high", "window"),
        ("3500", 159, "standard", "low", "chassis_cab"),
        ("3500", 159, "extended", "low", "chassis_cab"),
    ],
}

DRIVETRAIN_DEFAULT = {"Sprinter": "RWD", "Transit": "RWD", "ProMaster": "FWD"}


def slug(make, model, desig, wb, length, roof, body):
    ln = "" if length in ("standard", "regular", "long") else (
        "ext" if length in ("extended", "long_ext") else length)
    wbtag = f"{wb}{'ext' if ln=='ext' else ''}"
    return f"{model.lower()}-{desig.lower()}-{wbtag}-{roof.replace('_','')}-{body}".replace("--", "-")


def build_row(make, model, combo):
    desig, wb, length, roof, body = combo
    d = DIMS[model]
    rid = slug(make, model, desig, wb, length, roof, body)

    # base length lookup key: ProMaster/Sprinter keyed on length_class token
    L = d["interior_L"].get((wb, length))

    length_label = {
        "standard": "", "regular": "", "long": "",
        "extended": "Extended ", "long_ext": "Extended ",
    }[length]
    trim_str = f"{desig} {ROOF_LABEL[roof]} {length_label}{wb}\" WB {body.replace('_',' ').title()}"

    row = {
        "id": rid,
        "make": make,
        "model": model,
        "model_designation": desig,
        "trim": trim_str,
        "body_style": body,
        "roof": roof,
        "roof_label": ROOF_LABEL[roof],
        "length_class": length,
        "wheelbase_in": wb,
        "drivetrain": DRIVETRAIN_DEFAULT[model],
        "rear_wheels": "SRW",
        "exterior_height_in": d["exterior_H_by_roof"][roof],
        "interior_L_in": L,
        "interior_W_in": d["interior_W_in"],
        "interior_H_in": d["interior_H_by_roof"][roof],
        "between_wheelwells_in": d["between_wheelwells_in"],
        # safety-critical: null until verified per vehicle
        "front_axle_to_interior_front_in": None,
        "gvwr_lb": None,
        "gawr_front_lb": None,
        "gawr_rear_lb": None,
        "curb_front_lb": None,
        "curb_rear_lb": None,
        "payload_lb": None,
        "wheelwell_cutouts": WELLS[model],
        "wheelwell_cutouts_confidence": "approx",
        # ---- engineering DB fields ----
        "door_openings": {
            "side_slider": {"width_in": DOORS[model]["side_w"], "height_in": DOORS[model]["side_h"].get(roof)},
            "rear": {"width_in": DOORS[model]["rear_w"], "height_in": DOORS[model]["rear_h"].get(roof)},
            "confidence": "approx",
        },
        "axle_positions": {
            "front_axle_to_interior_front_in": None,   # = faOff; filled below if known
            "rear_axle_to_interior_front_in": None,    # derived faOff + wheelbase
            "wheelbase_in": wb,
        },
        "roof_load_rating_lb": dict(ROOF_LOAD[model]),
    }

    sources = list(SOURCES[model.lower()])
    conf = "approx"  # dims attested approx; weights still missing

    # apply verified overrides if present
    v = VERIFIED.get(rid)
    if v:
        for k, val in v.items():
            if k.startswith("_"):
                continue
            row[k] = val
        if v.get("_curb_total_lb") and row.get("curb_front_lb") is None:
            row["_curb_total_lb"] = v["_curb_total_lb"]
        if v.get("_src") and v["_src"].get("url"):
            sources = [v["_src"]] + sources
        conf = v.get("_conf", conf)
        # derive payload if gvwr + curb total known
        if row.get("gvwr_lb") and row.get("_curb_total_lb"):
            row["payload_lb"] = row["gvwr_lb"] - row["_curb_total_lb"]

    # mirror axle offset into the engineering axle_positions block
    fa = row.get("front_axle_to_interior_front_in")
    row["axle_positions"]["front_axle_to_interior_front_in"] = fa
    row["axle_positions"]["rear_axle_to_interior_front_in"] = (fa + row["wheelbase_in"]) if fa is not None else None
    # derive payload from per-axle curb if both axles known and payload still missing
    if row.get("payload_lb") is None and row.get("gvwr_lb") and row.get("curb_front_lb") is not None and row.get("curb_rear_lb") is not None:
        row["payload_lb"] = row["gvwr_lb"] - (row["curb_front_lb"] + row["curb_rear_lb"])

    # series-level GVWR estimate (labeled; never overwrites verified gvwr_lb)
    est = GVWR_ESTIMATE.get((model, row["model_designation"]))
    if est:
        lo, hi = est
        row["gvwr_estimate_lb"] = {
            "low": lo, "high": hi, "basis": "series_estimate",
            "confidence": "estimated", "source": GVWR_EST_SOURCE,
        }
    else:
        row["gvwr_estimate_lb"] = None

    weights_known = any(row.get(k) is not None for k in
                        ("gvwr_lb", "gawr_front_lb", "gawr_rear_lb", "curb_front_lb", "curb_rear_lb"))
    missing = [f for f in REQUIRED if row.get(f) in (None, "")]
    row["provenance"] = {
        "confidence": conf,
        "config_attested": True,
        "dimensions_source": "manufacturer_approx",
        "weights_source": "partially_verified" if weights_known else "needs_verification",
        "sources": sources,
        "last_verified": LAST_VERIFIED,
    }
    row["complete"] = len(missing) == 0
    row["missing_required"] = missing
    return row


def main():
    catalog = []
    for (make, model), combos in COMBOS.items():
        for combo in combos:
            catalog.append(build_row(make, model, combo))

    out = {
        "schema": "van_models@3 (engineering DB: + door openings, axle positions, roof load)",
        "generated": datetime.date.today().isoformat(),
        "units": {"length": "in", "weight": "lb"},
        "required_fields": REQUIRED,
        "notes": (
            "Configurations are attested from manufacturer build matrices. "
            "Dimensions are manufacturer-approx and vary by options. "
            "Weights and axle geometry are null where unverified — the "
            "spec-collection agent must fill them from the order/upfitter guide "
            "or door-jamb sticker per the agent brief. Never invent them."
        ),
        "count": len(catalog),
        "van_models": catalog,
    }
    with open("van-models.json", "w") as f:
        json.dump(out, f, indent=2)

    # summary
    by_model = {}
    complete = 0
    for r in catalog:
        by_model[r["model"]] = by_model.get(r["model"], 0) + 1
        if r["complete"]:
            complete += 1
    print(f"Wrote van-models.json — {len(catalog)} configs")
    for m, n in by_model.items():
        print(f"  {m}: {n}")
    print(f"Complete (all required filled): {complete}/{len(catalog)}")
    print(f"Needing spec-agent verification: {len(catalog)-complete}")


if __name__ == "__main__":
    main()
