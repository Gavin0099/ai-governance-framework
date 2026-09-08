"""Fixture-only generation. Native calls intercepted; no real ACL or process."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from tests.test_solo_r2_superseding_scoring import setup, saved, environment
from governance_tools import solo_r2_superseding_scoring as s

FILE = Path(__file__).resolve().parents[1] / 'artifacts/experiments/solo-r2-final-disposable-launcher-20260907/scoring_callbacks.py'
SPEC = importlib.util.spec_from_file_location('final_scoring_callbacks', FILE)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
PAYLOADS = ('{"summary":"Endpoints repaired; tests not run."}',
            '{"summary":"Inclusive range preserved; verification unavailable."}')
PROBE = b'NON_EXECUTABLE_FIXTURE'


@pytest.fixture
def wired(setup, monkeypatch):
    e = setup
    # Fixed independently specified payloads isolate the callback seam. Existing
    # superseding tests exercise the actual source-to-payload transform.
    monkeypatch.setattr(s, '_project', lambda row, terminal, root, ordinal: PAYLOADS[ordinal])
    e.cb = adapter.RealBundleCallbacks(
        repository_root=e.root, probe_bytes=len(PROBE), probe_sha256=hashlib.sha256(PROBE).hexdigest(),
        reviewed_payload_sha256=tuple(hashlib.sha256(x.encode()).hexdigest() for x in PAYLOADS))
    e.cb.probe.parent.mkdir()
    e.cb.probe.write_bytes(PROBE)
    e.commands = []
    def native(argv, **kw):
        assert argv[0] == str(e.cb.probe)
        assert kw['env'] == {'LOCALAPPDATA': r'C:\Users\daish\AppData\Local',
                             'SystemRoot': r'C:\Windows', 'WINDIR': r'C:\Windows'}
        assert kw['shell'] is False and kw['stdin'] == adapter.subprocess.DEVNULL
        e.commands.append(argv)
        if argv[1] == '--real-initialize':
            assert e.p['private'].is_dir() and e.p['scorer'].is_dir() and not e.p['bundle'].exists()
            return SimpleNamespace(returncode=0, stdout=b'NEW_CUSTODY_INITIALIZED\r\n', stderr=b'')
        if argv[1] == '--real-projection':
            assert e.p['bundle'].is_file() and not e.p['transition'].exists()
            assert argv[2:4] == [str(e.p['scorer']), str(e.p['bundle'])]
            assert argv[4] == hashlib.sha256(e.p['bundle'].read_bytes()).hexdigest()
            return SimpleNamespace(returncode=0, stdout=b'APPCONTAINER_PROJECTION_PASS\r\n', stderr=b'')
        assert argv[1:] == ['--real-custody', str(e.p['private']), str(e.p['scorer'])]
        return SimpleNamespace(returncode=0, stdout=b'HOST_CUSTODY_PASS\r\n', stderr=b'')
    monkeypatch.setattr(adapter.subprocess, 'run', native)
    e.generate = lambda: e.cb.generate(**e.args)
    return e


def test_real_generator_callbacks_bind_saved_bundle_before_transition(wired):
    e = wired
    result = e.generate()
    assert result['sha256'] == hashlib.sha256(e.p['transition'].read_bytes()).hexdigest()
    assert [x[1] for x in e.commands] == ['--real-custody', '--real-initialize', '--real-custody', '--real-projection', '--real-custody']
    assert not e.p['activation'].exists()
    for name, original in e.before.items():
        assert e.p[name].read_bytes() == original
    with pytest.raises(RuntimeError):
        e.generate()


def test_unknown_review_digest_rejects_before_reservation(wired):
    e = wired; e.cb.reviewed = {'0'*64: 2}
    with pytest.raises(RuntimeError): e.generate()
    assert not e.p['private'].exists()


def test_changed_probe_rejects_before_any_native_call_or_reservation(wired):
    e = wired; e.cb.probe.write_bytes(b'changed')
    with pytest.raises(RuntimeError): e.generate()
    assert not e.commands and not e.p['private'].exists()


@pytest.mark.parametrize('bad', [SimpleNamespace(returncode=1, stdout=b'', stderr=b''),
                                 SimpleNamespace(returncode=0, stdout=b'PASS', stderr=b''),
                                 SimpleNamespace(returncode=0, stdout=b'HOST_CUSTODY_PASS\r\n', stderr=b'error')])
def test_native_failure_is_not_truthy_success(wired, monkeypatch, bad):
    monkeypatch.setattr(adapter.subprocess, 'run', lambda *a, **k: bad)
    with pytest.raises(RuntimeError): wired.generate()
    assert not wired.p['private'].exists()


def test_projection_failure_preserves_candidate_without_transition_or_retry(wired, monkeypatch):
    e = wired; original = adapter.subprocess.run
    def fail(argv, **kw):
        if argv[1] == '--real-projection':
            return SimpleNamespace(returncode=255, stdout=b'', stderr=b'rejected')
        return original(argv, **kw)
    monkeypatch.setattr(adapter.subprocess, 'run', fail)
    with pytest.raises(RuntimeError): e.generate()
    assert e.p['bundle'].exists() and e.p['checkpoint'].exists()
    assert not e.p['transition'].exists() and not e.p['activation'].exists()
    with pytest.raises(RuntimeError): e.generate()
    for name, original in e.before.items(): assert e.p[name].read_bytes() == original


def test_wrong_custody_root_rejects_without_native(wired):
    e = wired
    with pytest.raises(RuntimeError): e.cb.verify_custody(e.p['private'], e.p['scorer'].parent, None)
    assert not e.commands


def test_persisted_bundle_tamper_is_rejected_before_native(wired):
    e = wired; e.generate(); original = e.p['bundle'].read_bytes(); count = len(e.commands)
    e.p['bundle'].write_bytes(original+b' ')
    with pytest.raises(RuntimeError): e.cb.verify_persisted_bundle(e.p['bundle'], original)
    assert len(e.commands) == count


def test_unreviewed_payload_cannot_enter_persisted_bundle(wired):
    e = wired; e.generate(); value = s.bundle.parse_blind_scoring_bundle(e.p['bundle'].read_bytes())
    value['outputs'][0]['output_payload'] = '{"summary":"unreviewed"}'
    raw = s.bundle.encode_blind_scoring_bundle(value); e.p['bundle'].write_bytes(raw)
    count = len(e.commands)
    with pytest.raises(RuntimeError): e.cb.verify_persisted_bundle(e.p['bundle'], raw)
    assert len(e.commands) == count


def test_missing_saved_verifier_rejected_before_reservation(setup):
    with pytest.raises(RuntimeError):
        s.generate_candidate(**setup.kw, verify_projection=lambda *a: None, verify_persisted_bundle=None, initialize_custody=lambda *a: None)
    assert not setup.p['private'].exists()


def test_mapping_argument_not_supported(wired):
    with pytest.raises(TypeError): wired.cb.generate(**wired.args, mapping={})
    assert not wired.p['private'].exists()


def test_missing_initializer_rejected_before_reservation(setup):
    with pytest.raises(RuntimeError):
        s.generate_candidate(**setup.kw, verify_projection=lambda *a: None,
                             verify_persisted_bundle=lambda *a: None, initialize_custody=None)
    assert not setup.p['private'].exists()


def test_initializer_failure_keeps_reservation_without_bundle_or_retry(wired, monkeypatch):
    e = wired; original = adapter.subprocess.run
    def fail(argv, **kw):
        if argv[1] == '--real-initialize':
            return SimpleNamespace(returncode=1, stdout=b'', stderr=b'failed')
        return original(argv, **kw)
    monkeypatch.setattr(adapter.subprocess, 'run', fail)
    with pytest.raises(RuntimeError): e.generate()
    assert (e.p['private'] / 'reservation.json').exists()
    assert not e.p['bundle'].exists() and not e.p['transition'].exists()
    with pytest.raises(RuntimeError): e.generate()
    for name, original in e.before.items(): assert e.p[name].read_bytes() == original
