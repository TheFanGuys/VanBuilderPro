/**
 * types.ts — data model for the van / RV component database.
 *
 * Design goals:
 *  - Every spec field is nullable. An AI agent populating from a datasheet
 *    fills what it can find and leaves the rest null; the warning engine
 *    (warnings.ts) flags the gaps instead of the data lying about itself.
 *  - Every part carries `sources` (where the numbers came from) and a
 *    `confidence` level + `verified` flag, so a human stays in the loop.
 *  - Units are fixed and documented so importers never have to guess:
 *    inches, pounds, USD, watts, amps. Capacity carries its own unit.
 */

/** Broad system a part belongs to. Drives the top-level filter. */
export type SystemType =
  | "electrical"
  | "plumbing"
  | "hvac"
  | "tank"
  | "appliance"
  | "roof"
  | "cabinetry"
  | "material";

/** Nominal voltage. "N/A" for non-powered parts (tanks, cabinets, panels). */
export type Voltage = "12V" | "24V" | "48V" | "120V" | "240V" | "N/A";

/**
 * How much to trust the numbers on this part.
 *  - verified:     a human checked them against the datasheet.
 *  - manufacturer: taken from the maker's published figures, not yet checked.
 *  - estimated:    approximate / typical values, confirm before building.
 *  - unverified:   placeholder from an unconfirmed source.
 */
export type ConfidenceLevel = "verified" | "manufacturer" | "estimated" | "unverified";

/** Capacity units, kept explicit so importers never guess. */
export type CapacityUnit =
  | "Ah"     // battery / charge current
  | "Wh"     // energy
  | "gal"    // tank volume (US gallons)
  | "L"      // litres
  | "BTU"    // heating / cooling
  | "W"      // rated power output (solar, inverter)
  | "cu_ft"  // storage / fridge interior
  | "sq_ft"  // insulation coverage
  | "";      // unit-less count (circuits, ports, CFM, etc. — see `kind`)

/** Bounding box of the installed part, in inches. Any axis may be unknown. */
export interface Dimensions {
  l: number | null; // length, in
  w: number | null; // width, in
  h: number | null; // height, in
}

/** Electrical draw. Present only for powered parts; null otherwise. */
export interface PowerSpec {
  voltage: Voltage;
  watts: number | null;       // nominal running power
  amps: number | null;        // nominal current at `voltage`
  surgeWatts: number | null;  // peak / startup draw
  idleWatts: number | null;   // standby draw
}

/**
 * A single capacity figure with its unit and a human label.
 * `kind` lets one field cover very different parts:
 *   { value: 100, unit: "Ah",  kind: "Battery capacity" }
 *   { value: 21,  unit: "gal", kind: "Potable water" }
 *   { value: 13500, unit: "BTU", kind: "Cooling" }
 */
export interface Capacity {
  value: number | null;
  unit: CapacityUnit;
  kind: string;
}

/** Where a spec came from. URL should point at a datasheet or product page. */
export interface SourceRef {
  label: string;
  url: string;
}

/** A single component in the database. */
export interface VanComponent {
  id: string;            // stable slug, unique across the DB
  name: string;          // human name shown in the UI
  system: SystemType;    // broad system (filter)
  category: string;      // sub-type within the system, e.g. "Battery", "Roof Fan"
  brand: string;         // manufacturer, or "Generic" / "Custom"
  model: string;         // model / part number

  dims: Dimensions;
  weightLb: number | null;
  costUsd: number | null;

  power: PowerSpec | null;     // null for non-electrical parts
  capacity: Capacity | null;   // null when not applicable

  mountingNotes: string;       // install guidance, free text
  sources: SourceRef[];        // traceability — may be empty
  confidence: ConfidenceLevel;
  verified: boolean;           // human sign-off
  tags: string[];
  updatedAt: string;           // ISO date, YYYY-MM-DD
}

/** Severity for a data-quality warning. */
export type WarnLevel = "error" | "warn" | "info";

/** A single flag raised by the warning engine. */
export interface Warning {
  level: WarnLevel;
  field: string;
  msg: string;
}

/** The set of fields the UI filters on. All optional / "all" = no filter. */
export interface ComponentFilter {
  query?: string;
  system?: SystemType | "all";
  category?: string | "all";
  brand?: string | "all";
  voltage?: Voltage | "all";
  maxWeightLb?: number | null;
  onlyFlagged?: boolean;
}
