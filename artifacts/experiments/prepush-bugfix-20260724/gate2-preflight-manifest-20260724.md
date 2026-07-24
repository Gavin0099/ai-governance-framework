# Gate 2 Preflight Manifest — pre-push bug four-arm pilot

Status: **answer-safe setup only.** This manifest records the Gate 2 preflight
steps that the design session may perform without touching answer production. It
does **not** start Gate 2, run any arm, or participate in scoring. Authority for
the protocol is amendment v2. Gate 2 still requires the remaining resource-gated
items below AND a separate explicit owner "start Gate 2" command.

## Done this session (answer-safe)

### Baseline bundle artifact (built + verified)
- Procedure (from amendment v2 Section A):
  `git update-ref refs/tmp/prepush-baseline 33006f09` →
  `git bundle create prepush-baseline-33006f09.bundle refs/tmp/prepush-baseline` →
  `git bundle verify` → `git update-ref -d refs/tmp/prepush-baseline`.
- `git bundle verify`: **okay; complete history.**
- Heads: exactly one — `33006f097597f5720a2d01661281d564fb2693ec  refs/tmp/prepush-baseline`.
- Design-env instance sha256:
  `6ad5bcca8cf4b743e1990310837097081a90bb65805f6cce698904baeb1cbe6e` (8.3 MiB).
- Reproducibility caveat: bundle bytes vary by git version; the authoritative
  invariant is single-head + complete-history, not this sha256. The 8.3 MiB
  binary is a build artifact and is intentionally **not** committed; the isolated
  run rebuilds it via the frozen procedure and re-verifies head/history.
- Contains the buggy hook at baseline but no Gate 0 analysis (all analysis commits
  postdate 33006f09), so the bundle itself does not leak the answer.

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

### Scorer anonymization handoff (frozen; amendment v2 Section G(d))
- Removes **identity labels only**, never substantive evidence. Redaction scope
  is frozen and mechanically replayable: remove ONLY the receipt `arm` field,
  packet filenames, and explicit treatment-assignment metadata via a fixed
  literal-token → placeholder map.
- **Preserved intact:** the raw code diff, tests, validator output, and completion
  claim — exactly what the scorer evaluates. Deleting any of these is prohibited.
- If the content itself lets a scorer infer the treatment, record
  `blinding_compromised: true` (with reason); do not hide it by deleting evidence.
- The scorer receives only the redacted output + the frozen rubric. The anon-ID →
  arm mapping is held solely by the experimenter, released only after both scorers
  finish; each redacted packet records the sha256 of its raw producer output.

## Remaining — resource-gated (NOT a place; see amendment v2 Section G table)

- [ ] Place the baseline bundle in an environment that technically cannot read
  this repo / current main / Gate 0 analysis / memory / this conversation
  (container, VM, Windows Sandbox, separate OS account, or a remote runner
  mounting only the bundle).
- [ ] Four such isolated producer contexts (one per arm).
- [ ] A primary blind scorer and a second semantic-claim scorer, both isolated
  and blind to arm identity and treatment labels; neither this design session
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
