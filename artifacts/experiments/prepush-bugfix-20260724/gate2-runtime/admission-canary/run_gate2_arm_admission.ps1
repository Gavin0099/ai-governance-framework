param(
    [string]$RunId = ("gate2-arm-runner-admission-" + (Get-Date -Format "yyyyMMdd-HHmmss")),
    [string]$EvidenceRoot = "D:\gate2-live-run-evidence"
)

$ErrorActionPreference = "Stop"
$Image = "sha256:e6df7283938a5c203910524083075843635d2d39ac42fcaa84c7e76cd0b5f168"
$SourceCommit = "33006f097597f5720a2d01661281d564fb2693ec"
$ExpectedTree = "36c346fa951a24cbf914ef04469aac5cb5fd8b86"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..\..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$DockerDir = "C:\Users\daish\AppData\Local\Programs\DockerDesktop\resources\bin"
$env:Path = "$DockerDir;$env:Path"
$Payload = Join-Path $PSScriptRoot "offline-pytest.zip"
$Manifest = Join-Path $PSScriptRoot "offline-pytest-manifest.json"
$Adapter = Join-Path $PSScriptRoot "gate2_arm_adapter.py"
$Policy = Join-Path $PSScriptRoot "policy_gate2_arm_d.json"
$Capture = Join-Path $PSScriptRoot "evidence-live\capture_command.py"
$StreamInput = Join-Path $PSScriptRoot "stream_gate2_input.py"
$RunDir = Join-Path $EvidenceRoot $RunId
$Container = $RunId

if (Test-Path -LiteralPath $RunDir) {
    throw "Evidence directory already exists: $RunDir"
}
New-Item -ItemType Directory -Path $RunDir | Out-Null

function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) {
        throw "docker command failed ($LASTEXITCODE): $($args -join ' ')"
    }
}

function Capture-Adapter {
    param(
        [string]$Label,
        [string[]]$AdapterArgs,
        [int]$ExpectedExit
    )
    & $Python $Capture `
        --stdout (Join-Path $RunDir "$Label.stdout.txt") `
        --stderr (Join-Path $RunDir "$Label.stderr.txt") `
        --exit-code-out (Join-Path $RunDir "$Label.exit-code.txt") `
        -- $Python $Adapter @AdapterArgs
    # capture_command intentionally returns the child's exit code.  A non-zero
    # adapter result is evidence for the negative control, not capture failure.
    $actual = [int](Get-Content -Raw -LiteralPath (Join-Path $RunDir "$Label.exit-code.txt"))
    if ($actual -ne $ExpectedExit) {
        throw "$Label returned $actual, expected $ExpectedExit"
    }
}

$manifestObject = Get-Content -Raw -LiteralPath $Manifest | ConvertFrom-Json
$payloadSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Payload).Hash.ToLowerInvariant()
if ($payloadSha -ne $manifestObject.payload_sha256) {
    throw "Offline pytest payload digest does not match its manifest."
}

$imageId = (& docker image inspect --format "{{.Id}}" $Image).Trim()
if ($LASTEXITCODE -ne 0 -or $imageId -ne $Image) {
    throw "Pinned image is absent or has the wrong identity: $imageId"
}

