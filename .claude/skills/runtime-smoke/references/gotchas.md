# Gotchas

- `quickstart_smoke.py` is the best first check for onboarding-path drift, not the deepest runtime check.
- `smoke_test.py` and `dispatcher.py` support contract-aware overrides; do not hand-edit example payloads unless you truly need a custom event.
- When only `--contract` is supplied, path inference can change `project_root` and `plan_path` behavior. Be explicit if the result looks surprising.
- A failing shell wrapper path does not automatically mean the underlying Python entrypoints are broken. Confirm whether the failure is wrapper-only.
- Treat wrapper smoke, direct smoke, and dispatcher replay as different surfaces. A regression in one does not prove all three are broken.
