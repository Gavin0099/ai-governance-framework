<#
.SYNOPSIS
  Install (or uninstall) the Hermes no_agent multi-repo checklist as a daily
  Windows Scheduled Task.

.DESCRIPTION
  THIS CHANGES OS STATE. It registers an unattended recurring task. Human-run
  only -- it is intentionally not executed by any agent.

  Safety properties:
    - Runs check_preflight.py BEFORE creating the task; aborts if it fails.
    - The scheduled command ALSO re-runs preflight before every cron tick, so
      each daily run self-gates on (deployed script/config == reviewed pin).
      If the deployed copy ever drifts from the pin, the tick is skipped.
    - no_agent only: no LLM / provider / agent path is invoked.
    - Current-user, least-privilege task; 10-minute limit; IgnoreNew instances.

  This script does NOT touch the git repo, does NOT push, and -- apart from the
  named scheduled task -- writes nothing outside Task Scheduler.

.EXAMPLE
  # install (daily 09:00, against the verified deploy HERMES_HOME)
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install_checklist_task.ps1

.EXAMPLE
  # remove the task
  powershell -NoProfile -ExecutionPolicy Bypass -File .\install_checklist_task.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string]$HermesHome = "C:\tmp\hermes-noagent-checklist-deploy-20260623",
    [string]$Venv       = "C:\tmp\hermes-cron-venv",
    [string]$TaskName   = "AI Governance Hermes NoAgent Checklist",
    [string]$StartTime  = "09:00",
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$pkg       = $PSScriptRoot
$python    = Join-Path $Venv "Scripts\python.exe"
$preflight = Join-Path $pkg  "check_preflight.py"
$config    = Join-Path $pkg  "multi_repo_status.config.json"

if ($Uninstall) {
    Write-Host "Removing scheduled task: $TaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed." -ForegroundColor Green
    return
}

# --- sanity: required files/paths exist ---
foreach ($p in @($python, $preflight, $config)) {
    if (-not (Test-Path $p)) { throw "Required path missing: $p" }
}

# --- 1. install-time preflight gate (abort if deployed != pin) ---
Write-Host "== Preflight (install-time) ==" -ForegroundColor Cyan
& $python $preflight --config $config --hermes-home $HermesHome --venv $Venv
if ($LASTEXITCODE -ne 0) {
    throw "Preflight FAILED (exit $LASTEXITCODE). Refusing to install. Deployed script/config must match the reviewed pin."
}
Write-Host "Preflight OK." -ForegroundColor Green

# --- 2. scheduled command: preflight THEN tick (self-gated on every run) ---
$inner = @(
    "`$env:HERMES_HOME='$HermesHome'"
    "& '$python' '$preflight' --config '$config' --hermes-home '$HermesHome' --venv '$Venv'"
    "if (`$LASTEXITCODE -ne 0) { exit 1 }"
    "& '$python' -m hermes_cli.main cron tick"
) -join "; "
$argument = "-NoProfile -ExecutionPolicy Bypass -Command `"$inner`""

$action   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument
$trigger  = New-ScheduledTaskTrigger -Daily -At $StartTime
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew -StartWhenAvailable

Write-Host "== Creating scheduled task '$TaskName' (daily $StartTime) ==" -ForegroundColor Cyan
Write-Host "This CHANGES OS STATE -- the task will run unattended every day." -ForegroundColor Yellow
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Hermes no_agent checklist daily tick. Observation-only; not governance enforcement. Re-runs preflight before each tick." `
    -Force | Out-Null

# --- 3. verify ---
Write-Host "== Verify ==" -ForegroundColor Cyan
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State | Format-Table -AutoSize
Write-Host "Installed. Rollback any time with:" -ForegroundColor Green
Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File .\install_checklist_task.ps1 -Uninstall"
