# Obsidian Reviewer Guide (read-only navigation layer)

> **Status**: reviewer-convenience doc. **Authority: none.**
> **Source of truth: committed git files** (`PLAN.md`, `memory/`, `governance/`,
> `docs/`, `artifacts/governance/`). This guide changes no runtime, no memory
> writer, no memory protocol, no validator, and introduces no plugin dependency.
> Obsidian is a **derived view**; it is never a memory writer or a governance
> authority.

## What Obsidian is for here

The framework's memory is already plain markdown and already links with
`[[name]]` wikilinks. Obsidian is therefore a natural **read-only reviewer
navigation surface** over the existing committed files: backlinks, graph view,
search, and (optionally) Dataview dashboards.

It adds reviewer-orientation value (navigating the PLAN -> memory -> claim
boundary -> decision graph). It adds **no data-layer value** — memory already
exists, written canonically by `governance_tools.memory_record`.

## Safe usage rules (all required)

1. **Read only.** Use Obsidian to read `memory/`, `PLAN.md`, `governance/`,
   `artifacts/governance/`, `docs/`. Do **not** edit `memory/` in Obsidian.
2. **All memory writes stay canonical.** Every memory entry is written with
   `python -m governance_tools.memory_record`. Editing a memory file directly
   (in Obsidian or any editor) makes you a non-canonical writer and trips the
   memory authority guard / the P1-A CI blocker.
3. **`.obsidian/` is git-ignored** (added to `.gitignore`). Never commit vault
   config.
4. **Disable Obsidian auto-rename / auto link-update.** A rename refactor would
   silently rewrite every memory file referencing a name — a non-canonical batch
   mutation and exactly the silent drift the framework fights.
   (Settings -> Files & Links -> "Automatically update internal links" = OFF.)
5. **The view is derived, not authority.** Obsidian's graph / backlinks /
   Dataview output is computed from files. It must never be cited as evidence
   that a governance state is "done." The committed git state is the truth.
6. **No second memory.** Do not create `ObsidianMemory/`, `Daily Notes/`,
   Obsidian-template session logs, or let any plugin write frontmatter into
   memory files. One memory authority only.

## Recommended vault entry points

Opening the repo root as a vault is fine. Treat these as the primary surfaces:

- `PLAN.md` (canonical planning surface)
- `memory/` (canonical session-derived records + structured files)
- `governance/` (codices, contracts, decisions)
- `artifacts/governance/` (design docs, exports)
- `docs/` (specs, guides, playbooks)

## Do NOT

- Use Obsidian as a memory writer.
- Replace `memory_record` with Obsidian daily notes.
- Cite the Obsidian graph as "governance complete" evidence.
- Let a plugin auto-organize links / frontmatter.
- Commit `.obsidian/`.
- Commit Dataview query *output* as authority.

## Dataview dashboards (optional, derived-only) — read the format caveat first

> **IMPORTANT format caveat (verified 2026-06-18).** The example queries below
> assume each memory file exposes its fields as file-level frontmatter. The
> **actual** memory format is different: each daily file (`memory/YYYY-MM-DD.md`)
> contains **multiple** records as YAML *list items* (`- memory_type: ...` with
> nested `plan_reconciliation`, `next_step`, etc.), **not** a single `---`
> frontmatter block. Dataview reads file-level frontmatter / inline fields, so
> these queries will **not** capture per-record fields plug-and-play.
>
> Record-level querying would require either (a) reformatting records into
> inline `key:: value` fields or one-file-per-record — both of which are a
> **memory-protocol change and are out of scope / not done here** — or (b)
> accepting file-granularity results only. Treat the examples as illustrative of
> the *intent* (a deferred-debt / pending dashboard), not as working queries.

If a reviewer wants a local-only dashboard, create it as a personal note
(uncommitted, or under `docs/status/` clearly marked `derived view only`). For
example:

````markdown
# Obsidian Reviewer Dashboard
Status: derived view only | Authority: none | Source of truth: committed git

```dataview
TABLE plan_reconciliation, next_step
FROM "memory"
WHERE contains(string(plan_reconciliation), "deferred")
SORT file.name DESC
```
````

Until the format caveat above is addressed, the most reliable derived view in
Obsidian is **not** Dataview but the built-in **backlinks panel** and **graph
view** over the existing `[[name]]` links, plus full-text search for tokens like
`deferred:`, `Gate 3`, `NOT CLAIMED`.

## Claim ceiling

This guide supports only: using Obsidian as a read-only reviewer navigation
layer over committed files. It does **not** support: Obsidian as a memory
writer or authority; Dataview record-level querying on the current memory
format; any runtime / memory-protocol / validator change; or treating any
Obsidian view as governance evidence.
