# Remaining Work

An honest, complete list of what's left to build for VanBuilder, grouped by goal.
Each item is tagged with effort (**S**mall / **M**edium / **L**arge) and what it
actually *needs* — because some items are code, but others are money, accounts,
or decisions only you can make.

> First, what's genuinely **done**: the planner, both databases, the live axle
> math, the sourcing agent (self-healing gap detection), and the discovery
> agent's full pipeline (extract → verify → normalize → merge → human-gated
> apply) with 38 real seeded candidates. See PROJECT-STATUS.md.

---

## A. Make the agents fully autonomous (the big gap)

This is what "finish the agents so they just work" really means. The logic is
done; these are the missing pieces.

| # | Item | Effort | Needs | Status |
|---|---|---|---|---|
| A1 | **Live discovery search** — replace the seed with real web search per category | **L** | a search-API account + key (paid or free-tier), network access, and a spec-extraction step (realistically an LLM/Anthropic-API call, which also costs money) | 🟡 scaffold in place (`agents/discovery_sources.py`); not functional without the above |
| A2 | **Datasheet spec extraction** — read a manufacturer PDF/page and pull structured numbers | **L** | an LLM API key + budget, or hand-written per-site parsers (fragile) | not started; this is the hard part of A1 |
| A3 | **Scheduling / automation** — run the agents on their own (nightly, etc.) | **M** | a place to run them: a free GitHub Action or a small server/cron. A laptop that's sometimes off won't cut it | not started — nothing runs on a schedule today |
| A4 | **Conflict-resolution workflow** — today conflicts just block; add a way to pick existing-vs-discovered and record the decision | **S–M** | code only | not started |

**Bottom line:** making discovery "live and automatic" is mostly *not* more code —
it's a search-API account, an LLM budget, and a place to run it. Those are your
calls. The code seam to plug them into is built.

---

## B. Finish the data (no new features — sourcing + verification)

This is the highest-value, lowest-tech work. It's what makes the existing
features light up. Almost all of it is data entry / verification, tracked in the
sourcing queue.

| # | Item | Effort | Needs |
|---|---|---|---|
| B1 | **Van weights** — fill GVWR / GAWR / curb-by-axle / axle-offset across trims (345 tasks) | **M** ongoing | order guides, door-jamb stickers, corner-scale weights |
| B2 | **Component specs + sources** — clear the 48 component tasks (mostly verification + source URLs) | **S–M** ongoing | datasheets; then flip `verified` |
| B3 | **Approve discovery candidates** — merge trusted finds into `parts-db.json` | **S** | review in the Discovery Queue, run `--apply` |

Unlocks: live axle math on every trim you fill (B1), and a fully-verified parts
catalog (B2–B3).

---

## C. Finish the planner (features that were frozen)

| # | Item | Effort | Needs |
|---|---|---|---|
| C1 | **One catalog everywhere** — migrate `VanPartsDB.jsx` to read `data/parts-db.json` | **S** | code |
| C2 | **Real wire sizing** — run-length-based gauge + voltage-drop checks (Spec §4.4) using actual layout distances, not nominal gauges | **M** | code |
| C3 | **Plumbing routing** — model line runs + fittings, not just tanks/fixtures | **M–L** | code |
| C4 | **Exports** — printable BOM, cut sheets, wiring schedule | **M** | code |
| C5 | **Conflict/where-used view** — see every build a part is in before changing it | **S** | code |

---

## D. Make it a real hosted product (beyond single files)

| # | Item | Effort | Needs |
|---|---|---|---|
| D1 | **Host the planner** — stand `VanBuilder.jsx` up as its own website (Vite + Tailwind) so it runs outside the Claude app | **M** | a developer + hosting (e.g. Netlify/Vercel, often free tier) |
| D2 | **Shared saving** — replace per-device `localStorage` (check-offs/approvals) with a small backend so state syncs across devices | **M–L** | a developer + a hosted database |
| D3 | **Accounts + saved builds** — let users save and reload layouts | **L** | full app work; only if this becomes a product |

---

## E. Repo / quality polish (before a public GitHub push)

| # | Item | Effort | Needs |
|---|---|---|---|
| E1 | **LICENSE file** — pick a license (MIT is common) | **S** | a decision |
| E2 | **Automated tests + CI** — lock in the pipeline behavior so changes don't silently break it | **M** | a developer |
| E3 | **README screenshots / demo** | **S** | screenshots |

---

## Suggested order

1. **B1–B3** — fill data; it makes what you already have noticeably better and
   needs no developer.
2. **C1** — unify the catalog (small, removes the last duplicate data path).
3. **A3 + A4** — decide where agents run and add conflict resolution; this gets
   the *sourcing* agent running on its own (no paid APIs needed).
4. **A1–A2** — only when you're ready to pay for a search API + LLM budget; this
   is the real "self-discovering" upgrade.
5. **C2–C4 / D / E** — features and productization, as the project warrants.

Nothing here is required to *use* VanBuilder today — it already works piece by
piece (see HOW-TO-RUN.md). This is the map for turning a working toolkit into a
self-running product.
