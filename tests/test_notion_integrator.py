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
import governance_tools.notion_integrator as notion_integrator_module

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

def test_update_active_task_file_missing(temp_memory, api_key_env):
    """update_active_task_with_notion_ids should silently return when file absent."""
    client = NotionClient()
    integrator = NotionIntegrator(temp_memory, client)
    integrator.update_active_task_with_notion_ids({"Task 1": "XXXXXXXX"})

def test_parse_active_task_file_missing(temp_memory, api_key_env):
    """parse_active_task returns [] when file doesn't exist."""
    client = NotionClient()
    integrator = NotionIntegrator(temp_memory, client)
    assert integrator.parse_active_task() == []

def test_sync_task_fail(temp_memory, api_key_env):
    """sync_task_to_notion returns None on exception."""
    with patch.object(NotionClient, 'create_page', side_effect=Exception("fail")):
        client = NotionClient()
        integrator = NotionIntegrator(temp_memory, client)
        res = integrator.sync_task_to_notion({"title": "X", "description": "Y"}, "DB-1")
        assert res is None


# ─── _request error paths ────────────────────────────────────────────────────

def test_request_http_error(api_key_env, monkeypatch):
    """HTTPError is re-raised with body."""
    err = urllib.error.HTTPError("url", 400, "bad", {}, None)
    err.read = lambda: b"error body"
    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(side_effect=err))
    client = NotionClient()
    with pytest.raises(urllib.error.HTTPError):
        client._request("GET", "/test")

def test_request_url_error(api_key_env, monkeypatch):
    """URLError is re-raised."""
    monkeypatch.setattr(
        urllib.request, "urlopen",
        MagicMock(side_effect=urllib.error.URLError("refused"))
    )
    client = NotionClient()
    with pytest.raises(urllib.error.URLError):
        client._request("GET", "/test")


# ─── _request_with_retry ─────────────────────────────────────────────────────

def test_retry_succeeds_after_429(api_key_env, monkeypatch):
    good = json.dumps({"ok": True}).encode("utf-8")
    call_count = {"n": 0}

    def fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            err = urllib.error.HTTPError("url", 429, "rate limit", {}, None)
            err.read = lambda: b""
            raise err
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = good
        cm.__exit__.return_value = False
        return cm

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)
    client = NotionClient()
    res = client._request_with_retry("GET", "/test")
    assert res == {"ok": True}

def test_retry_non_retryable_raises(api_key_env, monkeypatch):
    err = urllib.error.HTTPError("url", 403, json.dumps({"message": "forbidden"}), {}, None)
    err.read = lambda: b""
    monkeypatch.setattr(urllib.request, "urlopen", MagicMock(side_effect=err))
    monkeypatch.setattr("time.sleep", lambda _: None)
    client = NotionClient()
    with pytest.raises(Exception, match="403"):
        client._request_with_retry("GET", "/test")

def test_retry_url_error_then_succeed(api_key_env, monkeypatch):
    good = json.dumps({"data": "x"}).encode("utf-8")
    call_count = {"n": 0}

    def fake_urlopen(req, timeout=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise urllib.error.URLError("timeout")
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = good
        cm.__exit__.return_value = False
        return cm

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda _: None)
    client = NotionClient()
    res = client._request_with_retry("GET", "/test")
    assert "data" in res

def test_retry_exhausted_raises(api_key_env, monkeypatch):
    monkeypatch.setattr(
        urllib.request, "urlopen",
        MagicMock(side_effect=urllib.error.URLError("always fails"))
    )
    monkeypatch.setattr("time.sleep", lambda _: None)
    client = NotionClient()
    with pytest.raises(Exception):
        client._request_with_retry("GET", "/test")


# ─── query_database pagination ───────────────────────────────────────────────

