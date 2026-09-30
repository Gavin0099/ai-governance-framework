"""Subprocess acceptance tests for the inactive trust chain, without live services."""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "governance_tools/required_memory_bootstrap.py"
LAUNCHER = ROOT / "governance_tools/required_memory_launcher.py"


def inline_source(binding):
    return BOOTSTRAP.read_text(encoding="utf-8") + "\nrun(" + repr(binding) + ")\n"


def powershell_command(source):
    quote = lambda text: "'" + text.replace("'", "''") + "'"
    return "& " + quote(sys.executable) + " -I -B -c " + quote(source)


PAYLOAD = b'{ "hook_event_name":"Stop", "session_id":"probe-session", "turn_id":"probe-turn", "stop_hook_active":false }\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


@pytest.fixture
def deployment(tmp_path):
    root = tmp_path / "candidate with spaces"
    root.mkdir()
    (root / ".governance").mkdir()
    (root / ".codex").mkdir()
    (root / "memory").mkdir()
    launcher = root / "launcher.py"
    launcher.write_bytes(LAUNCHER.read_bytes())
    # This independently authored spy records actual dispatch and exact stdin.
    handler = root / "handler.py"
    handler.write_bytes(
        b"import json,sys\nfrom pathlib import Path\n"
        b"Path('dispatch.stdin.bin').write_bytes(sys.stdin.buffer.read())\n"
        b"print(json.dumps({'candidate_dispatched': True}))\n"
    )
    checker = root / ".governance/check-fwupd-container-prereq.ps1"
    checker.write_bytes(b"# Offline identity-only checker; never invoked by these tests.\n")
    contract = root / ".codex/memory-obligation-contract.json"
    contract.write_text(json.dumps({
        "event_id": "OFFLINE-DELIVERY-001", "dependency": "offline-prerequisite",
        "event_type": "required_dependency_blocked", "event_status": "blocked",
        "approved_producer": {"path": ".governance/" + checker.name,
                              "sha256": sha(checker.read_bytes()), "blocked_exit_code": 42},
        "plan_risk_headings": ["Risks"],
    }), encoding="utf-8")
    binding = {
        "launcher_path": str(launcher), "launcher_sha256": sha(launcher.read_bytes()),
        "delivery_root": str(root), "repo_root": str(root), "event": "stop",
        "handler": {"path": "handler.py", "sha256": sha(handler.read_bytes())},
        "checker": {"path": ".governance/" + checker.name, "sha256": sha(checker.read_bytes())},
        "contract": {"path": ".codex/" + contract.name, "sha256": sha(contract.read_bytes())},
    }
    return root, binding


def execute(binding, payload=PAYLOAD):
    process = subprocess.run(
        [sys.executable, "-I", "-B", "-c", inline_source(binding)],
        input=payload, capture_output=True, timeout=40,
    )
    assert process.returncode == 0, process.stderr
    assert process.stderr == b"", process.stderr
    return json.loads(process.stdout)


@pytest.mark.parametrize("event", ["stop", "post-tool-use"])
@pytest.mark.parametrize("fault", ["launcher_missing", "launcher_corrupt", "handler_sha",
                                    "checker_sha", "contract_sha", "handler_missing",
                                    "contract_missing"])
def test_integrity_failure_blocks_before_handler_dispatch(deployment, event, fault):
    root, binding = deployment
    binding["event"] = event
    target = fault.split("_")[0]
    path = Path(binding["launcher_path"]) if target == "launcher" else root / binding[target]["path"]
    if fault.endswith("missing"):
        path.unlink()
    elif target == "launcher":
        # If corrupt launcher executes, it would leave a separate persisted marker.
        path.write_text("from pathlib import Path\nPath(" + repr(str(root / "corrupt-launcher-ran")) +
                        ").write_text('unsafe')\n", encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"\n# changed after approval\n")
    result = execute(binding)
    assert result["decision"] == "block"
    expected = "MEMORY_BOOTSTRAP_INTEGRITY_ERROR" if target == "launcher" else "MEMORY_LAUNCHER_INTEGRITY_ERROR"
    assert expected in result["reason"]
    assert not (root / "dispatch.stdin.bin").exists()
    assert not (root / "corrupt-launcher-ran").exists()


