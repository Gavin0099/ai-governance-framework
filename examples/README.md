# Examples

This directory contains three different kinds of examples:

| Example | Status | What it is for | Runtime |
|---------|--------|----------------|---------|
| [todo-app-demo](todo-app-demo/) | Runnable demo | Minimal FastAPI app plus governance walkthrough | `fastapi`, `uvicorn` |
| [chaos-demo](chaos-demo/) | Walkthrough | Before/after narrative for architecture-boundary governance | No executable app |
| [usb-hub-contract](usb-hub-contract/) | Runnable contract sample | Minimal external domain contract with rules and validator | Python stdlib |
| [decision-boundary/minimal-preconditions](decision-boundary/minimal-preconditions/) | Minimal contract sample | First-slice DBL precondition example with deterministic verdict changes | Python stdlib |
| [decision-boundary/insufficiency-like-preconditions](decision-boundary/insufficiency-like-preconditions/) | Minimal boundary sample | Shows that the current first slice does not attempt to distinguish weak or irrelevant evidence | Python stdlib |
| [decision-boundary/adversarial-formal-presence](decision-boundary/adversarial-formal-presence/) | Limitation-demonstrating sample | Shows that formal presence can still satisfy the current first slice under semantically weak evidence | Python stdlib |
| [starter-pack](starter-pack/) | Scaffold | Copy-ready governance starter files for a new repo, with an opt-in upgrade path | No executable app |

## Recommended Path

1. Start with [start_session.md](../start_session.md)
2. Run the minimal framework commands from the repo root
3. Run `python governance_tools/example_readiness.py --format human` to check the current example set
4. Open `todo-app-demo/` if you want a runnable application example
5. Open `usb-hub-contract/` if you want a domain-plugin example
6. Open `decision-boundary/minimal-preconditions/` if you want the smallest executable DBL precondition example
7. Open `decision-boundary/insufficiency-like-preconditions/` if you want the smallest example of a current first-slice limitation
8. Open `decision-boundary/adversarial-formal-presence/` if you want the smallest formal-presence adversarial example
9. Open `chaos-demo/` if you want a short architecture-governance narrative
10. Open `starter-pack/` if you need the minimum governance scaffold and `upgrade_starter_pack` refresh path

## Important DBL framing

The `decision-boundary/insufficiency-like-preconditions/` example is a
limitation proof, not a capability proof.

A passing result there means only that the current first slice detected
explicit precondition presence. It does not mean the framework already performs
semantic adequacy or evidence-quality judgment.

The `decision-boundary/adversarial-formal-presence/` example goes one step
further: it shows that current first-slice `pass` results can still coexist
with semantically weak evidence when formal presence is satisfied.
