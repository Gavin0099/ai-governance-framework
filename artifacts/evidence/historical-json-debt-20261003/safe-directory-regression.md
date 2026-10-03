# PR204 P1: preserve protected safe.directory — 2026-10-03

GitHub review of 6675932 identified that the new scanner environment erased
standard global/system configuration. Thus an operator-approved shared or
mounted checkout could run the outer Git push but fail the inner scanner.

The corrected helper still strips inherited GIT_* selectors and disables
replace objects; it preserves standard protected configuration. It adds no
safe.directory value, wildcard approval, or ownership bypass.

Failure-first replay: replace only `_git_environment` in memory with the
previous helper's GIT_CONFIG_NOSYSTEM=1 / GIT_CONFIG_GLOBAL=os.devnull settings,
then execute the approved-global real-Git regression. Result: 1 failed,
5 deselected in 1.04s, scanner returned 4 instead of required 0. Working tree
source was not reverted during this replay.

Corrected code: real-Git global/system approval and rejection cases pass.
Tests inject Git's test-only different-owner control after environment filtering
to reproduce actual ownership validation without privileged filesystem changes.
Two additional POSIX outer-CLI tests use an isolated fixture launcher; Windows
skips those cases, and Linux CI must execute them before merge.

Initial narrow run: 27 passed, 2 skipped (safe-directory plus historical-debt
tests). Full focused results and current-head CI remain separately recorded.
The tests are local fixtures; no credentials, production imports or remote
publication occur in these ownership tests. Ambient executable lookup/config
remains trusted; this is not an authenticated executable freeze.
