# 快取感知權威清單 implementation tech-spec - 2026-06-29

狀態（Status）：`PENDING`
範圍（Scope）：docs-only implementation tech-spec
執行環境行為（runtime behavior）變更：否
工具行為（tooling behavior）變更：否
測試行為（test behavior）變更：否
CI 行為（CI behavior）變更：否
基準檔（baseline file）變更：否
強制執行（enforcement）變更：否
提示快取實作（prompt cache implementation）：否

## 問題

快取感知（cache-aware）文件已把 `AUTHORITY_MANIFEST v1` 列為第一個
repo-feasible 落地候選。但目前 repo 已經有 `.governance/baseline.yaml`
與 `governance_tools/governance_drift_checker.py` 這條權威基準與 drift
檢查路徑。

若直接新增一個獨立 `AUTHORITY_MANIFEST` 產生器，容易產生第二套權威清單：

- `.governance/baseline.yaml` 記錄一份權威檔案與 hash；
- `AUTHORITY_MANIFEST v1` 又記錄另一份權威檔案與 hash；
- reviewer 不知道哪一份才是 authority source。

這份 tech-spec 的目的，是先把 implementation tranche 的邊界寫清楚：
未來若實作，只能 reuse / extend 既有 baseline + drift checker path，
不得建立平行權威。

## Current Repository Truth

已確認的 repo 事實：

- `.governance/baseline.yaml` 由 `governance_tools/adopt_governance.py`
  寫入，檔頭明列：
  - `PROVENANCE`：基準來源與 commit；
  - `INTEGRITY`：`sha256.*` 與 `overridable.*`；
  - `CONTRACT`：由 drift checker enforce 的 governance mandates；
  - `OBSERVED`：採用或 refresh 時觀察到的 repo 結構。
- `.governance/baseline.yaml` 已記錄：
  - `sha256.AGENTS.base.md`
  - `sha256.PLAN.md`
  - `sha256.contract.yaml`
  - `sha256.AGENTS.md`
  - `plan_section_inventory`
  - `contract_required_fields`
- `governance_tools/governance_drift_checker.py` 已讀取 baseline 並消費：
  - `baseline_yaml_present`
  - `source_commit_recorded`
  - `protected_files_unmodified`
  - `plan_inventory_current`
  - `contract_required_fields_present`
- `governance_tools/adopt_governance.py --refresh` 已是 baseline refresh path：
  它會重算 tracked hashes 與 `plan_section_inventory`。
- `docs/governance/cache-aware-authority-manifest-invalidation-spec-2026-06-28.md`
  定義的是 proposed `AUTHORITY_MANIFEST v1` shape；它明確不能宣稱工具已產生
  `AUTHORITY_MANIFEST v1`。
- `docs/governance/cache-aware-runtime-adoption-review-packet-2026-06-28.md`
  把第一個 repo-side tranche 限定為：
  `AUTHORITY_MANIFEST generator + authority-change invalidation signal`。
- 目前 root `.github/workflows/governance.yml` 沒有直接執行
  `governance_drift_checker.py`；只有 `baselines/repo-min/.github/workflows/governance-drift.yml`
  是 consuming repo 的 baseline workflow template。
- 最新 read-only drift check 輸出顯示 baseline/protected/hash/inventory checks
  可執行；當時唯一 warning 是 `PLAN.md` freshness。

因此，最小 named consumer 是：

```text
governance_tools/governance_drift_checker.py
```

不是新的 CI workflow，也不是新的 runtime hook。

## Target Outcome

若 reviewer 後續批准 implementation，第一個實作 tranche 應提供：

- 一個 read-only `AUTHORITY_MANIFEST v1` candidate generator；
- 一個 read-only authority-change invalidation helper 或 report；
- focused tests 覆蓋 baseline reuse、hash stability、dynamic field handling、
  and invalidation semantics；
- 文件上保留 `repo_enforces_prompt_cache: false` 與 detection/accountability
  claim ceiling。

本 tech-spec 本身只定義上述目標，不實作。

## Scope

本 docs-only slice 只新增本 tech-spec：

