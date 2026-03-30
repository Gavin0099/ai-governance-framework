# Start Session

This file is the shortest path to seeing the framework produce real output.

## Prerequisites

Verify your environment before running anything:

```bash
python governance_tools/adopt_governance.py --check-env
```

Expected output:

```
[OK]   Python 3.x available
[OK]   pyyaml installed
[OK]   pytest installed
```

If `python` is not found, try `python3` or `py`.

**If all three fail, stop here and choose a route:**

---

### Route A — tool-backed (normal path)

Python is available. Install dependencies and continue:

```bash
pip install -r requirements.txt
```

Then proceed to [Adopting the baseline](#adopting-the-baseline-into-your-repo-first-time-setup) below.

---

### Route B — no-Python onboarding evidence

> **Use only if `python`, `python3`, and `py` all return "command not found".**
> If any Python variant is available but failing for another reason (wrong PATH,
> missing package), fix that first. Route B does not produce a machine-verifiable
> artifact and cannot substitute for Route A when Python is reachable.

Python is completely unavailable in this environment.

Route B does not produce a tool-backed artifact. It produces a formal observation record instead — an evidence file that documents what you were able to verify without execution.

**This is not a workaround. It is a defined onboarding path for constrained environments.**

Steps:

1. Copy the template at [`docs/no-python-onboarding-evidence.md`](docs/no-python-onboarding-evidence.md)
2. Fill it in by reading the files it references — no execution required
3. Save your completed record as `docs/no-python-evidence-<YYYY-MM-DD>.md`
4. The completed file is your onboarding artifact for this environment

If you need a working Python installation:

- Windows: [python.org/downloads](https://python.org/downloads)
- macOS: `brew install python`
- Linux: `sudo apt install python3` or equivalent

---

## Adopting the baseline into your repo (first-time setup)

**Primary path (cross-platform, recommended):**

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo
```

This copies `AGENTS.base.md` (protected), creates any missing files from template, and
records a `plan_section_inventory` of your existing PLAN.md structure — without
overwriting anything that already exists.

After adoption, verify with:

```bash
python governance_tools/governance_drift_checker.py --repo /path/to/your/repo --framework-root .
```

When your repo's PLAN.md or other files change later, refresh the baseline hashes:

```bash
python governance_tools/adopt_governance.py --target /path/to/your/repo --refresh
```

**Fallback path (if Python is unavailable — bash/Linux/macOS only):**

```bash
bash scripts/init-governance.sh --target /path/to/your/repo --adopt-existing
```

The bash script covers the same adoption flow. Use it only if Python is not available
in your environment. On Windows, use the Python path above.

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
