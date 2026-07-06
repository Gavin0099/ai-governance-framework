# .latest-main Consumer Investigation (2026-07-06)

As-of: 2026-07-06
Scope: read-only investigation answering the inventory-artifact follow-up
"identify the consumer of the tracked .latest-main/ snapshot". No file is
removed, untracked, or changed by this note.

## What .latest-main Is

- A git-tracked snapshot of the framework repository inside itself:
  226 tracked files, about 9.2 MB on disk.
- Introduced 2026-04-17 by `fe073f7b` ("chore: record accounts and sync
  workspace updates"), initially as an accidental submodule entry that was
  flattened into tracked files at `758fe4ed` (2026-04-28). Last touched
  2026-04-28 (`f9153771`).
- Its embedded `PLAN.md` is dated 2026-04-16; the snapshot is a stale copy,
  not a maintained mirror.

## Consumer Search Result: no tool consumer exists

Tracked references to `.latest-main` outside the snapshot itself:

- `pytest.ini` `norecursedirs` - an exclusion workaround, not a consumer.
- `artifacts/evidence/external-verification-2026-07-05/*` and
  `docs/status/external-repo-live-verification-2026-07-05.md` - documented
  pollution instances: Enumd and Hearth language-pack scanners suggested a
  csharp pack based on `.latest-main` fixture files that travel with every
  embedded framework checkout.
- `commit-log.txt` and `docs/governance/decision-change-ledger.inventory.v0.1.json`
  - historical/scan records.

No governance_tools module, script, hook, CI step, or test reads
`.latest-main`. `external_repo_version_audit` and lock comparison use
`governance/framework.lock.json`, not this snapshot.

## Costs While It Stays Tracked

1. Every consumer repo that embeds the framework carries a stale 9.2 MB
   duplicate and gets language-pack signal pollution (observed in Enumd and
   Hearth on 2026-07-05).
2. Every repo-wide scan must special-case it (the 2026-07-06 inventory-line
   pass had to discount its hits; pytest needs `norecursedirs`).
3. It silently ages: a reader can mistake its 2026-04-16 PLAN and AGENTS
   content for current guidance.

## Related Finding: root workspace residue (same class)

`a9077454` (2026-03-16, "chore: add workspace bootstrap and generated
artifacts") tracked agent-workspace files at the repo root: `SOUL.md`,
`IDENTITY.md`, `USER.md`, `HEARTBEAT.md`, `TOOLS.md`, `start_session.md`,
`deploy_to_memory.sh`, `commit-log.txt`. These are session-bootstrap residue,
not framework surfaces. Note: `HEARTBEAT.md` and `TOOLS.md` were the
documented-surface evidence that kept `required_freshness_probe` off the
zombie list in the inventory pass; if they are residue, that classification
weakens to zombie_candidate and should be revisited in any cleanup slice.

## Disposition Options

1. Untrack `.latest-main/` (git rm -r --cached, add to .gitignore) and remove
   the `pytest.ini` special case. History keeps the snapshot; consumers stop
   inheriting it on their next framework update. RECOMMENDED.
2. Keep it tracked and teach consumer-side scanners to exclude embedded
   framework paths. Higher cost, keeps all three ongoing costs.
3. Do nothing. Costs continue to accrue silently.

The root workspace residue can ride the same hygiene slice (untrack, or move
to an untracked local directory), with the `required_freshness_probe`
reclassification recorded in the same commit.

## Claim Boundary

- This note proves no in-repo tool consumer exists at HEAD; it cannot prove
  no human workflow reads the snapshot manually.
- No removal is authorized by this investigation; a disposition decision is
  required first.
