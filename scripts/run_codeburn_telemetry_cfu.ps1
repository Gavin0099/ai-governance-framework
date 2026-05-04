param(
  [string]$CfuRoot = "E:\BackUp\Git_EE\CFU",
  [string]$FrameworkRoot = "E:\BackUp\Git_EE\ai-governance-framework",
  [string]$StartDay = "2026-04-30",
  [string]$EndDay = "2026-05-04"
)

$ErrorActionPreference = "Stop"

$DbPath = Join-Path $CfuRoot "codeburn_phase1.db"
$SchemaPath = Join-Path $FrameworkRoot "codeburn\phase1\schema.sql"
$SessionCli = Join-Path $FrameworkRoot "codeburn\phase1\codeburn_session.py"
$RunCli = Join-Path $FrameworkRoot "codeburn\phase1\codeburn_run.py"
$SummaryCli = Join-Path $FrameworkRoot "Script\codeburn_phase1_7day_summary.py"

$env:PYTHONPATH = $FrameworkRoot

function Show-Counts {
  param([string]$Label)
  $counts = python -c "import sqlite3; c=sqlite3.connect(r'$DbPath'); print({'sessions':c.execute('select count(*) from sessions').fetchone()[0],'steps':c.execute('select count(*) from steps').fetchone()[0],'signals':c.execute('select count(*) from signals').fetchone()[0],'recovery_events':c.execute('select count(*) from recovery_events').fetchone()[0],'changed_files':c.execute('select count(*) from changed_files').fetchone()[0]})"
  Write-Host "[$Label] $counts"
}

function Get-OpenSessionId {
  $sid = python -c "import sqlite3; c=sqlite3.connect(r'$DbPath'); r=c.execute(\"select session_id from sessions where ended_at is null or ended_at='' order by created_at desc limit 1\").fetchone(); print(r[0] if r else '')"
  return $sid.Trim()
}

function Get-LatestStepIdForSession {
  param([string]$SessionId)
  $stepId = python -c "import sqlite3; c=sqlite3.connect(r'$DbPath'); r=c.execute(\"select step_id from steps where session_id=? order by started_at desc, step_id desc limit 1\", (r'$SessionId',)).fetchone(); print(r[0] if r else '')"
  return $stepId.Trim()
}

Write-Host "== Init schema =="
python -c "import sqlite3, pathlib; db=pathlib.Path(r'$DbPath'); sql=pathlib.Path(r'$SchemaPath').read_text(encoding='utf-8'); conn=sqlite3.connect(db); conn.executescript(sql); conn.commit(); conn.close()"
Show-Counts "after-schema-init"

Write-Host "== Baseline flow =="
python $SessionCli --db $DbPath --schema $SchemaPath session-start --task "CFU baseline flow"
Show-Counts "after-baseline-start"
python $RunCli --db $DbPath --schema $SchemaPath --step-kind planning -- powershell -NoProfile -Command "Write-Output baseline-plan"
python $RunCli --db $DbPath --schema $SchemaPath --step-kind execution -- powershell -NoProfile -Command "Write-Output baseline-exec"
python $RunCli --db $DbPath --schema $SchemaPath --step-kind test -- powershell -NoProfile -Command "Write-Output baseline-test"
Show-Counts "after-baseline-steps"
python $SessionCli --db $DbPath --schema $SchemaPath session-end
Show-Counts "after-baseline-end"

Write-Host "== Stressed flow =="
python $SessionCli --db $DbPath --schema $SchemaPath session-start --task "CFU stressed flow"
Show-Counts "after-stressed-start"

$stressedSessionId = Get-OpenSessionId
if (-not $stressedSessionId) { throw "no open stressed session found after session-start" }

python $RunCli --db $DbPath --schema $SchemaPath --step-kind test -- powershell -NoProfile -Command "exit 1"
$firstStepId = Get-LatestStepIdForSession -SessionId $stressedSessionId
if (-not $firstStepId) { throw "no first stressed step_id found for retry chain" }

python $RunCli --db $DbPath --schema $SchemaPath --step-kind retry --retry-of $firstStepId -- powershell -NoProfile -Command "exit 1"
$secondStepId = Get-LatestStepIdForSession -SessionId $stressedSessionId
if (-not $secondStepId) { throw "no second stressed step_id found for retry chain" }

python $RunCli --db $DbPath --schema $SchemaPath --step-kind retry --retry-of $secondStepId -- powershell -NoProfile -Command "Write-Output retry-recovered"
Show-Counts "after-stressed-steps"
python $SessionCli --db $DbPath --schema $SchemaPath session-end
Show-Counts "after-stressed-end"

Write-Host "== 5-day summary =="
python $SummaryCli --db $DbPath --start-day $StartDay --end-day $EndDay --runtime-validation-status degraded --runtime-validation-blocker permission_denied_tmp_cache --format json
