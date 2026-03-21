import pytest
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error
import urllib.request
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from governance_tools.notion_integrator import NotionClient, NotionIntegrator

@pytest.fixture
def api_key_env(monkeypatch):
    monkeypatch.setenv("NOTION_API_KEY", "test_key_xxxx")

@pytest.fixture
def mock_urlopen(monkeypatch):
    mock = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = mock
    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(return_value=cm))
    return mock

@pytest.fixture
def temp_memory(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    return mem

def test_notion_client_init_no_key(monkeypatch):
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(ValueError):
        NotionClient()

def test_notion_client_init_with_key(api_key_env):
    client = NotionClient()
    assert client.api_key == "test_key_xxxx"

def test_scan_sensitive(api_key_env):
    client = NotionClient()
    assert "API_KEY" in client.scan_sensitive("secret_1234567890abcdef")
    assert not client.scan_sensitive("Just a normal task")

def test_request_success(api_key_env, mock_urlopen):
    mock_urlopen.read.return_value = json.dumps({"success": True}).encode('utf-8')
    client = NotionClient()
    res = client._request("GET", "/test")
    assert res == {"success": True}

@patch.object(NotionClient, '_request_with_retry')
def test_search_databases(mock_req, api_key_env):
    mock_req.return_value = {"results": [{"id": "1", "title": [{"plain_text": "DB"}], "url": "url"}]}
    client = NotionClient()
    assert client.search_databases() == [{"id": "1", "title": "DB", "url": "url"}]

@patch.object(NotionClient, '_request_with_retry')
def test_query_database(mock_req, api_key_env):
    mock_req.return_value = {
        "results": [{"id": "1", "url": "url", "properties": {"Name": {"type": "title", "title": [{"plain_text": "P"}]}}}],
        "has_more": False
    }
    client = NotionClient()
    assert client.query_database("DB1") == [{"id": "1", "title": "P", "url": "url"}]

def test_create_page_sensitive(api_key_env):
    client = NotionClient()
    with pytest.raises(ValueError, match="拒絕送出"):
        client.create_page("DB1", "password=supersecret")

@patch.object(NotionClient, '_request_with_retry')
def test_create_page_success(mock_req, api_key_env):
    mock_req.return_value = {"id": "12345678-abcd", "url": "url"}
    client = NotionClient()
    res = client.create_page("DB1", "Title", "Desc")
    assert res["identifier"] == "12345678"
    assert res["url"] == "url"

def test_parse_active_task(temp_memory, api_key_env):
    active_task = temp_memory / "01_active_task.md"
    active_task.write_text("- [ ] Task 1\n- [x] Task 2 [NOTION:ABCDEF12]\n", encoding="utf-8")
    client = NotionClient()
    integrator = NotionIntegrator(temp_memory, client)
    tasks = integrator.parse_active_task()
    assert len(tasks) == 2
    assert tasks[0]["title"] == "Task 1"
    assert not tasks[0]["is_completed"]
    assert tasks[0]["notion_id"] is None
    assert tasks[1]["title"] == "Task 2"
    assert tasks[1]["is_completed"]
    assert tasks[1]["notion_id"] == "ABCDEF12"

@patch.object(NotionClient, 'create_page')
def test_sync_task_success(mock_create, temp_memory, api_key_env):
    mock_create.return_value = {"identifier": "12345678", "url": "url"}
    client = NotionClient()
    integrator = NotionIntegrator(temp_memory, client)
    res = integrator.sync_task_to_notion({"title": "A", "description": "B"}, "DB-1")
    assert res == "12345678"

def test_sync_task_already_synced(temp_memory, api_key_env):
    client = NotionClient()
    integrator = NotionIntegrator(temp_memory, client)
    res = integrator.sync_task_to_notion({"title": "A", "notion_id": "ID1"}, "DB-1")
    assert res == "ID1"

def test_update_active_task(temp_memory, api_key_env):
    active_task = temp_memory / "01_active_task.md"
    active_task.write_text("- [ ] Task 1\n", encoding="utf-8")
    client = NotionClient()
    integrator = NotionIntegrator(temp_memory, client)
    integrator.update_active_task_with_notion_ids({"Task 1": "NOT-ID"})
    assert "NOT-ID" in active_task.read_text(encoding="utf-8")
