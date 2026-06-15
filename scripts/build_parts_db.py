#!/usr/bin/env python3
"""
build_parts_db.py — canonical Parts Database (single source of truth)
=====================================================================
Emits `parts-db.json`. This is THE component catalog the whole app reads:
the layout planner, the electrical + plumbing tabs, the weight analysis, and
the BOM all resolve a placed part back to one record here. Nothing downstream
redefines a component — they reference it by `id`.

Schema `parts_db@2` (extends Van Parts DB `VanComponent`, Spec §5.2) so one
record carries every spec a consumer needs:

  id, name, system, category, brand, model
  dims:{l,w,h}            inches  (floor-plan footprint + height)
  weightLb, costUsd
  electrical | null       {role, voltage, contAmps, peakAmps, surgeWatts,
                           idleWatts, dailyAh, recommendedFuseA, fuseType,
                           minWireAwg, comms, switchedBy, terminals,
                           inverterW, runWatts}
  plumbing   | null       {flowGpm, connectionSizeIn, powered, valveType,
                           tankGal, fluid}
  capacity   | null       {value, unit, kind}
  mounting                {surface, fasteners, clearanceIn, orientation, notes}
  sources[]               {label, url}
  confidence              verified | manufacturer | estimated | unverified
  verified                human sign-off (bool)
  tags[], updatedAt

HONESTY: any spec the source doesn't give is `null` — never invented. The
planner surfaces those gaps as warnings; the sourcing queue turns them into
tasks. Run:  python3 build_parts_db.py
"""

import json, datetime
import os
from pathlib import Path
# Read/write the repo's /data folder, so this runs from anywhere.
os.chdir(Path(__file__).resolve().parent.parent / "data")

DATE = "2026-06-14"

# Required-by-consumer fields per system — drive the "missing spec" warnings.
REQUIRED = {
    "_all": ["dims.l", "dims.w", "dims.h", "weightLb", "costUsd"],
    "electrical": ["electrical.voltage", "electrical.contAmps", "electrical.minWireAwg", "electrical.recommendedFuseA"],
    "plumbing": ["plumbing.fluid"],
}


def C(**k):
    """one component with sane defaults"""
    base = dict(
        system=None, category=None, brand="Generic", model="",
        dims={"l": None, "w": None, "h": None}, weightLb=None, costUsd=None,
        electrical=None, plumbing=None, capacity=None,
        mounting={"surface": None, "fasteners": None, "clearanceIn": None, "orientation": None, "notes": ""},
        sources=[], confidence="estimated", verified=False, tags=[], updatedAt=DATE,
    )
    base.update(k)
    return base


def E(role, voltage, contAmps=None, peakAmps=None, surgeWatts=None, idleWatts=None,
      dailyAh=None, fuse=None, fuseType=None, awg=None, comms="none",
      switchedBy="none", terminals=None, inverterW=None, runWatts=None):
    return {"role": role, "voltage": voltage, "contAmps": contAmps, "peakAmps": peakAmps,
            "surgeWatts": surgeWatts, "idleWatts": idleWatts, "dailyAh": dailyAh,
            "recommendedFuseA": fuse, "fuseType": fuseType, "minWireAwg": awg,
            "comms": comms, "switchedBy": switchedBy, "terminals": terminals,
            "inverterW": inverterW, "runWatts": runWatts}


def P(fluid, tankGal=None, flowGpm=None, conn=None, powered=False, valveType=None):
    return {"flowGpm": flowGpm, "connectionSizeIn": conn, "powered": powered,
            "valveType": valveType, "tankGal": tankGal, "fluid": fluid}


def M(surface=None, fasteners=None, clearanceIn=None, orientation=None, notes=""):
    return {"surface": surface, "fasteners": fasteners, "clearanceIn": clearanceIn,
            "orientation": orientation, "notes": notes}


