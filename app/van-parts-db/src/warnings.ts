/**
 * warnings.ts — flags missing or unverified specs.
 *
 * This is the quality gate that makes the DB safe to auto-populate: an agent
 * can drop in partial data and the UI immediately shows what still needs a
 * human's eyes. Severity order is error > warn > info.
 */
import type { VanComponent, Warning, WarnLevel } from "./types";

/** Returns every data-quality flag for a component (empty = clean). */
export function getWarnings(c: VanComponent): Warning[] {
  const w: Warning[] = [];
  const d = c.dims;

  if (d.l == null || d.w == null || d.h == null)
    w.push({ level: "error", field: "Dimensions", msg: "Missing one or more dimensions." });

  if (c.weightLb == null)
    w.push({ level: "error", field: "Weight", msg: "No weight on file — affects payload math." });

  if (c.costUsd == null)
    w.push({ level: "warn", field: "Cost", msg: "No price on file." });

  // Powered systems should declare a draw.
  if (c.system === "electrical" || c.system === "appliance") {
    if (!c.power) w.push({ level: "warn", field: "Power", msg: "No power spec for an electrical part." });
    else if (c.power.watts == null && c.power.amps == null)
      w.push({ level: "warn", field: "Power", msg: "Power draw not specified." });
  }

  // Tanks and batteries are defined by their capacity.
  if ((c.system === "tank" || c.category === "Battery") && (!c.capacity || c.capacity.value == null))
    w.push({ level: "warn", field: "Capacity", msg: "Capacity not specified." });

  if (!c.sources || c.sources.length === 0)
    w.push({ level: "warn", field: "Source", msg: "No source link — can't trace the spec." });

  if (c.confidence === "unverified")
    w.push({ level: "error", field: "Confidence", msg: "Marked unverified — placeholder data." });
  else if (c.confidence === "estimated")
    w.push({ level: "info", field: "Confidence", msg: "Estimated — confirm before building." });

  if (!c.verified)
    w.push({ level: "info", field: "Review", msg: "Not human-reviewed yet." });

  return w;
}

/** The worst severity present, or "ok" when the part is clean. */
export function worstLevel(warns: Warning[]): WarnLevel | "ok" {
  if (warns.some((x) => x.level === "error")) return "error";
  if (warns.some((x) => x.level === "warn")) return "warn";
  return warns.length ? "info" : "ok";
}

/** Convenience: is this component free of any flags? */
export function isClean(c: VanComponent): boolean {
  return getWarnings(c).length === 0;
}
