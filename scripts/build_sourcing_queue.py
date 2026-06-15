#!/usr/bin/env python3
"""
build_sourcing_queue.py - sourcing-agent task queue (self-healing)
==================================================================
The parts database is the ONLY source of truth. This generator reads the live
records and DETECTS gaps; it keeps no hand-maintained component list. Fill a
spec in parts-db.json, regenerate, and the matching task disappears on its own.

    Parts DB  -->  Missing-Spec Detection  -->  Sourcing Queue
        ^                                          |
        +----------  Parts DB Update  <-- Verification

Two streams:
  1. component_spec - derived from parts-db.json. For each component, a missing
     field auto-creates a task: dimensions, weight, cost, electrical specs,
     plumbing specs, mounting requirements, source URL, verification status.
  2. van_spec - derived from van-models.json missing_required (weights, GAWR,
     curb-by-axle, axle offset).

Run:  python3 build_sourcing_queue.py   (reads parts-db.json + van-models.json)
"""

import json, datetime
import os
from pathlib import Path
# Read/write the repo's /data folder, so this runs from anywhere.
os.chdir(Path(__file__).resolve().parent.parent / "data")

LAST = datetime.date.today().isoformat()

VAN_FIELD_META = {
    "gvwr_lb":        ("high",   "Order guide / door-jamb certification label"),
    "gawr_front_lb":  ("high",   "Upfitter/body-builder guide or door-jamb label"),
    "gawr_rear_lb":   ("high",   "Upfitter/body-builder guide or door-jamb label"),
    "curb_front_lb":  ("high",   "Door-jamb label or corner-scale the actual van"),
    "curb_rear_lb":   ("high",   "Door-jamb label or corner-scale the actual van"),
    "front_axle_to_interior_front_in": ("high", "Body-builder guide dimension drawing (axle to cargo wall)"),
    "interior_L_in":  ("low",    "Upfitter guide interior/load-floor length"),
    "interior_W_in":  ("low",    "Upfitter guide interior width"),
    "interior_H_in":  ("low",    "Upfitter guide interior height by roof"),
}
VAN_FIELD_LABEL = {
    "gvwr_lb": "GVWR", "gawr_front_lb": "Front GAWR", "gawr_rear_lb": "Rear GAWR",
    "curb_front_lb": "Curb weight, front axle", "curb_rear_lb": "Curb weight, rear axle",
    "front_axle_to_interior_front_in": "Axle-to-cargo-wall offset (axle math)",
    "interior_L_in": "Interior length", "interior_W_in": "Interior width", "interior_H_in": "Interior height",
}

SRC_DATASHEET = "Manufacturer datasheet / supplier product page"


def detect_component_gaps(c):
    """Inspect one live parts-db record; return (field, label, priority, why, src) per gap."""
    gaps = []
    d = c.get("dims") or {}
    if d.get("l") is None or d.get("w") is None or d.get("h") is None:
        gaps.append(("dimensions", "Dimensions (LxWxH)", "high",
                     "Needed to place the part and check the van boundary", SRC_DATASHEET))
    if c.get("weightLb") is None:
        gaps.append(("weightLb", "Weight", "high", "Drives payload + axle-load math", SRC_DATASHEET))
    if c.get("costUsd") is None:
        gaps.append(("costUsd", "Cost", "low", "Budget / BOM total", "Supplier price"))

    e = c.get("electrical")
    if e is not None:
        role, volt = e.get("role"), e.get("voltage")
        ac = volt in ("120V", "240V")
        miss = []
        if e.get("voltage") in (None, ""):
            miss.append("voltage")
        if e.get("minWireAwg") in (None, ""):
            miss.append("wire gauge")
        if role == "load":
            if e.get("contAmps") is None:
                miss.append("continuous amps")
            if e.get("recommendedFuseA") is None:
                miss.append("branch breaker (A)" if ac else "fuse (A)")
        if miss:
            gaps.append(("electrical", "Electrical: " + ", ".join(miss),
                         "high", "Wire/fuse sizing is a safety spec", SRC_DATASHEET))

    p = c.get("plumbing")
    if p is not None and p.get("fluid") in (None, ""):
        gaps.append(("plumbing", "Plumbing: fluid type", "medium", "Routing fresh vs gray vs waste", SRC_DATASHEET))

    m = c.get("mounting") or {}
    if not (m.get("surface") or (m.get("notes") or "").strip()):
        gaps.append(("mounting", "Mounting requirements", "medium", "How/where it fastens and clearances", "Install manual / datasheet"))

    srcs = c.get("sources") or []
    if not srcs or not (srcs[0].get("url") or "").strip():
        gaps.append(("sources", "Source / datasheet URL", "low", "Traceability for every spec", "Manufacturer product page"))

    if not c.get("verified", False):
        gaps.append(("verified", "Human verification", "low", "Final sign-off after specs are collected", "Cross-check record vs datasheet"))
    return gaps


def component_tasks(parts):
    tasks = []
    for c in parts:
        for field, label, pri, why, src in detect_component_gaps(c):
            tasks.append({
                "id": "comp:" + c["id"] + ":" + field, "stream": "component_spec",
                "target": c["id"], "target_label": c["name"], "system": c.get("system"),
                "field": field, "field_label": label, "priority": pri, "why": why,
                "source_hint": src, "status": "open",
            })
    return tasks


def van_tasks(catalog):
    tasks = []
    for r in catalog["van_models"]:
        for field in r.get("missing_required", []):
            if field not in VAN_FIELD_META:
                continue
            pri, src = VAN_FIELD_META[field]
            tasks.append({
                "id": "van:" + r["id"] + ":" + field, "stream": "van_spec",
                "make": r["make"], "model": r["model"], "target": r["id"], "target_label": r["trim"],
                "field": field, "field_label": VAN_FIELD_LABEL.get(field, field), "priority": pri,
                "why": "Needed for axle/GVWR safety warnings" if pri == "high" else "Refines floor-plan accuracy",
                "source_hint": src, "status": "open",
            })
    return tasks


def main():
    parts = json.load(open("parts-db.json"))["components"]
    catalog = json.load(open("van-models.json"))
    tasks = component_tasks(parts) + van_tasks(catalog)
    order = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(key=lambda t: (order[t["priority"]], t["stream"], t["target"]))
    counts = {"high": 0, "medium": 0, "low": 0}
    by_stream = {}
    for t in tasks:
        counts[t["priority"]] += 1
        by_stream[t["stream"]] = by_stream.get(t["stream"], 0) + 1
    out = {
        "generated": LAST,
        "pipeline": ["Parts DB", "Missing-Spec Detection", "Sourcing Queue", "Verification", "Parts DB Update"],
        "source": "parts-db.json + van-models.json (detected live; no hand-kept list)",
        "summary": {"total": len(tasks), "by_priority": counts, "by_stream": by_stream},
        "priority_legend": {
            "high": "Safety-relevant; a build decision rides on it",
            "medium": "Refines accuracy",
            "low": "Provenance / verification / hygiene",
        },
        "tasks": tasks,
    }
    json.dump(out, open("sourcing-queue.json", "w"), indent=2)
    comp = by_stream.get("component_spec", 0)
    print("Wrote sourcing-queue.json - %d tasks (%d component, %d van)" % (len(tasks), comp, by_stream.get("van_spec", 0)))
    print("  by priority:", counts)
    print("  component tasks detected straight from %d parts-db records" % len(parts))


if __name__ == "__main__":
    main()