PARTS = [
  # ---------------- ELECTRICAL ----------------
  C(id="el-bb-200", name="LiFePO4 battery bank (2×100Ah)", system="electrical", category="Battery",
    brand="Battle Born", model="2× BB10012", dims={"l": 27, "w": 13, "h": 9}, weightLb=62, costUsd=1750,
    electrical=E("source", "12V", contAmps=200, peakAmps=400, awg="2 AWG", fuse=125, fuseType="Class-T",
                 comms="BT", terminals="M8 ring"),
    capacity={"value": 200, "unit": "Ah", "kind": "Battery capacity"},
    mounting=M("floor", "strap / hold-down", 2, "upright",
               "Class-T main fuse within 7\" of the positive terminal. Strap down; no venting needed for LiFePO4."),
    sources=[{"label": "Battle Born BB10012 spec", "url": "https://battlebornbatteries.com"}],
    confidence="manufacturer", verified=True, tags=["lithium", "house bank"]),

  C(id="el-mp-2000", name="MultiPlus 12/2000 inverter/charger", system="electrical", category="Inverter/Charger",
    brand="Victron", model="PMP122200000", dims={"l": 16, "w": 8, "h": 8}, weightLb=23, costUsd=760,
    electrical=E("converter", "12V", contAmps=167, peakAmps=350, surgeWatts=4000, idleWatts=8,
                 awg="2/0 AWG", fuse=250, fuseType="Class-T", comms="VE.Bus", terminals="M8 ring", inverterW=2000),
    capacity={"value": 2000, "unit": "W", "kind": "Continuous output"},
    mounting=M("wall/floor", "lag into frame", 4, "vertical",
               "Mount near the bank for short DC runs. AC output to a GFCI sub-panel; bond neutral–ground per code."),
    sources=[{"label": "Victron MultiPlus datasheet", "url": "https://www.victronenergy.com"}],
    confidence="manufacturer", verified=True, tags=["inverter", "shore charging"]),

  C(id="el-mppt-10050", name="SmartSolar MPPT 100/50", system="electrical", category="Charge Controller",
    brand="Victron", model="SCC110050210", dims={"l": 8, "w": 6, "h": 5}, weightLb=6, costUsd=290,
    electrical=E("converter", "12V", contAmps=50, awg="6 AWG", fuse=60, fuseType="MEGA",
                 comms="VE.Direct", terminals="ferrule"),
    capacity={"value": 700, "unit": "W", "kind": "Max solar (12V)"},
    mounting=M("wall", "screws into frame", 6, "vertical",
               "Airflow above/below. Battery side fused; connect battery first, then PV."),
    sources=[{"label": "Victron MPPT page", "url": "https://www.victronenergy.com"}],
    confidence="manufacturer", verified=True, tags=["solar", "mppt"]),

  C(id="el-rng-200", name="200W solar panel", system="electrical", category="Solar Panel",
    brand="Renogy", model="RNG-200D", dims={"l": 59, "w": 26, "h": 1.4}, weightLb=27, costUsd=230,
    electrical=E("source", "N/A", awg="10 AWG", terminals="MC4"),
    capacity={"value": 200, "unit": "W", "kind": "Rated output"},
    mounting=M("roof", "Z-bracket / rail feet", None, "flat",
               "Bed bracket feet in lap sealant. One cable gland for the roof penetration."),
    sources=[{"label": "Renogy product page", "url": "https://www.renogy.com"}],
    confidence="manufacturer", verified=False, tags=["solar", "roof-mount"]),

  C(id="el-orion-30", name="Orion-Tr 12/12-30 DC-DC charger", system="electrical", category="DC-DC Charger",
    brand="Victron", model="ORI121236120", dims={"l": 9, "w": 5, "h": 3}, weightLb=3.3, costUsd=215,
    electrical=E("converter", "12V", contAmps=30, awg="6 AWG", fuse=50, fuseType="MEGA",
                 comms="VE.Direct", terminals="ring"),
    capacity={"value": 30, "unit": "Ah", "kind": "Charge current"},
    mounting=M("wall/floor", "screws into frame", 2, "any",
               "Between starter and house battery. Fuse BOTH ends; run + and − the full distance."),
    sources=[{"label": "Victron Orion-Tr", "url": "https://www.victronenergy.com"}],
    confidence="manufacturer", verified=True, tags=["alternator", "b2b"]),

  C(id="el-fuse-12", name="12-circuit fuse block", system="electrical", category="Fuse Block",
    brand="Blue Sea", model="5026", dims={"l": 7, "w": 3.4, "h": 1.4}, weightLb=0.7, costUsd=55,
    electrical=E("distribution", "12V", contAmps=100, awg="8 AWG", fuse=None, fuseType="blade",
                 terminals="ring + blade"),
    capacity={"value": 12, "unit": "", "kind": "Circuits"},
    mounting=M("wall", "screws", 1, "any", "Accessible, covered. Common negative bus included; label every circuit."),
    sources=[{"label": "Blue Sea 5026", "url": "https://www.bluesea.com"}],
    confidence="verified", verified=True, tags=["distribution"]),

  # ---------------- APPLIANCE ----------------
  C(id="ap-fridge-45", name="12V compressor fridge", system="appliance", category="Refrigerator",
    brand="Dometic", model="CFX3 45", dims={"l": 28, "w": 19, "h": 18}, weightLb=43, costUsd=900,
    electrical=E("load", "12V", contAmps=4, peakAmps=7, dailyAh=50, awg="12 AWG", fuse=15, fuseType="blade",
                 switchedBy="always-hot", terminals="blade"),
    capacity={"value": 1.6, "unit": "cu_ft", "kind": "Fridge interior"},
    mounting=M("floor/cabinet", "cabinet straps", 2, "upright", "Own circuit from the fuse block. Allow compressor airflow."),
    sources=[{"label": "Dometic CFX3 45 (corrected from overview; confirm on datasheet)", "url": "https://www.dometic.com"}],
    confidence="estimated", verified=False, tags=["fridge"]),

  C(id="ap-induction", name="Induction cooktop (single)", system="appliance", category="Cooktop",
    brand="Generic", model="IND-1800", dims={"l": 14, "w": 12, "h": 3}, weightLb=8, costUsd=120,
    electrical=E("load", "120V", contAmps=13, runWatts=1500, awg="14 AWG", fuse=None, fuseType=None,
                 switchedBy="AC-panel", terminals="plug"),
    mounting=M("countertop", "drop-in or portable", 4, "flat", "Needs inverter or shore. Confirm draw; some pull 1800W on boost."),
    sources=[], confidence="estimated", verified=False, tags=["galley", "ac-load"]),

  # ---------------- CLIMATE / HVAC ----------------
  C(id="hv-fan-7500", name="Roof fan", system="hvac", category="Roof Fan",
    brand="Maxxair", model="Deluxe 7500K", dims={"l": 16, "w": 16, "h": 4}, weightLb=12, costUsd=300,
    electrical=E("load", "12V", contAmps=5, dailyAh=15, awg="14 AWG", fuse=7.5, fuseType="blade",
                 switchedBy="STAR", terminals="blade"),
    mounting=M("roof", "14×14 cutout + butyl", None, "flat", "Switched circuit. Lap-seal the flange."),
    sources=[{"label": "Maxxair datasheet", "url": "https://www.maxxair.com"}],
    confidence="manufacturer", verified=True, tags=["ventilation", "roof"]),

  C(id="hv-ac-penguin", name="Roof air conditioner", system="hvac", category="Air Conditioner",
    brand="Dometic", model="Penguin II", dims={"l": 30, "w": 20, "h": 14}, weightLb=70, costUsd=1200,
    electrical=E("load", "120V", contAmps=13, peakAmps=24, surgeWatts=2900, dailyAh=150, runWatts=1500,
                 awg="14 AWG", fuse=None, fuseType=None, switchedBy="AC-panel", terminals="screw"),
    capacity={"value": 13500, "unit": "BTU", "kind": "Cooling"},
    mounting=M("roof", "14×14 cutout + gasket", None, "flat",
               "Own 15A AC branch. Needs inverter or shore; a soft-start tames the surge."),
    sources=[], confidence="estimated", verified=False, tags=["cooling", "roof", "ac-load"]),

  C(id="hv-heater-d4", name="Diesel air heater", system="hvac", category="Heater",
    brand="Espar", model="Airtronic B4", dims={"l": 12, "w": 6, "h": 6}, weightLb=12, costUsd=200,
    electrical=E("load", "12V", contAmps=3, peakAmps=10, surgeWatts=110, dailyAh=5, awg="14 AWG",
                 fuse=15, fuseType="blade", switchedBy="STAR", terminals="blade"),
    capacity={"value": 13600, "unit": "BTU", "kind": "Heat output"},
    mounting=M("floor", "bracket + tank", 3, "flat", "Glow-plug inrush at start; fuse near source. Exhaust vents fully outside (CO risk)."),
    sources=[], confidence="estimated", verified=False, tags=["heat", "diesel"]),

  # ---------------- TANK / PLUMBING ----------------
  C(id="pl-fresh-25", name="Fresh water tank (25 gal)", system="tank", category="Fresh Tank",
    brand="Generic", model="FW-25", dims={"l": 30, "w": 14, "h": 12}, weightLb=18, costUsd=150,
    plumbing=P("fresh", tankGal=25, conn=0.5, powered=False),
    mounting=M("floor/wheel-well", "straps to frame", 1, "level", "Mount low and centered for ballast. Fill port + vent."),
    sources=[], confidence="estimated", verified=False, tags=["water", "tank"]),

  C(id="pl-gray-20", name="Gray water tank (20 gal)", system="tank", category="Gray Tank",
    brand="Generic", model="GW-20", dims={"l": 28, "w": 14, "h": 10}, weightLb=16, costUsd=130,
    plumbing=P("gray", tankGal=20, conn=1.5, powered=False),
    mounting=M("under-floor/floor", "straps", 1, "level", "Slope to the dump valve. Vent above."),
    sources=[], confidence="estimated", verified=False, tags=["water", "tank"]),

  C(id="pl-pump", name="Water pump (12V)", system="plumbing", category="Water Pump",
    brand="Shurflo", model="4008", dims={"l": 9, "w": 5, "h": 5}, weightLb=4, costUsd=90,
    electrical=E("load", "12V", contAmps=7, peakAmps=10, awg="14 AWG", fuse=15, fuseType="blade",
                 switchedBy="always-hot", terminals="blade"),
    plumbing=P("fresh", flowGpm=3.0, conn=0.5, powered=True),
    mounting=M("floor", "screws + rubber feet", 1, "any", "Powered device: bought here, wired in the electrical BOM. Accumulator smooths flow."),
    sources=[{"label": "Shurflo 4008", "url": "https://www.shurflo.com"}],
    confidence="manufacturer", verified=False, tags=["water", "powered"]),

  C(id="pl-heater-cal", name="Hydronic calorifier (hot water)", system="plumbing", category="Water Heater",
    brand="Generic", model="CAL-10L", dims={"l": 16, "w": 12, "h": 12}, weightLb=22, costUsd=450,
    plumbing=P("hot_water", tankGal=2.6, conn=0.5, powered=False),
    mounting=M("floor/cabinet", "bracket", 2, "upright", "Heat exchanger off the diesel hydronic loop. No direct power."),
    sources=[], confidence="estimated", verified=False, tags=["hot water", "hydronic"]),

  C(id="pl-sink", name="Galley sink + faucet", system="plumbing", category="Sink",
    brand="Generic", model="SINK-15", dims={"l": 15, "w": 13, "h": 7}, weightLb=9, costUsd=140,
    plumbing=P("fresh", flowGpm=1.5, conn=0.5, powered=False),
    mounting=M("countertop", "drop-in clips", 2, "level", "Drains to gray. Pair with a hand pump or the 12V pump."),
    sources=[], confidence="estimated", verified=False, tags=["galley"]),

  C(id="pl-shower", name="Shower pan + walls", system="plumbing", category="Shower",
    brand="Generic", model="FRP-3232", dims={"l": 32, "w": 32, "h": 78}, weightLb=90, costUsd=700,
    plumbing=P("fresh", flowGpm=1.8, conn=0.5, powered=False),
    mounting=M("floor", "sealed to floor + wall frame", None, "upright", "Drain to gray. Tall unit — check interior roof height."),
    sources=[], confidence="estimated", verified=False, tags=["wet bath"]),

  C(id="pl-valve-elec", name="Electric drain valve", system="plumbing", category="Valve",
    brand="Generic", model="MV-1", dims={"l": 4, "w": 3, "h": 3}, weightLb=1, costUsd=70,
    electrical=E("load", "12V", contAmps=1, peakAmps=3, awg="16 AWG", fuse=5, fuseType="blade",
                 switchedBy="IO-Ext", terminals="ferrule"),
    plumbing=P("gray", conn=1.5, powered=True, valveType="electric"),
    mounting=M("tank outlet", "thread-on", 1, "any", "Motorized ball valve. Counts against STAR/IO-Extender channels."),
    sources=[], confidence="estimated", verified=False, tags=["powered", "drain"]),

  # ---------------- CABINETRY / FURNITURE ----------------
  C(id="cb-bed", name="Bed platform", system="cabinetry", category="Bed",
    brand="Custom", model="BED-PLAT", dims={"l": 74, "w": 54, "h": 14}, weightLb=120, costUsd=350,
    mounting=M("frame", "t-nuts into 10-series", None, "flat", "3/4\" ply deck + slats on a t-slot frame. Often spans rear width."),
    sources=[], confidence="estimated", verified=False, tags=["sleep"]),

  C(id="cb-galley", name="Galley cabinet", system="cabinetry", category="Cabinet",
    brand="Custom", model="GALLEY-40", dims={"l": 40, "w": 24, "h": 36}, weightLb=110, costUsd=600,
    mounting=M("floor/frame", "screws + t-nuts", None, "upright", "3/4\" birch carcass, butcher top, drawer slides, sink cutout."),
    sources=[], confidence="estimated", verified=False, tags=["galley"]),

  C(id="cb-bench", name="Bench seat", system="cabinetry", category="Seating",
    brand="Custom", model="BENCH-44", dims={"l": 44, "w": 18, "h": 18}, weightLb=70, costUsd=300,
    mounting=M("floor/frame", "screws", None, "upright", "Hinged-lid storage box + cushions. Rated belts if used as seating."),
    sources=[], confidence="estimated", verified=False, tags=["seat", "storage"]),

  C(id="cb-upper", name="Upper cabinet", system="cabinetry", category="Cabinet",
    brand="Custom", model="UPPER-36", dims={"l": 36, "w": 12, "h": 14}, weightLb=40, costUsd=350,
    mounting=M("wall", "t-nuts into wall frame", None, "wall", "Wall-hung ply cabinet w/ doors. Tie into the t-slot uprights."),
    sources=[], confidence="estimated", verified=False, tags=["storage"]),

  C(id="cb-box", name="Storage box", system="cabinetry", category="Storage",
    brand="Custom", model="BOX-24", dims={"l": 24, "w": 18, "h": 16}, weightLb=25, costUsd=120,
    mounting=M("floor", "straps", None, "any", "Secured ply or poly box."),
    sources=[], confidence="estimated", verified=False, tags=["storage"]),

  # ---------------- EXPANSION: electrical ----------------
  C(id="el-bb-100", name="LiFePO4 battery (100Ah)", system="electrical", category="Battery",
    brand="Battle Born", model="BB10012", dims={"l": 12.75, "w": 6.875, "h": 9}, weightLb=31, costUsd=875,
    electrical=E("source", "12V", contAmps=100, peakAmps=200, awg="4 AWG", fuse=100, fuseType="Class-T",
                 comms="none", terminals="M8 ring"),
    capacity={"value": 100, "unit": "Ah", "kind": "Battery capacity"},
    mounting=M("floor", "strap / hold-down", 2, "upright", "Group-27 footprint. No venting (LiFePO4)."),
    sources=[{"label": "Battle Born BB10012", "url": "https://battlebornbatteries.com"}],
    confidence="manufacturer", verified=True, tags=["lithium", "single"]),

  C(id="el-lynx", name="Lynx Distributor (busbar)", system="electrical", category="Busbar",
    brand="Victron", model="LYN060102000", dims={"l": 12, "w": 7, "h": 4}, weightLb=4, costUsd=170,
    electrical=E("distribution", "12V", contAmps=1000, awg="2/0 AWG", fuseType="MEGA", terminals="M8 ring"),
    mounting=M("wall", "screws into frame", 2, "any", "Modular +/- bus. ≤1000A bus; MEGA fuse per branch. Keep runs short."),
    sources=[{"label": "Victron Lynx", "url": "https://www.victronenergy.com"}],
    confidence="manufacturer", verified=False, tags=["distribution", "busbar"]),

  C(id="el-shunt", name="Battery monitor / shunt", system="electrical", category="Monitor",
    brand="Victron", model="SmartShunt 500A", dims={"l": 4, "w": 3, "h": 2}, weightLb=0.6, costUsd=130,
    electrical=E("monitor", "12V", awg="2/0 AWG", comms="BT/VE.Direct", terminals="M10 stud"),
    mounting=M("battery negative", "inline on main −", 1, "any", "Sits on the main negative; all loads return through it."),
    sources=[{"label": "Victron SmartShunt", "url": "https://www.victronenergy.com"}],
    confidence="manufacturer", verified=False, tags=["monitor"]),

  C(id="el-shore-30", name="Shore power inlet (30A)", system="electrical", category="AC Inlet",
    brand="Marinco", model="6373EL-B", dims={"l": 5, "w": 5, "h": 3}, weightLb=1.5, costUsd=60,
    electrical=E("distribution", "120V", contAmps=30, awg="10 AWG", terminals="screw"),
    mounting=M("exterior wall", "4 screws + sealant", 1, "flush", "Feeds the AC sub-panel main breaker. Weatherproof gasket."),
    sources=[], confidence="estimated", verified=False, tags=["ac", "shore"]),

  # ---------------- EXPANSION: climate ----------------
  C(id="hv-dc-ac", name="12V DC air conditioner", system="hvac", category="Air Conditioner",
    brand="Generic", model="DC-5000", dims={"l": 32, "w": 16, "h": 11}, weightLb=42, costUsd=1500,
    electrical=E("load", "12V", contAmps=45, peakAmps=60, dailyAh=200, awg="6 AWG", fuse=60, fuseType="MEGA",
                 switchedBy="STAR", terminals="ring"),
    capacity={"value": 5000, "unit": "BTU", "kind": "Cooling"},
    mounting=M("floor/under-bed", "bracket", 4, "level", "Runs straight off 12V — no inverter. Big DC draw; size wire/fuse carefully."),
    sources=[], confidence="estimated", verified=False, tags=["cooling", "dc"]),

  # ---------------- EXPANSION: plumbing / tank ----------------
  C(id="pl-toilet", name="Composting toilet", system="plumbing", category="Toilet",
    brand="Nature's Head", model="NH-STD", dims={"l": 20, "w": 19, "h": 20}, weightLb=28, costUsd=1000,
    plumbing=P("waste", powered=True),
    electrical=E("load", "12V", contAmps=0.1, awg="18 AWG", fuse=2, fuseType="blade", switchedBy="always-hot", terminals="blade"),
    mounting=M("floor", "2 floor brackets", 2, "upright", "Tiny 12V vent fan. Vent hose to exterior. No black tank."),
    sources=[{"label": "Nature's Head", "url": "https://natureshead.net"}],
    confidence="manufacturer", verified=False, tags=["toilet", "waste"]),

  C(id="pl-fresh-40", name="Fresh water tank (40 gal)", system="tank", category="Fresh Tank",
    brand="Generic", model="FW-40", dims={"l": 36, "w": 16, "h": 14}, weightLb=26, costUsd=200,
    plumbing=P("fresh", tankGal=40, conn=0.5, powered=False),
    mounting=M("floor", "straps to frame", 1, "level", "Heavy when full (~330 lb). Mount low + centered for ballast."),
    sources=[], confidence="estimated", verified=False, tags=["water", "tank"]),

  # ---------------- EXPANSION: appliance / cabinetry ----------------
  C(id="ap-microwave", name="Microwave (700W)", system="appliance", category="Microwave",
    brand="Generic", model="MW-700", dims={"l": 18, "w": 14, "h": 11}, weightLb=25, costUsd=110,
    electrical=E("load", "120V", contAmps=8, runWatts=900, awg="14 AWG", switchedBy="AC-panel", terminals="plug"),
    mounting=M("cabinet", "secured in cabinet", 2, "upright", "Needs inverter or shore. Surge on start; confirm inverter handles it."),
    sources=[], confidence="estimated", verified=False, tags=["galley", "ac-load"]),

  C(id="cb-swivel", name="Swivel seat base", system="cabinetry", category="Seating",
    brand="Generic", model="SWIVEL-1", dims={"l": 18, "w": 18, "h": 4}, weightLb=18, costUsd=250,
    mounting=M("seat pedestal", "bolt to factory seat box", None, "level", "Lets a cab seat rotate into the living space. Vehicle-specific bracket."),
    sources=[], confidence="estimated", verified=False, tags=["seat"]),

  C(id="cb-shelf", name="Garage shelving", system="cabinetry", category="Storage",
    brand="Custom", model="GARAGE-36", dims={"l": 36, "w": 16, "h": 40}, weightLb=35, costUsd=200,
    mounting=M("frame", "t-nuts into 10-series", None, "upright", "Under-bed gear garage. Ties into the t-slot frame."),
    sources=[], confidence="estimated", verified=False, tags=["storage", "garage"]),
]


