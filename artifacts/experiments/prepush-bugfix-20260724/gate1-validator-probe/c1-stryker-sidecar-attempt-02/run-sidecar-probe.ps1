param(
    [Parameter(Mandatory = $true)]
    [string]$FrameworkRepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$ConsumerRepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$FrameworkCommit,

    [Parameter(Mandatory = $true)]
    [string]$RemoteBranch,

    [Parameter(Mandatory = $true)]
    [string]$RunRoot,

    [string]$DockerPath = "C:/Users/daish/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$probeId = "c1-stryker-sidecar-materialization-20260821-02"
$baselineCommit = "15d5d51356b4808e5fb12782961a94d9985b2ae6"
$baselineTree = "a6946a0ba48f161f40e7ae7e3a4322bdef704e9a"
$image = "docker.io/library/node@sha256:d649c27dae7ba0137b3cef5dd75baa422c08dc3d9e3fc0c23dfb172dc3cc6436"
$attempt01Commit = "f7831551e2988e590734288de66fff2db1c5369c"
$attempt01Root = "artifacts/experiments/prepush-bugfix-20260724/gate1-validator-probe/c1-stryker-sidecar"
$sharedRoot = "artifacts/experiments/prepush-bugfix-20260724/gate1-validator-probe/c1-stryker"
$attempt02Root = "artifacts/experiments/prepush-bugfix-20260724/gate1-validator-probe/c1-stryker-sidecar-attempt-02"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$totalWatch = [System.Diagnostics.Stopwatch]::StartNew()

function Write-Utf8Json {
    param([string]$Path, [object]$Value)
    $json = ConvertTo-Json -InputObject $Value -Depth 20
    [System.IO.File]::WriteAllText($Path, $json + "`n", $utf8NoBom)
}

function Get-Sha256Lower {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Invoke-ProcessCapture {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$StdoutPath,
        [string]$StderrPath,
        [int]$TimeoutSeconds,
        [string]$ContainerName = ""
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    foreach ($argument in $ArgumentList) {
        $psi.ArgumentList.Add($argument)
    }

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) {
        throw "PROCESS_START_FAILED:$FilePath"
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
    if ($timedOut) {
        if ($ContainerName) {
            & $DockerPath kill $ContainerName 2>$null | Out-Null
        }
        try { $process.Kill($true) } catch { }
        $process.WaitForExit()
    }
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $watch.Stop()
    [System.IO.File]::WriteAllText($StdoutPath, $stdout, $utf8NoBom)
    [System.IO.File]::WriteAllText($StderrPath, $stderr, $utf8NoBom)

    [ordered]@{
        file = $FilePath
        arguments = @($ArgumentList)
        exit_code = if ($timedOut) { $null } else { $process.ExitCode }
        timed_out = $timedOut
        wall_seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
        stdout = [System.IO.Path]::GetFileName($StdoutPath)
        stderr = [System.IO.Path]::GetFileName($StderrPath)
    }
}

function Assert-StepPassed {
    param([object]$Step, [string]$Label)
    if ($Step.timed_out -or $Step.exit_code -ne 0) {
        throw "SIDECAR_RESOLUTION_FAILED:${Label}:exit=$($Step.exit_code):timeout=$($Step.timed_out)"
    }
}

if (Test-Path -LiteralPath $RunRoot) {
    throw "SIDECAR_RESOLUTION_FAILED:RUN_ROOT_ALREADY_EXISTS:$RunRoot"
}
New-Item -ItemType Directory -Path $RunRoot | Out-Null
$runRootResolved = (Resolve-Path -LiteralPath $RunRoot).Path
$baselineDir = Join-Path $runRootResolved "baseline"
$consumerDir = Join-Path $runRootResolved "consumer"
$toolDir = Join-Path $runRootResolved "tool"
$probeInputDir = Join-Path $runRootResolved "probe-input"
$evidenceDir = Join-Path $runRootResolved "evidence"
$frameworkExportDir = Join-Path $runRootResolved "framework-export"
$inputSourceDir = Join-Path $runRootResolved "input-source"
foreach ($directory in @($baselineDir, $consumerDir, $toolDir, $probeInputDir, $evidenceDir, $frameworkExportDir, $inputSourceDir)) {
    New-Item -ItemType Directory -Path $directory | Out-Null
}

$steps = [ordered]@{}
$dockerPhases = [System.Collections.Generic.List[object]]::new()
$functionalFailure = $null
$graphChanged = $false
$leakageBlocked = $false
$costBlocked = $false
$mountViolation = $false
$deniedHits = [System.Collections.Generic.List[object]]::new()

function Invoke-DockerPhase {
    param(
        [string]$Name,
        [string]$Network,
        [string]$ContainerWorkingDirectory,
        [string[]]$Environment,
        [string[]]$Command,
        [int]$TimeoutSeconds
    )

    $containerName = "c1-sidecar-a02-$Name-" + [guid]::NewGuid().ToString("N").Substring(0, 10)
    $arguments = [System.Collections.Generic.List[string]]::new()
    foreach ($value in @(
        "run", "--name", $containerName,
        "--platform", "linux/amd64",
        "--network", $Network,
        "--cpus", "2",
        "--memory", "2g",
        "--pids-limit", "512",
        "--mount", "type=bind,source=$consumerDir,target=/consumer",
        "--mount", "type=bind,source=$toolDir,target=/tool",
        "--mount", "type=bind,source=$probeInputDir,target=/probe-input,readonly",
        "--mount", "type=bind,source=$evidenceDir,target=/evidence",
        "--workdir", $ContainerWorkingDirectory
    )) { $arguments.Add($value) }
    foreach ($entry in $Environment) {
        $arguments.Add("--env")
        $arguments.Add($entry)
    }
    $arguments.Add($image)
    foreach ($entry in $Command) { $arguments.Add($entry) }

    $stdoutPath = Join-Path $evidenceDir "$Name.stdout.txt"
    $stderrPath = Join-Path $evidenceDir "$Name.stderr.txt"
    $result = Invoke-ProcessCapture -FilePath $DockerPath -ArgumentList $arguments.ToArray() -WorkingDirectory $runRootResolved -StdoutPath $stdoutPath -StderrPath $stderrPath -TimeoutSeconds $TimeoutSeconds -ContainerName $containerName

    $inspectStatePath = Join-Path $evidenceDir "$Name.container-state.json"
    $inspectMountsPath = Join-Path $evidenceDir "$Name.container-mounts.json"
    $inspectStateError = Join-Path $evidenceDir "$Name.container-state.stderr.txt"
    $inspectMountsError = Join-Path $evidenceDir "$Name.container-mounts.stderr.txt"
    $state = Invoke-ProcessCapture -FilePath $DockerPath -ArgumentList @("inspect", $containerName, "--format", "{{json .State}}") -WorkingDirectory $runRootResolved -StdoutPath $inspectStatePath -StderrPath $inspectStateError -TimeoutSeconds 30
    $mounts = Invoke-ProcessCapture -FilePath $DockerPath -ArgumentList @("inspect", $containerName, "--format", "{{json .Mounts}}") -WorkingDirectory $runRootResolved -StdoutPath $inspectMountsPath -StderrPath $inspectMountsError -TimeoutSeconds 30
    & $DockerPath rm -f $containerName 2>$null | Out-Null

    $oomKilled = $false
    if ($state.exit_code -eq 0) {
        try {
            $stateObject = (Get-Content -Raw -LiteralPath $inspectStatePath).Trim() | ConvertFrom-Json
            $oomKilled = [bool]$stateObject.OOMKilled
        }
        catch { }
    }
    $result["container_name"] = $containerName
    $result["network"] = $Network
    $result["container_working_directory"] = $ContainerWorkingDirectory
    $result["oom_killed"] = $oomKilled
    $result["state_inspect_exit_code"] = $state.exit_code
    $result["mount_inspect_exit_code"] = $mounts.exit_code
    $dockerPhases.Add($result)
    return $result
}

try {
    $selfTestPath = Join-Path $frameworkExportDir "$attempt02Root/test-materialize-sidecar-inputs.ps1"
    $materializerPath = Join-Path $frameworkExportDir "$attempt02Root/materialize-sidecar-inputs.ps1"
    $manifestPath = Join-Path $frameworkExportDir "$attempt02Root/validator-sidecar-probe-manifest.json"

    if (-not (Test-Path -LiteralPath $DockerPath -PathType Leaf)) {
        throw "SIDECAR_RESOLUTION_FAILED:DOCKER_CLI_MISSING:$DockerPath"
    }

    $remoteStdout = Join-Path $evidenceDir "remote-binding.stdout.txt"
    $remoteStderr = Join-Path $evidenceDir "remote-binding.stderr.txt"
    $remoteStep = Invoke-ProcessCapture -FilePath "git" -ArgumentList @("-C", $FrameworkRepoRoot, "ls-remote", "origin", "refs/heads/$RemoteBranch") -WorkingDirectory $runRootResolved -StdoutPath $remoteStdout -StderrPath $remoteStderr -TimeoutSeconds 60
    $steps["remote_binding"] = $remoteStep
    Assert-StepPassed $remoteStep "REMOTE_BINDING_COMMAND"
    $remoteHead = ((Get-Content -Raw -LiteralPath $remoteStdout).Trim() -split "\s+")[0]
    if ($remoteHead -ne $FrameworkCommit) {
        throw "SIDECAR_RESOLUTION_FAILED:REMOTE_HEAD:$remoteHead"
    }

    $actualTree = (& git -C $ConsumerRepoRoot rev-parse "$baselineCommit^{tree}").Trim()
    if ($LASTEXITCODE -ne 0 -or $actualTree -ne $baselineTree) {
        throw "SIDECAR_RESOLUTION_FAILED:BASELINE_TREE:$actualTree"
    }

    $consumerArchive = Join-Path $runRootResolved "consumer-baseline.tar"
    & git -C $ConsumerRepoRoot archive --format=tar "--output=$consumerArchive" $baselineCommit
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:CONSUMER_ARCHIVE" }
    & tar -xf $consumerArchive -C $baselineDir
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:BASELINE_EXTRACT" }
    & tar -xf $consumerArchive -C $consumerDir
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:CONSUMER_EXTRACT" }

    $reusedArchive = Join-Path $runRootResolved "framework-reused-inputs.tar"
    $reusedPaths = @(
        "$attempt01Root/tool/package.json",
        "$attempt01Root/tool/package-lock.json",
        "$attempt01Root/plugin-entry-binding.json",
        "$attempt01Root/resolution-probe.mjs",
        "$attempt01Root/dependency-graph-fingerprint.mjs",
        "$attempt01Root/stryker.sidecar.config.mjs",
        "$attempt01Root/vitest.sidecar-probe.config.mjs",
        "$sharedRoot/diff_to_mutation_ranges.py",
        "$sharedRoot/probe-fixture/src/validator-probe-fixture.ts",
        "$sharedRoot/probe-fixture/src/__tests__/validator-probe-fixture.test.ts"
    )
    $reusedArchiveArguments = @("-C", $FrameworkRepoRoot, "archive", "--format=tar", "--output=$reusedArchive", $attempt01Commit, "--") + $reusedPaths
    & git @reusedArchiveArguments
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:REUSED_FRAMEWORK_ARCHIVE" }
    & tar -xf $reusedArchive -C $frameworkExportDir
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:REUSED_FRAMEWORK_EXTRACT" }

    $attempt02Archive = Join-Path $runRootResolved "framework-attempt02-inputs.tar"
    $attempt02Paths = @(
        "$attempt02Root/.gitattributes",
        "$attempt02Root/materialize-sidecar-inputs.ps1",
        "$attempt02Root/test-materialize-sidecar-inputs.ps1",
        "$attempt02Root/run-sidecar-probe.ps1",
        "$attempt02Root/validator-sidecar-probe-manifest.json"
    )
    $attempt02ArchiveArguments = @("-C", $FrameworkRepoRoot, "archive", "--format=tar", "--output=$attempt02Archive", $FrameworkCommit, "--") + $attempt02Paths
    & git @attempt02ArchiveArguments
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:ATTEMPT02_FRAMEWORK_ARCHIVE" }
    & tar -xf $attempt02Archive -C $frameworkExportDir
    if ($LASTEXITCODE -ne 0) { throw "SIDECAR_RESOLUTION_FAILED:ATTEMPT02_FRAMEWORK_EXTRACT" }

    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    if ($manifest.probe_id -ne $probeId) { throw "SIDECAR_RESOLUTION_FAILED:PROBE_ID" }
    if ($manifest.reused_design_commit -ne $attempt01Commit) { throw "SIDECAR_RESOLUTION_FAILED:REUSED_COMMIT" }
    if ((Get-Sha256Lower $DockerPath) -ne $manifest.execution_environment.host_docker_cli.sha256 -or (Get-Item -LiteralPath $DockerPath).Length -ne $manifest.execution_environment.host_docker_cli.bytes) {
        throw "SIDECAR_RESOLUTION_FAILED:DOCKER_CLI_BINDING"
    }

    $dockerVersionStdout = Join-Path $evidenceDir "docker-version.json"
    $dockerVersionStderr = Join-Path $evidenceDir "docker-version.stderr.txt"
    $dockerVersionStep = Invoke-ProcessCapture -FilePath $DockerPath -ArgumentList @("version", "--format", "{{json .}}") -WorkingDirectory $runRootResolved -StdoutPath $dockerVersionStdout -StderrPath $dockerVersionStderr -TimeoutSeconds 60
    $steps["docker_version"] = $dockerVersionStep
    Assert-StepPassed $dockerVersionStep "DOCKER_VERSION"
    $dockerVersion = (Get-Content -Raw -LiteralPath $dockerVersionStdout).Trim() | ConvertFrom-Json
    if ($dockerVersion.Client.Version -ne $manifest.execution_environment.host_docker_cli.client_version -or $dockerVersion.Server.Version -ne $manifest.execution_environment.host_docker_cli.server_version -or $dockerVersion.Server.Platform.Name -ne $manifest.execution_environment.host_docker_cli.server_platform) {
        throw "SIDECAR_RESOLUTION_FAILED:DOCKER_VERSION_BINDING"
    }

    foreach ($binding in $manifest.frozen_harness_bindings) {
        $sourcePath = Join-Path (Split-Path -Parent $manifestPath) $binding.path
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "SIDECAR_RESOLUTION_FAILED:HARNESS_INPUT_MISSING:$($binding.path)"
        }
        if ((Get-Sha256Lower $sourcePath) -ne $binding.sha256 -or (Get-Item -LiteralPath $sourcePath).Length -ne $binding.bytes) {
            throw "SIDECAR_RESOLUTION_FAILED:HARNESS_INPUT_BINDING:$($binding.path)"
        }
    }

    foreach ($binding in $manifest.reused_input_bindings) {
        $sourcePath = Join-Path $frameworkExportDir $binding.source_path
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "SIDECAR_RESOLUTION_FAILED:INPUT_MISSING:$($binding.source_path)"
        }
        if ((Get-Sha256Lower $sourcePath) -ne $binding.sha256 -or (Get-Item -LiteralPath $sourcePath).Length -ne $binding.bytes) {
            throw "SIDECAR_RESOLUTION_FAILED:INPUT_BINDING:$($binding.source_path)"
        }
        $destinationPath = Join-Path $inputSourceDir $binding.materialized_path
        New-Item -ItemType Directory -Path (Split-Path -Parent $destinationPath) -Force | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $destinationPath
    }

    $selfTestOutput = Join-Path $evidenceDir "materialization-self-test.json"
    $selfTestStdout = Join-Path $evidenceDir "materialization-self-test.stdout.txt"
    $selfTestStderr = Join-Path $evidenceDir "materialization-self-test.stderr.txt"
    $selfTestStep = Invoke-ProcessCapture -FilePath "pwsh" -ArgumentList @("-NoProfile", "-File", $selfTestPath, "-OutputPath", $selfTestOutput) -WorkingDirectory $runRootResolved -StdoutPath $selfTestStdout -StderrPath $selfTestStderr -TimeoutSeconds 60
    $steps["materialization_self_test"] = $selfTestStep
    Assert-StepPassed $selfTestStep "MATERIALIZATION_SELF_TEST"
    $selfTest = Get-Content -Raw -LiteralPath $selfTestOutput | ConvertFrom-Json
    if ($selfTest.status -ne "PASS") { throw "SIDECAR_RESOLUTION_FAILED:MATERIALIZATION_SELF_TEST_STATUS" }

    . $materializerPath
    $materialization = Copy-ExactDirectoryChildren -Source $inputSourceDir -Destination $probeInputDir
    Write-Utf8Json -Path (Join-Path $evidenceDir "materialization-inventory.json") -Value $materialization
    if ($materialization.file_count -ne $manifest.expected_materialized_file_count) {
        throw "SIDECAR_RESOLUTION_FAILED:MATERIALIZATION_FILE_COUNT:$($materialization.file_count)"
    }

    Copy-Item -LiteralPath (Join-Path $probeInputDir "tool/package.json") -Destination (Join-Path $toolDir "package.json")
    Copy-Item -LiteralPath (Join-Path $probeInputDir "tool/package-lock.json") -Destination (Join-Path $toolDir "package-lock.json")
    New-Item -ItemType Directory -Path (Join-Path $consumerDir "src/__tests__") -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $probeInputDir "probe-fixture/src/validator-probe-fixture.ts") -Destination (Join-Path $consumerDir "src/validator-probe-fixture.ts")
    Copy-Item -LiteralPath (Join-Path $probeInputDir "probe-fixture/src/__tests__/validator-probe-fixture.test.ts") -Destination (Join-Path $consumerDir "src/__tests__/validator-probe-fixture.test.ts")
    Copy-Item -LiteralPath (Join-Path $probeInputDir "vitest.sidecar-probe.config.mjs") -Destination (Join-Path $consumerDir "vitest.sidecar-probe.config.mjs")

    $rangeStdout = Join-Path $evidenceDir "range-adapter.stdout.txt"
    $rangeStderr = Join-Path $evidenceDir "range-adapter.stderr.txt"
    $rangeOutput = Join-Path $evidenceDir "mutation-ranges.json"
    $pythonPath = "C:/Users/daish/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
    $rangeStep = Invoke-ProcessCapture -FilePath $pythonPath -ArgumentList @((Join-Path $probeInputDir "diff_to_mutation_ranges.py"), "--baseline-root", $baselineDir, "--candidate-root", $consumerDir, "--output", $rangeOutput) -WorkingDirectory $runRootResolved -StdoutPath $rangeStdout -StderrPath $rangeStderr -TimeoutSeconds 60
    $steps["mutation_range"] = $rangeStep
    Assert-StepPassed $rangeStep "MUTATION_RANGE"
    $rangeRecord = Get-Content -Raw -LiteralPath $rangeOutput | ConvertFrom-Json
    $rangeJson = ConvertTo-Json -InputObject @($rangeRecord.mutate_ranges) -Compress
    if ($rangeJson -cne '["src/validator-probe-fixture.ts:1-4"]') {
        throw "SIDECAR_RESOLUTION_FAILED:MUTATION_RANGE_VALUE:$rangeJson"
    }
    $excludedJson = ConvertTo-Json -InputObject @($rangeRecord.excluded_changed_paths) -Compress
    if ($excludedJson -cne '["src/__tests__/validator-probe-fixture.test.ts","vitest.sidecar-probe.config.mjs"]') {
        throw "SIDECAR_RESOLUTION_FAILED:MUTATION_EXCLUSION_VALUE:$excludedJson"
    }

    $toolInstall = Invoke-DockerPhase -Name "tool-npm-ci" -Network "bridge" -ContainerWorkingDirectory "/tool" -Environment @() -Command @("npm", "ci") -TimeoutSeconds 300
    $steps["tool_npm_ci"] = $toolInstall
    Assert-StepPassed $toolInstall "TOOL_NPM_CI"

    $consumerInstall = Invoke-DockerPhase -Name "consumer-npm-ci" -Network "bridge" -ContainerWorkingDirectory "/consumer" -Environment @() -Command @("npm", "ci") -TimeoutSeconds 600
    $steps["consumer_npm_ci"] = $consumerInstall
    Assert-StepPassed $consumerInstall "CONSUMER_NPM_CI"

    $fingerprintBefore = Invoke-DockerPhase -Name "consumer-graph-before" -Network "none" -ContainerWorkingDirectory "/consumer" -Environment @() -Command @("node", "/probe-input/dependency-graph-fingerprint.mjs") -TimeoutSeconds 120
    $steps["consumer_graph_before"] = $fingerprintBefore
    Assert-StepPassed $fingerprintBefore "CONSUMER_GRAPH_BEFORE"

    $resolution = Invoke-DockerPhase -Name "resolution-probe" -Network "none" -ContainerWorkingDirectory "/consumer" -Environment @() -Command @("node", "/probe-input/resolution-probe.mjs") -TimeoutSeconds 120
    $steps["resolution_probe"] = $resolution
    Assert-StepPassed $resolution "RESOLUTION_PROBE"

    $timeoutSentinel = Invoke-DockerPhase -Name "timeout-sentinel" -Network "none" -ContainerWorkingDirectory "/consumer" -Environment @() -Command @("node", "-e", "setTimeout(() => {}, 10000)") -TimeoutSeconds 2
    $steps["timeout_sentinel"] = $timeoutSentinel
    if (-not $timeoutSentinel.timed_out -or $timeoutSentinel.oom_killed) {
        throw "SIDECAR_RESOLUTION_FAILED:TIMEOUT_SENTINEL:timeout=$($timeoutSentinel.timed_out):oom=$($timeoutSentinel.oom_killed)"
    }

    $dryRun = Invoke-DockerPhase -Name "stryker-dry-run" -Network "none" -ContainerWorkingDirectory "/consumer" -Environment @(
        "C1_SIDECAR_MUTATE_RANGES_JSON=$rangeJson",
        "C1_SIDECAR_DRY_RUN_ONLY=1",
        "C1_SIDECAR_RUNTIME_EVIDENCE_DIR=/evidence",
        "C1_SIDECAR_RUNTIME_PHASE=dry-run"
    ) -Command @("node", "/tool/node_modules/@stryker-mutator/core/bin/stryker.js", "run", "/probe-input/stryker.sidecar.config.mjs") -TimeoutSeconds 300
    $steps["stryker_dry_run"] = $dryRun
    Assert-StepPassed $dryRun "STRYKER_DRY_RUN"

    $mutation = Invoke-DockerPhase -Name "stryker-mutation" -Network "none" -ContainerWorkingDirectory "/consumer" -Environment @(
        "C1_SIDECAR_MUTATE_RANGES_JSON=$rangeJson",
        "C1_SIDECAR_DRY_RUN_ONLY=0",
        "C1_SIDECAR_RUNTIME_EVIDENCE_DIR=/evidence",
        "C1_SIDECAR_RUNTIME_PHASE=mutation"
    ) -Command @("node", "/tool/node_modules/@stryker-mutator/core/bin/stryker.js", "run", "/probe-input/stryker.sidecar.config.mjs") -TimeoutSeconds 300
    $steps["stryker_mutation"] = $mutation
    Assert-StepPassed $mutation "STRYKER_MUTATION"

    $fingerprintAfter = Invoke-DockerPhase -Name "consumer-graph-after" -Network "none" -ContainerWorkingDirectory "/consumer" -Environment @() -Command @("node", "/probe-input/dependency-graph-fingerprint.mjs") -TimeoutSeconds 120
    $steps["consumer_graph_after"] = $fingerprintAfter
    Assert-StepPassed $fingerprintAfter "CONSUMER_GRAPH_AFTER"

    $beforeGraph = Get-Content -Raw -LiteralPath (Join-Path $evidenceDir "consumer-graph-before.stdout.txt") | ConvertFrom-Json
    $afterGraph = Get-Content -Raw -LiteralPath (Join-Path $evidenceDir "consumer-graph-after.stdout.txt") | ConvertFrom-Json
    foreach ($field in @("package_json_sha256", "package_lock_sha256", "node_modules_package_lock_sha256", "npm_ls_exit_code", "npm_ls_canonical_sha256", "npm_ls_stderr_sha256")) {
        if ($beforeGraph.$field -ne $afterGraph.$field) { $graphChanged = $true }
    }

    $runtimeRecords = @(Get-ChildItem -LiteralPath $evidenceDir -Filter "vitest-runtime-resolution-*.json" -File)
    if ($runtimeRecords.Count -lt 2) {
        throw "SIDECAR_RESOLUTION_FAILED:VITEST_RUNTIME_RECORD_COUNT:$($runtimeRecords.Count)"
    }
}
catch {
    $functionalFailure = $_.Exception.Message
}
finally {
    $totalWatch.Stop()

    foreach ($phase in $dockerPhases) {
        if ($phase.oom_killed) { $costBlocked = $true }
        $mountPath = Join-Path $evidenceDir "$($phase.container_name -replace '^c1-sidecar-a02-|-[0-9a-f]{10}$','').container-mounts.json"
        if (Test-Path -LiteralPath $mountPath) {
            try {
                $mounts = (Get-Content -Raw -LiteralPath $mountPath).Trim() | ConvertFrom-Json
                $destinations = @($mounts | ForEach-Object { $_.Destination } | Sort-Object)
                $expected = @("/consumer", "/evidence", "/probe-input", "/tool")
                if ((ConvertTo-Json $destinations -Compress) -cne (ConvertTo-Json $expected -Compress)) { $mountViolation = $true }
                foreach ($mount in $mounts) {
                    if ([System.IO.Path]::GetFullPath($mount.Source).TrimEnd('\') -ieq [System.IO.Path]::GetFullPath($ConsumerRepoRoot).TrimEnd('\')) {
                        $mountViolation = $true
                    }
                }
            }
            catch { $mountViolation = $true }
        }
    }

    $denied = @("a607564", "softmap", "softmissbooks", "master-existing", "mixed-batch", "attempt-c1", "oracle_does_not_discriminate", "gate3-c1-method-sensitivity", "gate1-c1-bugfix-skill-proposal")
    foreach ($file in @(Get-ChildItem -LiteralPath $evidenceDir -File | Where-Object { $_.Name -notin @("non-leakage-scan.json", "probe-terminal.json") })) {
        $text = ""
        try { $text = [System.IO.File]::ReadAllText($file.FullName) } catch { continue }
        foreach ($literal in $denied) {
            if ($text.IndexOf($literal, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
                $deniedHits.Add([ordered]@{ file = $file.Name; literal = $literal })
            }
        }
    }
    if ($deniedHits.Count -gt 0 -or $mountViolation) { $leakageBlocked = $true }
    if ($totalWatch.Elapsed.TotalSeconds -gt 900) { $costBlocked = $true }

    $leakageRecord = [ordered]@{
        schema = "c1-stryker-sidecar-non-leakage.v1"
        scanned_surface_count = @(Get-ChildItem -LiteralPath $evidenceDir -File | Where-Object { $_.Name -notin @("non-leakage-scan.json", "probe-terminal.json") }).Count
        denied_match_count = $deniedHits.Count
        denied_matches = @($deniedHits)
        mount_violation = $mountViolation
        consumer_worktree_mounted = $mountViolation
    }
    Write-Utf8Json -Path (Join-Path $evidenceDir "non-leakage-scan.json") -Value $leakageRecord

    if ($leakageBlocked) {
        $terminal = "SIDECAR_LEAKAGE_BLOCKED"
    }
    elseif ($graphChanged) {
        $terminal = "CONSUMER_GRAPH_CHANGED"
    }
    elseif ($costBlocked) {
        $terminal = "SIDECAR_COST_BLOCKED"
    }
    elseif ($null -ne $functionalFailure) {
        $terminal = "SIDECAR_RESOLUTION_FAILED"
    }
    else {
        $terminal = "SIDECAR_BOUNDARY_PASSED"
    }

    $artifactRecords = foreach ($file in @(Get-ChildItem -LiteralPath $evidenceDir -File | Where-Object { $_.Name -ne "probe-terminal.json" } | Sort-Object Name)) {
        [ordered]@{
            path = $file.Name
            sha256 = Get-Sha256Lower $file.FullName
            bytes = [int64]$file.Length
        }
    }
    $terminalRecord = [ordered]@{
        schema = "c1-stryker-sidecar-probe-terminal.v2"
        probe_id = $probeId
        terminal = $terminal
        completed_at_utc = [DateTime]::UtcNow.ToString("o")
        bindings = [ordered]@{
            framework_commit = $FrameworkCommit
            remote_branch = $RemoteBranch
            source_baseline_commit = $baselineCommit
            source_baseline_tree = $baselineTree
            reused_design_commit = $attempt01Commit
            image = $image
            manifest_sha256 = $(if (Test-Path -LiteralPath $manifestPath) { Get-Sha256Lower $manifestPath } else { $null })
            manifest_bytes = $(if (Test-Path -LiteralPath $manifestPath) { [int64](Get-Item -LiteralPath $manifestPath).Length } else { $null })
        }
        materialization_only_delta = $true
        steps = $steps
        functional_failure = $functionalFailure
        classification = [ordered]@{
            leakage_blocked = $leakageBlocked
            consumer_graph_changed = $graphChanged
            cost_blocked = $costBlocked
            resolution_failed = ($null -ne $functionalFailure)
            selected_terminal = $terminal
        }
        resources = [ordered]@{
            total_wall_seconds = [Math]::Round($totalWatch.Elapsed.TotalSeconds, 3)
            ceiling_seconds = 900
            docker_phase_count = $dockerPhases.Count
            any_oom_killed = @($dockerPhases | Where-Object { $_.oom_killed }).Count -gt 0
        }
        repair_in_place = $false
        retry_authorized = $false
        artifacts = @($artifactRecords)
        claim_ceiling = "This terminal establishes only the result of one exact C1 Stryker sidecar attempt-02 whose sole intended design delta from attempt-01 is the frozen exact-input materialization harness. It cannot establish validator effect, Skill effect, general sidecar reuse, Gate 1 readiness, preregistration, freeze, or any A/B/C/D result."
        not_claimed = @("validator effect", "Skill effect", "general sidecar reuse", "Gate 1 readiness", "preregistration", "Gate 1 freeze", "A/B/C/D result")
    }
    Write-Utf8Json -Path (Join-Path $evidenceDir "probe-terminal.json") -Value $terminalRecord
    Write-Output ("terminal={0}" -f $terminal)
    Write-Output ("terminal_path={0}" -f (Join-Path $evidenceDir "probe-terminal.json"))
}