- `docs/governance/cache-aware-authority-manifest-implementation-tech-spec-2026-06-29.md`

未來 implementation tranche 若另行批准，建議允許的實作範圍是：

- `governance_tools/authority_manifest.py` 或等價單一 read-only module；
- `tests/test_authority_manifest.py` 或等價 focused test file；
- 必要時，更新既有 cache-aware docs 的 claim ceiling 語句。

未來 implementation tranche 不應自動包含 CI、runtime hook、schema 或
baseline writer 改動。

## Non-Goals

本 slice 不做：

- 不修改 `governance_tools/`；
- 不修改 `tests/`；
- 不修改 `runtime_hooks/`；
- 不修改 `.github/workflows/`；
- 不修改 `.governance/baseline.yaml`；
- 不修改 `PLAN.md`；
- 不寫 memory；
- 不 push；
- 不新增 prompt cache implementation；
- 不新增 cache hit/miss monitoring；
- 不新增 runtime enforcement；
- 不新增 mode/auth/tool-denial/compaction receipt tooling；
- 不把 `AUTHORITY_MANIFEST v1` 升格成 canonical authority；
- 不聲稱外部 harness 已採用本 repo 的 cache-aware specs。

## Affected Surfaces

本 slice 直接影響：

- `docs/governance/cache-aware-authority-manifest-implementation-tech-spec-2026-06-29.md`

未來 implementation 可能影響，但本 slice 不授權修改：

- `governance_tools/governance_drift_checker.py`
- `governance_tools/adopt_governance.py`
- `.governance/baseline.yaml`
- `.github/workflows/governance.yml`
- `baselines/repo-min/.github/workflows/governance-drift.yml`
- `runtime_hooks/**`
- `schemas/**`
- `tests/**`

## Boundary And API Considerations

### Reuse / Extend Rule

`AUTHORITY_MANIFEST v1` must be derived from existing baseline truth where possible.

Allowed source mapping:

| Manifest concept | Existing source to reuse |
| --- | --- |
| repo baseline provenance | `.governance/baseline.yaml` `source_commit`, `initialized_at`, `initialized_by` |
| protected authority hashes | `.governance/baseline.yaml` `sha256.*` plus `overridable.*` |
| observed PLAN inventory | `.governance/baseline.yaml` `plan_section_inventory` |
| enforced contract mandates | `.governance/baseline.yaml` `contract_required_fields` and future explicit CONTRACT fields |
| current invalidation signal | `governance_drift_checker.py` check results |

Not allowed:

- independent hard-coded authority file list that disagrees with baseline;
- independent hash semantics that reviewer must reconcile manually with baseline;
- generated artifact that claims to replace `.governance/baseline.yaml`;
- manifest status that implies prompt cache enforcement.

### Proposed Read-Only CLI Shape

If later implemented, the CLI should be explicit and side-effect free:

```powershell
python -m governance_tools.authority_manifest `
  --project-root . `
  --base-ref <ref> `
  --head-ref <ref> `
  --format json
```

Optional later extension:

```powershell
python -m governance_tools.authority_manifest `
  --project-root . `
  --compare-baseline `
  --format human
```

The default mode must write to stdout only. Any file output must require an
explicit `--output` path in a separately reviewed tranche.

### Suggested Output Fields

The candidate output should preserve the existing cache-aware shape while making
baseline reuse visible:

```text
AUTHORITY_MANIFEST v1
repo:
base_ref:
head:
generated_at:
generated_by:
baseline_source:
  path: .governance/baseline.yaml
  source_commit:
  baseline_version:
authority_files:
  - path:
    baseline_hash:
    current_hash:
    overridable:
    loaded_as:
    invalidates_cache_on_change:
checks:
  governance_drift_checker:
    severity:
    checks:
