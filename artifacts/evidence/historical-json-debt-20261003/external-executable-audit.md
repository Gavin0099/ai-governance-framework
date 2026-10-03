# Scoped subprocess audit

Authority: owner-requested repair of a reproduced Bookstore publication blocker.
This is an audit record, not an authenticated executable freeze or security gate.

| Active executable | Binding | Child environment | First effect | Evidence / limit |
| --- | --- | --- | --- | --- |
| Git hook Bash | Installed managed script; shell executable still ambient | Existing hook environment | Select target/framework, invoke scanner | Actual push fixture executes installed hook; no binary digest binding |
| Python selected by `scripts/lib/python.sh` | Existing configured/discovered command | Existing inherited Python environment | Import scanner, read private policy | No new interpreter selection introduced; no isolated-module or binary attestation claim |
| Scanner Git (`rev-parse`, `cat-file`, `rev-list`, `merge-base`) | Existing bare `git` name; PATH/PATHEXT still ambient | Inherited `GIT_*` stripped; explicit repo `-C`; global/system Git config suppressed; replacement objects disabled | Read repository metadata/object bytes, establish debt eligibility | Regression substitutes `GIT_DIR`, `GIT_WORK_TREE` and replace refs; real bad bytes remain blocked |
| Installer/manual publication verification | Existing local operator tools | Outside scanner runtime | Write private policy; verify remote baseline | Deployment must follow exact policy review and recorded authoritative remote response; not yet deployed |

Result: **ambient executable trust roots remain**. The patch protects object and
repository selection for the named regression cases; it does not bind executable
bytes/digests, remove PATH, authenticate hooks against a malicious local operator,
or prove every repository-local config and indirect launcher is immutable.

The policy is an explicit trusted operator setting outside the pushed tree.
Runtime does not consume production credentials or perform a production import.
No policy field, receipt, passing parser or test is treated as approval authority.
