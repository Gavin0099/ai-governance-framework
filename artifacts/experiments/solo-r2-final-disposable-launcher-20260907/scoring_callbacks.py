"""Fixed final-run adapter; importing it never generates or launches anything.

The owner/controller supplies the independently pinned probe identity and two
payload digests from complete semantic review. Hash matching is delivery proof,
not an automated substitute for that review. Only newly reserved instance ACL initialization; no parent/history ACL mutation or activation.
"""
from collections import Counter
from pathlib import Path
import subprocess

from governance_tools import solo_r2_superseding_scoring as scoring


_ENV = {
    'LOCALAPPDATA': r'C:\Users\daish\AppData\Local',
    'SystemRoot': r'C:\Windows',
    'WINDIR': r'C:\Windows',
}


def _digest(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        scoring._fail()
    return value


class RealBundleCallbacks:
    """One generation only; all real execution still needs owner authorization."""

    def __init__(self, *, repository_root, probe_bytes, probe_sha256, reviewed_payload_sha256):
        self.root = Path(repository_root)
        self.paths = scoring._paths(self.root)
        self.probe = self.paths['base'] / 'scorer-isolation-probe-1/Probe.exe'
        if type(probe_bytes) is not int or probe_bytes <= 0:
            scoring._fail()
        self.probe_bytes = probe_bytes
        self.probe_sha256 = _digest(probe_sha256)
        if type(reviewed_payload_sha256) is not tuple or len(reviewed_payload_sha256) != 2:
            scoring._fail()
        self.reviewed = Counter(_digest(x) for x in reviewed_payload_sha256)
        self.projected = None
        self.used = False

    def _native(self, arguments, expected_output):
        # Exact fixed executable, argv, environment; no PATH/shell/helper fallback.
        raw = scoring._raw(self.probe)
        if len(raw) != self.probe_bytes or scoring._sha(raw) != self.probe_sha256:
            scoring._fail()
        result = subprocess.run(
            [str(self.probe), *arguments], cwd=str(self.probe.parent),
            env=dict(_ENV), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=40, shell=False, check=False,
        )
        if result.returncode != 0 or result.stdout != expected_output or result.stderr:
            scoring._fail()
        if scoring._raw(self.probe) != raw:
            scoring._fail()

    def verify_custody(self, private, scorer, boundary):
        expected = scoring.crypto.CustodyBoundary(
            self.root, *(self.paths['base']/n for n in ('consumer','materialization','execution','scoring')))
        if private != self.paths['private'] or scorer != self.paths['scorer'] or boundary != expected:
            scoring._fail()
        self._native(['--real-custody', str(private), str(scorer)], b'HOST_CUSTODY_PASS\r\n')

    def initialize_custody(self, private, scorer, boundary):
        expected = scoring.crypto.CustodyBoundary(
            self.root, *(self.paths['base']/n for n in ('consumer','materialization','execution','scoring')))
        if private != self.paths['private'] or scorer != self.paths['scorer'] or boundary != expected:
            scoring._fail()
        self._native(['--real-initialize', str(private), str(scorer)], b'NEW_CUSTODY_INITIALIZED\r\n')

    def verify_projection(self, payloads):
        # Complete semantic review is supplied as independent expected identities.
        # Existing structural leakage checks remain additional guards.
        if self.projected is not None or type(payloads) is not tuple or len(payloads) != 2:
            scoring._fail()
        if any(type(p) is not str or scoring.bundle._contains_scorer_forbidden_identity(p) for p in payloads):
            scoring._fail()
        if Counter(scoring._sha(p.encode('utf-8')) for p in payloads) != self.reviewed:
            scoring._fail()
        self.projected = Counter(payloads)

    def verify_persisted_bundle(self, path, generated_bytes):
        if path != self.paths['bundle'] or type(generated_bytes) is not bytes or self.projected is None:
            scoring._fail()
        value = scoring.bundle.parse_blind_scoring_bundle(generated_bytes)
        if value['evaluation_id'] != scoring.EVALUATION or value['pair_id'] != scoring.PAIR:
            scoring._fail()
        if Counter(x['output_payload'] for x in value['outputs']) != self.projected:
            scoring._fail()
        # Expected digest derives from generator-produced bytes, not this readback.
        if scoring._raw(path) != generated_bytes:
            scoring._fail()
        digest = scoring._sha(generated_bytes)
        self._native(['--real-projection', str(self.paths['scorer']), str(path), digest],
                     b'APPCONTAINER_PROJECTION_PASS\r\n')
        if scoring._raw(path) != generated_bytes:
            scoring._fail()

    def generate(self, *, git, repository, temp_root):
        if self.used:
            scoring._fail()
        self.used = True
        return scoring.generate_candidate(
            git=git, repository=repository, temp_root=temp_root,
            verify_custody=self.verify_custody, verify_projection=self.verify_projection,
            verify_persisted_bundle=self.verify_persisted_bundle, initialize_custody=self.initialize_custody,
        )
