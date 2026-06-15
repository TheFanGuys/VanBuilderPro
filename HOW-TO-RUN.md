# How to Run VanBuilder

Plain-English guide. No developer background assumed. This walks through what
actually works today, what to click, and what to type.

First, the honest summary:

- **The 3 viewers** (`van-picker.html`, `sourcing-queue.html`, `discovery-queue.html`)
  → double-click, open in a browser. **Work instantly, no install.**
- **The planner** (`VanBuilder.jsx`) → needs a place that can run React.
  Easiest today: the Claude app. Running it standalone is a developer task.
- **The scripts/agents** (the `.py` files) → need Python installed; you run them
  with a typed command. They rebuild the data files.
- **Nothing runs by itself.** There is no server and no schedule. The "agents" do
  their work only when you run them. And the discovery agent does **not** search
  the web yet — today it rebuilds a starter list I seeded by hand.

---

## 1. The easy part — open the three viewers

These are self-contained web pages. Nothing to install.

1. Unzip `vanbuilder.zip`.
2. Open the `app` folder.
3. Double-click any of these — they open in your normal web browser:
   - `van-picker.html` — browse the 59 van configurations.
   - `sourcing-queue.html` — the to-do list of missing specs.
   - `discovery-queue.html` — review discovered parts, Approve / Reject.

Your checkmarks and approvals are saved **in that browser on that device** (so
phone and laptop won't share them). That's normal for this stage.

---

## 2. The planner (VanBuilder.jsx)

This is the drag-and-drop floor-plan app. It's written in React, so it is **not**
a double-click file. Two ways to use it:

**Easiest (recommended): run it in the Claude app.**
Open the `VanBuilder.jsx` file with Claude (or paste its contents) and it renders
as a live app you can use right away. This is how you've been using it.

**Standalone (a developer job):**
To host it on its own, someone would set up a small React project (Vite + Tailwind
CSS + the `lucide-react` icon pack) and drop `VanBuilder.jsx` in. That's a couple
hours for a developer and not something you need to do to use the planner today.

---

## 3. The data and the scripts

The `data` folder holds four files that are the brains of everything:
`parts-db.json` (parts), `van-models.json` (vans), `sourcing-queue.json` and
`discovery-queue.json` (the two to-do lists). The scripts **rebuild** those files.

You only need this section if you want to change data or refresh the queues.

### One-time: install Python

- **Mac:** open the **Terminal** app, type `python3 --version`, press Enter. If you
  see a version number, you're set. If not, install it from python.org.
- **Windows:** open **Command Prompt**, type `python --version`. If missing,
  install from python.org and check "Add Python to PATH" during setup.

(On Windows, use `python` wherever this guide says `python3`.)

### Run a script

1. Open Terminal / Command Prompt.
2. Move into the project folder. Example:
   `cd Downloads/vanbuilder`
3. Run any of these (each prints one line and updates a file in `data/`):

```
python3 scripts/build_van_models.py        rebuilds data/van-models.json
python3 scripts/build_parts_db.py          rebuilds data/parts-db.json
python3 scripts/build_sourcing_queue.py    rebuilds the missing-spec to-do list
python3 agents/discovery_agent.py          rebuilds the discovered-parts list
```

Nothing installs, nothing connects to the internet — they just read and rewrite
the JSON files. If you edit a spec in `parts-db.json` by hand, re-run
`build_sourcing_queue.py` afterward to refresh the to-do list.

---

## 4. Approving discovered parts (the review loop)

This is how a found part actually becomes part of your catalog:

1. Open `app/discovery-queue.html`.
2. Click **Approve** on parts you trust (conflicts are locked until resolved).
3. Click **Export approved IDs** — it copies a little block of text.
4. Make a new file called `approvals.json` inside the `vanbuilder` folder and
   paste that text in. It looks like:
   `{ "approved": ["victron-orion-xs-50"], "dry_run": true }`
5. **Test first:** run `python3 agents/discovery_agent.py --apply approvals.json`.
   With `"dry_run": true` it only *shows* what it would do — nothing is written.
6. **Do it for real:** change `"dry_run": true` to `"dry_run": false`, save, and
   run the command again. Approved new parts are added to `data/parts-db.json`;
   verified specs are never overwritten, and conflicts are skipped.

> Reminder: discovery is **seeded** right now. Running the agent rebuilds the same
> 33 starter parts; it won't find anything new until the live web-search step is
> built (see PROJECT-STATUS, priority #4).

---

## 5. (Optional) Put it on GitHub

GitHub just **stores** the files — it doesn't run anything. Easiest way without
developer tools:

1. Make a free account at github.com.
2. Click **New repository**, name it `vanbuilder`, create it.
3. On the repo page, choose **uploading an existing file**, then drag in the
   **unzipped** `vanbuilder` folder's contents.
4. Click **Commit changes**.

That's it — your project is backed up and shareable. To run anything, you still
download it and follow the steps above.

---

## Reality check — what does NOT happen automatically

- No part of this runs on a schedule or in the background.
- The discovery agent doesn't browse the web yet (it's seeded).
- Queue checkmarks/approvals live in your browser, not a shared database.

Making it self-running (a hosted server + scheduled jobs + live web search) is a
real build that hasn't been done yet. Everything above is the project as it
honestly stands today: a tidy toolkit you run piece by piece.
