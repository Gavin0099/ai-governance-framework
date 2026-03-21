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
