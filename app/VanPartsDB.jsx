import React, { useMemo, useRef, useState } from "react";
import {
  Zap, Droplets, Wind, Package, Boxes, Refrigerator, Cog, Layers,
  Search, Download, Upload, X, AlertTriangle, CheckCircle2, ShieldQuestion,
  ExternalLink, Filter, FileJson, FileSpreadsheet, Gauge, Ruler, Scale,
  DollarSign, Tag, Info, ChevronRight,
} from "lucide-react";

/* ============================================================================
   VAN PARTS DB  —  component database for DIY van / RV builds
   Single-file demo. All state lives in React (no storage). The data model is
   designed so an AI agent can later fill rows straight from manufacturer
   datasheets: every spec can be null, every part carries source URLs + a
   confidence level, and a warning system flags anything missing or unverified.
   ========================================================================== */

/* ---- system + confidence vocabularies ----------------------------------- */
const SYSTEMS = [
  "electrical", "plumbing", "hvac", "tank", "appliance", "roof", "cabinetry", "material",
];

const SYSTEM_META = {
  electrical: { label: "Electrical", icon: Zap,          badge: "bg-amber-500/10 text-amber-300 border-amber-500/30",   dot: "bg-amber-400" },
  plumbing:   { label: "Plumbing",   icon: Droplets,     badge: "bg-cyan-500/10 text-cyan-300 border-cyan-500/30",      dot: "bg-cyan-400" },
  hvac:       { label: "HVAC",       icon: Wind,         badge: "bg-violet-500/10 text-violet-300 border-violet-500/30", dot: "bg-violet-400" },
  tank:       { label: "Tanks",      icon: Droplets,     badge: "bg-blue-500/10 text-blue-300 border-blue-500/30",      dot: "bg-blue-400" },
  appliance:  { label: "Appliances", icon: Refrigerator, badge: "bg-sky-500/10 text-sky-300 border-sky-500/30",         dot: "bg-sky-400" },
  roof:       { label: "Roof",       icon: Cog,          badge: "bg-teal-500/10 text-teal-300 border-teal-500/30",      dot: "bg-teal-400" },
  cabinetry:  { label: "Cabinetry",  icon: Layers,       badge: "bg-orange-500/10 text-orange-300 border-orange-500/30", dot: "bg-orange-400" },
  material:   { label: "Materials",  icon: Boxes,        badge: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30", dot: "bg-emerald-400" },
};

const VOLTAGES = ["12V", "24V", "48V", "120V", "240V", "N/A"];

const CONFIDENCE_META = {
  verified:     { label: "Verified",      badge: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30", note: "Specs checked against the datasheet by a human." },
  manufacturer: { label: "Manufacturer",  badge: "bg-blue-500/10 text-blue-300 border-blue-500/30",          note: "Pulled from the maker's published figures." },
  estimated:    { label: "Estimated",     badge: "bg-amber-500/10 text-amber-300 border-amber-500/30",        note: "Approximate. Confirm before you cut or wire." },
  unverified:   { label: "Unverified",    badge: "bg-red-500/10 text-red-300 border-red-500/30",              note: "Unconfirmed source. Treat as a placeholder." },
};

/* ---- seed database (30 parts) ------------------------------------------- */
/* Figures are realistic but approximate. Always confirm against the actual
   datasheet and your van's payload sticker before buying or building.        */
const SEED = [
  // ---------- ELECTRICAL ----------
  { id: "el-bb-100", name: "100Ah LiFePO4 Battery", system: "electrical", category: "Battery", brand: "Battle Born", model: "BB10012",
    dims: { l: 12.75, w: 6.875, h: 9 }, weightLb: 31, costUsd: 875,
    power: { voltage: "12V", watts: null, amps: 100, surgeWatts: null, idleWatts: null },
    capacity: { value: 100, unit: "Ah", kind: "Battery capacity" },
    mountingNotes: "Mount on a flat floor, strapped down. Group 27 footprint. Vents not required (LiFePO4).",
    sources: [{ label: "Battle Born spec page", url: "https://battlebornbatteries.com" }],
    confidence: "manufacturer", verified: true, tags: ["lithium", "house bank"], updatedAt: "2026-05-02" },

  { id: "el-mp-2000", name: "MultiPlus 12/2000/80 Inverter/Charger", system: "electrical", category: "Inverter/Charger", brand: "Victron", model: "PMP122200000",
    dims: { l: 14.6, w: 8.5, h: 6.1 }, weightLb: 23, costUsd: 760,
    power: { voltage: "12V", watts: 2000, amps: null, surgeWatts: 4000, idleWatts: 8 },
    capacity: { value: 2000, unit: "W", kind: "Continuous output" },
    mountingNotes: "Wall or floor mount near the battery to keep DC cable runs short. Leave clearance for the cooling fan.",
    sources: [{ label: "Victron datasheet", url: "https://www.victronenergy.com" }],
    confidence: "manufacturer", verified: true, tags: ["inverter", "shore charging"], updatedAt: "2026-05-02" },

  { id: "el-mppt-10050", name: "SmartSolar MPPT 100/50 Charge Controller", system: "electrical", category: "Charge Controller", brand: "Victron", model: "SCC110050210",
    dims: { l: 8.3, w: 5.9, h: 4.7 }, weightLb: 6, costUsd: 290,
    power: { voltage: "12V", watts: 700, amps: 50, surgeWatts: null, idleWatts: null },
    capacity: { value: 700, unit: "W", kind: "Max solar (12V)" },
    mountingNotes: "Vertical mount with clearance above/below for airflow. Short, fused run from controller to battery.",
    sources: [{ label: "Victron MPPT page", url: "https://www.victronenergy.com" }],
    confidence: "manufacturer", verified: true, tags: ["solar", "mppt", "bluetooth"], updatedAt: "2026-05-02" },

  { id: "el-rng-200", name: "200W Monocrystalline Solar Panel", system: "electrical", category: "Solar Panel", brand: "Renogy", model: "RNG-200D",
    dims: { l: 58.7, w: 26.4, h: 1.4 }, weightLb: 26.5, costUsd: 230,
    power: { voltage: "N/A", watts: 200, amps: null, surgeWatts: null, idleWatts: null },
    capacity: { value: 200, unit: "W", kind: "Rated output" },
    mountingNotes: "Roof-mount on Z-brackets or rail feet. Bed corner brackets in lap sealant; keep one cable gland for the run inside.",
    sources: [{ label: "Renogy product page", url: "https://www.renogy.com" }],
    confidence: "manufacturer", verified: false, tags: ["solar", "roof-mount"], updatedAt: "2026-04-18" },

  { id: "el-orion-30", name: "Orion-Tr Smart 12/12-30 DC-DC Charger", system: "electrical", category: "DC-DC Charger", brand: "Victron", model: "ORI121236120",
    dims: { l: 8.6, w: 4.6, h: 2.8 }, weightLb: 3.3, costUsd: 215,
    power: { voltage: "12V", watts: null, amps: 30, surgeWatts: null, idleWatts: null },
    capacity: { value: 30, unit: "Ah", kind: "Charge current" },
    mountingNotes: "Mount between starter and house battery to charge from the alternator while driving. Fuse both ends.",
    sources: [{ label: "Victron Orion-Tr", url: "https://www.victronenergy.com" }],
    confidence: "manufacturer", verified: true, tags: ["alternator charging", "b2b"], updatedAt: "2026-05-02" },

  { id: "el-bs-5026", name: "ST Blade Fuse Block (12 circuit)", system: "electrical", category: "Fuse Block", brand: "Blue Sea Systems", model: "5026",
    dims: { l: 7.1, w: 3.4, h: 1.4 }, weightLb: 0.7, costUsd: 55,
    power: { voltage: "12V", watts: null, amps: 100, surgeWatts: null, idleWatts: null },
    capacity: { value: 12, unit: "", kind: "Circuits" },
    mountingNotes: "Mount in an accessible spot with the cover on. Common negative bus included. Label every circuit.",
    sources: [{ label: "Blue Sea 5026", url: "https://www.bluesea.com" }],
    confidence: "verified", verified: true, tags: ["distribution", "fuses"], updatedAt: "2026-05-10" },

  { id: "el-aims-3000", name: "3000W Pure Sine Inverter", system: "electrical", category: "Inverter", brand: "AIMS Power", model: "PWRIX300012S",
    dims: { l: null, w: null, h: null }, weightLb: null, costUsd: 420,
    power: { voltage: "12V", watts: 3000, amps: null, surgeWatts: 6000, idleWatts: null },
    capacity: { value: 3000, unit: "W", kind: "Continuous output" },
    mountingNotes: "Needs very heavy DC cable (4/0) and a class-T fuse at the battery. Confirm exact dims/weight before buying.",
    sources: [],
    confidence: "unverified", verified: false, tags: ["inverter", "high-draw"], updatedAt: "2026-03-30" },

  { id: "el-lynx", name: "Lynx Distributor Busbar", system: "electrical", category: "Busbar", brand: "Victron", model: "LYN060102000",
    dims: { l: 8.5, w: 7.4, h: 3.5 }, weightLb: 3.5, costUsd: 190,
    power: { voltage: "12V", watts: null, amps: 1000, surgeWatts: null, idleWatts: null },
    capacity: { value: 1000, unit: "", kind: "Bus rating (A)" },
    mountingNotes: "Central positive/negative distribution with built-in fuse holders. Pairs with MultiPlus + MPPT.",
    sources: [{ label: "Victron Lynx", url: "https://www.victronenergy.com" }],
    confidence: "estimated", verified: false, tags: ["distribution", "busbar"], updatedAt: "2026-04-01" },

  // ---------- PLUMBING ----------
  { id: "pl-shurflo", name: "Revolution 4008 Water Pump", system: "plumbing", category: "Water Pump", brand: "SHURFLO", model: "4008-101-E65",
    dims: { l: 9.3, w: 5.0, h: 4.5 }, weightLb: 4.5, costUsd: 95,
    power: { voltage: "12V", watts: 90, amps: 7, surgeWatts: null, idleWatts: 0 },
    capacity: { value: 3, unit: "", kind: "Flow (GPM)" },
    mountingNotes: "Soft-mount on rubber feet to cut noise. Add an accumulator to stop cycling. Inline strainer on the inlet.",
    sources: [{ label: "SHURFLO 4008", url: "https://www.shurflo.com" }],
    confidence: "manufacturer", verified: true, tags: ["fresh water", "pump"], updatedAt: "2026-05-02" },

  { id: "pl-faucet", name: "Twist Combo Faucet", system: "plumbing", category: "Faucet", brand: "Whale", model: "RT2498",
    dims: { l: 4, w: 4, h: 11 }, weightLb: 1.2, costUsd: 75,
    power: null,
    capacity: null,
    mountingNotes: "Single-hole deck mount with a microswitch option to trigger the pump. Pull-out spray doubles as a shower.",
    sources: [{ label: "Whale faucets", url: "https://www.whalepumps.com" }],
    confidence: "estimated", verified: false, tags: ["fresh water", "galley"], updatedAt: "2026-04-12" },

  { id: "pl-shower", name: "Shower Pan 32 x 32", system: "plumbing", category: "Shower", brand: "Generic", model: "FRP-3232",
    dims: { l: 32, w: 32, h: 6 }, weightLb: 22, costUsd: 160,
    power: null,
    capacity: null,
    mountingNotes: "Wet-bay floor with a center or corner drain to the gray tank. Seal seams; slope toward the drain.",
    sources: [],
    confidence: "estimated", verified: false, tags: ["wet bath"], updatedAt: "2026-03-22" },

  { id: "pl-accum", name: "Accumulator Tank", system: "plumbing", category: "Accumulator", brand: "SEAFLO", model: "SFAT-125",
    dims: { l: 6.5, w: 6.5, h: 8 }, weightLb: 2, costUsd: 35,
    power: null,
    capacity: { value: 0.5, unit: "L", kind: "Air chamber" },
    mountingNotes: "Mount on the pressure side after the pump to smooth flow and stop rapid cycling. Pre-charge the air valve.",
    sources: [{ label: "SEAFLO accumulator", url: "https://www.seaflo.com" }],
    confidence: "unverified", verified: false, tags: ["fresh water"], updatedAt: "2026-02-28" },

  // ---------- TANKS ----------
  { id: "tk-fresh-21", name: "Fresh Water Tank 21 gal", system: "tank", category: "Fresh Tank", brand: "Generic", model: "FW-21",
    dims: { l: 30, w: 14, h: 12 }, weightLb: 18, costUsd: 150,
    power: null,
    capacity: { value: 21, unit: "gal", kind: "Potable water" },
    mountingNotes: "Strap low and central for balance — water is ~8.34 lb/gal (≈175 lb full). Fill port + vent + pickup.",
    sources: [],
    confidence: "estimated", verified: false, tags: ["fresh water"], updatedAt: "2026-03-15" },

  { id: "tk-gray-15", name: "Gray Water Tank 15 gal", system: "tank", category: "Gray Tank", brand: "Generic", model: "GW-15",
    dims: { l: 28, w: 12, h: 10 }, weightLb: 14, costUsd: 130,
    power: null,
    capacity: { value: 15, unit: "gal", kind: "Waste water" },
    mountingNotes: "Underslung or in a bay below the shower drain. Gravity-feed with a dump valve; vent to outside.",
    sources: [],
    confidence: "estimated", verified: false, tags: ["gray water"], updatedAt: "2026-03-15" },

  { id: "tk-lpg-11", name: "Propane Tank 11 lb (DOT)", system: "tank", category: "Propane", brand: "Worthington", model: "281149",
    dims: { l: 12.2, w: 12.2, h: 17.9 }, weightLb: 18.5, costUsd: 70,
    power: null,
    capacity: { value: 2.6, unit: "gal", kind: "Propane (≈11 lb)" },
    mountingNotes: "Upright, secured, in a vented/sealed locker that drains to outside. Regulator + leak detector required.",
    sources: [{ label: "Worthington cylinders", url: "https://www.worthingtonindustries.com" }],
    confidence: "manufacturer", verified: false, tags: ["propane", "fuel"], updatedAt: "2026-04-09" },

  { id: "tk-diesel-3", name: "Aux Diesel Tank 3 gal", system: "tank", category: "Diesel", brand: "Generic", model: "DSL-3",
    dims: { l: 14, w: 8, h: 8 }, weightLb: 5, costUsd: 60,
    power: null,
    capacity: { value: 3, unit: "gal", kind: "Heater fuel" },
    mountingNotes: "Feeds a diesel air heater. Mount the pickup standpipe; vent the tank. Keep fuel lines away from heat.",
    sources: [],
    confidence: "unverified", verified: false, tags: ["diesel", "heater fuel"], updatedAt: "2026-02-20" },

  // ---------- HVAC ----------
  { id: "hv-maxxfan", name: "MaxxFan Deluxe 7500K", system: "hvac", category: "Roof Fan", brand: "Maxxair", model: "00-07500K",
    dims: { l: 16, w: 16, h: 4.5 }, weightLb: 11, costUsd: 320,
    power: { voltage: "12V", watts: 60, amps: 5, surgeWatts: null, idleWatts: 0 },
    capacity: { value: 900, unit: "", kind: "Airflow (CFM)" },
    mountingNotes: "Standard 14x14 roof cutout. Rain shield lets it run in weather; remote + thermostat built in.",
    sources: [{ label: "Maxxair fans", url: "https://www.maxxair.com" }],
    confidence: "manufacturer", verified: true, tags: ["ventilation", "roof"], updatedAt: "2026-05-02" },

  { id: "hv-penguin", name: "Penguin II Rooftop AC 13500 BTU", system: "hvac", category: "Air Conditioner", brand: "Dometic", model: "640315CXX1J0",
    dims: { l: 29, w: 28, h: 9.8 }, weightLb: 77, costUsd: 1150,
    power: { voltage: "120V", watts: 1450, amps: 13, surgeWatts: 2900, idleWatts: null },
    capacity: { value: 13500, unit: "BTU", kind: "Cooling" },
    mountingNotes: "Heavy roof load — confirm payload and roof structure. Needs a large inverter or shore power to run.",
    sources: [{ label: "Dometic Penguin II", url: "https://www.dometic.com" }],
    confidence: "manufacturer", verified: false, tags: ["cooling", "roof", "high-draw"], updatedAt: "2026-04-25" },

  { id: "hv-espar", name: "Airtronic B4 Diesel Heater", system: "hvac", category: "Heater", brand: "Espar", model: "B4L",
    dims: { l: 12, w: 4.7, h: 5.1 }, weightLb: 6, costUsd: 1300,
    power: { voltage: "12V", watts: 30, amps: 2.5, surgeWatts: 110, idleWatts: null },
    capacity: { value: 13648, unit: "BTU", kind: "Heat output (≈4kW)" },
    mountingNotes: "Mount under floor or in a bay with intake/exhaust to outside. Draws from main or aux diesel tank.",
    sources: [{ label: "Espar heaters", url: "https://www.espar.com" }],
    confidence: "estimated", verified: false, tags: ["heat", "diesel"], updatedAt: "2026-04-03" },

  { id: "hv-propex", name: "HS2000 Propane Heater", system: "hvac", category: "Heater", brand: "Propex", model: "HS2000",
    dims: { l: 11, w: 6.7, h: 6.3 }, weightLb: 9, costUsd: 650,
    power: { voltage: "12V", watts: 18, amps: 1.5, surgeWatts: null, idleWatts: null },
    capacity: { value: 6824, unit: "BTU", kind: "Heat output (≈2kW)" },
    mountingNotes: "Sealed combustion — intake/exhaust to outside. Runs off the propane system; ducted warm air inside.",
    sources: [{ label: "Propex heaters", url: "https://www.propexheating.com" }],
    confidence: "manufacturer", verified: false, tags: ["heat", "propane"], updatedAt: "2026-04-03" },

  // ---------- ROOF ----------
  { id: "rf-rack", name: "Modular Roof Rack (per ft)", system: "roof", category: "Roof Rack", brand: "Generic", model: "RR-MOD",
    dims: { l: 12, w: 50, h: 4 }, weightLb: 9, costUsd: 110,
    power: null,
    capacity: { value: 300, unit: "", kind: "Static load (lb)" },
    mountingNotes: "Bolts to factory roof mounts or fender washers w/ backing plates + sealant. Spreads solar + deck loads.",
    sources: [],
    confidence: "estimated", verified: false, tags: ["roof", "structure"], updatedAt: "2026-03-08" },

  { id: "rf-gland", name: "Cable Entry Gland (triple)", system: "roof", category: "Cable Gland", brand: "Scanstrut", model: "DS-MULTI",
    dims: { l: 3.3, w: 3.3, h: 1.4 }, weightLb: 0.3, costUsd: 45,
    power: null,
    capacity: { value: 3, unit: "", kind: "Cable ports" },
    mountingNotes: "Weatherproof roof penetration for solar/antenna cables. Bed in lap sealant; route to the controller.",
    sources: [{ label: "Scanstrut glands", url: "https://www.scanstrut.com" }],
    confidence: "unverified", verified: false, tags: ["roof", "weatherproofing"], updatedAt: "2026-02-15" },

  // ---------- APPLIANCES ----------
  { id: "ap-cfx3-45", name: "CFX3 45 Fridge/Freezer", system: "appliance", category: "Refrigerator", brand: "Dometic", model: "CFX3 45",
    dims: { l: 28.1, w: 18.5, h: 16.1 }, weightLb: 41, costUsd: 900,
    power: { voltage: "12V", watts: 45, amps: 3.7, surgeWatts: null, idleWatts: null },
    capacity: { value: 1.6, unit: "cu_ft", kind: "Interior (46 L)" },
    mountingNotes: "Allow airflow around the compressor side. Slide mount for lid access. ~30–50 Ah/day depending on temp.",
    sources: [{ label: "Dometic CFX3", url: "https://www.dometic.com" }],
    confidence: "manufacturer", verified: true, tags: ["fridge", "12v"], updatedAt: "2026-05-02" },

  { id: "ap-induction", name: "2-Burner Induction Cooktop", system: "appliance", category: "Cooktop", brand: "Generic", model: "IND-2B",
    dims: { l: 23, w: 14, h: 2.5 }, weightLb: 12, costUsd: 180,
    power: { voltage: "120V", watts: 1800, amps: 15, surgeWatts: null, idleWatts: 1 },
    capacity: { value: 1800, unit: "W", kind: "Peak draw" },
    mountingNotes: "High AC draw — size the inverter for it or run on shore power. Needs clearance and ventilation above.",
    sources: [],
    confidence: "estimated", verified: false, tags: ["cooking", "high-draw"], updatedAt: "2026-03-19" },

  { id: "ap-natureshead", name: "Composting Toilet", system: "appliance", category: "Toilet", brand: "Nature's Head", model: "NH-STD",
    dims: { l: 19, w: 20.5, h: 20 }, weightLb: 28, costUsd: 1030,
    power: { voltage: "12V", watts: 2, amps: 0.15, surgeWatts: null, idleWatts: null },
    capacity: { value: 2, unit: "", kind: "Vent fan (W)" },
    mountingNotes: "Bolt to floor; vent the fan to outside. Separates liquids/solids — no black tank or plumbing needed.",
    sources: [{ label: "Nature's Head", url: "https://natureshead.net" }],
    confidence: "manufacturer", verified: false, tags: ["toilet", "no plumbing"], updatedAt: "2026-04-21" },

  // ---------- CABINETRY ----------
  { id: "cb-upper", name: "Upper Galley Cabinet (custom)", system: "cabinetry", category: "Overhead Cabinet", brand: "Custom", model: "UPPER-36",
    dims: { l: 36, w: 12, h: 14 }, weightLb: 40, costUsd: 350,
    power: null,
    capacity: { value: 3, unit: "cu_ft", kind: "Storage" },
    mountingNotes: 'Lag into wall ribs or unistrut backing — never just into sheet metal. 1/2"–3/4" birch ply with doors.',
    sources: [],
    confidence: "estimated", verified: false, tags: ["storage", "plywood"], updatedAt: "2026-03-11" },

  { id: "cb-bed", name: "Bed Platform Frame (custom)", system: "cabinetry", category: "Bed Frame", brand: "Custom", model: "BED-PLAT",
    dims: { l: 74, w: 54, h: 14 }, weightLb: 120, costUsd: 350,
    power: null,
    capacity: { value: 400, unit: "", kind: "Rated load (lb)" },
    mountingNotes: '2x2 frame with 3/4" deck and slats; ties into wall studs. Garage storage underneath.',
    sources: [],
    confidence: "estimated", verified: false, tags: ["sleeping", "plywood"], updatedAt: "2026-03-11" },

  { id: "cb-galley", name: "Galley Base Cabinet (custom)", system: "cabinetry", category: "Base Cabinet", brand: "Custom", model: "GALLEY-40",
    dims: { l: 40, w: 24, h: 36 }, weightLb: 110, costUsd: 600,
    power: null,
    capacity: { value: 8, unit: "cu_ft", kind: "Storage" },
    mountingNotes: 'Birch ply carcass, butcher-block top, drawer slides, sink cutout. Bolt to floor + wall.',
    sources: [],
    confidence: "estimated", verified: false, tags: ["kitchen", "plywood"], updatedAt: "2026-03-11" },

  // ---------- MATERIALS ----------
  { id: "mt-havelock", name: "Havelock Wool Insulation (bag)", system: "material", category: "Insulation", brand: "Havelock Wool", model: "HW-BATT",
    dims: { l: null, w: null, h: null }, weightLb: 18, costUsd: 110,
    power: null,
    capacity: { value: 30, unit: "sq_ft", kind: "Coverage (≈2in)" },
    mountingNotes: "Friction-fit into cavities; breathable, manages moisture. R≈3.4/in. No vapor barrier needed.",
    sources: [{ label: "Havelock Wool", url: "https://havelockwool.com" }],
    confidence: "estimated", verified: false, tags: ["insulation", "wool"], updatedAt: "2026-04-07" },

  { id: "mt-thinsulate", name: "3M Thinsulate SM600L (roll)", system: "material", category: "Insulation", brand: "3M", model: "SM600L",
    dims: { l: null, w: 60, h: null }, weightLb: 12, costUsd: 220,
    power: null,
    capacity: { value: 50, unit: "sq_ft", kind: "Coverage (per roll)" },
    mountingNotes: "Spray-glue to walls/ceiling. Hydrophobic, fills irregular cavities. R≈5.2 at 1.6in loft.",
    sources: [{ label: "3M Thinsulate", url: "https://www.3m.com" }],
    confidence: "manufacturer", verified: false, tags: ["insulation", "synthetic"], updatedAt: "2026-04-07" },
];

/* ---- warning engine ----------------------------------------------------- */
/* Flags missing or unverified specs. Severity: error > warn > info.          */
function getWarnings(c) {
  const w = [];
  const d = c.dims || {};
  if (d.l == null || d.w == null || d.h == null) w.push({ level: "error", field: "Dimensions", msg: "Missing one or more dimensions." });
  if (c.weightLb == null) w.push({ level: "error", field: "Weight", msg: "No weight on file — affects payload math." });
  if (c.costUsd == null) w.push({ level: "warn", field: "Cost", msg: "No price on file." });
  if (c.system === "electrical" || c.system === "appliance") {
    if (!c.power) w.push({ level: "warn", field: "Power", msg: "No power spec for an electrical part." });
    else if (c.power.watts == null && c.power.amps == null) w.push({ level: "warn", field: "Power", msg: "Power draw not specified." });
  }
  if ((c.system === "tank" || c.category === "Battery") && (!c.capacity || c.capacity.value == null))
    w.push({ level: "warn", field: "Capacity", msg: "Capacity not specified." });
  if (!c.sources || c.sources.length === 0) w.push({ level: "warn", field: "Source", msg: "No source link — can't trace the spec." });
  if (c.confidence === "unverified") w.push({ level: "error", field: "Confidence", msg: "Marked unverified — placeholder data." });
  else if (c.confidence === "estimated") w.push({ level: "info", field: "Confidence", msg: "Estimated — confirm before building." });
  if (!c.verified) w.push({ level: "info", field: "Review", msg: "Not human-reviewed yet." });
  return w;
}
const worstLevel = (warns) =>
  warns.some((x) => x.level === "error") ? "error" : warns.some((x) => x.level === "warn") ? "warn" : warns.length ? "info" : "ok";

/* ---- formatting helpers ------------------------------------------------- */
const dash = "—";
const money = (n) => (n == null ? dash : "$" + n.toLocaleString());
const dims = (d) => (!d || d.l == null || d.w == null || d.h == null ? dash : `${d.l} × ${d.w} × ${d.h} in`);
const wt = (n) => (n == null ? dash : `${n} lb`);
const power = (p) => {
  if (!p) return dash;
  const bits = [];
  if (p.watts != null) bits.push(`${p.watts} W`);
  if (p.amps != null) bits.push(`${p.amps} A`);
  return (bits.length ? bits.join(" · ") : dash) + (p.voltage && p.voltage !== "N/A" ? ` @ ${p.voltage}` : "");
};
const cap = (c) => (!c || c.value == null ? dash : `${c.value}${c.unit ? " " + c.unit.replace("_", " ") : ""}`);

/* ---- CSV import / export ------------------------------------------------ */
const CSV_COLS = [
  "id", "name", "system", "category", "brand", "model",
  "length_in", "width_in", "height_in", "weight_lb", "cost_usd",
  "voltage", "watts", "amps", "surge_watts", "idle_watts",
  "capacity_value", "capacity_unit", "capacity_kind",
  "mounting_notes", "confidence", "verified", "tags", "sources", "updated_at",
];
const csvCell = (v) => {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
function toCSV(list) {
  const rows = [CSV_COLS.join(",")];
  for (const c of list) {
    const d = c.dims || {}, p = c.power || {}, cp = c.capacity || {};
    const row = [
      c.id, c.name, c.system, c.category, c.brand, c.model,
      d.l, d.w, d.h, c.weightLb, c.costUsd,
      p.voltage, p.watts, p.amps, p.surgeWatts, p.idleWatts,
      cp.value, cp.unit, cp.kind,
      c.mountingNotes, c.confidence, c.verified,
      (c.tags || []).join(";"),
      (c.sources || []).map((s) => `${s.label}|${s.url}`).join(";"),
      c.updatedAt,
    ];
    rows.push(row.map(csvCell).join(","));
  }
  return rows.join("\n");
}
function parseCSV(text) {
  const rows = [];
  let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += ch;
    } else {
      if (ch === '"') q = true;
      else if (ch === ",") { row.push(cell); cell = ""; }
      else if (ch === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
      else if (ch === "\r") { /* skip */ }
      else cell += ch;
    }
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  if (!rows.length) return [];
  const head = rows[0].map((h) => h.trim());
  const num = (v) => (v === "" || v == null ? null : Number(v));
  return rows.slice(1).filter((r) => r.some((x) => x !== "")).map((r) => {
    const g = (k) => r[head.indexOf(k)] ?? "";
    return {
      id: g("id") || "imp-" + Math.random().toString(36).slice(2, 8),
      name: g("name"), system: g("system"), category: g("category"),
      brand: g("brand"), model: g("model"),
      dims: { l: num(g("length_in")), w: num(g("width_in")), h: num(g("height_in")) },
      weightLb: num(g("weight_lb")), costUsd: num(g("cost_usd")),
      power: g("voltage") || g("watts") || g("amps")
        ? { voltage: g("voltage") || "N/A", watts: num(g("watts")), amps: num(g("amps")), surgeWatts: num(g("surge_watts")), idleWatts: num(g("idle_watts")) }
        : null,
      capacity: g("capacity_value") ? { value: num(g("capacity_value")), unit: g("capacity_unit"), kind: g("capacity_kind") } : null,
      mountingNotes: g("mounting_notes"),
      confidence: g("confidence") || "unverified",
      verified: String(g("verified")).toLowerCase() === "true",
      tags: g("tags") ? g("tags").split(";").filter(Boolean) : [],
      sources: g("sources") ? g("sources").split(";").filter(Boolean).map((s) => { const [label, url] = s.split("|"); return { label: label || url, url: url || "" }; }) : [],
      updatedAt: g("updated_at") || new Date().toISOString().slice(0, 10),
    };
  });
}
function download(filename, text, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ---- small UI atoms ----------------------------------------------------- */
function SystemBadge({ system }) {
  const m = SYSTEM_META[system] || SYSTEM_META.material;
  const Icon = m.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs font-medium ${m.badge}`}>
      <Icon className="h-3 w-3" /> {m.label}
    </span>
  );
}
function ConfidenceBadge({ level }) {
  const m = CONFIDENCE_META[level] || CONFIDENCE_META.unverified;
  return <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium ${m.badge}`}>{m.label}</span>;
}
function WarnPip({ warns }) {
  const lvl = worstLevel(warns);
  if (lvl === "ok") return <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="h-3.5 w-3.5" /></span>;
  const map = { error: "text-red-400", warn: "text-amber-400", info: "text-sky-400" };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-mono ${map[lvl]}`}>
      <AlertTriangle className="h-3.5 w-3.5" /> {warns.length}
    </span>
  );
}

/* ============================ MAIN APP ==================================== */
export default function App() {
  const [components, setComponents] = useState(SEED);
  const [q, setQ] = useState("");
  const [fSystem, setFSystem] = useState("all");
  const [fCategory, setFCategory] = useState("all");
  const [fBrand, setFBrand] = useState("all");
  const [fVoltage, setFVoltage] = useState("all");
  const [fWeight, setFWeight] = useState(200); // lb ceiling
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [toast, setToast] = useState(null);
  const fileRef = useRef(null);

  const flash = (msg) => { setToast(msg); setTimeout(() => setToast(null), 2600); };

  /* filter option lists */
  const brands = useMemo(() => Array.from(new Set(components.map((c) => c.brand))).sort(), [components]);
  const categories = useMemo(() => {
    const inSystem = components.filter((c) => fSystem === "all" || c.system === fSystem);
    return Array.from(new Set(inSystem.map((c) => c.category))).sort();
  }, [components, fSystem]);
  const maxWeight = useMemo(() => Math.max(50, ...components.map((c) => c.weightLb || 0)), [components]);

  /* the filtered set */
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return components.filter((c) => {
      if (fSystem !== "all" && c.system !== fSystem) return false;
      if (fCategory !== "all" && c.category !== fCategory) return false;
      if (fBrand !== "all" && c.brand !== fBrand) return false;
      if (fVoltage !== "all") {
        const v = c.power?.voltage || "N/A";
        if (v !== fVoltage) return false;
      }
      if (c.weightLb != null && c.weightLb > fWeight) return false;
      if (onlyFlagged && worstLevel(getWarnings(c)) === "ok") return false;
      if (needle) {
        const hay = `${c.name} ${c.brand} ${c.model} ${c.category} ${(c.tags || []).join(" ")}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
  }, [components, q, fSystem, fCategory, fBrand, fVoltage, fWeight, onlyFlagged]);

  const flaggedCount = useMemo(() => components.filter((c) => worstLevel(getWarnings(c)) !== "ok").length, [components]);
  const selected = components.find((c) => c.id === selectedId) || null;

  const resetFilters = () => {
    setQ(""); setFSystem("all"); setFCategory("all"); setFBrand("all"); setFVoltage("all"); setFWeight(maxWeight); setOnlyFlagged(false);
  };

  /* export */
  const exportJSON = () => { download("van-parts.json", JSON.stringify(filtered, null, 2), "application/json"); flash(`Exported ${filtered.length} parts as JSON`); };
  const exportCSV = () => { download("van-parts.csv", toCSV(filtered), "text/csv"); flash(`Exported ${filtered.length} parts as CSV`); };

  /* import */
  const onImport = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const text = String(reader.result || "").trim();
        let incoming = [];
        if (text.startsWith("[") || text.startsWith("{")) {
          const parsed = JSON.parse(text);
          incoming = Array.isArray(parsed) ? parsed : [parsed];
        } else {
          incoming = parseCSV(text);
        }
        if (!incoming.length) { flash("No rows found in that file"); return; }
        setComponents((prev) => {
          const byId = new Map(prev.map((c) => [c.id, c]));
          for (const c of incoming) byId.set(c.id, { ...byId.get(c.id), ...c });
          return Array.from(byId.values());
        });
        flash(`Imported ${incoming.length} part${incoming.length > 1 ? "s" : ""}`);
      } catch (err) {
        flash("Couldn't read that file — check it's valid JSON or CSV");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const fieldCls = "w-full rounded-md border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

  return (
    <div className="flex h-screen flex-col bg-slate-950 font-sans text-slate-200">
      {/* ---- top bar ---- */}
      <header className="flex flex-wrap items-center gap-3 border-b border-slate-800 bg-slate-900 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-600 text-white"><Boxes className="h-5 w-5" /></div>
          <div>
            <div className="text-sm font-semibold tracking-tight text-white">Van Parts DB</div>
            <div className="font-mono text-xs text-slate-500">component spec database</div>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-4 font-mono text-xs">
          <div className="text-slate-400"><span className="text-base font-semibold text-white">{components.length}</span> parts</div>
          <div className="text-slate-400"><span className="text-base font-semibold text-white">{filtered.length}</span> shown</div>
          <div className="flex items-center gap-1 text-amber-400"><AlertTriangle className="h-3.5 w-3.5" /><span className="text-base font-semibold">{flaggedCount}</span> flagged</div>
        </div>

        <div className="flex items-center gap-1.5">
          <button onClick={() => fileRef.current?.click()} className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700">
            <Upload className="h-3.5 w-3.5" /> Import
          </button>
          <input ref={fileRef} type="file" accept=".json,.csv,application/json,text/csv" onChange={onImport} className="hidden" />
          <button onClick={exportJSON} className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700">
            <FileJson className="h-3.5 w-3.5" /> JSON
          </button>
          <button onClick={exportCSV} className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700">
            <FileSpreadsheet className="h-3.5 w-3.5" /> CSV
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        {/* ---- filter rail ---- */}
        <aside className="hidden w-60 shrink-0 flex-col gap-4 overflow-y-auto border-r border-slate-800 bg-slate-900 p-4 md:flex">
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            <Filter className="h-3.5 w-3.5" /> Filters
          </div>

          <label className="block">
            <span className="mb-1 block text-xs text-slate-400">System</span>
            <select value={fSystem} onChange={(e) => { setFSystem(e.target.value); setFCategory("all"); }} className={fieldCls}>
              <option value="all">All systems</option>
              {SYSTEMS.map((s) => <option key={s} value={s}>{SYSTEM_META[s].label}</option>)}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-slate-400">Category</span>
            <select value={fCategory} onChange={(e) => setFCategory(e.target.value)} className={fieldCls}>
              <option value="all">All categories</option>
              {categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-slate-400">Brand</span>
            <select value={fBrand} onChange={(e) => setFBrand(e.target.value)} className={fieldCls}>
              <option value="all">All brands</option>
              {brands.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-slate-400">Voltage</span>
            <select value={fVoltage} onChange={(e) => setFVoltage(e.target.value)} className={fieldCls}>
              <option value="all">Any voltage</option>
              {VOLTAGES.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>

          <label className="block">
            <span className="mb-1 flex items-center justify-between text-xs text-slate-400">
              <span>Max weight</span><span className="font-mono text-slate-300">{fWeight} lb</span>
            </span>
            <input type="range" min="0" max={maxWeight} step="1" value={fWeight} onChange={(e) => setFWeight(Number(e.target.value))} className="w-full accent-blue-500" />
          </label>

          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input type="checkbox" checked={onlyFlagged} onChange={(e) => setOnlyFlagged(e.target.checked)} className="h-4 w-4 accent-blue-500" />
            Only show flagged parts
          </label>

          <button onClick={resetFilters} className="mt-auto rounded-md border border-slate-700 px-2 py-1.5 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200">
            Reset filters
          </button>
        </aside>

        {/* ---- list ---- */}
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="border-b border-slate-800 bg-slate-900/60 p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-500" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, brand, model, tag…"
                className="w-full rounded-md border border-slate-700 bg-slate-800 py-2 pl-9 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {filtered.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-slate-500">
                <Search className="h-8 w-8" />
                <p className="text-sm">No parts match these filters.</p>
                <button onClick={resetFilters} className="text-xs text-blue-400 hover:underline">Clear filters</button>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-2 lg:grid-cols-2 xl:grid-cols-3">
                {filtered.map((c) => {
                  const warns = getWarnings(c);
                  const active = c.id === selectedId;
                  return (
                    <button key={c.id} onClick={() => setSelectedId(c.id)}
                      className={`group rounded-lg border p-3 text-left transition ${active ? "border-blue-500 bg-slate-800" : "border-slate-800 bg-slate-900 hover:border-slate-600 hover:bg-slate-800/60"}`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-white">{c.name}</div>
                          <div className="truncate font-mono text-xs text-slate-500">{c.brand} · {c.model}</div>
                        </div>
                        <WarnPip warns={warns} />
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <SystemBadge system={c.system} />
                        <ConfidenceBadge level={c.confidence} />
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-1 font-mono text-xs text-slate-400">
                        <div className="flex items-center gap-1"><Scale className="h-3 w-3 text-slate-600" />{wt(c.weightLb)}</div>
                        <div className="flex items-center gap-1"><DollarSign className="h-3 w-3 text-slate-600" />{c.costUsd == null ? dash : c.costUsd}</div>
                        <div className="flex items-center gap-1"><Gauge className="h-3 w-3 text-slate-600" />{c.power ? (c.power.watts != null ? c.power.watts + "W" : c.power.amps + "A") : dash}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </main>

        {/* ---- detail panel ---- */}
        {selected && <DetailPanel c={selected} onClose={() => setSelectedId(null)}
          onToggleVerified={() => setComponents((prev) => prev.map((x) => x.id === selected.id ? { ...x, verified: !x.verified } : x))} />}
      </div>

      {toast && (
        <div className="pointer-events-none fixed bottom-4 left-1/2 -translate-x-1/2 rounded-md border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-100 shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

/* ---- detail panel (the spec sheet) ------------------------------------- */
function DetailPanel({ c, onClose, onToggleVerified }) {
  const warns = getWarnings(c);
  const m = SYSTEM_META[c.system];
  const cm = CONFIDENCE_META[c.confidence] || CONFIDENCE_META.unverified;
  const lvlIcon = { error: <AlertTriangle className="h-4 w-4 text-red-400" />, warn: <AlertTriangle className="h-4 w-4 text-amber-400" />, info: <Info className="h-4 w-4 text-sky-400" /> };

  return (
    <aside className="flex w-full max-w-md shrink-0 flex-col overflow-y-auto border-l border-slate-800 bg-slate-900 md:w-96">
      {/* header */}
      <div className="sticky top-0 z-10 border-b border-slate-800 bg-slate-900 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-white">{c.name}</h2>
            <p className="font-mono text-xs text-slate-500">{c.brand} · {c.model}</p>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"><X className="h-5 w-5" /></button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <SystemBadge system={c.system} />
          <span className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-xs text-slate-300">{c.category}</span>
          <ConfidenceBadge level={c.confidence} />
        </div>
      </div>

      <div className="space-y-5 p-4">
        {/* warnings */}
        {warns.length > 0 ? (
          <section className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <ShieldQuestion className="h-3.5 w-3.5" /> Data check · {warns.length}
            </div>
            <ul className="space-y-1.5">
              {warns.map((w, i) => (
                <li key={i} className="flex items-start gap-2 text-xs">
                  <span className="mt-0.5">{lvlIcon[w.level]}</span>
                  <span><span className="font-medium text-slate-200">{w.field}:</span> <span className="text-slate-400">{w.msg}</span></span>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <section className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm text-emerald-300">
            <CheckCircle2 className="h-4 w-4" /> All key specs present and verified.
          </section>
        )}

        {/* spec grid */}
        <section>
          <SpecRow icon={Ruler}  label="Dimensions (L×W×H)" value={dims(c.dims)} />
          <SpecRow icon={Scale}  label="Weight"            value={wt(c.weightLb)} />
          <SpecRow icon={DollarSign} label="Cost"          value={money(c.costUsd)} />
          <SpecRow icon={Gauge}  label="Power"             value={power(c.power)} />
          {c.power?.surgeWatts != null && <SpecRow icon={Zap} label="Surge" value={`${c.power.surgeWatts} W`} />}
          <SpecRow icon={Boxes}  label={c.capacity?.kind || "Capacity"} value={cap(c.capacity)} />
        </section>

        {/* mounting notes */}
        {c.mountingNotes && (
          <section>
            <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">Mounting notes</h3>
            <p className="text-sm leading-relaxed text-slate-300">{c.mountingNotes}</p>
          </section>
        )}

        {/* tags */}
        {c.tags?.length > 0 && (
          <section className="flex flex-wrap gap-1.5">
            {c.tags.map((t) => (
              <span key={t} className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                <Tag className="h-3 w-3" />{t}
              </span>
            ))}
          </section>
        )}

        {/* sources */}
        <section>
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">Sources</h3>
          {c.sources?.length ? (
            <ul className="space-y-1">
              {c.sources.map((s, i) => (
                <li key={i}>
                  <a href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sm text-blue-400 hover:underline">
                    <ExternalLink className="h-3.5 w-3.5" /> {s.label}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No source on file — spec can't be traced to a datasheet.</p>
          )}
        </section>

        {/* confidence + review */}
        <section className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Confidence</span>
            <ConfidenceBadge level={c.confidence} />
          </div>
          <p className="mt-1 text-xs text-slate-500">{cm.note}</p>
          <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-3">
            <span className="text-xs text-slate-400">Human-reviewed</span>
            <button onClick={onToggleVerified}
              className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium ${c.verified ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-slate-700 bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
              <CheckCircle2 className="h-3.5 w-3.5" /> {c.verified ? "Verified" : "Mark verified"}
            </button>
          </div>
          <p className="mt-2 font-mono text-xs text-slate-600">updated {c.updatedAt}</p>
        </section>
      </div>
    </aside>
  );
}

function SpecRow({ icon: Icon, label, value }) {
  const missing = value === dash;
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-800 py-2 last:border-0">
      <span className="inline-flex items-center gap-2 text-sm text-slate-400"><Icon className="h-4 w-4 text-slate-600" />{label}</span>
      <span className={`font-mono text-sm ${missing ? "text-red-400" : "text-slate-100"}`}>{value}</span>
    </div>
  );
}
