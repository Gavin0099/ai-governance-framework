---
name: fwupd-upstream-pr-gate
description: End-to-end fwupd upstream development lifecycle (G0-G5): SPEC & scope boundaries, risk-based gate escalation, upstream architecture/PoC first, Core-vs-Product PR splitting, -Dwerror=true + ASan/LSan validation, SHA-bound independent review, and four-layer PASS separation.
---

# fwupd Upstream Development & PR Gate (G0–G5, v1.0)

Use this skill for `fwupd/fwupd` plugin work, new hardware/model support, core bugfixes, or upstream PR preparation.

## Global Invariant — Owner Gate (MUST, Applies Across All Stages G0–G5)

At **every** stage (G0 through G5), explicit owner approval is mandatory before any:
- `git push` / `--force-with-lease` / branch deletion
- Opening, editing, or closing any PR, or posting any public GitHub comment
- Physical hardware flashing or irreversible device/firmware operation
- Disclosing any customer internal specification, firmware binary, or hardware log externally

## Risk-Based Gate Escalation (MUST)

Select **Light Path** vs **Full Path** strictly by **behavioral impact and safety risk**, never by line count:
- **Light Path (Brief Scope/Boundary/Risk Check → G3 → G4):** Docs, typos, formatting, `static` / `-Wmissing-prototypes` fixes, mechanical equivalent API swaps (e.g. `g_bytes_get_size()`), or adding a quirk using already-supported mechanisms. MUST still briefly confirm Scope, Regression Boundary, and Risk classification before editing (never skip impact confirmation).
- **Full Path (G0 → G5):** Even a **1-line change** touching Flash, Bank selection, ISP, Reset/Replug, HID Proxy pairing, Parent/Child topology, `CompositeId`, update ordering, customer safety guards, new plugin flags/quirk keys, or `fwupd` Core APIs/lifecycle.
- **Mandatory Escalation:** If a Light Path task uncovers architecture ambiguity, safety risk, or a generic `fwupd` Core bug, MUST immediately escalate to the Full Path.

## G0. SPEC & Scope Boundary Gate (MUST)

- **Original SPEC & RTM:** Read the original customer SPEC directly (never rely solely on secondary summaries) and build a Requirement Traceability Matrix (RTM) citing exact sections/lines.
- **Scope & Regression Boundary:** Before editing code, explicitly define: (1) in-scope changes, (2) out-of-scope / untouched areas, (3) safety invariants of existing products, and (4) non-target legacy device compatibility. Do not expand scope to solve side issues.
- **SPEC vs. Implementation Separation:** Keep mandatory customer requirements separate from specific C functions, flags, or quirk keys. Maintain strict priority: **(1) Customer SPEC mandatory safety/functional requirements → (2) `fwupd` upstream architecture & maintainability → (3) Minimal plugin implementation**.
  - Never treat a maintainer's simplification suggestion as authorization to relax customer SPEC.
  - Never claim an alternative upstream architecture is equivalent by static code reading alone; MUST prove equivalence via positive, negative, missing-requirement, wrong-topology, timing (e.g. `setup` vs pre-write), and bypass-flag (`--force`, `--ignore-requirements`) tests.

## G1. Upstream Architecture & Responsibility Gate (MUST)

- **Upstream API First:** Before writing custom code, inspect `upstream/main` APIs, flags, quirks, metadata, and sibling plugins (e.g. `AUTO_PARENT_CHILDREN`, `fu_firmware_write()`, `g_bytes_get_size()`, `fu_byte_array_to_string()`). Do not reimplement framework features or bypass private `libfwupdplugin` APIs (e.g. `g_object_set()` on hidden properties).
  - *Exception:* Temporary plugin fallback is allowed ONLY when a confirmed core limitation is reproduced and tracked in a dedicated upstream bugfix PR with an explicit migration plan once merged.
- **Responsibility Separation:** Every new mechanism MUST justify its layer:
  - **Core (`libfwupdplugin`/`src/`):** Device lifecycle, Parent/Child, `CompositeId`, ordering, emulation, common chunk/transport APIs.
  - **Metadata (CAB/LVFS):** Product matching, GUIDs, `<requires>` parent/version constraints, release info.
  - **Plugin (`plugins/*`):** IC protocol, HID/USB transport, Flash, ISP, Bank safety, firmware format, mandatory hardware safety guards.
  - **Quirks (`*.quirk`):** Per-model VID/PID, HID Proxy ID, `RemoveDelay`, declarative flags.