@pytest.mark.parametrize("event", ["stop", "post-tool-use"])
def test_all_pins_match_dispatches_exact_stdin(deployment, event):
    root, binding = deployment
    binding["event"] = event
    payload = PAYLOAD if event == "stop" else b'{"hook_event_name":"PostToolUse", "text":"\xe4\xb8\xad\xe6\x96\x87"}\r\n'
    assert execute(binding, payload) == {"candidate_dispatched": True}
    assert (root / "dispatch.stdin.bin").read_bytes() == payload


def test_untrusted_disk_config_cannot_replace_inline_expected_sha(deployment):
    root, binding = deployment
    checker = root / binding["checker"]["path"]
    checker.write_bytes(b"fake bytes")
    attacker = copy.deepcopy(binding)
    attacker["checker"]["sha256"] = sha(checker.read_bytes())
    (root / "candidate-pins.json").write_text(json.dumps(attacker), encoding="utf-8")
    assert execute(binding)["decision"] == "block"
    assert not (root / "dispatch.stdin.bin").exists()


def test_artifact_path_outside_root_blocks(deployment):
    root, binding = deployment
    outside = root.parent / "outside-handler.py"
    outside.write_bytes((root / "handler.py").read_bytes())
    binding["handler"]["path"] = "../outside-handler.py"
    assert execute(binding)["decision"] == "block"
    assert not (root / "dispatch.stdin.bin").exists()


@pytest.mark.parametrize("source", [b"raise RuntimeError('failed')\n", b"print('not JSON')\n"])
def test_handler_execution_failure_is_not_allow(deployment, source):
    root, binding = deployment
    (root / "handler.py").write_bytes(source)
    binding["handler"]["sha256"] = sha(source)
    result = execute(binding)
    assert result["decision"] == "block"
    assert "MEMORY_LAUNCHER_INTEGRITY_ERROR" in result["reason"]


@pytest.mark.parametrize("event_name", ["PostToolUse", "Stop"])
def test_rendered_windows_hook_command_handles_spaces_and_quotes(deployment, event_name):
    root, binding = deployment
    # A quote in a filesystem path verifies real PowerShell argument escaping.
    quoted_launcher = root / "launcher'approved.py"
    quoted_launcher.write_bytes(Path(binding["launcher_path"]).read_bytes())
    binding["launcher_path"] = str(quoted_launcher)
    binding["event"] = "post-tool-use" if event_name == "PostToolUse" else "stop"
    command = powershell_command(inline_source(binding))
    pwsh = shutil.which("pwsh")
    assert pwsh, "PowerShell is required for this Windows command regression"
    process = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", command],
                             input=PAYLOAD, capture_output=True, timeout=40)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"candidate_dispatched": True}
    assert (root / "dispatch.stdin.bin").read_bytes() == PAYLOAD


def test_frozen_v5_stop_dispatch_allows_no_obligation(deployment):
    root, binding = deployment
    source = (ROOT / "governance_tools/required_memory_obligation.py").read_bytes()
    assert sha(source) == "8FBB4A3DDC40A34ED5F3283C35C01BB34EB77862C3477672A4EABEC11900E6A2"
    (root / "handler.py").write_bytes(source)
    binding["handler"]["sha256"] = sha(source)
    assert execute(binding) == {}
    assert not (root / "dispatch.stdin.bin").exists()


def test_unicode_handler_response_survives_windows_encoding(deployment):
    root, binding = deployment
    source = b"import json\nprint(json.dumps({'reason':'\\u4e2d\\u6587'},ensure_ascii=False))\n"
    (root / "handler.py").write_bytes(source)
    binding["handler"]["sha256"] = sha(source)
    assert execute(binding) == {"reason": "\u4e2d\u6587"}
