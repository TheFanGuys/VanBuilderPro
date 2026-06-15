#!/usr/bin/env python3
"""
discovery_agent.py — Component Discovery Agent
==============================================
Continuously finds real, currently-available van/RV build components and feeds
them — safely — toward the parts database. parts-db.json stays the single
source of truth; this agent never writes verified specs and never guesses.

PIPELINE
  Discovery Agent
    └─► Candidate Component List      discover()         (seeded; web in prod)
        └─► Spec Extraction           extract_specs()
            └─► Source Verification    verify_sources()  (datasheet > retailer > community)
                └─► Normalize Units    normalize_units() (mm→in, kg→lb, price→usd)
                    └─► Merge Plan      plan_merge()     vs parts-db.json
                        ├─► Add / Update parts-db.json   apply_approved()  (human-gated)
                        └─► Missing-spec tasks            detect gaps

SOURCE HIERARCHY (verify_sources)
  datasheet / manual  →  authoritative specs        (confidence "manufacturer")
  supplier / retailer →  availability + price        (confidence "estimated")
  community (forum/YouTube/Reddit/blog) → POPULARITY ONLY, never a spec source.

SAFETY RULES
  • Never overwrite a verified spec with unverified data.
  • If a discovered value conflicts with an existing value → flag for review,
    do not guess, do not overwrite.
  • Discovered items land in the Discovery Queue as "pending"; a human approves
    before anything is written to parts-db.json.

This is the PIPELINE seeded with high-value components — not a full scrape.
Run:  python3 discovery_agent.py            # builds discovery-queue.json
      python3 discovery_agent.py --apply approvals.json   # merge approved items
"""

import json, re, sys, datetime
import os
from pathlib import Path
_ORIG_CWD = Path.cwd()
os.chdir(Path(__file__).resolve().parent.parent / "data")
sys.path.insert(0, str(Path(__file__).resolve().parent))  # so we can import discovery_sources

TODAY = datetime.date.today().isoformat()

# Source kinds, best → weakest. Community can never supply a spec.
SRC_RANK = {"datasheet": 0, "manual": 1, "supplier": 2, "retailer": 3, "community": 4}
SPEC_SOURCES = {"datasheet", "manual", "supplier"}     # may carry specs
PRICE_SOURCES = {"supplier", "retailer"}               # may carry price/availability
POP_SOURCES = {"community"}                            # popularity only


def S(kind, label, url):
    return {"kind": kind, "label": label, "url": url}


def E(role, voltage, contAmps=None, peakAmps=None, surgeWatts=None, dailyAh=None,
      fuse=None, fuseType=None, awg=None, comms="none", terminals=None,
      inverterW=None, runWatts=None):
    return {"role": role, "voltage": voltage, "contAmps": contAmps, "peakAmps": peakAmps,
            "surgeWatts": surgeWatts, "idleWatts": None, "dailyAh": dailyAh,
            "recommendedFuseA": fuse, "fuseType": fuseType, "minWireAwg": awg,
            "comms": comms, "switchedBy": "none", "terminals": terminals,
            "inverterW": inverterW, "runWatts": runWatts}


def P(fluid, tankGal=None, flowGpm=None, conn=None, powered=False, valveType=None):
    return {"flowGpm": flowGpm, "connectionSizeIn": conn, "powered": powered,
            "valveType": valveType, "tankGal": tankGal, "fluid": fluid}


def D(id, brand, model, category, system, ptype, sources, popularity, pop_signal,
      dims=(None, None, None), weightLb=None, price=None, weight_kg=None, dims_mm=None,
      electrical=None, plumbing=None, mounting="", compat="", release_year=None, is_new=False):
    l, w, h = dims
    lo = hi = None
    if isinstance(price, (list, tuple)):
        lo, hi = price
    elif price is not None:
        lo = hi = price
    return {
        "id": id, "brand": brand, "model": model, "category": category, "system": system,
        "productType": ptype,
        "dims": {"l": l, "w": w, "h": h}, "dims_mm": dims_mm,
        "weightLb": weightLb, "weight_kg": weight_kg,
        "priceRange": {"low": lo, "high": hi},
        "electrical": electrical, "plumbing": plumbing,
        "mounting": mounting, "compatibilityNotes": compat,
        "sources": sources,
        "popularity": {"score": popularity, "signal": pop_signal},
        "newness": {"releaseYear": release_year, "isNew": is_new},
        "lastChecked": TODAY,
    }


