# P5 fixed local pre-push installation profile

## Scope and authority

This capability supports only the compatible set derived from
`195a204f3e7e7d6055bc2293e0fe011c64285946`. It is not the repository-wide
canonical installer, a hook updater, or a migration of the historical installer.
The existing tracked installer and actual `.git/hooks` are not changed here.

This fixed local profile supports Windows only. `prepare` and `verify` reject
other platforms before reading deployment inputs or producing a candidate.
Linux Git 2.43 does not provide the object framing assumed by the frozen scanner;
Unix executable-mode deployment is not implemented or claimed. Receipt identity
validation alone does not qualify the Git/runtime combination. The actual
object-closure dry run remains required on the destination Windows installation.

The exact historical hook template is kept at
`governance_tools/profiles/pre_push_195a204f.sh` (SHA-256
`42db229b0461e5bdb6bdb09da4fc0ea49a073fd63a6639a22d2888372429a807`).
The only accepted scanner is 27,034 bytes, SHA-256
`f80b2ae95728b1468697de02c89cf7267fdde3c16d1705b7464160012dfabcb8`.
The profile does not install, modify, import, or canonically adopt that scanner.

The exact scanner is shipped as the immutable deployment asset
`governance_tools/profiles/external_tree_inventory_guard_195a204f.py`. Before
preparation, the owner must explicitly provision those bytes at
`<dedicated-framework-root>/governance_tools/external_tree_inventory_guard.py`
and verify the full digest above. Use a separate fixed-profile deployment root
containing this verifier, the template, and the existing required runtime tools;
do not overwrite a current canonical scanner from another generation. The
scanner asset is not automatically installed, selected, or adopted. A normal
checkout containing the current scanner is therefore not by itself a prepared
195a204f installation. The accepted deployment path and exact-byte validation
remain unchanged.

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

## Identity-config byte binding and line endings

`--adopted-config-sha256` is a digest of the **worktree bytes** of
`governance/external-tree-inventory-guard.json`, not of its Git blob. Git's
end-of-line normalization therefore changes the value the verifier computes: a
config authored with LF and adopted at an LF digest checks out as CRLF wherever
`core.autocrlf` converts it, and `verify` then reports
`adopted identity config changed` even though no one edited the file.

Because of that, the path is pinned verbatim in `.gitattributes`:

```gitattributes
/governance/external-tree-inventory-guard.json -text
```

`-text` places it with the other inputs verified by exact-byte digests, so the
blob bytes, the checked-out bytes and the adopted digest stay the same value on
every platform. Removing that entry, or reformatting the file, invalidates the
adopted digest and every receipt derived from it.

An adoption that exists only as an untracked local file is not durable. A pull
that starts tracking the same path replaces those bytes, and the installation is
rejected until the config is re-adopted. Keep the adopted identities in the
tracked config.

## Re-pinning after a legitimate config change

`verify` has no refresh path, so changing the adopted identities is an explicit
re-adoption. The content change and the re-pin are separate steps, and neither
is a licence to bypass a rejection:

1. Change `governance/external-tree-inventory-guard.json` in the tracked repo,
   preserving the schema and the previously adopted identities. The actual
   `remote.origin.url` of each installation that pushes must appear in
   `repository_identities`, together with `@repository-root`.
2. Record the new worktree digest, for example
   `python -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('governance/external-tree-inventory-guard.json').read_bytes()).hexdigest())"`.
   Confirm the file still has LF endings and that `git check-attr text <path>`
   reports `unset`.
3. Run `prepare` with `--adopted-config-sha256` set to that digest and
   `--output` pointing at a new candidate directory. `prepare` never installs.
4. Review the candidate `pre-push` and `p5-pre-push-receipt.json`, then deploy
   both into `.git/hooks` under explicit owner authorization. Deploying one file
   leaves the installation rejected.
5. Re-run `verify` and record the result as adoption evidence beside the
   previous record, rather than editing that record.

Each installation carries its own pin, so a config change is not complete until
every installation that pushes has been re-prepared and re-deployed.

## Framework root separation is a precondition, not advice

`verify` checks the scanner at
`<framework-root>/governance_tools/external_tree_inventory_guard.py` against the
frozen 195a204f digest. When `--framework-root` is the live repository checkout,
that path is also the repository's own evolving canonical scanner, so the
installation is rejected with `scanner generation mismatch` as soon as the
tracked scanner advances past the frozen generation. Provisioning the frozen
bytes over the tracked path hides the conflict instead of resolving it, and this
document already forbids overwriting a current canonical scanner from another
generation.

Point `--framework-root` at a dedicated fixed-profile deployment root holding
the frozen scanner, the template and the required runtime tools, and keep
`--repo-root` on the working checkout. If the frozen generation is no longer
wanted, retiring the 195a204f pin is its own authorized change, not a re-pin.
