#!/usr/bin/env python3
"""
discovery_sources.py — where the Discovery Agent gets its candidates
====================================================================
Stage 1 of the pipeline is pluggable. By default it uses the SEEDED list baked
into discovery_agent.py (works offline, no keys). A live web source can be
dropped in by setting an environment variable — but read the honesty note below
before expecting it to "just work".

    get_source(seed_fn)  →  .fetch()  →  list[candidate dict]

────────────────────────────────────────────────────────────────────────────
HONEST STATUS
────────────────────────────────────────────────────────────────────────────
• SeedSource      ✅ finished, tested, offline. This is what runs today.
• LiveWebSource   🟡 SCAFFOLD ONLY — NOT finished, NOT tested.
                  It needs ALL of the following, none of which ship in this repo:
                    1. A paid/free-tier SEARCH API account + key
                       (e.g. Brave Search API, Bing, SerpAPI, Google CSE).
                    2. Network access from wherever you run it.
                    3. A spec-extraction step that reads each datasheet/manual
                       and pulls structured numbers — realistically an LLM call
                       (e.g. the Anthropic API) or hand-written per-site parsers.
                  Until those exist, LiveWebSource raises NotConfigured and the
                  agent falls back to the seed. This file documents the shape of
                  the work so it can be finished deliberately — not pretended.
────────────────────────────────────────────────────────────────────────────
"""

import os


class NotConfigured(Exception):
    """Raised when a live source is selected but its prerequisites are missing."""


class Source:
    """Base interface. A source returns Stage-1 candidate dicts in the same shape
    the seed produces (see discovery_agent.D / seed_candidates)."""
    def fetch(self):
        raise NotImplementedError


class SeedSource(Source):
    """Default. Returns the hand-curated, sourced candidate list. Offline."""
    def __init__(self, seed_fn):
        self._seed_fn = seed_fn

    def fetch(self):
        return self._seed_fn()


class LiveWebSource(Source):
    """SCAFFOLD for live discovery. Not functional without the pieces in the
    honesty note above. Kept deliberately explicit so 'finishing' it is a clear,
    bounded task rather than a vague promise.

    Required environment:
      VANBUILDER_SEARCH_API_KEY   key for a search provider
      VANBUILDER_SEARCH_ENDPOINT  the provider's search URL
      (optional) ANTHROPIC_API_KEY  for LLM-based spec extraction

    The categories to sweep are the ones in the project brief (batteries,
    inverters, DC-DC, MPPT, solar, fuse/distribution, wire/lugs, tanks, pumps,
    water heaters, fridges, toilets, showers, roof fans, roof AC, diesel heaters,
    windows, roof racks, insulation, plywood, extrusion, cabinet hardware,
    plumbing fittings).
    """

    CATEGORIES = [
        "12V LiFePO4 battery", "inverter charger", "DC-DC charger", "MPPT controller",
        "solar panel", "fuse block", "distribution block", "battery cable lugs",
        "fresh water tank", "water pump", "tankless water heater", "12V fridge",
        "composting toilet", "RV shower pan", "roof fan", "12V air conditioner",
        "diesel air heater", "campervan window", "roof rack", "insulation",
        "baltic birch plywood", "t-slot aluminum extrusion", "cabinet latch",
        "push-fit plumbing fitting",
    ]

    def __init__(self):
        self.api_key = os.environ.get("VANBUILDER_SEARCH_API_KEY")
        self.endpoint = os.environ.get("VANBUILDER_SEARCH_ENDPOINT")
        if not (self.api_key and self.endpoint):
            raise NotConfigured(
                "LiveWebSource needs VANBUILDER_SEARCH_API_KEY and "
                "VANBUILDER_SEARCH_ENDPOINT. Falling back to the seed list. "
                "See discovery_sources.py for what 'finishing' live discovery requires."
            )

    # --- the three steps a finished implementation must provide ---------------
    def _search(self, category):
        """TODO: call the search API for `category`, return result URLs/snippets.
        Must rank by source kind (datasheet/manual/supplier > retailer > community)."""
        raise NotConfigured("search() not implemented — wire your search API here.")

    def _extract(self, result):
        """TODO: fetch the best (datasheet/manual) URL and extract structured
        specs into the candidate shape. Realistically an LLM call. Community
        sources must NEVER set specs — only popularity."""
        raise NotConfigured("extract() not implemented — wire datasheet parsing here.")

    def fetch(self):
        candidates = []
        for cat in self.CATEGORIES:
            for result in self._search(cat):
                candidates.append(self._extract(result))
        return candidates


def get_source(seed_fn):
    """Pick a source. Live if explicitly configured, otherwise the seed.

    Set VANBUILDER_DISCOVERY=live (plus the API env vars) to attempt live mode;
    anything else, or any failure, uses the seed."""
    mode = os.environ.get("VANBUILDER_DISCOVERY", "seed").lower()
    if mode == "live":
        try:
            return LiveWebSource()
        except NotConfigured as e:
            print("[discovery] live source not ready:", e)
    return SeedSource(seed_fn)
