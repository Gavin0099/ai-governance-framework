# Historical JSON parse debt in pre-push

The default guard still scans every JSON blob in the per-ref newly reachable
object union. New refs include all ancestry. Bookstore-Scraper reproduced a
publication blocker: eight malformed export blobs containing merge conflict
markers already existed in its published main history, despite repaired current
exports. Deleting or repairing current files cannot change historical bytes.

An optional operator-installed policy acknowledges exact historical parse
failures without excluding any ancestry from inventory classification. This is
an explicit allowance for known historical bytes, not repair of those bytes.
No policy means the existing strict behavior. CI path scans remain strict.

## Installation authority

The sole policy location is `<git-common-dir>/hooks/external-tree-json-debt.json`,
alongside `ai-governance-framework-root`. The managed hook passes this fixed path
when present. The scanner rejects policy paths in the pushed working tree,
arbitrary alternative paths and policy symlinks. Worktree files cannot opt into
this allowance. The installed file is a trusted local operator input; anyone
able to rewrite local hooks can also rewrite it. This is not an OS security
boundary.

Installation requires all of these steps, in order:

1. Obtain independent review of the framework implementation and green PR
   checks before deploying it.
2. Review the exact policy bytes, every listed raw blob and its historical path.
   Bind the repository identity, full immutable baseline commit and policy
   SHA-256 to that review. Do not auto-generate approval from `approved=true`
   or a review-reference string inside the policy.
3. Independently verify that the baseline is published in the intended remote.
   For GitHub main, `gh api repos/OWNER/REPO/git/ref/heads/main --jq .object.sha`
   must return the exact baseline; record this response and policy digest.
   Local tracking refs alone do not prove publication. Runtime does not perform
   this remote verification or claim that a string proves human approval.
4. Deploy the reviewed managed hook/framework through the normal hook installer;
   install the reviewed policy bytes at the fixed private hook path. Record the
   selected framework commit and the installed policy digest. Preserve a prior
   policy for rollback; never merge unrelated allowances automatically.
5. Retry the original ordinary push with all hooks enabled. Removing the policy
   restores strict behavior. Never use remote branch seeding or `--no-verify`
   as an installation step.

The Bookstore repair is authorized by the owner's request to repair the observed
publication blocker. Its policy requires a separate exact-byte independent
review before local deployment; pending product files do not supply approval.

## Policy format and runtime checks

```json
{
  "schema": "external-tree-historical-json-debt.v1",
  "repository_id": "OWNER/REPO",
  "baseline_commit": "FULL_COMMIT_OID",
  "review_reference": "durable independent review reference",
  "blobs": [{"oid": "FULL_BLOB_OID", "path": "exports/latest/old.json"}]
}
```

Unknown fields, duplicate OIDs, wrong repository identity, invalid OIDs/paths,
empty review references and unreadable policies fail closed. Policies contain
1..100 exact entries. The baseline must resolve to an available commit ancestor
of every non-deletion pushed tip. Each listed OID/path must occur in its full
JSON history, and its raw bytes must still classify as `UNREADABLE`. A valid
external or unattributed inventory cannot be registered as parse debt.

The complete candidate closure is scanned as before. Only exact registered
unreadable blob bytes receive `ACKNOWLEDGED_UNREADABLE`. This status explicitly
reports the OID, observed path, baseline and review reference. All other
unreadable blobs, external inventories and unattributed inventories block. The
status acknowledges those same exact bytes if later reused; it does not authorize
other malformed bytes. A policy-baseline mismatch on a force-pushed branch fails
closed rather than silently dropping the policy.

Git object reads disable replacement objects and remove inherited Git
repository/object selectors, so an ambient repository selector or replace ref cannot change the
OID/baseline being assessed. Operator-controlled protected configuration is
preserved, including `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` and
`GIT_CONFIG_NOSYSTEM` selecting global/system sources, and command-scope
`GIT_CONFIG_PARAMETERS` / `GIT_CONFIG_COUNT` with numbered KEY/VALUE pairs.
These are Git's protected configuration inputs, including approved `safe.directory` exceptions for
shared repositories; no automatic wildcard or new safety approval is added.
See [Git's protected safe.directory configuration](https://git-scm.com/docs/git-config#Documentation/git-config.txt-safedirectory).
Executable names, PATH, shell/Python launchers and
repository-local Git config still have ambient trust roots. This patch does not
claim authenticated executable bindings or protection from a malicious local
operator. Publication and review remain explicit installation prerequisites.

## Verification

`python -m pytest tests/test_external_tree_inventory_guard.py
tests/test_historical_json_debt.py tests/test_hook_memory_policy.py -q`

The real Git push fixture first rejects a new ref with historical malformed
JSON, rejects a working-tree allowance, then accepts only the privately installed
historical allowance. It asserts the resulting remote ref and verifies that a
new malformed blob still prevents publication. Fixture setup is distinct from
the measured push, which always runs its installed hooks.
