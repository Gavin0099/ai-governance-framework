from pathlib import Path
from unittest.mock import patch

from governance_tools.session_closeout_entry import run


def test_session_closeout_entry_forwards_no_ledger_write_mode(tmp_path: Path) -> None:
    hook_result = {"ok": True, "session_id": "entry-no-ledger"}

    with patch("governance_tools.session_closeout_entry.run_session_end_hook", return_value=hook_result) as mocked:
        result = run(tmp_path, ledger_write_allowed=False)

    assert result == hook_result
    mocked.assert_called_once_with(
        project_root=tmp_path,
        transcript_path=None,
        hook_session_id=None,
        ledger_write_allowed=False,
    )
