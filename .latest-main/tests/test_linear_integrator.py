import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
import urllib.request
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.linear_integrator import LinearClient, LinearIntegrator
import governance_tools.linear_integrator as linear_integrator_module

@pytest.fixture
def api_key_env(monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "test_key_xxxx")

@pytest.fixture
def mock_urlopen(monkeypatch):
    mock = MagicMock()
    # Mock context manager
    cm = MagicMock()
    cm.__enter__.return_value = mock
    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(return_value=cm))
    return mock

@pytest.fixture
def temp_memory(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    return mem

def test_linear_client_init_no_key(monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    with pytest.raises(ValueError):
        LinearClient()

def test_linear_client_init_with_key(api_key_env):
    client = LinearClient()
    assert client.api_key == "test_key_xxxx"

def test_scan_sensitive(api_key_env):
    client = LinearClient()
    assert "API_KEY" in client.scan_sensitive("Use key lin_api_1234567890abcdef")
    assert "CREDENTIAL" in client.scan_sensitive("password = supersecret")
    assert not client.scan_sensitive("Just a normal task")

def test_graphql_request_success(api_key_env, mock_urlopen):
    mock_urlopen.read.return_value = json.dumps({"data": {"success": True}}).encode('utf-8')
    client = LinearClient()
    res = client._graphql_request("query {}")
    assert res == {"data": {"success": True}}

def test_create_issue_sensitive_blocks(api_key_env):
    client = LinearClient()
    with pytest.raises(ValueError, match="拒絕送出"):
        client.create_issue(title="password=12345", description="", team_id="TEAM-1")

@patch.object(LinearClient, '_graphql_request_with_retry')
def test_create_issue_success(mock_req, api_key_env):
    mock_req.return_value = {"data": {"issueCreate": {"success": True, "issue": {"id": "1", "identifier": "T-1", "url": "url"}}}}
    client = LinearClient()
    res = client.create_issue("Title", "Desc", "TEAM-1")
    assert res["identifier"] == "T-1"

@patch.object(LinearClient, '_graphql_request_with_retry')
def test_create_issue_fail(mock_req, api_key_env):
    mock_req.return_value = {"data": {"issueCreate": {"success": False}}, "errors": ["err"]}
    client = LinearClient()
    with pytest.raises(Exception, match="建立 Issue 失敗"):
        client.create_issue("Title", "Desc", "TEAM-1")

@patch.object(LinearClient, '_graphql_request_with_retry')
def test_get_team_info(mock_req, api_key_env):
    mock_req.return_value = {"data": {"teams": {"nodes": [{"id": "1", "name": "N"}]}}}
    client = LinearClient()
    assert client.get_team_info() == [{"id": "1", "name": "N"}]

@patch.object(LinearClient, '_graphql_request_with_retry')
def test_update_issue_status(mock_req, api_key_env):
    mock_req.return_value = {"data": {"issueUpdate": {"success": True}}}
    client = LinearClient()
    assert client.update_issue_status("1", "state") is True

def test_parse_active_task_empty(temp_memory, api_key_env):
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    assert integrator.parse_active_task() == []

def test_parse_active_task(temp_memory, api_key_env):
    active_task = temp_memory / "01_active_task.md"
    active_task.write_text("- [ ] Task 1\n- [x] Task 2 [LINEAR:ENG-123]\n", encoding="utf-8")
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    tasks = integrator.parse_active_task()
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task 1"
    assert not tasks[0]["is_completed"]
    assert tasks[0]["linear_id"] is None
    assert tasks[1]["title"] == "Task 2"
    assert tasks[1]["is_completed"]
    assert tasks[1]["linear_id"] == "ENG-123"

def test_sync_task_already_synced(temp_memory, api_key_env):
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    res = integrator.sync_task_to_linear({"title": "A", "linear_id": "L-1"}, "T-1")
    assert res == "L-1"

@patch.object(LinearClient, 'create_issue')
def test_sync_task_success(mock_create, temp_memory, api_key_env):
    mock_create.return_value = {"identifier": "ENG-1", "url": "url"}
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    res = integrator.sync_task_to_linear({"title": "A", "description": "B"}, "T-1")
    assert res == "ENG-1"
    assert (temp_memory / "03_knowledge_base.md").exists()

@patch.object(LinearClient, 'create_issue')
def test_sync_task_fail(mock_create, temp_memory, api_key_env):
    mock_create.side_effect = Exception("err")
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    res = integrator.sync_task_to_linear({"title": "A", "description": "B"}, "T-1")
    assert res is None

def test_update_active_task(temp_memory, api_key_env):
    active_task = temp_memory / "01_active_task.md"
    active_task.write_text("- [ ] Task 1\n", encoding="utf-8")
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    integrator.update_active_task_with_linear_ids({"Task 1": "ENG-1"})
    assert "ENG-1" in active_task.read_text(encoding="utf-8")

def test_update_active_task_file_missing(temp_memory, api_key_env):
    """update_active_task_with_linear_ids should silently return when file absent."""
    client = LinearClient()
    integrator = LinearIntegrator(temp_memory, client)
    # Should not raise
    integrator.update_active_task_with_linear_ids({"Task 1": "ENG-99"})


# ─── _graphql_request error paths ───────────────────────────────────────────

def test_graphql_request_http_error(api_key_env, monkeypatch):
    """HTTPError is re-raised with body as reason."""
    err = urllib.error.HTTPError("url", 400, "bad request", {}, None)
    err.read = lambda: b"bad body"
    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(side_effect=err))
    client = LinearClient()
    with pytest.raises(urllib.error.HTTPError):
        client._graphql_request("query {}")

def test_graphql_request_url_error(api_key_env, monkeypatch):
    """URLError is re-raised."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        MagicMock(side_effect=urllib.error.URLError("conn refused"))
    )
    client = LinearClient()
    with pytest.raises(urllib.error.URLError):
        client._graphql_request("query {}")


# ─── _graphql_request_with_retry ────────────────────────────────────────────

def test_retry_succeeds_after_429(api_key_env, monkeypatch):
    """Retryable 429 error should retry and eventually succeed."""
    good_response_data = json.dumps({"data": {"ok": True}}).encode("utf-8")
    call_count = {"n": 0}

    def fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            err = urllib.error.HTTPError("url", 429, "rate limit", {}, None)
            err.read = lambda: b""
            raise err
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = good_response_data
        cm.__exit__.return_value = False
        return cm

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    client = LinearClient()
    res = client._graphql_request_with_retry("query {}")
    assert res == {"data": {"ok": True}}

def test_retry_non_retryable_error_raises(api_key_env, monkeypatch):
    """Non-retryable HTTP error (e.g. 401) should raise immediately."""
    err = urllib.error.HTTPError("url", 401, "unauthorized", {}, None)
    err.read = lambda: b"unauthorized"
    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(side_effect=err))
    monkeypatch.setattr("time.sleep", lambda _: None)

    client = LinearClient()
    with pytest.raises(Exception, match="401"):
        client._graphql_request_with_retry("query {}")

def test_retry_url_error_then_succeed(api_key_env, monkeypatch):
    """URLError should retry and eventually succeed."""
    good_response_data = json.dumps({"data": {}}).encode("utf-8")
    call_count = {"n": 0}

    def fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise urllib.error.URLError("timeout")
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = good_response_data
        cm.__exit__.return_value = False
        return cm

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)

    client = LinearClient()
    res = client._graphql_request_with_retry("query {}")
    assert "data" in res

def test_retry_exceeds_max_raises(api_key_env, monkeypatch):
    """Exhausting all retries on URLError should raise Exception."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        MagicMock(side_effect=urllib.error.URLError("always fails"))
    )
    monkeypatch.setattr("time.sleep", lambda _: None)

    client = LinearClient()
    with pytest.raises(Exception):
        client._graphql_request_with_retry("query {}")


