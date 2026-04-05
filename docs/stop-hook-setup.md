# Stop Hook Setup

Configure Claude Code to automatically call `session_end_hook` when a session ends.

This enforces session closeout at the runtime level — not dependent on AI compliance.

---

## Global hook (applies to all repos)

Edit `~/.claude/settings.json` (Windows: `C:\Users\<you>\.claude\settings.json`):

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m governance_tools.session_end_hook --project-root \"${workspaceFolder}\" --format human"
          }
        ]
      }
    ]
  }
}
```

**Note:** `${workspaceFolder}` resolves to the current project root in Claude Code.
The hook runs in the framework repo's working directory — if you run this from an
external repo, change `--project-root` to the consuming repo path.

---

## Per-repo hook (if different repos need different project roots)

For a consuming repo that has adopted governance, add a `.claude/settings.json`
in that repo:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python -m governance_tools.session_end_hook --project-root \"${workspaceFolder}\" --format human",
            "cwd": "<path-to-ai-governance-framework>"
          }
        ]
      }
    ]
  }
}
```

Replace `<path-to-ai-governance-framework>` with the absolute path to this repo.

---

## What the hook does

1. Reads `${workspaceFolder}/artifacts/session-closeout.txt`
2. Classifies the closeout artifact (valid / missing / insufficient)
3. Calls `session_end.py` regardless of classification
4. Produces `artifacts/runtime/verdict/` and `artifacts/runtime/trace/` artifacts
5. Updates memory if closeout is valid and policy is AUTO_PROMOTE

**The hook always runs.** A missing or invalid closeout does not abort — it
produces a degraded verdict that records the gap.

---

## What the AI must do before session ends

Before the stop hook fires, the AI must write `artifacts/session-closeout.txt`.

See [docs/session-closeout-schema.md](session-closeout-schema.md) for required fields.

If the AI does not write the file, the hook still runs and records `closeout_missing`
in the verdict. Memory will not update, but the gap is recorded and auditable.

---

## Verifying the hook works

After configuring, end a session. Then check:

```bash
# Should show a recent session artifact
ls artifacts/runtime/verdicts/

# Read the latest verdict
python -c "
import json, pathlib, os
d = pathlib.Path('artifacts/runtime/verdicts')
latest = max(d.glob('*.json'), key=os.path.getmtime)
v = json.loads(latest.read_text())
print('decision:', v['verdict']['decision'])
print('closeout_status:', v.get('evidence_summary', {}).get('check_keys'))
"
```

A verdict with `closeout_missing` means the hook ran but the AI did not write
the closeout file. This is the expected degraded state, not a hook failure.
