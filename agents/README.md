# Agents

Human-in-the-loop pipelines that keep the Parts DB complete and growing. Neither
agent invents data or overwrites verified specs. Full detail in
[../AGENT-WORKFLOW.md](../AGENT-WORKFLOW.md).

| Agent | Script | Output | Review surface |
|---|---|---|---|
| **Component Discovery** | `agents/discovery_agent.py` | `data/discovery-queue.json` | `app/discovery-queue.html` |
| **Sourcing / verification** | `scripts/build_sourcing_queue.py` | `data/sourcing-queue.json` | `app/sourcing-queue.html` |

The Sourcing Queue generator lives in `scripts/` because it is run the same way as
the other database builders, but it *is* the sourcing/verification agent: it reads
`parts-db.json` + `van-models.json` and detects every missing spec as a task. The
Discovery Agent lives here because it has its own multi-stage pipeline and a
human-gated `--apply` step that writes back to `parts-db.json`.

## Run

```bash
python3 agents/discovery_agent.py                    # build data/discovery-queue.json
python3 agents/discovery_agent.py --apply approvals.json   # merge approved (dry-run by default)
python3 scripts/build_sourcing_queue.py              # build data/sourcing-queue.json
```

`approvals.json` is produced by the "Export approved IDs" button in
`app/discovery-queue.html` and looks like `{ "approved": ["id", ...], "dry_run": true }`.