manifest_hash:
harness_dependent: true
repo_enforces_prompt_cache: false
```

`generated_at` is dynamic-tail metadata. It must not affect stable authority
source hash comparisons.

### Minimum Named Consumer

The named consumer is:

```text
governance_tools/governance_drift_checker.py
```

The manifest should consume or summarize drift checker semantics rather than
forcing reviewers to compare two independent authority systems.

If a future reviewer requires CI as consumer, that is a separate scope expansion
and must be reviewed as CI behavior change.

## Failure Paths Or Risk Points

1. Parallel authority
   - Risk: `AUTHORITY_MANIFEST v1` duplicates baseline and becomes a competing
     authority map.
   - Required boundary: manifest is derived/reporting surface only.

2. Evidence for evidence's sake
   - Risk: generator exists but no tool or reviewer surface consumes it.
   - Required boundary: first consumer is `governance_drift_checker.py` output
     semantics or a named reviewer-facing command.

3. Dynamic-tail pollution
   - Risk: `generated_at`, current user DONE, or dirty-tree state changes
     stable hash.
   - Required boundary: dynamic fields are excluded from stable source hashing.

4. CI scope creep
   - Risk: adding workflow integration turns a docs/tooling tranche into
     delivery or enforcement behavior.
   - Required boundary: CI consumer is not part of first tranche.

5. Enforcement overclaim
   - Risk: authority-change invalidation signal is described as prevention or
     prompt-cache enforcement.
   - Required boundary: detection/accountability only.

6. Baseline writer mutation
   - Risk: first tranche edits `adopt_governance.py` or rewrites baseline.
   - Required boundary: first tranche reads existing baseline only.

## Evidence Plan

For this docs-only tech-spec:

- `git diff --check -- docs/governance/cache-aware-authority-manifest-implementation-tech-spec-2026-06-29.md`
- sub-agent read-only review of this spec

For a future implementation tranche, minimum evidence should include:

- focused unit tests for manifest field presence;
- fixture test showing baseline `sha256.*` values are reused or clearly mapped;
- fixture test showing authority file content changes alter current hash or
  invalidation status;
- fixture test showing `generated_at` does not alter stable source hashes;
- focused test that `governance_drift_checker.py` remains the named consumer or
  semantic source for invalidation status;
- CLI smoke with explicit `--project-root` and `--format json`;
- overclaim scan confirming no prompt-cache enforcement, provider cache
  visibility, or prevention-grade claim.

## Implementation Tranche Recommendation

Recommended next action after this spec is reviewed:

```text
needs high-rigor review before implementation
```

If a future implementation review approves, the first implementation tranche should be:

```text
Implement read-only authority manifest generator that derives from
.governance/baseline.yaml and summarizes governance_drift_checker.py
invalidation semantics.
```

Allowed implementation files for that future tranche:

- one new `governance_tools/authority_manifest.py`;
- one new focused `tests/test_authority_manifest.py`;
- optional docs wording update limited to claim ceiling and command examples.

Forbidden in that future first tranche unless separately authorized:

- CI workflow wiring;
- runtime hook wiring;
- baseline writer changes;
- `.governance/baseline.yaml` rewrite;
- prompt cache behavior;
- receipt tooling beyond this manifest;
- memory write behavior;
- cross-repo writes.

## Claim Ceiling

This tech-spec may claim only:

- the implementation boundary for `AUTHORITY_MANIFEST v1` has been proposed;
- current repo truth shows `.governance/baseline.yaml` and
  `governance_drift_checker.py` are the existing baseline/drift path;
- the proposed first implementation tranche must reuse or extend that path;
- the named consumer is `governance_drift_checker.py`;
- future validation requirements are listed.

This tech-spec must not claim:

- `AUTHORITY_MANIFEST v1` is implemented;
- drift is fixed;
- prompt cache is implemented;
- cache hit/miss is monitored;
- runtime enforcement exists;
- CI validates the manifest;
- external harness adopts the manifest;
- B implementation is authorized.

## Review Questions

Reviewer should answer:

1. Does this spec correctly prevent `AUTHORITY_MANIFEST v1` from becoming a
   parallel authority map?
2. Is `governance_drift_checker.py` an acceptable minimum named consumer for the
   first implementation tranche?
3. Are CI workflow changes correctly excluded from the first tranche?
4. Are claim ceilings bounded to detection/accountability only?
5. Are the future allowed files narrow enough for a focused implementation slice?