# ─── main() CLI paths ────────────────────────────────────────────────────────

def _make_client_and_integrator(monkeypatch, temp_memory, teams=None, tasks=None):
    mock_client = MagicMock(spec=LinearClient)
    mock_client.get_team_info.return_value = teams or [{"name": "Eng", "key": "ENG", "id": "T1"}]
    mock_integrator = MagicMock(spec=LinearIntegrator)
    mock_integrator.parse_active_task.return_value = tasks or []
    monkeypatch.setattr(linear_integrator_module, "LinearClient", lambda: mock_client)
    monkeypatch.setattr(linear_integrator_module, "LinearIntegrator", lambda *a: mock_integrator)
    return mock_client, mock_integrator


def test_main_list_teams_human(api_key_env, monkeypatch, temp_memory, capsys):
    _make_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.setattr(sys, "argv", ["prog", "--memory-root", str(temp_memory), "--list-teams"])
    linear_integrator_module.main()
    out = capsys.readouterr().out
    assert "Eng" in out


def test_main_list_teams_json(api_key_env, monkeypatch, temp_memory, capsys):
    _make_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.setattr(sys, "argv", ["prog", "--memory-root", str(temp_memory), "--list-teams", "--format", "json"])
    linear_integrator_module.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "teams" in data


def test_main_sync_no_team_id_exits(api_key_env, monkeypatch, temp_memory):
    _make_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.setattr(sys, "argv", ["prog", "--memory-root", str(temp_memory), "--sync"])
    with pytest.raises(SystemExit):
        linear_integrator_module.main()