def get(d, path):
    cur = d
    for k in path.split("."):
        if cur is None:
            return None
        cur = cur.get(k)
    return cur


def missing_fields(c):
    req = list(REQUIRED["_all"])
    if c["electrical"]:
        req += REQUIRED["electrical"]
    if c["plumbing"]:
        req += REQUIRED["plumbing"]
    out = []
    for f in req:
        v = get(c, f)
        if v in (None, ""):
            out.append(f)
    # AC loads need a breaker, not a fuse — don't flag fuse for them
    return out


def main():
    for c in PARTS:
        c["missing"] = missing_fields(c)
        c["placeable"] = all(c["dims"][a] is not None for a in ("l", "w", "h"))
        # data-quality flag for the planner
        c["needsReview"] = (not c["verified"]) or c["confidence"] in ("estimated", "unverified") or len(c["missing"]) > 0

    out = {
        "schema": "parts_db@2 (Van Parts DB / Spec §5.2, extended)",
        "generated": datetime.date.today().isoformat(),
        "units": {"length": "in", "weight": "lb", "cost": "usd", "power": "W", "current": "A"},
        "count": len(PARTS),
        "systems": sorted({c["system"] for c in PARTS}),
        "components": PARTS,
    }
    json.dump(out, open("parts-db.json", "w"), indent=2)

    rev = sum(1 for c in PARTS if c["needsReview"])
    print(f"Wrote parts-db.json — {len(PARTS)} components across {len(out['systems'])} systems")
    print(f"  needing review (unverified / missing specs): {rev}/{len(PARTS)}")
    print(f"  fully verified: {sum(1 for c in PARTS if c['verified'] and not c['missing'])}")


if __name__ == "__main__":
    main()
