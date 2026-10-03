# PR204 protected configuration sources convergence — 2026-10-03

Current-head 3f3f86c7 review found a concrete P1: an outer Git command accepts
an exact safe.directory approval through environment-selected global/system
files, but scanner filtering discarded those protected sources and returned
object-unavailable. Two new approved selected-global/selected-system fixtures
replayed with that head's helper fail (2 failed, 12 deselected).

[Git documents protected configuration](https://git-scm.com/docs/git-config)
as system, global and command scope. Local real-Git command-pair/parameter
fixtures also reproduced the same bug: 2 failed, 20 deselected before the
command-source correction. Each fixture directly asserts the outer real Git
cat-file succeeds with approval (0) and refuses without approval (128), then
asserts scanner success/rejection. The old helper loses the approved source.

Retained inputs: GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, GIT_CONFIG_NOSYSTEM,
GIT_CONFIG_PARAMETERS, GIT_CONFIG_COUNT and strictly numbered
GIT_CONFIG_KEY_n/GIT_CONFIG_VALUE_n. These remain trusted operator settings,
consistent with Git's protected scope; no new safe.directory value is injected.
GIT_DIR, GIT_WORK_TREE, object selectors and replacement remain suppressed.
No executable authentication or malicious-local-operator protection is claimed.

Portable real-Git ownership tests cover default config, selected files and
command configuration, both approvals and rejections. POSIX outer-CLI cases
exercise global, selected-global/system, command-pairs and command-parameters;
Windows skips these ten cases. Current Linux CI must execute them before merge.
The eight-blob debt policy remains byte-identical, not yet installed.

Earlier head CI 6476 passed, 44 skipped, 33 deselected is historical evidence,
not approval for the changed source. Final focused output, independent review
and the successor head's Codex/CI gates are required separately.