def test_main_sync_with_team_id(api_key_env, monkeypatch, temp_memory):
    task = {"title": "T1", "description": "D", "is_completed": False, "linear_id": None}
    mock_client, mock_integrator = _make_client_and_integrator(monkeypatch, temp_memory, tasks=[task])
    mock_integrator.sync_task_to_linear.return_value = "ENG-1"
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--sync", "--team-id", "T1",
        "--batch-delay", "0"
    ])
    linear_integrator_module.main()
    mock_integrator.sync_task_to_linear.assert_called_once()
    mock_integrator.update_active_task_with_linear_ids.assert_called_once_with({"T1": "ENG-1"})


def test_main_sync_json_output(api_key_env, monkeypatch, temp_memory, capsys):
    task = {"title": "T1", "description": "D", "is_completed": False, "linear_id": None}
    mock_client, mock_integrator = _make_client_and_integrator(monkeypatch, temp_memory, tasks=[task])
    mock_integrator.sync_task_to_linear.return_value = "ENG-2"
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--sync", "--team-id", "T1",
        "--batch-delay", "0", "--format", "json"
    ])
    linear_integrator_module.main()
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "ok"
    assert "ENG-2" in data["synced"]


def test_main_value_error_exits(api_key_env, monkeypatch, temp_memory):
    monkeypatch.setattr(linear_integrator_module, "LinearClient", MagicMock(side_effect=ValueError("bad key")))
    monkeypatch.setattr(sys, "argv", ["prog", "--memory-root", str(temp_memory), "--list-teams"])
    with pytest.raises(SystemExit):
        linear_integrator_module.main()


def test_main_generic_error_exits(api_key_env, monkeypatch, temp_memory):
    monkeypatch.setattr(linear_integrator_module, "LinearClient", MagicMock(side_effect=Exception("boom")))
    monkeypatch.setattr(sys, "argv", ["prog", "--memory-root", str(temp_memory), "--list-teams"])
    with pytest.raises(SystemExit):
        linear_integrator_module.main()


def test_main_no_args_prints_help(api_key_env, monkeypatch, temp_memory, capsys):
    _make_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.setattr(sys, "argv", ["prog", "--memory-root", str(temp_memory)])
    linear_integrator_module.main()
