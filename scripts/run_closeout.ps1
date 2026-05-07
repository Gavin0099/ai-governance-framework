$ErrorActionPreference = "Stop"

if (!(Test-Path "artifacts/session-closeout.txt")) {
  Write-Host "[closeout] skipped: missing artifacts/session-closeout.txt"
  exit 2
}

python -m governance_tools.session_end_hook --project-root .

Write-Host "[closeout] completed"
