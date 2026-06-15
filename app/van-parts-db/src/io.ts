/**
 * io.ts — JSON and CSV import / export.
 *
 * CSV is the flat interchange format an AI agent or spreadsheet will produce;
 * the nested PowerSpec / Capacity / sources collapse into named columns and
 * expand back on import. JSON is the lossless format for round-tripping.
 */
import type { VanComponent, Voltage, ConfidenceLevel, CapacityUnit } from "./types";

/* ----------------------------- JSON ------------------------------------- */

export function exportJSON(list: VanComponent[]): string {
  return JSON.stringify(list, null, 2);
}

export function importJSON(text: string): VanComponent[] {
  const parsed = JSON.parse(text);
  return Array.isArray(parsed) ? parsed : [parsed];
}

/* ------------------------------ CSV ------------------------------------- */

export const CSV_COLUMNS = [
  "id", "name", "system", "category", "brand", "model",
  "length_in", "width_in", "height_in", "weight_lb", "cost_usd",
  "voltage", "watts", "amps", "surge_watts", "idle_watts",
  "capacity_value", "capacity_unit", "capacity_kind",
  "mounting_notes", "confidence", "verified", "tags", "sources", "updated_at",
] as const;

function csvCell(v: unknown): string {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function exportCSV(list: VanComponent[]): string {
  const rows: string[] = [CSV_COLUMNS.join(",")];
  for (const c of list) {
    const d = c.dims, p = c.power, cp = c.capacity;
    const row = [
      c.id, c.name, c.system, c.category, c.brand, c.model,
      d.l, d.w, d.h, c.weightLb, c.costUsd,
      p?.voltage, p?.watts, p?.amps, p?.surgeWatts, p?.idleWatts,
      cp?.value, cp?.unit, cp?.kind,
      c.mountingNotes, c.confidence, c.verified,
      c.tags.join(";"),
      c.sources.map((s) => `${s.label}|${s.url}`).join(";"),
      c.updatedAt,
    ];
    rows.push(row.map(csvCell).join(","));
  }
  return rows.join("\n");
}

/** Minimal RFC-4180-ish parser: handles quoted fields, escaped quotes, CRLF. */
function parseRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
    else if (ch !== "\r") cell += ch;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

export function importCSV(text: string): VanComponent[] {
  const rows = parseRows(text);
  if (!rows.length) return [];
  const head = rows[0].map((h) => h.trim());
  const idx = (k: string) => head.indexOf(k);
  const num = (v: string): number | null => (v === "" ? null : Number(v));

  return rows.slice(1)
    .filter((r) => r.some((x) => x !== ""))
    .map((r) => {
      const g = (k: string): string => r[idx(k)] ?? "";
      const hasPower = g("voltage") || g("watts") || g("amps");
      return {
        id: g("id") || "imp-" + Math.random().toString(36).slice(2, 8),
        name: g("name"), system: g("system") as VanComponent["system"], category: g("category"),
        brand: g("brand"), model: g("model"),
        dims: { l: num(g("length_in")), w: num(g("width_in")), h: num(g("height_in")) },
        weightLb: num(g("weight_lb")), costUsd: num(g("cost_usd")),
        power: hasPower
          ? { voltage: (g("voltage") || "N/A") as Voltage, watts: num(g("watts")), amps: num(g("amps")), surgeWatts: num(g("surge_watts")), idleWatts: num(g("idle_watts")) }
          : null,
        capacity: g("capacity_value")
          ? { value: num(g("capacity_value")), unit: (g("capacity_unit") || "") as CapacityUnit, kind: g("capacity_kind") }
          : null,
        mountingNotes: g("mounting_notes"),
        confidence: (g("confidence") || "unverified") as ConfidenceLevel,
        verified: g("verified").toLowerCase() === "true",
        tags: g("tags") ? g("tags").split(";").filter(Boolean) : [],
        sources: g("sources")
          ? g("sources").split(";").filter(Boolean).map((s) => { const [label, url] = s.split("|"); return { label: label || url, url: url || "" }; })
          : [],
        updatedAt: g("updated_at") || new Date().toISOString().slice(0, 10),
      } as VanComponent;
    });
}

/** Detects format from the text and imports. Merges by id is left to the caller. */
export function importAny(text: string): VanComponent[] {
  const t = text.trim();
  return t.startsWith("[") || t.startsWith("{") ? importJSON(t) : importCSV(t);
}