$archive = Join-Path $RunDir "sanitized-baseline.tar"
& git -C $RepoRoot -c core.autocrlf=false archive `
    --format=tar --output=$archive $SourceCommit `
    scripts/hooks/pre-push scripts/lib `
    governance_tools/version_bump_guard.py tests/test_version_bump_guard.py
if ($LASTEXITCODE -ne 0) {
    throw "Sanitized baseline archive failed."
}

Invoke-Docker run -d --name $Container --network none --read-only `
    --tmpfs "/tmp:rw,noexec,nosuid,size=64m" `
    --tmpfs "/work:rw,nosuid,uid=65532,gid=65532,size=512m" `
    --cap-drop ALL --security-opt no-new-privileges `
    $Image python -c "import time; time.sleep(86400)"

try {
    Invoke-Docker inspect $Container | Set-Content -Encoding utf8 `
        -LiteralPath (Join-Path $RunDir "container-inspect.json")
    Invoke-Docker exec -u 65532:65532 $Container mkdir -p `
        /work/repo /work/out /work/vendor /work/input
    & $Python $StreamInput --container $Container --kind baseline --source $archive
    if ($LASTEXITCODE -ne 0) {
        throw "Streaming the sanitized baseline into /work failed."
    }
    & $Python $StreamInput --container $Container --kind pytest --source $Payload
    if ($LASTEXITCODE -ne 0) {
        throw "Streaming the offline pytest payload into /work failed."
    }
    & $Python $StreamInput --container $Container --kind task `
        --source (Join-Path $RepoRoot "artifacts\experiments\prepush-bugfix-20260724\arm-dispatch-packet.md")
    if ($LASTEXITCODE -ne 0) {
        throw "Streaming the fixed input packet into /work failed."
    }
    Invoke-Docker exec -u 65532:65532 $Container `
        tar -xf /work/sanitized-baseline.tar -C /work/repo
    Invoke-Docker exec -u 65532:65532 -w /work/repo $Container `
        git init -b main
    Invoke-Docker exec -u 65532:65532 -w /work/repo $Container `
        git config core.autocrlf false
    Invoke-Docker exec -u 65532:65532 -w /work/repo $Container `
        git config user.name gate2-admission
    Invoke-Docker exec -u 65532:65532 -w /work/repo $Container `
        git config user.email gate2-admission@invalid
    Invoke-Docker exec -u 65532:65532 -w /work/repo $Container git add -A
    Invoke-Docker exec -u 65532:65532 -w /work/repo `
        -e GIT_AUTHOR_DATE=2026-07-27T00:00:00Z `
        -e GIT_COMMITTER_DATE=2026-07-27T00:00:00Z `
        $Container git commit -m "Gate 2 sanitized admission baseline"

    $actualTree = (& docker exec -u 65532:65532 -w /work/repo `
        $Container git rev-parse "HEAD^{tree}").Trim()
    if ($actualTree -ne $ExpectedTree) {
        throw "Sanitized tree mismatch: $actualTree"
    }
    $crlfPaths = (& docker exec -u 65532:65532 -w /work/repo $Container `
        grep -rlU ([char]13) . --exclude-dir=.git)
    if ($LASTEXITCODE -eq 0 -and $crlfPaths) {
        throw "Sanitized working tree contains CR bytes: $crlfPaths"
    }
    if ($LASTEXITCODE -notin @(0, 1)) {
        throw "LF-only verification could not run."
    }

    $env:GATE2_CANARY_CONTAINER = $Container
    $env:GATE2_POLICY = $Policy
    $env:GATE2_ADAPTER_LOG = Join-Path $RunDir "adapter-log.jsonl"
    $env:GATE2_TREATMENT_VALIDATORS = "1"

    Capture-Adapter "00-input-read" @("read", "input/TASK.md") 0
    Capture-Adapter "01-baseline-test" @("test") 0
    $baselineTest = Get-Content -Raw -LiteralPath `
        (Join-Path $RunDir "01-baseline-test.stdout.txt")
    if ($baselineTest -notmatch "4 passed") {
        throw "Offline pytest did not execute all four frozen tests."
    }
    Capture-Adapter "01b-baseline-validate" @("validate") 0
    $validatorOutput = Get-Content -Raw -LiteralPath `
        (Join-Path $RunDir "01b-baseline-validate.stdout.txt")
    if ($validatorOutput -notmatch "\[shellcheck exit=1\]" -or
        $validatorOutput -notmatch "\[ruff exit=1\]" -or
        $validatorOutput -notmatch "\[mypy exit=0\]") {
        throw "Pinned treatment validator exits do not match the signed expectation."
    }

    Capture-Adapter "02-baseline-reproduce" @("reproduce") 1
    $baselineRepro = Get-Content -Raw -LiteralPath `
        (Join-Path $RunDir "02-baseline-reproduce.stdout.txt")
    if ($baselineRepro -notmatch '"verdict": "FAIL"' -or
        $baselineRepro -notmatch '"marker_reported": false') {
        throw "Baseline reproduction did not expose the frozen defect."
    }

    $hook = (& git -C $RepoRoot show "${SourceCommit}:scripts/hooks/pre-push") -join "`n"
    $positiveControl = @"
# Admission-only positive control; never enters an arm baseline.
echo "changed_files=1"
echo "gate2-pushed-ref-marker.txt"
exit 0
"@
    $hook = [Text.RegularExpressions.Regex]::Replace(
        $hook,
        "\nexit 0\s*$",
        "`n$positiveControl"
    )
    if ($hook -notmatch "Admission-only positive control") {
        throw "Could not install the admission-only positive control."
    }
    $hookBytes = [Text.Encoding]::UTF8.GetBytes($hook)
    $hookB64 = [Convert]::ToBase64String($hookBytes)
    Capture-Adapter "03-write-positive-control" `
        @("write", "scripts/hooks/pre-push", $hookB64) 0
    Capture-Adapter "04-mutated-test" @("test") 0
    Capture-Adapter "05-positive-reproduce" @("reproduce") 0
    $positiveRepro = Get-Content -Raw -LiteralPath `
        (Join-Path $RunDir "05-positive-reproduce.stdout.txt")
    if ($positiveRepro -notmatch '"verdict": "PASS"') {
        throw "Positive reproduction control did not pass."
    }
    Capture-Adapter "06-diff" @("diff") 0
    Capture-Adapter "07-status" @("status") 0
    Capture-Adapter "08-commit" @("commit") 0
    Capture-Adapter "09-final-status" @("status") 0
    $finalStatus = Get-Content -Raw -LiteralPath `
        (Join-Path $RunDir "09-final-status.stdout.txt")
    if ($finalStatus.Trim()) {
        throw "Admission workspace is dirty after the fixed commit operation."
    }

    $summary = [ordered]@{
        admission = "PASS"
        run_id = $RunId
        image_id = $imageId
        platform = "linux/amd64"
        source_commit = $SourceCommit
        sanitized_tree = $actualTree
        offline_pytest_sha256 = $payloadSha
        offline_pytest_packages = $manifestObject.packages
        baseline_tests = "4 passed"
        fixed_input_read = "PASS"
        arm_d_validator_feedback = "shellcheck=1, ruff=1, mypy=0"
        baseline_reproduction = "FAIL as expected (pushed marker not reported)"
        positive_control_reproduction = "PASS"
        output_commit_created = $true
        final_status_clean = $true
        formal_arm_started = $false
    }
    $summary | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 `
        -LiteralPath (Join-Path $RunDir "admission-summary.json")
}
finally {
    & docker stop $Container | Out-Null
}

Write-Output $RunDir