- **Maintainer Communication (SHOULD, under Owner Gate):** For new Core APIs, lifecycle/ordering changes, new plugin-specific quirk keys, or SPEC-vs-upstream conflicts, prepare a concise proposal (minimal repro, actual vs expected, code evidence, non-negotiable safety invariants, alternatives) for owner approval before posting. Never disclose unauthorized customer internal specs, binaries, or logs.

## G2. Minimal PoC & Core/Product Split Gate (MUST)

- **PoC Before Workarounds:** For any architectural uncertainty or suspected Core bug, build a minimal PoC first using generic `FuDevice`/`FuBackend`/`FuEngine` objects (zero vendor plugin or customer data dependency) on clean `upstream/main` and save the raw failing log.
- **Core Bugfix vs. Product PR Splitting:** Submit generic Core bugs as small, single-purpose standalone upstream PRs; rebase and simplify the product PR only after the Core PR merges.
- **Adopt Better Maintainer Solutions:** Never cling to a custom fix; if the maintainer proposes a cleaner upstream PR, validate it with the full regression suite and close the superseded PR once verified.

## G3. Minimal Implementation & Layered Testing Gate (MUST)

- **Clean Implementation:** Keep each PR single-purpose and bisectable (no "add then delete" noise commits). Avoid magic-number firmware builders (**SHOULD** add setters/writer support and test `fu_firmware_write()` → `fu_firmware_parse_bytes()` round-trips).
- **Production / Test Separate Evaluation:** Always report production code and test code diff stats separately; do not use total line count as a quality metric, and **SHOULD** reuse existing test helpers.
- **Layered Test Ownership & Regression Preservation:** Place tests in their proper layer:
  1. **Plugin self-test:** Parser/writer, protocol, bank, and hardware safety guards.
  2. **Core regression (`src/`):** Only for actual Core behavior or Core bugfixes.
  3. **Internal regression (local backup branch):** Full customer SPEC matrix & large product synthetic tests. Removing tests or metainfo XMLs from an upstream PR MUST NOT reduce local coverage — overlay-run them against the **latest production code**.
  4. **LVFS emulation:** Real hardware capture/replay.
  5. **Hardware acceptance:** Physical flashing on the target commit.
- **Pre-Push Validation:** MUST pass **`-Dwerror=true -Db_sanitize=address`** (ASan + LSan, zero warnings/leaks), `python3 contrib/ci/check-source.py`, `clang-format --dry-run --Werror`, and verified plain `git config --local user.name`/`user.email` (never alter other contributors' authorship).

## G4. Upstream PR & Independent Review Gate (MUST)

- **Maintainer-Oriented Independent Review:** Never rely solely on self-review or bare CI PASS. Run independent sub-agents in isolated contexts/worktrees covering as applicable: (1) **Upstream Maintainer Quality** (API idioms, encapsulation, magic numbers, redundant params, GLib/GError lifecycle, legacy compatibility), (2) **Core Repro/Architecture**, (3) **Safety & Overlaid Regression** (exact test counts, never bare PASS), and (4) **Customer SPEC Compliance** (RTM against original SPEC). Parent agent MUST cross-verify all findings (no majority vote).
- **Final HEAD Independent Review Gate:** Review evidence MUST bind to an **exact commit SHA**, never a branch name. Any logic edit or `git commit --amend` invalidates prior review for push authorization and requires an independent **Delta Review** on the exact final HEAD **before** pushing.
  - *Exception:* Pure commit-message typo amendments may skip logic re-review ONLY when author, commit message, final SHA, identical tree OID (`git diff <reviewed_sha> <new_sha>` empty), and evidence binding are all explicitly verified. This exception MUST NOT be applied to rebases or upstream base/dependency changes.
- **Review Stop Condition:** Once all required gates pass with zero unresolved `P0`/`P1`/`P2` issues, **freeze the version** and stop; restart review only on new code changes, maintainer feedback, or SPEC changes.

## G5. Acceptance, Persistent Evidence & Owner Gates (MUST)

- **Persistent Evidence:** Save raw reproduction logs, regression logs, patches, and RTM tables outside temporary `/tmp` worktrees before cleanup.
- **Four-Layer PASS Separation:** Strictly report four layers separately (never conflate or promote one into another):
  1. **Local test PASS** (`-Dwerror=true` + ASan/LSan + overlaid tests)
  2. **Upstream CI PASS** (GitHub Actions matrix on the PR)
  3. **Formal governance PASS** (R2 canonical closeout; report `UNSUPPORTED / NOT PERSISTED` honestly when unavailable)
  4. **Real hardware acceptance PASS** (physical flashing & post-update verification on the target commit)
- **Owner Gate Enforcement:** Re-verify Global Invariant Owner Gate approvals before any external release, PR action, or hardware acceptance run.
