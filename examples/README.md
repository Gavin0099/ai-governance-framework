# Examples

This directory contains three different kinds of examples:

| Example | Status | What it is for | Runtime |
|---------|--------|----------------|---------|
| [todo-app-demo](todo-app-demo/) | Runnable demo | Minimal FastAPI app plus governance walkthrough | `fastapi`, `uvicorn` |
| [chaos-demo](chaos-demo/) | Walkthrough | Before/after narrative for architecture-boundary governance | No executable app |
| [usb-hub-contract](usb-hub-contract/) | Runnable contract sample | Minimal external domain contract with rules and validator | Python stdlib |
| [decision-boundary/minimal-preconditions](decision-boundary/minimal-preconditions/) | Minimal contract sample | First-slice DBL precondition example with deterministic verdict changes | Python stdlib |
| [starter-pack](starter-pack/) | Scaffold | Copy-ready governance starter files for a new repo | No executable app |

## Recommended Path

1. Start with [start_session.md](../start_session.md)
2. Run the minimal framework commands from the repo root
3. Run `python governance_tools/example_readiness.py --format human` to check the current example set
4. Open `todo-app-demo/` if you want a runnable application example
5. Open `usb-hub-contract/` if you want a domain-plugin example
6. Open `decision-boundary/minimal-preconditions/` if you want the smallest executable DBL precondition example
7. Open `chaos-demo/` if you want a short architecture-governance narrative
