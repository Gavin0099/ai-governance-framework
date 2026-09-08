# P5 fixed local pre-push installation profile

## Scope and authority

This capability supports only the compatible set derived from
`195a204f3e7e7d6055bc2293e0fe011c64285946`. It is not the repository-wide
canonical installer, a hook updater, or a migration of the historical installer.
The existing tracked installer and actual `.git/hooks` are not changed here.

The exact historical hook template is kept at
`governance_tools/profiles/pre_push_195a204f.sh` (SHA-256
`42db229b0461e5bdb6bdb09da4fc0ea49a073fd63a6639a22d2888372429a807`).
The only accepted scanner is 27,034 bytes, SHA-256
`f80b2ae95728b1468697de02c89cf7267fdde3c16d1705b7464160012dfabcb8`.
The profile does not install, modify, import, or canonically adopt that scanner.

## Explicit preparation, separate deployment

`governance_tools/pre_push_installation_integrity.py prepare` requires:

- `--repo-root` and `--framework-root`;
- `--repository-id`: explicitly adopted exact origin URL, also present in the config;
- `--adopted-config-sha256`: owner-selected exact bytes, not a hash discovered
  and automatically enrolled by the tool;
- `--output`: a new candidate directory outside the target `.git`.

Preparation checks the fixed template/scanner, config schema and repository
identity before creating the candidate directory. It writes only `pre-push` and
`p5-pre-push-receipt.json`. Reusing an existing output directory fails.
It does not fetch, change remotes, copy the scanner, generate identity-config,
replace installed hooks, or execute a scan.

An owner must separately authorize deployment of the reviewed candidate pair
into the target `.git/hooks`. Ordinary repositories with a real `.git` directory
are supported; shared worktree/gitfile and symlink/junction placements reject.
Deploying only one file leaves the installation rejected. No automatic recovery
or refresh occurs. A module/profile update also requires explicit re-preparation.

## Runtime behavior

The derived hook inserts one verification call before the historical closure
scan. The rest of the historical hook, including the exact scanner argv, stdin
updated-ref stream, rejection handling and downstream runtime checks, is retained.
The verifier does not consume stdin. It checks:

- exact installed hook bytes and placement;
- fixed template/scanner generation and digests;
- explicit config digest, supported schema and expected identity;
- actual origin identity supplied by the existing Git command path;
- receipt schema, root placement, verifier digest and receipt digest.

Missing, stale, extra-field, changed or wrong-repository records return
`INSTALLATION_MISMATCH` and stop before scanner invocation. A valid receipt only
permits the unchanged scanner to run; it does not assert that the pending closure
is safe. Scanner failure remains hook failure, including an inventory introduced
in history and deleted from the current worktree.

## Trust and claim boundaries

Receipt hashes detect accidental installation drift, not a hostile administrator
who can rewrite the hook, verifier and receipt together. They are not signatures
or proof of canonical repository adoption. The provided identity and config hash
are explicit local adoption inputs; syntactic acceptance alone is not authority.

The existing shell, Python helper and Git executable-resolution behavior remains
unchanged. P5 does not claim elimination of ambient runtime selectors, atomic
filesystem custody, race-free execution or P4 runtime-pin hardening. The added
verifier uses Python isolated mode and imports only the standard library.

Tests use isolated repositories, exact historical scanner bytes and the derived
hook. Downstream runtime smoke is a test sentinel; tests establish ordering and
closure preservation, not a live push or full installed governance validation.
No real repository deployment or push is included in this implementation slice.

## Test fixture provenance

The test-only scanner at `tests/fixtures/p5_pre_push_195a204f/external_tree_inventory_guard.py`
preserves the 27,034 exact bytes from the fixed source commit, SHA-256
`f80b2ae95728b1468697de02c89cf7267fdde3c16d1705b7464160012dfabcb8`.
Tests verify that digest before use. This keeps fresh checkouts independent of
unreachable historical Git objects; it is not a production scanner deployment.