# ===========================================================================
# STAGE 1 — DISCOVERY  (seeded with high-value components; web search in prod)
# Specs filled only from datasheet/supplier; community URLs are popularity-only.
# ===========================================================================
def seed_candidates():
    return [
      # ---------------- BATTERIES ----------------
      D("battle-born-bb10012", "Battle Born", "BB10012", "Battery", "electrical", "LiFePO4 100Ah",
        [S("datasheet", "Battle Born BB10012 spec", "https://battlebornbatteries.com"),
         S("retailer", "Amazon listing", "https://www.amazon.com"),
         S("community", "VanPowerCalc 2026 roundup (popularity)", "https://vanpowercalc.com")],
        92, "Long-standing US RV standard; most-cited 100Ah unit",
        dims=(12.75, 6.875, 9), weightLb=31, price=989,
        electrical=E("source", "12V", contAmps=100, peakAmps=200, awg="4 AWG", fuse=100, fuseType="Class-T", comms="none", terminals="M8 ring"),
        mounting="Strap down, Group-27 footprint; no venting (LiFePO4)."),

      D("epoch-300-v2", "Epoch", "300Ah Heated V2", "Battery", "electrical", "LiFePO4 300Ah",
        [S("datasheet", "Epoch Batteries spec", "https://epochbatteries.com"),
         S("community", "FarOutRide alternatives (popularity)", "https://faroutride.com")],
        82, "Rising favorite; CANBUS/Victron comms, best cost-per-kWh",
        weightLb=None, price=(900, 1300),
        electrical=E("source", "12V", contAmps=200, awg=None, fuse=None, fuseType="Class-T", comms="CANBUS", terminals="M8 ring"),
        mounting="Heavy (~66 lb) — confirm floor support; self-heating.", is_new=True, release_year=2025),

      D("sok-206", "SOK", "SK12V206", "Battery", "electrical", "LiFePO4 206Ah",
        [S("supplier", "SOK product page", "https://www.sokbattery.com"),
         S("community", "Builder teardown praise (popularity)", "https://faroutride.com")],
        74, "Praised for teardown build quality / value",
        price=(500, 700), electrical=E("source", "12V", contAmps=100, awg=None, comms="BT")),

      D("litime-200", "LiTime", "LT12V200", "Battery", "electrical", "LiFePO4 200Ah",
        [S("supplier", "LiTime product page", "https://www.litime.com"),
         S("community", "Budget pick (popularity)", "https://vanpowercalc.com")],
        76, "Budget value leader (formerly Ampere Time)",
        price=(380, 520), electrical=E("source", "12V", contAmps=100, awg=None, comms="BT")),

      D("dakota-200", "Dakota Lithium", "DL+ 200Ah", "Battery", "electrical", "LiFePO4 200Ah",
        [S("supplier", "Dakota Lithium page", "https://dakotalithium.com")],
        70, "Cold-climate favorite, 11-yr warranty",
        price=(1100, 1300), electrical=E("source", "12V", contAmps=200, awg=None, comms="BT"), is_new=False),

      # ---------------- INVERTERS / CHARGERS / DC-DC / MPPT / DIST ----------------
      D("victron-orion-xs-50", "Victron", "ORI121217040", "DC-DC Charger", "electrical", "Orion XS 12/12-50A",
        [S("datasheet", "Victron Orion XS", "https://www.victronenergy.com"),
         S("retailer", "Current Connected", "https://www.currentconnected.com")],
        85, "New standard alternator charger; replaces Orion-Tr Smart",
        dims=(5.4, 4.85, 1.6), weightLb=0.73, price=303,
        electrical=E("converter", "12V", contAmps=50, awg="6 AWG", fuse=60, fuseType="MEGA", comms="VE.Direct/BT", terminals="screw"),
        mounting="No fan, IP65. Fuse both ends.", is_new=True, release_year=2024),

      D("renogy-inv-2000", "Renogy", "RIV12102S1", "Inverter/Charger", "electrical", "2000W pure sine inverter/charger",
        [S("datasheet", "Renogy datasheet", "https://www.renogy.com"),
         S("retailer", "Renogy store", "https://www.renogy.com")],
        68, "Common budget inverter/charger",
        price=(450, 600), electrical=E("converter", "12V", contAmps=167, surgeWatts=6000, awg="2/0 AWG", fuse=250, fuseType="Class-T", inverterW=2000, terminals="M8 ring")),

      D("victron-lynx-dist", "Victron", "LYN060102000", "Busbar", "electrical", "Lynx Distributor",
        [S("datasheet", "Victron Lynx", "https://www.victronenergy.com")],
        80, "Default modular busbar in Victron van systems",
        dims=(12, 7, 4), weightLb=4, price=170,
        electrical=E("distribution", "12V", contAmps=1000, awg="2/0 AWG", fuseType="MEGA", terminals="M8 ring")),

      # ---------------- SOLAR ----------------
      D("newpowa-200", "Newpowa", "NPA200S-12H", "Solar Panel", "electrical", "200W rigid mono panel",
        [S("datasheet", "Newpowa spec", "https://www.newpowa.com"),
         S("retailer", "Amazon", "https://www.amazon.com")],
        72, "Value rigid panel, common in DIY arrays",
        dims=(59, 26, 1.4), weightLb=24, price=150,
        electrical=E("source", "N/A", awg="10 AWG", terminals="MC4"),
        mounting="Roof Z-brackets; one gland for the run."),

      D("rich-solar-200", "Rich Solar", "RS-M200D", "Solar Panel", "electrical", "200W rigid mono panel",
        [S("supplier", "Rich Solar page", "https://richsolar.com")],
        66, "Popular value panel",
        dims=(58, 26, 1.4), weightLb=25, price=170, electrical=E("source", "N/A", awg="10 AWG", terminals="MC4")),

      # ---------------- WIRE & LUGS ----------------
      D("ancor-2-0-cable", "Ancor", "2/0 Marine Battery Cable", "Wire", "electrical", "2/0 AWG tinned battery cable",
        [S("datasheet", "Ancor / marine spec", "https://www.ancorproducts.com"),
         S("supplier", "Marine electrical supplier", "https://www.defender.com")],
        78, "Marine-grade tinned cable, common for inverter/battery runs",
        price=(4, 7), electrical=E("source", "12V", awg="2/0 AWG"),
        compat="Sold per foot; pair with adhesive-lined heat shrink + tinned lugs."),

      D("selterm-lugs", "Selterm", "Tinned Copper Lug Kit", "Lug", "electrical", "Battery cable lugs (assorted)",
        [S("retailer", "Amazon", "https://www.amazon.com"),
         S("community", "Builder favorite (popularity)", "https://faroutride.com")],
        64, "Common DIY crimp-lug kit",
        price=(20, 40)),

      # ---------------- WATER TANKS / PUMPS / HEATERS ----------------
      D("class-a-fresh-24", "Class A Customs", "WT-2400", "Fresh Tank", "tank", "24-gal fresh water tank",
        [S("supplier", "Class A Customs", "https://www.classacustoms.com")],
        70, "Go-to van fresh-tank supplier",
        dims=(30, 15, 13), weightLb=18, price=160, plumbing=P("fresh", tankGal=24, conn=0.5)),

      D("seaflo-55", "SEAFLO", "SFDP1-055-100-51", "Water Pump", "plumbing", "12V 5.5 GPM 55-PSI pump",
        [S("datasheet", "SEAFLO spec", "https://www.seaflo.com"),
         S("retailer", "Amazon", "https://www.amazon.com")],
        72, "Budget alt to Shurflo, widely used",
        dims=(9, 5, 5), weightLb=4, price=70,
        electrical=E("load", "12V", contAmps=7, peakAmps=10, awg="14 AWG", fuse=15, fuseType="blade"),
        plumbing=P("fresh", flowGpm=5.5, conn=0.5, powered=True)),

      D("truma-aquago", "Truma", "AquaGo Comfort", "Water Heater", "plumbing", "Tankless on-demand water heater",
        [S("manual", "Truma AquaGo manual", "https://www.truma.com")],
        67, "Popular tankless RV water heater",
        weightLb=None, price=(900, 1100), plumbing=P("hot_water", conn=0.5, powered=True),
        electrical=E("load", "12V", contAmps=5, awg="14 AWG", fuse=10, fuseType="blade")),

      # ---------------- TOILETS / SHOWERS ----------------
      D("natures-head", "Nature's Head", "Standard", "Toilet", "plumbing", "Composting toilet",
        [S("manual", "Nature's Head manual", "https://natureshead.net"),
         S("community", "Long-time builder standard (popularity)", "https://www.reddit.com")],
        80, "Long-time composting-toilet standard",
        dims=(20, 19, 20), weightLb=28, price=1000, plumbing=P("waste", powered=True),
        electrical=E("load", "12V", contAmps=0.1, awg="18 AWG", fuse=2, fuseType="blade")),

      D("ogo-toilet", "OGO", "Origin", "Toilet", "plumbing", "Composting toilet w/ agitator",
        [S("supplier", "OGO product page", "https://www.ogo-go.com")],
        74, "Newer compact composting toilet, electric agitator",
        dims=(16, 15, 18), weightLb=20, price=1000, plumbing=P("waste", powered=True),
        electrical=E("load", "12V", contAmps=2, awg="16 AWG", fuse=5, fuseType="blade"), is_new=True, release_year=2022),

      D("thetford-565", "Thetford", "Porta Potti 565", "Toilet", "plumbing", "Portable cassette toilet",
        [S("retailer", "Camping World", "https://www.campingworld.com")],
        62, "Common budget cassette toilet",
        dims=(18, 15, 17), weightLb=12, price=130, plumbing=P("waste", tankGal=5.5)),

      # ---------------- ROOF FANS / AC / HEAT ----------------
      D("maxxair-7500k", "MaxxAir", "MaxxFan Deluxe 7500K", "Roof Fan", "hvac", "14×14 roof vent fan w/ remote",
        [S("manual", "MaxxAir manual", "https://www.maxxair.com"),
         S("community", "Most-installed van fan (popularity)", "https://www.reddit.com")],
        90, "The default van roof fan",
        dims=(16, 16, 4), weightLb=12, price=300,
        electrical=E("load", "12V", contAmps=5, dailyAh=15, awg="14 AWG", fuse=7.5, fuseType="blade"),
        mounting="14×14 cutout + butyl; lap-seal flange."),

      D("dometic-rtx-2000", "Dometic", "CoolAir RTX 2000", "Air Conditioner", "hvac", "12V rooftop DC air conditioner",
        [S("datasheet", "Dometic RTX 2000", "https://www.dometic.com")],
        78, "Established 12V rooftop AC",
        dims=(25.4, 33.9, 6.6), weightLb=71, price=(2500, 3000),
        electrical=E("load", "12V", contAmps=10, peakAmps=45, dailyAh=120, awg="4 AWG", fuse=80, fuseType="MEGA"),
        mounting="Roof; ~6,824 BTU; ~9.5A eco. Cutout ~14.5×15.5. Size 4 AWG / 80A.", is_new=False),

      D("velit-2000r", "Velit", "2000R", "Air Conditioner", "hvac", "12/24/48V rooftop DC AC",
        [S("manual", "Velit 2000R user manual", "https://velitcamping.com"),
         S("community", "Fast-rising affordable 12V AC (popularity)", "https://faroutride.com")],
        80, "Newest popular low-cost 12V rooftop AC",
        dims=(31.5, 31.5, 7.1), weightLb=61, price=1599,
        electrical=E("load", "12V", contAmps=20, peakAmps=60, dailyAh=None, awg="4 AWG", fuse=80, fuseType="MEGA"),
        mounting="~8,000 BTU; 20-60A; 45-58 dB; BT app. Roof-unit dims per overview (verify vs datasheet).", is_new=True, release_year=2023),

      D("nomadic-x2", "Nomadic Cooling", "X2", "Air Conditioner", "hvac", "12V rooftop DC AC",
        [S("supplier", "Nomadic Cooling page", "https://nomadiccooling.com"),
         S("community", "Pioneer 12V AC, easy install (popularity)", "https://faroutride.com")],
        75, "Pioneer 12V rooftop AC; fits MaxxFan cutout",
        dims=(28, 22.5, 6.9), weightLb=44, price=(2400, 2700),
        electrical=E("load", "12V", contAmps=35, peakAmps=65, dailyAh=200, awg="4 AWG", fuse=80, fuseType="MEGA"),
        mounting="Fits 14×14 cutout; ~35A eco to ~65A max; 9,500-12,150 BTU."),

      D("webasto-2000stc", "Webasto", "Air Top 2000 STC", "Heater", "hvac", "2kW diesel air heater",
        [S("manual", "Webasto installation manual", "https://www.webasto.com")],
        82, "One of the two dominant diesel heaters",
        dims=(12.2, 4.7, 4.6), weightLb=5.7, price=(1100, 1400),
        electrical=E("load", "12V", contAmps=3, peakAmps=10, surgeWatts=110, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Underfloor or interior w/ ducting; exhaust fully outside (CO)."),

      # ---------------- WINDOWS ----------------
      D("amauto-slider", "AM Auto", "T4 Sliding Window", "Window", "material", "Bonded sliding window (Sprinter/Transit)",
        [S("supplier", "AM Auto", "https://www.amauto.us")],
        70, "Common bonded van window supplier",
        price=(300, 450), compat="Model varies by van + side; confirm fitment."),

      D("vanglass-bunk", "VanGlassUSA", "Bunk Window", "Window", "material", "Bonded fixed bunk window",
        [S("supplier", "VanGlassUSA", "https://vanglassusa.com")],
        66, "Popular fixed/bunk windows",
        price=(200, 350), compat="Fitment by van model + opening."),

      # ---------------- ROOF RACKS ----------------
      D("frontrunner-slimline", "Front Runner", "Slimline II", "Roof Rack", "roof", "Modular roof rack platform",
        [S("datasheet", "Front Runner spec", "https://www.frontrunneroutfitters.com"),
         S("community", "Overland staple (popularity)", "https://www.reddit.com")],
        80, "Overland roof-rack staple",
        weightLb=None, price=(900, 1500), compat="Kit sized per van + roof length."),

      D("aluminess-rack", "Aluminess", "Roof Rack", "Roof Rack", "roof", "Welded aluminum roof rack",
        [S("supplier", "Aluminess", "https://www.aluminess.com")],
        72, "Premium welded van rack",
        price=(1500, 2500), compat="Van-specific; confirm model."),

      # ---------------- INSULATION ----------------
      D("havelock-wool", "Havelock Wool", "Batt/Loose", "Insulation", "material", "Sheep-wool insulation",
        [S("supplier", "Havelock Wool", "https://havelockwool.com"),
         S("community", "Builder favorite (popularity)", "https://www.reddit.com")],
        82, "Most-cited natural van insulation",
        price=(None, None), compat="Sold by area; combine batt + loose fill."),

      D("thinsulate-sm600l", "3M", "Thinsulate SM600L", "Insulation", "material", "Synthetic insulation roll",
        [S("datasheet", "3M Thinsulate SM600L", "https://www.3m.com"),
         S("community", "Builder favorite (popularity)", "https://faroutride.com")],
        80, "Hydrophobic synthetic, very popular",
        price=(None, None), compat="Spray-adhesive to walls/ceiling; sold per yard."),

      # ---------------- PLYWOOD / EXTRUSION / HARDWARE / FITTINGS ----------------
      D("baltic-birch-half", "Generic", "Baltic Birch 1/2\" 5×5", "Plywood", "material", "Cabinet-grade plywood sheet",
        [S("supplier", "Lumber supplier", "https://www.homedepot.com")],
        72, "Standard cabinetry plywood",
        dims=(60, 60, 0.5), weightLb=36, price=(60, 90), compat="½\" ≈ 1.45 lb/sqft."),

      D("8020-1010", "80/20", "1010 (1\" T-slot)", "Aluminum Extrusion", "material", "10-series 1\"×1\" T-slot extrusion",
        [S("datasheet", "80/20 1010 spec", "https://8020.net")],
        76, "Common 10-series framing for van interiors",
        weightLb=None, price=(None, None), compat="~0.30 lb/ft; pair with t-nuts + corner brackets."),

      D("lagun-mount", "Lagun", "Table Leg Mount", "Cabinet Hardware", "cabinetry", "Swiveling table-leg mount",
        [S("supplier", "Lagun / supplier", "https://www.lagunsupply.com"),
         S("community", "Van table standard (popularity)", "https://www.reddit.com")],
        78, "The default van table mount",
        weightLb=None, price=(150, 200)),

      D("johnguest-fittings", "John Guest", "Speedfit 1/2\"", "Plumbing Fitting", "plumbing", "Push-to-connect water fittings",
        [S("datasheet", "John Guest Speedfit", "https://www.johnguest.com")],
        74, "Standard push-fit plumbing fittings",
        price=(2, 6), plumbing=P("fresh", conn=0.5), compat="½\" PEX/tube push-fit; no-tool joints."),
      D("espar-s3-d2l", "Espar", "Airtronic S3 D2L", "Heater", "hvac", "2.2kW diesel air heater (altitude-comp)",
        [S("datasheet", "Espar Airtronic S3 datasheet", "https://www.espar.com"),
         S("community", "Top-rated diesel heater 2026 (popularity)", "https://www.thewaywardhome.com")],
        84, "Premium diesel heater; automatic altitude adjustment",
        weightLb=None, price=(1300, 1500),
        electrical=E("load", "12V", contAmps=3, peakAmps=10, surgeWatts=110, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Underfloor/interior + ducting; exhaust fully outside (CO).", is_new=True, release_year=2023),

      D("vevor-d1", "VEVOR", "XMZ-F-D1", "Heater", "hvac", "2kW budget diesel air heater",
        [S("retailer", "Amazon listing", "https://www.amazon.com"),
         S("community", "Budget diesel heater favorite (popularity)", "https://everywherewithclaire.com")],
        70, "Budget Chinese diesel heater; huge install base",
        price=(120, 180),
        electrical=E("load", "12V", contAmps=3, peakAmps=10, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="2kW is right-sized for a van; louder fuel pump than premium units."),

      D("precisiontemp-550nsp", "PrecisionTemp", "550NSP-EC", "Water Heater", "plumbing", "Floor-vented tankless propane water heater",
        [S("datasheet", "PrecisionTemp 550NSP-EC", "https://precisiontemp.com")],
        78, "Most-cited van tankless water heater",
        dims=(13.5, 13.5, 14.25), weightLb=26.5, price=(1200, 1500),
        plumbing=P("hot_water", conn=0.5, powered=True),
        electrical=E("load", "12V", contAmps=3, awg="14 AWG", fuse=7.5, fuseType="blade"),
        mounting="Vents through floor (2 inch exhaust); 55,000 BTU max; propane."),

      D("camplux-rs264", "Camplux", "RS264", "Water Heater", "plumbing", "Tankless propane water heater 2.64 GPM",
        [S("retailer", "Retailer listing", "https://www.amazon.com")],
        64, "Budget tankless option",
        dims=(15.1, 12.8, 12.6), weightLb=35, price=550,
        plumbing=P("hot_water", flowGpm=2.64, conn=0.5, powered=True),
        electrical=E("load", "12V", contAmps=2, awg="14 AWG", fuse=5, fuseType="blade"),
        mounting="65,000 BTU; propane; confirm venting + clearances."),

      D("autoterm-2d", "Autoterm", "Air 2D", "Heater", "hvac", "2kW diesel air heater (Planar)",
        [S("supplier", "Autoterm/Planar supplier", "https://www.tprc.us"),
         S("community", "Overlander favorite (popularity)", "https://www.thevanconversion.com")],
        76, "Robust mid-tier diesel heater, 2-yr warranty",
        weightLb=None, price=(450, 600),
        electrical=E("load", "12V", contAmps=3, peakAmps=10, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="122R/10R certified; popular Webasto/Espar alternative."),
      D("webasto-pro25", "Webasto", "Air Top Pro 25", "Heater", "hvac", "0.7-2.5kW diesel air heater",
        [S("supplier", "Webasto site (spec via overview; verify)", "https://www.webasto.com")],
        74, "Whisper-quiet; altitude-ready to ~5,500 m",
        weightLb=None, price=None,
        electrical=E("load", "12V", contAmps=3, peakAmps=10, surgeWatts=110, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Underfloor/interior + ducting; exhaust fully outside (CO).", is_new=True, release_year=2023),

      D("webasto-evo40", "Webasto", "Air Top Evo 40", "Heater", "hvac", "1.5-4.0kW diesel/gas air heater",
        [S("supplier", "Webasto site (spec via overview; verify)", "https://www.webasto.com")],
        76, "Altitude-compensating; mid-output",
        dims=(16.7, 5.8, 6.4), weightLb=13, price=None,
        electrical=E("load", "12V", contAmps=4, peakAmps=12, surgeWatts=110, awg="14 AWG", fuse=20, fuseType="blade"),
        mounting="approx 5,100-13,650 BTU; ducted; exhaust outside."),

      D("webasto-evo55", "Webasto", "Air Top Evo 55", "Heater", "hvac", "1.5-5.5kW diesel/gas air heater",
        [S("supplier", "Webasto site (spec via overview; verify)", "https://www.webasto.com")],
        72, "Higher output for larger vans",
        dims=(16.7, 5.8, 6.4), weightLb=13, price=None,
        electrical=E("load", "12V", contAmps=5, peakAmps=14, surgeWatts=110, awg="14 AWG", fuse=20, fuseType="blade"),
        mounting="approx 5,100-18,800 BTU; same body as Evo 40."),

      D("rixen-s3-hydronic", "Rixen", "S-3 Hydronic (MCS-7)", "Hydronic Heater", "hvac", "Diesel hydronic furnace (heat + hot water)",
        [S("supplier", "Rixen site (spec via overview; verify)", "https://www.rixens.com")],
        68, "Premium integrated heat + hot water (glycol loop)",
        dims=(8.5, 3.5, 5.6), weightLb=4.4, price=None,
        electrical=E("load", "12V", contAmps=4, peakAmps=10, awg="14 AWG", fuse=15, fuseType="blade"),
        plumbing=P("hot_water", powered=True),
        mounting="Furnace dims/weight only; full glycol system (pump/tank/handlers) adds 40+ lb. Exhaust outside.",
        compat="approx 8,200-17,100 BTU; multi-zone; electric backup option."),

      D("rixen-mcs-one", "Rixen", "MCS One", "Hydronic Heater", "hvac", "All-in-one hydronic furnace + hot water",
        [S("supplier", "Rixen site (spec via overview; verify)", "https://www.rixens.com")],
        66, "Newer integrated all-in-one unit",
        dims=(18, 15.25, None), weightLb=45, price=None,
        electrical=E("load", "12V", contAmps=4, peakAmps=10, awg="14 AWG", fuse=15, fuseType="blade"),
        plumbing=P("hot_water", powered=True),
        mounting="approx 45 lb total; integrated furnace + hot water.", is_new=True, release_year=2024),

      D("propex-hs2000", "Propex", "HS2000", "Heater", "hvac", "LPG forced-air heater (~6,500 BTU)",
        [S("supplier", "Propex site (spec via overview; verify)", "https://propexheating.com")],
        70, "Simple LPG install if you already carry propane",
        dims=(15.5, 6.8, 4), weightLb=6, price=None,
        electrical=E("load", "12V", contAmps=3, peakAmps=6, awg="14 AWG", fuse=10, fuseType="blade"),
        mounting="Runs on propane (no diesel); small 12V fan draw; quiet."),

      D("propex-hs2800", "Propex", "HS2800", "Heater", "hvac", "2.8kW LPG forced-air heater",
        [S("supplier", "Propex site (spec via overview; verify)", "https://propexheating.com")],
        66, "Higher-output LPG option",
        dims=(17, 7.5, 5.7), weightLb=17, price=None,
        electrical=E("load", "12V", contAmps=3, peakAmps=6, awg="14 AWG", fuse=10, fuseType="blade"),
        mounting="Propane-fired; larger body than HS2000."),

      D("truma-combi-4e", "Truma", "Combi 4E", "Combi Heater", "hvac", "Gas/electric heat + hot water (2-6kW)",
        [S("supplier", "Truma site (spec via overview; verify)", "https://www.truma.com")],
        68, "Integrated heat + water; popular in Europe",
        dims=(20.6, 18.3, 11.8), weightLb=35, price=None,
        electrical=E("load", "12V", contAmps=4, peakAmps=8, awg="14 AWG", fuse=10, fuseType="blade"),
        plumbing=P("hot_water", tankGal=2.6, powered=True),
        mounting="approx 35 lb empty; gas + optional 120V electric element; ~10 L boiler."),
      D("nomadic-x3", "Nomadic Cooling", "X3 (Helix)", "Air Conditioner", "hvac", "12V/48V rooftop DC AC (max output)",
        [S("supplier", "Nomadic Cooling site (spec via overview; verify)", "https://nomadiccooling.com")],
        74, "Most powerful in the lineup; quiet",
        dims=(31.5, 30.9, 7.36), weightLb=57.3, price=None,
        electrical=E("load", "12V", contAmps=50, peakAmps=110, dailyAh=260, awg="2/0 AWG", fuse=150, fuseType="MEGA"),
        mounting="14x14 cutout; 11,830-15,120 BTU; up to ~110A at 12V max (far lower on 48V).", is_new=True, release_year=2024),

      D("velit-2000r-mini", "Velit", "2000R Mini", "Air Conditioner", "hvac", "12V rooftop DC AC (compact)",
        [S("supplier", "Velit site (spec via overview; verify)", "https://velitcamping.com")],
        70, "Lower-draw compact Velit",
        weightLb=None, price=None,
        electrical=E("load", "12V", contAmps=20, peakAmps=50, awg="6 AWG", fuse=60, fuseType="MEGA"),
        mounting="~6,500-7,500 BTU; ~20A min; low-profile.", is_new=True, release_year=2024),

      D("indelb-plein-aircon", "Indel B", "Plein-Aircon OFF", "Air Conditioner", "hvac", "12V rooftop DC AC (compact)",
        [S("supplier", "Indel B site (spec via overview; verify)", "https://www.indelb.com")],
        64, "Compact, strong dehumidify; smaller vans",
        dims=(31.5, 26.4, 9.7), weightLb=55.8, price=None,
        electrical=E("load", "12V", contAmps=16, peakAmps=42, awg="4 AWG", fuse=60, fuseType="MEGA"),
        mounting="Cutout 15.75x15.75 (400x400mm); ~4,100 BTU (1,200W); 16-42A."),

      D("houghton-belaire-135", "Houghton / RecPro", "Belaire 13.5K Low-Profile", "Air Conditioner", "hvac", "Low-profile rooftop AC + heat pump",
        [S("supplier", "RecPro/Houghton site (spec via overview; verify)", "https://www.recpro.com")],
        72, "Popular low-profile AC + heat pump",
        dims=(None, None, 7), weightLb=75, price=None,
        electrical=E("load", "120V", contAmps=None, runWatts=1550, awg="12 AWG"),
        mounting="13,500 BTU; standard RV cutout; 120V (~1,550W) or 48V DC version; heat pump."),

      D("houghton-95", "Houghton / RecPro", "9.5K Low-Profile", "Air Conditioner", "hvac", "Low-profile rooftop AC",
        [S("supplier", "RecPro/Houghton site (spec via overview; verify)", "https://www.recpro.com")],
        66, "Smaller-footprint low-profile option",
        dims=(None, None, 7), weightLb=65, price=None,
        electrical=E("load", "120V", contAmps=None, runWatts=1100, awg="14 AWG"),
        mounting="9,500 BTU; standard RV cutout; 120V or 48V DC version."),

      D("zerobreeze-mark3", "Zero Breeze", "Mark 3", "Air Conditioner", "hvac", "Portable battery air conditioner",
        [S("supplier", "Zero Breeze site (spec via overview; verify)", "https://www.zerobreeze.com")],
        66, "Highly portable spot cooling (no roof install)",
        weightLb=35, price=None,
        electrical=E("load", "12V", contAmps=20, peakAmps=40, awg="10 AWG", fuse=30, fuseType="blade"),
        mounting="Portable - no roof cutout; ~2,300+ BTU; battery or 12V; spot cooling only.", is_new=True, release_year=2024),

      D("ecoflow-wave2", "EcoFlow", "Wave 2", "Air Conditioner", "hvac", "Portable AC / heat (~5,000 BTU)",
        [S("supplier", "EcoFlow site (spec via overview; verify)", "https://www.ecoflow.com")],
        68, "Flexible portable; battery / AC / DC",
        weightLb=40, price=None,
        electrical=E("load", "12V", contAmps=30, peakAmps=60, awg="8 AWG", fuse=60, fuseType="MEGA"),
        mounting="Portable; ~5,000 BTU modes; runs on battery/AC/DC; add-on battery."),
      D("dometic-cfx3-45", "Dometic", "CFX3 45", "Refrigerator", "appliance", "Portable 12V chest fridge (45-58 Qt)",
        [S("supplier", "Dometic site (spec via overview; verify)", "https://www.dometic.com")],
        88, "Premium all-around van fridge; app control",
        dims=(28, 19, 18), weightLb=43, price=(800, 1000),
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=35, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Portable chest; dual-zone fridge/freezer option; Secop compressor."),

      D("dometic-crx-50", "Dometic", "CRX 50", "Refrigerator", "appliance", "Built-in upright 12V fridge (~50L)",
        [S("supplier", "Dometic site (spec via overview; verify)", "https://www.dometic.com")],
        80, "Reliable built-in front-load for cabinet installs",
        weightLb=60, price=(900, 1200),
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=30, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Built-in front-load; cabinet install; dims vary by model."),

      D("isotherm-85", "Isotherm", "Cruise 85", "Refrigerator", "appliance", "Built-in 12V fridge (85L)",
        [S("supplier", "Isotherm site (spec via overview; verify)", "https://www.indelb.com")],
        78, "Efficient, lightweight; good for solos/short trips",
        dims=(19.9, 18.5, 20.8), weightLb=53, price=None,
        electrical=E("load", "12V", contAmps=4, peakAmps=6, dailyAh=19, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="~0.7-0.9 Ah/hr; small freezer; built-in."),

      D("isotherm-130", "Isotherm", "Cruise 130", "Refrigerator", "appliance", "Built-in 12V fridge (130L)",
        [S("supplier", "Isotherm site (spec via overview; verify)", "https://www.indelb.com")],
        78, "Balanced size for couples",
        dims=(21.6, 20.1, 30.3), weightLb=57, price=None,
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=29, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="~1.0-1.4 Ah/hr; built-in upright."),

      D("isotherm-200", "Isotherm", "Cruise 200", "Refrigerator", "appliance", "Built-in 12V fridge (200L)",
        [S("supplier", "Isotherm site (spec via overview; verify)", "https://www.indelb.com")],
        72, "Full-time / family capacity",
        dims=(21.4, 20.4, 50.3), weightLb=90, price=None,
        electrical=E("load", "12V", contAmps=6, peakAmps=9, dailyAh=43, awg="12 AWG", fuse=20, fuseType="blade"),
        mounting="~1.6-2.0 Ah/hr; larger freezer; heavy - check support."),

      D("arb-50qt", "ARB", "Classic 50Qt (47L)", "Refrigerator", "appliance", "Portable 12V chest fridge (~50 Qt)",
        [S("supplier", "ARB site (spec via overview; verify)", "https://www.arbusa.com")],
        76, "Rugged overlanding chest fridge",
        dims=(29.5, 22, 19), weightLb=52, price=(900, 1100),
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=35, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Rugged portable chest; reliable compressor."),

      D("vitrifrigo-c51i", "Vitrifrigo", "C51i", "Refrigerator", "appliance", "Built-in 12V fridge (~50L)",
        [S("supplier", "Vitrifrigo site (spec via overview; verify)", "https://www.vitrifrigo.com")],
        70, "Marine-grade durability; Secop/Danfoss compressor",
        weightLb=60, price=None,
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=30, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Built-in upright; dims vary by model."),

      D("novakool-r5810", "NovaKool", "R5810", "Refrigerator", "appliance", "Built-in 12V fridge (~5.8 cu ft)",
        [S("supplier", "NovaKool site (spec via overview; verify)", "https://www.novakool.com")],
        68, "Quiet built-in for full-time use",
        weightLb=65, price=None,
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=35, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Cabinet install; includes small freezer."),

      D("bougerv-30qt", "BougeRV", "30 Qt", "Refrigerator", "appliance", "Budget portable 12V fridge (30 Qt)",
        [S("retailer", "Retailer listing (spec via overview; verify)", "https://www.bougerv.com")],
        66, "Budget portable; shorter lifespan",
        dims=(22.7, 12.6, 15.6), weightLb=23, price=(250, 380),
        electrical=E("load", "12V", contAmps=4, peakAmps=6, dailyAh=25, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Affordable portable; single-zone."),

      D("alpicool-c55", "Alpicool", "C55 (55 Qt)", "Refrigerator", "appliance", "Budget portable 12V fridge (55 Qt)",
        [S("retailer", "Retailer listing (spec via overview; verify)", "https://www.alpicool.com"),
         S("community", "Popular budget pick (popularity)", "https://www.reddit.com")],
        68, "Budget large-capacity portable",
        dims=(27, 16, 20), weightLb=40, price=(300, 450),
        electrical=E("load", "12V", contAmps=5, peakAmps=7, dailyAh=38, awg="14 AWG", fuse=15, fuseType="blade"),
        mounting="Affordable; check long-term reliability."),
      D("renogy-200ah", "Renogy", "12V 200Ah Core", "Battery", "electrical", "LiFePO4 200Ah",
        [S("supplier", "Renogy site (spec via overview; verify)", "https://www.renogy.com")],
        72, "Affordable 200Ah with low-temp protection",
        dims=(20.6, 9.5, 8.6), weightLb=50, price=(600, 900),
        electrical=E("source", "12V", contAmps=100, peakAmps=200, awg="2 AWG", fuse=125, fuseType="Class-T", comms="BT", terminals="M8 ring"),
        mounting="Strap down; Bluetooth option; low-temp cutoff."),

      D("battleborn-270", "Battle Born", "BB270", "Battery", "electrical", "LiFePO4 270Ah",
        [S("supplier", "Battle Born site (spec via overview; verify)", "https://battlebornbatteries.com")],
        76, "Large single-battery house bank",
        weightLb=77, price=(2000, 2500),
        electrical=E("source", "12V", contAmps=200, peakAmps=400, awg="2/0 AWG", fuse=250, fuseType="Class-T", comms="none", terminals="M8 ring"),
        mounting="Heavy (~73-81 lb) - confirm floor support."),

      D("victron-multiplus-ii-3000", "Victron", "MultiPlus-II 12/3000/120", "Inverter/Charger", "electrical", "3000VA inverter/charger",
        [S("datasheet", "Victron MultiPlus-II", "https://www.victronenergy.com"),
         S("supplier", "spec via overview; verify", "https://www.victronenergy.com")],
        84, "Common flagship inverter/charger",
        dims=(22.8, 10.9, 5.8), weightLb=45, price=(1100, 1400),
        electrical=E("converter", "12V", contAmps=250, peakAmps=400, surgeWatts=6000, awg="4/0 AWG", fuse=400, fuseType="Class-T", inverterW=3000, comms="VE.Bus", terminals="M8 ring"),
        mounting="3000VA continuous, 120A charger, pure sine; large cable + Class-T."),

      D("redarc-bcdc", "REDARC", "BCDC1240", "DC-DC Charger", "electrical", "40A DC-DC charger (solar input)",
        [S("supplier", "REDARC site (spec via overview; verify)", "https://www.redarc.com.au")],
        72, "Rugged dual-input DC-DC (alternator + solar)",
        dims=(6.5, 4.7, 1.5), weightLb=2.2, price=(300, 400),
        electrical=E("converter", "12V", contAmps=40, awg="8 AWG", fuse=50, fuseType="MEGA", terminals="screw"),
        mounting="Alternator + solar input; common in overland builds."),

      D("renogy-dcdc-mppt", "Renogy", "DCC50S", "DC-DC Charger", "electrical", "50A DC-DC charger w/ MPPT",
        [S("supplier", "Renogy site (spec via overview; verify)", "https://www.renogy.com")],
        74, "Value DC-DC with built-in solar MPPT",
        dims=(9.6, 5.7, 3), weightLb=3.1, price=(250, 350),
        electrical=E("converter", "12V", contAmps=50, awg="6 AWG", fuse=60, fuseType="MEGA", comms="BT", terminals="screw"),
        mounting="Combined alternator + solar input; one box."),

      D("victron-cerbo-gx", "Victron", "Cerbo GX MK2", "Monitor", "electrical", "System monitoring hub",
        [S("datasheet", "Victron Cerbo GX", "https://www.victronenergy.com")],
        78, "Central monitoring/control hub for Victron systems",
        dims=(6.06, 3.07, 1.89), weightLb=1, price=(300, 400),
        electrical=E("monitor", "12V", contAmps=1, awg="18 AWG", fuse=3, fuseType="blade", comms="VE.Can/WiFi", terminals="screw"),
        mounting="Pairs with GX Touch display; ties batteries/MPPT/inverter together."),
    ]


# ===========================================================================
# STAGE 2 — SPEC EXTRACTION (here: specs are pre-attached from datasheet/supplier;
# in production this parses the datasheet/manual PDF). Community sources are
# stripped of any spec authority.
# ===========================================================================
def discover():
    """Stage 1. Return raw candidate components.

    Uses a live web source if one is configured (see discovery_sources.py),
    otherwise the seeded high-value list. The seed always works offline and
    needs no network; live search needs a search-API key and connectivity.
    """
    try:
        from discovery_sources import get_source
        return get_source(seed_candidates).fetch()
    except Exception:
        return seed_candidates()


def extract_specs(c):
    has_spec_source = any(s["kind"] in SPEC_SOURCES for s in c["sources"])
    if not has_spec_source:
        # only community/retailer — specs (if any slipped in) are NOT authoritative
        c["_spec_authority"] = "none"
    else:
        c["_spec_authority"] = "datasheet" if any(s["kind"] in ("datasheet", "manual") for s in c["sources"]) else "supplier"
    return c


# ===========================================================================
# STAGE 3 — SOURCE VERIFICATION (apply hierarchy → confidence)
# ===========================================================================
def verify_sources(c):
    kinds = {s["kind"] for s in c["sources"]}
    if kinds & {"datasheet", "manual"}:
        conf = "manufacturer"
    elif kinds & {"supplier"}:
        conf = "manufacturer" if c["_spec_authority"] == "datasheet" else "estimated"
    elif kinds & {"retailer"}:
        conf = "estimated"          # price/availability only
    else:
        conf = "unverified"         # community-only → popularity, no specs
    c["confidence"] = conf
    c["verified"] = False           # human verifies later
    c["bestSource"] = min(c["sources"], key=lambda s: SRC_RANK[s["kind"]]) if c["sources"] else None
    return c


# ===========================================================================
# STAGE 4 — NORMALIZE UNITS (mm→in, kg→lb, price→single usd estimate)
# ===========================================================================
MM_PER_IN = 25.4
KG_PER_LB = 0.453592

def normalize_units(c):
    if c.get("dims_mm") and any(v is not None for v in c["dims_mm"]):
        l, w, h = c["dims_mm"]
        conv = lambda v: round(v / MM_PER_IN, 1) if v is not None else None
        for axis, val in zip(("l", "w", "h"), (conv(l), conv(w), conv(h))):
            if c["dims"][axis] is None:
                c["dims"][axis] = val
    if c.get("weight_kg") is not None and c.get("weightLb") is None:
        c["weightLb"] = round(c["weight_kg"] / KG_PER_LB, 1)
    pr = c["priceRange"]
    if pr["low"] is not None and pr["high"] is not None:
        c["costUsd"] = round((pr["low"] + pr["high"]) / 2)
    elif pr["low"] is not None:
        c["costUsd"] = pr["low"]
    else:
        c["costUsd"] = None
    for k in ("dims_mm", "weight_kg", "_spec_authority"):
        c.pop(k, None)
    return c


# ===========================================================================
# MISSING-SPEC DETECTION (same fields the sourcing queue tracks)
# ===========================================================================
def detect_missing(c):
    miss = []
    d = c["dims"]
    if d["l"] is None or d["w"] is None or d["h"] is None:
        miss.append("dimensions")
    if c.get("weightLb") is None:
        miss.append("weight")
    if c.get("costUsd") is None:
        miss.append("cost")
    e = c.get("electrical")
    if e is not None:
        need = [f for f in ("voltage", "minWireAwg") if e.get(f) in (None, "")]
        if e.get("role") == "load":
            if e.get("contAmps") is None:
                need.append("contAmps")
            if e.get("recommendedFuseA") is None and e.get("voltage") not in ("120V", "240V"):
                need.append("fuse")
        if need:
            miss.append("electrical")
    p = c.get("plumbing")
    if p is not None and p.get("fluid") in (None, ""):
        miss.append("plumbing")
    if not (c.get("mounting") or "").strip():
        miss.append("mounting")
    if not any((s.get("url") or "").strip() for s in c["sources"]):
        miss.append("sources")
    return miss


# ===========================================================================
# STAGE 5 — MERGE PLAN vs parts-db.json (never overwrite verified; flag conflicts)
# ===========================================================================
def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

SPEC_KEYS = ["dims.l", "dims.w", "dims.h", "weightLb", "costUsd"]

def getp(d, path):
    cur = d
    for k in path.split("."):
        cur = (cur or {}).get(k)
    return cur

def plan_merge(c, db_index):
    key = (norm(c["brand"]), norm(c["model"]))
    existing = db_index.get(key)
    conflicts = []
    if existing is None:
        c["match"] = None
        c["action"] = "add"          # new component → add on approval
        return c
    c["match"] = existing["id"]
    ev = existing.get("verified", False)
    fills = []
    for path in SPEC_KEYS:
        old, new = getp(existing, path), getp(c, path)
        if new is None:
            continue
        if old is None:
            fills.append(path)        # existing missing → safe to fill
        elif old != new:
            # value disagreement
            if ev:
                conflicts.append({"field": path, "existing": old, "discovered": new, "note": "existing is verified — not overwritten"})
            else:
                conflicts.append({"field": path, "existing": old, "discovered": new, "note": "values differ — needs review"})
    c["conflicts"] = conflicts
    c["fills"] = fills
    c["action"] = "conflict" if conflicts else ("update" if fills else "noop")
    return c


# ===========================================================================
# STAGE 6 — APPLY APPROVED (human-gated write to parts-db.json)
# ===========================================================================
def apply_approved(approved_ids, dry_run=True):
    db = json.load(open("parts-db.json"))
    by_key = {(norm(c["brand"]), norm(c["model"])): c for c in db["components"]}
    cands = {c["id"]: c for c in run_pipeline()["candidates"]}
    added, updated, blocked = [], [], []
    for cid in approved_ids:
        c = cands.get(cid)
        if not c:
            continue
        if c["action"] == "conflict":
            blocked.append(cid)       # conflicts never auto-applied
            continue
        if c["action"] == "add":
            rec = {
                "id": "disc-" + cid, "name": f"{c['brand']} {c['model']}", "system": c["system"],
                "category": c["category"], "brand": c["brand"], "model": c["model"],
                "dims": c["dims"], "weightLb": c.get("weightLb"), "costUsd": c.get("costUsd"),
                "electrical": c.get("electrical"), "plumbing": c.get("plumbing"), "capacity": None,
                "mounting": {"surface": None, "fasteners": None, "clearanceIn": None, "orientation": None, "notes": c.get("mounting", "")},
                "sources": [{"label": s["label"], "url": s["url"]} for s in c["sources"]],
                "confidence": c["confidence"], "verified": False, "tags": [c["productType"]], "updatedAt": TODAY,
            }
            added.append(rec)
        elif c["action"] == "update":
            existing = by_key[(norm(c["brand"]), norm(c["model"]))]
            for path in c["fills"]:
                ks = path.split(".")
                tgt = existing
                for k in ks[:-1]:
                    tgt = tgt[k]
                tgt[ks[-1]] = getp(c, path)   # only fills previously-null fields
            updated.append(existing["id"])
    if not dry_run:
        db["components"].extend(added)
        json.dump(db, open("parts-db.json", "w"), indent=2)
    return {"added": [a["id"] for a in added], "updated": updated, "blocked_conflicts": blocked, "dry_run": dry_run}


# ===========================================================================
# ORCHESTRATION
# ===========================================================================
def run_pipeline():
    db = json.load(open("parts-db.json"))
    db_index = {(norm(c["brand"]), norm(c["model"])): c for c in db["components"]}
    cands = []
    for c in discover():
        c = extract_specs(c)
        c = verify_sources(c)
        c = normalize_units(c)
        c["missing"] = detect_missing(c)
        c = plan_merge(c, db_index)
        c["status"] = "conflict" if c["action"] == "conflict" else "pending"
        cands.append(c)
    counts = {}
    for c in cands:
        counts[c["action"]] = counts.get(c["action"], 0) + 1
    new_count = sum(1 for c in cands if c["newness"]["isNew"])
    return {
        "generated": TODAY,
        "pipeline": ["Discovery", "Candidate List", "Spec Extraction", "Source Verification",
                     "Normalize Units", "Merge Plan", "Add/Update parts-db.json", "Missing-Spec Tasks"],
        "rules": {
            "spec_authority": "datasheet/manual > supplier; retailer = price/availability; community = popularity only",
            "no_overwrite_verified": True,
            "conflicts": "flagged for review, never auto-applied",
            "single_source_of_truth": "parts-db.json",
        },
        "summary": {"candidates": len(cands), "by_action": counts, "new_releases": new_count,
                    "conflicts": sum(1 for c in cands if c["action"] == "conflict")},
        "candidates": cands,
    }


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--apply":
        approvals = json.load(open((_ORIG_CWD / sys.argv[2]) if not os.path.isabs(sys.argv[2]) else sys.argv[2]))
        res = apply_approved(approvals.get("approved", []), dry_run=approvals.get("dry_run", True))
        print("apply:", json.dumps(res, indent=2))
        return
    out = run_pipeline()
    json.dump(out, open("discovery-queue.json", "w"), indent=2)
    s = out["summary"]
    print(f"Wrote discovery-queue.json — {s['candidates']} candidates")
    print(f"  actions: {s['by_action']}")
    print(f"  new releases flagged: {s['new_releases']} | conflicts: {s['conflicts']}")


if __name__ == "__main__":
    main()
