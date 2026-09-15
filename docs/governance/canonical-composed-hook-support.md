# Canonical composed-hook support (H1)

This is a bounded compatibility adapter for the Lenovo consumer's existing
install-time composition. It is not a hook plugin interface or a generic
composition declaration format.

## Accepted declaration

The reviewed source is `lenoveo-isp-tool-avalonia` commit
`3a4278c4bd2a18548b4920f2e999372be1834d44`:

- `scripts/hooks/install-governance-hooks.ps1`
- `wire-pre-push-memory-quality.ps1`
- `scripts/hooks/pre-push.memory-quality.fragment.sh`

The adapter pins the LF-normalized SHA-256 of these three files. Fixture copies
under `tests/fixtures/lenovo_composed_hook/` preserve their complete reviewed
content. All three, and the referenced `validate-memory-quality.ps1`, must be
regular in-repository files whose worktree and index content match HEAD. The
gate script remains consumer-owned; this change neither rewrites it nor
certifies its behavior. Unsupported declaration revisions fail closed and need
a separate compatibility review, not an automatic plugin discovery path.
Presence of any of the three profile paths enters this validation, including
an unrecognized installer without its wire or fragment; it cannot fall back to
raw hook installation.
Consumer HEAD/index comparison also disables replacement objects; a local
replacement ref cannot hide a declaration that is uncommitted against real HEAD.
HEAD and index are also checked when the worktree profile is absent. Sparse or
unstaged/staged removals cannot silently downgrade a tracked profile to raw hooks.

No consumer script is executed while recognizing the declaration. In a repo
without the declaration, the existing raw-framework-hook path remains valid.

## Comparison and installation

Before F-7 changes the framework checkout, its mutation guard reconstructs the
expected pre-push from the **current base** plus the committed fragment. It
compares the entire installed content, ignoring CRLF versus LF only. A marker
alone is never sufficient; missing extensions and unknown extra content fail.

After the checkout advances, both F-7's internal hook writer and the standalone
installer construct the **new base** plus the same declared fragment. The
complete file is written to a sibling temporary file and replaced atomically.
The old hook remains if preparing or replacing the file fails. No intermediate
raw pre-push is installed. This is a per-hook-file guarantee, not a transaction
over the entire F-7 update or all configuration files.

The standalone installer also accepts an older complete composition only when
it exactly matches a pre-push blob reachable from the selected framework
checkout's `HEAD`, composed with the currently verified fragment. It does not
search unrelated branches, execute historical hooks, or accept a consumer's
claim about its old base. This allows direct upgrades without running F-7's
writer first. Missing history (for example a source archive or shallow clone
without the old blob) remains a refusal; obtain the matching framework history
before retrying. Unknown edits, removed extensions and dirty declarations are
still rejected before hook installation begins.
For a declared profile, existing pre-push symlinks, including dangling links,
are refused and left untouched rather than replaced by the installer.
Historical traversal includes merged side histories and disables Git replacement
objects, so local replacement refs cannot substitute unrelated content for HEAD.
It also ignores legacy graft files, including an inherited `GIT_GRAFT_FILE`.
Committed sources must have regular-file modes in both HEAD and the stage-zero
index; equal blob bytes do not authorize a symlink-to-regular-file type change.
Local provenance queries clear inherited `GIT_*` environment overrides and use
the explicitly selected repository, so alternate indexes or Git directories
cannot substitute another source of authority. Git still uses the selected
checkout's own on-disk repository data and ordinary configuration.
Deletion commits contain no hook candidate and are skipped; earlier reachable
blobs remain eligible after a delete/re-add cycle.

The declared insertion is before the unique structured-memory anchor. A
standalone terminal `exit 0` is the supported fallback; an ambiguous or absent
insertion point is rejected rather than guessing a place that may skip gates.

Repeated install leaves an already identical hook untouched. Existing F-7
receipt, dirty-tree, authorization and parent-commit gates still apply to a
second F-7 run; H1 does not make an uncommitted update globally idempotent.

## Evidence boundaries

The focused tests check full payload matching, missing/unknown changes,
declaration provenance, base updates, unchanged repeat install and replacement
failure. Shell replay checks independent framework and extension rejection;
the PowerShell stand-in is explicitly a fixture and does not certify the
consumer's memory-quality validator internals.

Formal disposable-consumer replay additionally exercises F-7 and the original
tracked installer. Passing those checks does not establish fleet-wide adoption,
M1 completion-state behavior, or permission to push a consumer.
