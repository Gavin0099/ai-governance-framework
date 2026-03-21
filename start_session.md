# Start Session

This file is the shortest path to seeing the framework produce real output.

## Prerequisites

- Python 3.10+
- `pip install -r requirements.txt`

If your Python interpreter is not on `PATH`, set `AI_GOVERNANCE_PYTHON` first.

PowerShell:

```powershell
$env:AI_GOVERNANCE_PYTHON='C:\Path\To\python.exe'
```

## Adopting the baseline into your repo (first-time setup)

If you want to apply this framework's governance baseline to a repo that already has
its own `PLAN.md`, `AGENTS.md`, or other governance files:

```bash
bash scripts/init-governance.sh --target /path/to/your/repo --adopt-existing
```

This copies `AGENTS.base.md` (protected), creates any missing files from template, and
records a `plan_section_inventory` of your existing PLAN.md structure — without
overwriting anything that already exists.

For a fresh repo (no existing governance files):

```bash
bash scripts/init-governance.sh --target /path/to/new/repo
```

After adoption, verify with:

```bash
python governance_tools/governance_drift_checker.py --repo /path/to/your/repo --framework-root .
```

When your repo's PLAN.md or other files change later, refresh the baseline hashes:

```bash
bash scripts/init-governance.sh --target /path/to/your/repo --refresh-baseline
```

---

## One-Command Smoke

If you want the shortest possible verification path, run:

```bash
python governance_tools/quickstart_smoke.py \
  --project-root . \
  --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

That command exercises both:

- a minimal `pre_task_check`
- a domain-aware `session_start`

## Step 1: Confirm the tools are available

```bash
python governance_tools/contract_validator.py --help
```

You should see the CLI help text.

## Step 2: Run a minimal governance check

```bash
python runtime_hooks/core/pre_task_check.py \
  --project-root . \
  --rules common \
  --risk low \
  --oversight review-required \
  --memory-mode candidate \
  --task-text "Quickstart governance check" \
  --format human
```

You should see a reviewer-first `summary=...` line and a successful pre-task result.

Because this repository intentionally contains multiple language fixtures and example stacks, seeing a few advisory pack-suggestion warnings at the repo root is normal.

## Step 3: Run a domain-aware session start

```bash
python runtime_hooks/core/session_start.py \
  --project-root . \
  --plan PLAN.md \
  --rules common,hub-firmware \
  --risk medium \
  --oversight review-required \
  --memory-mode candidate \
  --task-text "Validate USB hub firmware response flow" \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

This should show:

- the runtime contract
- proposal guidance
- contract context from `examples/usb-hub-contract`
- domain document injection

## Step 4: Optional runnable demo app

The repo includes a minimal FastAPI demo:

```bash
python examples/todo-app-demo/src/main.py
```

To run it as a local server:

```bash
uvicorn src.main:app --app-dir examples/todo-app-demo --reload
```

## Step 5: What to open next

- `README.md` for the overall architecture and entry points
- `python governance_tools/example_readiness.py --format human` to inspect the current example set
- `python governance_tools/trust_signal_overview.py --project-root . --plan PLAN.md --release-version v1.0.0-alpha --contract examples/usb-hub-contract/contract.yaml --format human` for a one-command adoption/release overview
- `examples/README.md` for runnable vs walkthrough examples
- `examples/usb-hub-contract/README.md` for the domain plugin path
