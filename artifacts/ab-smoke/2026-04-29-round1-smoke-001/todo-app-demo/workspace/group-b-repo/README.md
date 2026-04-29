# Todo App Demo

This is the smallest runnable app example in the repository.

It exists to give new users a lightweight place to:

- see the framework next to a real app entrypoint
- verify that the documented Python dependencies are sufficient
- compare a normal demo app with the heavier governance examples

## Status

- Type: runnable demo
- Runtime dependency: `fastapi`
- Optional local server: `uvicorn`

## Files

```text
todo-app-demo/
├── PLAN.md
├── DEMO_LOG.md
├── memory/
└── src/
    └── main.py
```

## Run It

From the repo root:

```bash
python examples/todo-app-demo/src/main.py
```

That verifies the example imports cleanly.

To run it as a local API:

```bash
uvicorn src.main:app --app-dir examples/todo-app-demo --reload
```

Then open:

- `http://127.0.0.1:8000/health`

After installing `requirements.txt`, you can also validate the example through the shared readiness checker:

```bash
python governance_tools/example_readiness.py --strict-runtime --format human
```

## Read Next

- `DEMO_LOG.md` for the walkthrough
- [../../start_session.md](../../start_session.md) for the shortest repo-level quickstart
- [../../README.md](../../README.md) for the full framework overview
