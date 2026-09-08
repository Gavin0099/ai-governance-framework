"""P5 fixed local compatibility profile, not the canonical hook installer.

prepare writes a candidate hook/receipt to a NEW directory, never installs them.
An owner must explicitly supply the repository identity and adopted config hash.
verify runs before the unchanged 195a204f object-closure invocation. Receipts
detect accidental deployment drift; they are not signatures or OS trust roots.
Existing shell/Python/Git resolution and downstream governance are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path

GENERATION = '195a204f3e7e7d6055bc2293e0fe011c64285946'
SCHEMA = 'p5-pre-push-installation.v1'
TEMPLATE_SHA = '42db229b0461e5bdb6bdb09da4fc0ea49a073fd63a6639a22d2888372429a807'
SCANNER_SHA = 'f80b2ae95728b1468697de02c89cf7267fdde3c16d1705b7464160012dfabcb8'
SCANNER = 'governance_tools/external_tree_inventory_guard.py'
CONFIG = 'governance/external-tree-inventory-guard.json'
VERIFIER = 'governance_tools/pre_push_installation_integrity.py'
TEMPLATE = 'governance_tools/profiles/pre_push_195a204f.sh'
RECEIPT = 'p5-pre-push-receipt.json'
MARKER = b'if [ ! -f "$RUNTIME_SCRIPT" ]; then\n'


class InstallationMismatch(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode()


def unique(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise InstallationMismatch('duplicate JSON key')
        value[k] = v
    return value


def parse(raw):
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise InstallationMismatch('invalid JSON') from exc
    if type(value) is not dict:
        raise InstallationMismatch('JSON object required')
    return value


def canonical(path: Path) -> Path:
    absolute = path.absolute()
    if absolute.resolve(strict=True) != absolute:
        raise InstallationMismatch('path alias or substitution')
    for part in (absolute, *absolute.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise InstallationMismatch('linked installation path')
    return absolute


def read(path: Path) -> bytes:
    path = canonical(path)
    if not path.is_file():
        raise InstallationMismatch('regular file required')
    return path.read_bytes()


def validate_adoption(repository_id: str, config_sha256: str):
    if (not repository_id or repository_id.strip() != repository_id
            or not re.fullmatch(r'[A-Za-z0-9@:/._+\-]+', repository_id)
            or not re.fullmatch(r'[0-9a-f]{64}', config_sha256)):
        raise InstallationMismatch('explicit repository identity and adopted config digest required')


def render_hook(template: bytes, repository_id: str, config_sha256: str) -> bytes:
    validate_adoption(repository_id, config_sha256)
    if digest(template) != TEMPLATE_SHA or template.count(MARKER) != 1:
        raise InstallationMismatch('unsupported hook generation')
    # Quoted literals are adoption inputs, not selectors inherited from the env.
    preflight = '''# P5 fixed-generation installation check. Do not consume push stdin here.
P5_VERIFIER="$FRAMEWORK_ROOT/governance_tools/pre_push_installation_integrity.py"
if ! P5_REPOSITORY_ID="$(git -C "$TARGET_REPO_ROOT" config --get remote.origin.url)"; then
    governance_error "INSTALLATION_MISMATCH: repository origin unavailable"
    exit 1
fi
if ! "${PYTHON_CMD[@]}" -I -B "$P5_VERIFIER" verify \\
    --repo-root "$TARGET_REPO_ROOT" --framework-root "$FRAMEWORK_ROOT" \\
    --hook "$HOOK_DIR/pre-push" --receipt "$HOOK_DIR/p5-pre-push-receipt.json" \\
    --repository-id "$P5_REPOSITORY_ID" \\
    --expected-repository-id REPOSITORY_LITERAL --adopted-config-sha256 CONFIG_LITERAL; then
    governance_error "INSTALLATION_MISMATCH: fixed local profile rejected before closure scan"
    exit 1
fi

'''.replace('REPOSITORY_LITERAL', shlex.quote(repository_id)).replace('CONFIG_LITERAL', shlex.quote(config_sha256))
    return template.replace(MARKER, preflight.encode()+MARKER, 1)


def expected(repo_root: Path, framework_root: Path, repository_id: str, config_sha256: str):
    validate_adoption(repository_id, config_sha256)
    repo_root, framework_root = canonical(repo_root), canonical(framework_root)
    # This profile deliberately supports ordinary .git directories only. Shared
    # worktree hooks require a distinct installation design, not guessed roots.
    if not canonical(repo_root/'.git').is_dir():
        raise InstallationMismatch('ordinary repository .git directory required')
    config = read(repo_root/CONFIG)
    if digest(config) != config_sha256:
        raise InstallationMismatch('adopted identity config changed')
    value = parse(config)
    if (set(value) != {'schema', 'repository_identities'}
            or value['schema'] != 'external-tree-inventory-guard-identities.v1'
            or type(value['repository_identities']) is not list
            or any(type(v) is not str or not v.strip() for v in value['repository_identities'])
            or repository_id not in value['repository_identities']
            or '@repository-root' not in value['repository_identities']):
        raise InstallationMismatch('repository identity/config schema mismatch')
    scanner = read(framework_root/SCANNER)
    if len(scanner) != 27034 or digest(scanner) != SCANNER_SHA:
        raise InstallationMismatch('scanner generation mismatch')
    template = read(framework_root/TEMPLATE)
    hook = render_hook(template, repository_id, config_sha256)
    verifier = read(framework_root/VERIFIER)
    # Prevent generating a receipt for an arbitrary unrelated verifier.
    if verifier != read(Path(__file__)):
        raise InstallationMismatch('verifier deployment mismatch')
    receipt = dict(schema_version=SCHEMA, installer_generation=GENERATION,
        repository_id=repository_id, repo_root=str(repo_root), framework_root=str(framework_root),
        hook_sha256=digest(hook), scanner_sha256=SCANNER_SHA,
        identity_config_sha256=config_sha256, template_sha256=TEMPLATE_SHA,
        verifier_sha256=digest(verifier), authority='EXPLICIT_LOCAL_PROFILE_ONLY')
    receipt['receipt_sha256'] = digest(encode(receipt))
    return hook, receipt


def prepare(repo_root: Path, framework_root: Path, repository_id: str,
            adopted_config_sha256: str, output: Path):
    """Explicit preparation, no auto-discovery/adoption, no live hook writes."""
    hook, receipt = expected(repo_root, framework_root, repository_id, adopted_config_sha256)
    output = output.absolute()
    canonical(output.parent)
    # Never offer an accidental deployment mode through the candidate output.
    if output == repo_root.absolute()/'.git' or repo_root.absolute()/'.git' in output.parents:
        raise InstallationMismatch('prepare cannot write into target .git')
    output.mkdir(exist_ok=False)
    (output/'pre-push').write_bytes(hook)
    (output/RECEIPT).write_bytes(encode(receipt))
    return receipt


def verify(repo_root: Path, framework_root: Path, hook: Path, receipt: Path,
           repository_id: str, expected_repository_id: str, adopted_config_sha256: str):
    if repository_id != expected_repository_id:
        raise InstallationMismatch('wrong repository identity')
    # Read receipt first. Absence must stop rather than enroll the current state.
    value = parse(read(receipt))
    if (canonical(hook) != canonical(repo_root/'.git/hooks/pre-push')
            or canonical(receipt) != canonical(repo_root/'.git/hooks'/RECEIPT)):
        raise InstallationMismatch('unexpected installed hook/receipt placement')
    wanted_hook, wanted_receipt = expected(repo_root, framework_root, expected_repository_id, adopted_config_sha256)
    if value != wanted_receipt:
        raise InstallationMismatch('missing, stale or mismatched receipt identity')
    if read(hook) != wanted_hook:
        raise InstallationMismatch('installed hook changed')
    return wanted_receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for mode in ('prepare', 'verify'):
        p = commands.add_parser(mode)
        p.add_argument('--repo-root', type=Path, required=True)
        p.add_argument('--framework-root', type=Path, required=True)
        p.add_argument('--repository-id', required=True)
        p.add_argument('--adopted-config-sha256', required=True)
        if mode == 'prepare':
            p.add_argument('--output', type=Path, required=True)
        else:
            p.add_argument('--expected-repository-id', required=True)
            p.add_argument('--hook', type=Path, required=True)
            p.add_argument('--receipt', type=Path, required=True)
    args = vars(parser.parse_args(argv)); mode = args.pop('command')
    try:
        result = prepare(**args) if mode == 'prepare' else verify(**args)
    except (InstallationMismatch, OSError) as exc:
        print(json.dumps(dict(result='INSTALLATION_MISMATCH', reason=str(exc))))
        return 1
    print(json.dumps(dict(result='P5_PROFILE_PREPARED' if mode=='prepare' else 'P5_INSTALLATION_MATCH',
                         receipt_sha256=result['receipt_sha256'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
