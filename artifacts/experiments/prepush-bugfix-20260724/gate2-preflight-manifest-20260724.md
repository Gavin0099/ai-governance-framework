# Gate 2 Preflight Manifest — pre-push bug four-arm pilot

Status: **answer-safe setup only.** This manifest records the Gate 2 preflight
steps that the design session may perform without touching answer production. It
does **not** start Gate 2, run any arm, or participate in scoring. Authority for
the protocol is amendment v2. Gate 2 still requires the remaining resource-gated
items below AND a separate explicit owner "start Gate 2" command.

## Done this session (answer-safe)

### Baseline bundle artifact (built + verified — CORRECTED procedure)
- Corrected procedure (amendment v2 Section A; the old `refs/tmp/*` bundle cloned
  EMPTY):
  `git branch -f prepush-baseline 33006f09` →
  `git bundle create prepush-baseline-33006f09.bundle prepush-baseline` →
  `git bundle verify` → `git branch -D prepush-baseline`; clone with
  `git clone -b prepush-baseline …`.
- `git bundle verify`: **okay; complete history**, one head
  `33006f097597…  refs/heads/prepush-baseline`.
- **Real clone check (was missing before):** `git clone -b prepush-baseline` →
  non-empty, HEAD == 33006f09, 3664 files, buggy hook present.
- Design-env instance sha256:
  `da1a47d735a32433dff2ed2be0aeda2e287686a750187a0ba4d6c22ed559f5e7` (8.3 MiB).
  Bytes vary by git version; authoritative invariant is single-head +
  complete-history + non-empty clone. Binary not committed (rebuilt in the run).
- Verified in a real Docker container (`--network=none`, bundle-only mount): host
  repo unreachable, network blocked, answer analysis absent.
- **Open (Finding 2):** the full 33006f09 tree still carries `memory/`, `PLAN.md`,
  the program/gate docs, and `artifacts/ab-*`, which leak the experimental frame
  (not the answer). A producer-checkout denylist must be frozen before Gate 2.

### Frozen execution order
- `random.seed(20260724); random.sample(['A','B','C','D'], 4)` → **[D, C, A, B]**.

### Packet hashes (re-verified against amendment v2)
| File | sha256 | Arms |
|---|---|---|
| arm-dispatch-packet.md | 59ef5915bccf09eb6a5c7a344412d512415eb6e8fab0c83e7f122612a3b822a8 | A/B/C/D |
| skill-packet-bugfix.md | f2c6862f70d2db0d2268b20d956a90fada4687cceab6d5ef07fd6553f2e75b14 | B/C/D |
| governance-packet.md | f6dfe7268851b59717405550c39502a76774165a1b35ee9c9e056506c79bdc28 | C/D |
| validator-pins.md (producer-safe) | 6ea4b3226a3f54dce265ad27a67209b9d803b27d690cc4d899d20fff9a7f2d5f | D |
| validator-expectation-DESIGNER-ONLY.md (withheld) | dcff3d2d0d3f02f4ef57283718c61b5fe890e54b109b90be05b68d7a25fb52c6 | none (designer/scorer) |

### Validator install spec (pins verified real)
- `pip install ruff==0.6.9 mypy==1.11.2` (ruff 0.6.9 confirmed present on PyPI).
- shellcheck 0.10.0 (release binary) — install in the run environment.
- Installation belongs in the isolated producer/scorer environment, not this
  design session; recorded here as a frozen requirement.

### Frozen policy (values stamped at dispatch)
- Identical model build across all four arms; 60 tool calls / 30 min per arm.
  **Non-treatment** tool permissions identical across arms; **Arm D's
  treatment-time validator feedback is the pre-registered treatment exception**,
  not a permission difference to be equalized away. The uniformity of
  non-treatment permissions is the frozen guarantee; concrete build/permission
  strings are stamped identically at dispatch.

### Producer receipt template (raw, producer-side)
- `gate2-producer-receipt-template.json` — raw producer-side, NOT scorer-facing.
  The producer fills linked_commit, timestamps, command, output_artifacts,
  results, and an experimenter-only `arm` field.

### Scorer anonymization handoff — executable contract
- Frozen as `scorer-handoff-contract.json` (`gate2-scorer-handoff.v1`): the fixed
  `raw-output.txt` section order; the 11-rule literal redaction map (identity /
  packet / assignment tokens only) with case + `\s+` + basename rules; the
  anonymous-ID algorithm (`OUT-` + sha256(raw bytes)[:12], full sha256 recorded,
  16-hex collision rule); the `blinding_compromised` determination (experimenter,
  per output, flagged not deleted); and the scorer blinding-check fields
  (`suspected_treatment` / `confidence` / `reason` recorded before mapping release).
- Preserved intact (never redacted): FIX_DIFF, TEST_LOG, VALIDATOR_OUTPUT. Only
  COMPLETION_CLAIM free text and receipt metadata are redacted.

## Remaining — resource-gated (NOT a place; see amendment v2 Section G table)

- [ ] Place the baseline bundle in an environment that technically cannot read
  this repo / current main / Gate 0 analysis / memory / this conversation
  (container, VM, Windows Sandbox, separate OS account, or a remote runner
  mounting only the bundle).
- [ ] Four such **answer-blind** producer contexts (one per arm) — blind to the
  root cause/fix, but each knows its own treatment.
- [ ] Two **arm-identity-blind** scorers (primary + semantic-claim second scorer),
  isolated and not knowing the A/B/C/D mapping before scoring; neither this design
  session
  nor the author.
- [ ] Install the pinned validators in that environment.
- [ ] Stamp the actual model build, permissions, and per-arm dispatch record.
- [ ] Separate explicit owner "start Gate 2" command.

## Cannot claim

- That Gate 2 is ready (resource-gated items remain) or may start (needs the
  separate owner command).
- That the design-env bundle is an isolated run environment — it is a verified
  build artifact only.
- That any arm has run or that the Skill is effective.
