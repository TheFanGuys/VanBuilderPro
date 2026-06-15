/**
 * filter.ts — apply the UI filter set to a list of components.
 * Pure function, no React, so it's testable and reusable on a server too.
 */
import type { VanComponent, ComponentFilter } from "./types";
import { getWarnings, worstLevel } from "./warnings";

export function filterComponents(list: VanComponent[], f: ComponentFilter): VanComponent[] {
  const needle = (f.query || "").trim().toLowerCase();

  return list.filter((c) => {
    if (f.system && f.system !== "all" && c.system !== f.system) return false;
    if (f.category && f.category !== "all" && c.category !== f.category) return false;
    if (f.brand && f.brand !== "all" && c.brand !== f.brand) return false;

    if (f.voltage && f.voltage !== "all") {
      const v = c.power?.voltage || "N/A";
      if (v !== f.voltage) return false;
    }

    if (f.maxWeightLb != null && c.weightLb != null && c.weightLb > f.maxWeightLb) return false;

    if (f.onlyFlagged && worstLevel(getWarnings(c)) === "ok") return false;

    if (needle) {
      const hay = `${c.name} ${c.brand} ${c.model} ${c.category} ${c.tags.join(" ")}`.toLowerCase();
      if (!hay.includes(needle)) return false;
    }
    return true;
  });
}

/** Distinct, sorted brand list for a filter dropdown. */
export function brandsOf(list: VanComponent[]): string[] {
  return Array.from(new Set(list.map((c) => c.brand))).sort();
}

/** Distinct, sorted category list, optionally scoped to one system. */
export function categoriesOf(list: VanComponent[], system?: string): string[] {
  const scoped = !system || system === "all" ? list : list.filter((c) => c.system === system);
  return Array.from(new Set(scoped.map((c) => c.category))).sort();
}