@patch.object(NotionClient, '_request_with_retry')
def test_query_database_pagination(mock_req, api_key_env):
    """has_more=True on first page triggers a second request with start_cursor."""
    page = {"id": "1", "url": "u", "properties": {"Name": {"type": "title", "title": [{"plain_text": "P"}]}}}
    mock_req.side_effect = [
        {"results": [page], "has_more": True, "next_cursor": "cur1"},
        {"results": [page], "has_more": False},
    ]
    client = NotionClient()
    results = client.query_database("DB1")
    assert len(results) == 2
    assert mock_req.call_count == 2


# ─── _extract_page_title fallback ────────────────────────────────────────────

def test_extract_page_title_no_title_property(api_key_env):
    """Returns fallback string when no title property exists."""
    client = NotionClient()
    page = {"properties": {"Status": {"type": "select", "select": {"name": "Done"}}}}
    assert client._extract_page_title(page) == "(無標題)"


def test_extract_page_title_with_title(api_key_env):
    """Returns concatenated plain_text when title property exists."""
    client = NotionClient()
    page = {
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": "My "}, {"plain_text": "Task"}],
            }
        }
    }
    assert client._extract_page_title(page) == "My Task"


# ---------------------------------------------------------------------------
# main() CLI paths
# ---------------------------------------------------------------------------

def _make_notion_client_and_integrator(monkeypatch, temp_memory, databases=None, tasks=None):
    mock_client = MagicMock(spec=NotionClient)
    mock_client.search_databases.return_value = databases or [
        {"title": "TestDB", "id": "db-001", "url": "https://notion.so/db-001"}
    ]
    mock_integrator = MagicMock(spec=NotionIntegrator)
    mock_integrator.parse_active_task.return_value = tasks or []
    monkeypatch.setattr(notion_integrator_module, "NotionClient", lambda: mock_client)
    monkeypatch.setattr(notion_integrator_module, "NotionIntegrator", lambda *a: mock_integrator)
    return mock_client, mock_integrator


def test_main_list_databases_human(api_key_env, monkeypatch, temp_memory, capsys):
    _make_notion_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--list-databases"
    ])
    notion_integrator_module.main()
    out = capsys.readouterr().out
    assert "TestDB" in out


def test_main_list_databases_json(api_key_env, monkeypatch, temp_memory, capsys):
    _make_notion_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--list-databases", "--format", "json"
    ])
    notion_integrator_module.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "databases" in data
    assert data["databases"][0]["title"] == "TestDB"


def test_main_list_databases_empty_human(api_key_env, monkeypatch, temp_memory, capsys):
    _make_notion_client_and_integrator(monkeypatch, temp_memory, databases=[])
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--list-databases"
    ])
    notion_integrator_module.main()
    out = capsys.readouterr().out
    assert "找不到" in out or "Database" in out


def test_main_sync_no_database_id_exits(api_key_env, monkeypatch, temp_memory):
    _make_notion_client_and_integrator(monkeypatch, temp_memory)
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--sync"
    ])
    with pytest.raises(SystemExit):
        notion_integrator_module.main()


def test_main_sync_with_database_id(api_key_env, monkeypatch, temp_memory):
    task = {"title": "T1", "description": "D", "is_completed": False, "notion_id": None}
    mock_client, mock_integrator = _make_notion_client_and_integrator(
        monkeypatch, temp_memory, tasks=[task]
    )
    mock_integrator.sync_task_to_notion.return_value = "page-abc123"
    mock_integrator.parse_active_task.return_value = [task]
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory),
        "--sync", "--database-id", "db-001", "--batch-delay", "0"
    ])
    notion_integrator_module.main()
    mock_integrator.sync_task_to_notion.assert_called_once()
    mock_integrator.update_active_task_with_notion_ids.assert_called_once()


def test_main_generic_error_exits(api_key_env, monkeypatch, temp_memory):
    monkeypatch.setattr(
        notion_integrator_module, "NotionClient",
        MagicMock(side_effect=RuntimeError("boom"))
    )
    monkeypatch.setattr(sys, "argv", [
        "prog", "--memory-root", str(temp_memory), "--list-databases"
    ])
    with pytest.raises(SystemExit):
        notion_integrator_module.main()
