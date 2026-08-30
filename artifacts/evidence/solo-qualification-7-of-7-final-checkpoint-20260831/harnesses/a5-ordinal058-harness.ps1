param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{64}$')]
    [string]$ExpectedSourceSha256
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExpectedPowerShell = @{
    Path = 'C:\Users\daish\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    Length = 301368
    Sha256 = 'db6dd81183fe57d22e03b911ec9a30a2fd7c40542e97743615355a6fb44f458f'
}
$ExpectedGit = @{
    Path = 'C:\Program Files\Git\cmd\git.exe'
    Length = 46480
    Sha256 = '3cbd024d9d11ef08bd6a0cb5a973613c50825b4952bc6006f3f4222f436091e5'
}
$ExpectedTar = @{
    Path = 'C:\Windows\System32\tar.exe'
    Length = 92176
    Sha256 = '9b77d4c912f2edae8c241d0ece1094d2ac068b084269ceaf85d7c7b085d2ae86'
}
$ExpectedNode = @{
    Path = 'C:\Program Files\nodejs\node.exe'
    Length = 89953280
    Sha256 = 'd14ba95cdce1ef7dc9ad3ac74949ca5db38b27378ee30f30a23cf26f9e875a11'
}
$ExpectedTsx = @(
    @{
        Path = 'D:\Hearth\node_modules\tsx\package.json'
        Length = 1624
        Sha256 = '6e764b21991c21595441f82387c1451ccd10a3e7a3f0973cc5e3649a12dea7d2'
    },
    @{
        Path = 'D:\Hearth\node_modules\tsx\dist\loader.mjs'
        Length = 729
        Sha256 = '0b1c5b86192772fe9257710e739959cee5947c11ae1f93b61abfaa9b80c6def1'
    }
)

$ExpectedLaunchCwd = 'D:\ai-governance-framework'
$Repository = 'D:\Hearth'
$GitSafeDirectory = 'D:/Hearth'
$ExpectedGitDirectory = 'D:\Hearth\.git'
$GitConfigArguments = @('-c', "safe.directory=$GitSafeDirectory", '-c', 'core.hooksPath=')
$BaseCommit = '61124b55e777357749beb82d3f724dec7978bdd2'
$FixCommit = '1aacc03b69d06fc5bc965f509b18582f28e1892b'
$OracleFiles = @(
    @{ Path = 'apps/api/tests/auth-accounts.test.ts'; Blob = 'e582f2ad2b4df9886f8981fd6aa3da76b6ecb97c' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Blob = 'b2f33040f0c0d9ed99f049b3e48b6af31935b1ab' }
)
$RequiredCases = @(
    @{ Path = 'apps/api/tests/auth-accounts.test.ts'; Name = 'POST /api/import/credit-card-tw prefers posted date over transaction date' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseSinopacPdfTransactions handles purchases, cashback, installments, and ignores autopay' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseSinopacPdfTransactions keeps current installment amount when statement uses spaced colon and full-width digits' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseEsunPdfTransactions limits parsing to detail sections and handles cashback plus installment rows' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseTaishinPdfTransactions handles ROC full-date rows with trailing country code' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseTaishinPdfTransactions applies previous-year heuristic for MM/DD rows in early-year statements' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseCtbcPdfTransactions handles ROC full-date rows with amount before card suffix' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseCtbcPdfTransactions applies previous-year heuristic for MM/DD rows in early-year statements' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseCtbcPdfTransactions falls back to full-text scan when rows are not separated by newlines' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseMegaPdfTransactions handles full ROC year dates with fullwidth description on same line' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseMegaPdfTransactions handles description on adjacent line (date+amount row without description)' },
    @{ Path = 'apps/api/tests/pdf-credit-card.test.ts'; Name = 'parseCtbcPdfTransactions recovers transaction rows from noisy token stream with cover-page summary fragments' }
)
$WorkspaceScope = '@hearth'
$RequiredWorkspaceModule = '@hearth/shared'

function Get-CanonicalPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}

function Resolve-GitReportedPath([string]$Path) {
    $trimmed = $Path.Trim()
    if ([IO.Path]::IsPathRooted($trimmed)) {
        return Get-CanonicalPath $trimmed
    }
    return Get-CanonicalPath (Join-Path $Repository $trimmed)
}

function Assert-DirectoryIdentity([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "DIRECTORY_IDENTITY_MISMATCH: $Path"
    }
    if ((Get-CanonicalPath $item.FullName) -ne (Get-CanonicalPath $Path)) {
        throw "DIRECTORY_CANONICAL_PATH_MISMATCH: $Path"
    }
}

function Test-IsWithin([string]$Child, [string]$Parent) {
    $childPath = Get-CanonicalPath $Child
    $parentPath = Get-CanonicalPath $Parent
    return $childPath.Equals($parentPath, [StringComparison]::OrdinalIgnoreCase) -or
        $childPath.StartsWith($parentPath + '\', [StringComparison]::OrdinalIgnoreCase)
}

function Assert-FileIdentity([hashtable]$Expected) {
    $item = Get-Item -LiteralPath $Expected.Path -Force
    if (-not $item.PSIsContainer -and -not ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        $actualLength = $item.Length
        $actualHash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualLength -eq $Expected.Length -and $actualHash -eq $Expected.Sha256) {
            return
        }
    }
    throw "EXECUTABLE_OR_MODULE_IDENTITY_MISMATCH: $($Expected.Path)"
}

function Invoke-ExactProcess(
    [string]$Executable,
    [string[]]$Arguments,
    [string]$WorkingDirectory,
    [hashtable]$ExtraEnvironment = @{}
) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Executable
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($argument in $Arguments) {
        [void]$psi.ArgumentList.Add($argument)
    }
    $psi.Environment.Clear()
    $psi.Environment['SystemRoot'] = $env:SystemRoot
    $psi.Environment['WINDIR'] = $env:WINDIR
    $psi.Environment['TEMP'] = $env:TEMP
    $psi.Environment['TMP'] = $env:TMP
    foreach ($entry in $ExtraEnvironment.GetEnumerator()) {
        $psi.Environment[$entry.Key] = [string]$entry.Value
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $psi
    if (-not $process.Start()) {
        throw "PROCESS_START_FAILED: $Executable"
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        Stdout = $stdoutTask.GetAwaiter().GetResult()
        Stderr = $stderrTask.GetAwaiter().GetResult()
    }
}

function Write-GitBlob([string]$Blob, [string]$Destination) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $ExpectedGit.Path
    $psi.WorkingDirectory = $Repository
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($argument in $GitConfigArguments) {
        [void]$psi.ArgumentList.Add($argument)
    }
    [void]$psi.ArgumentList.Add('cat-file')
    [void]$psi.ArgumentList.Add('blob')
    [void]$psi.ArgumentList.Add($Blob)
    $psi.Environment.Clear()
    $psi.Environment['SystemRoot'] = $env:SystemRoot
    $psi.Environment['WINDIR'] = $env:WINDIR
    $psi.Environment['TEMP'] = $env:TEMP
    $psi.Environment['TMP'] = $env:TMP
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $psi
    if (-not $process.Start()) {
        throw 'GIT_BLOB_START_FAILED'
    }
    $stream = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $process.StandardOutput.BaseStream.CopyTo($stream)
    } finally {
        $stream.Dispose()
    }
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) {
        throw "GIT_BLOB_FAILED: $stderr"
    }
}

function Assert-GitObject([string]$Object, [string]$ExpectedType) {
    $result = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('cat-file', '-t', $Object)) $Repository
    if ($result.ExitCode -ne 0 -or $result.Stdout.Trim() -ne $ExpectedType) {
        throw "GIT_OBJECT_MISMATCH: $Object"
    }
}

function New-HearthSnapshot([string]$Revision, [string]$Destination, [string]$ArchivePath) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
    $archive = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @(
        'archive', '--format=tar', "--output=$ArchivePath", $Revision
    )) $Repository
    if ($archive.ExitCode -ne 0) {
        throw "GIT_ARCHIVE_FAILED: $($archive.Stderr)"
    }
    $extract = Invoke-ExactProcess $ExpectedTar.Path @('-xf', $ArchivePath, '-C', $Destination) $Repository
    if ($extract.ExitCode -ne 0) {
        throw "TAR_EXTRACT_FAILED: $($extract.Stderr)"
    }
}

function Assert-GitTopology {
    Assert-DirectoryIdentity $Repository
    Assert-DirectoryIdentity $ExpectedGitDirectory
    $top = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('rev-parse', '--show-toplevel')) $Repository
    $gitDirectory = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('rev-parse', '--absolute-git-dir')) $Repository
    $commonDirectory = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('rev-parse', '--git-common-dir')) $Repository
    if ($top.ExitCode -ne 0 -or (Resolve-GitReportedPath $top.Stdout) -ne (Get-CanonicalPath $Repository)) {
        throw 'GIT_WORKTREE_IDENTITY_MISMATCH'
    }
    if ($gitDirectory.ExitCode -ne 0 -or (Resolve-GitReportedPath $gitDirectory.Stdout) -ne (Get-CanonicalPath $ExpectedGitDirectory)) {
        throw 'GIT_DIRECTORY_IDENTITY_MISMATCH'
    }
    if ($commonDirectory.ExitCode -ne 0 -or (Resolve-GitReportedPath $commonDirectory.Stdout) -ne (Get-CanonicalPath $ExpectedGitDirectory)) {
        throw 'GIT_COMMON_DIRECTORY_IDENTITY_MISMATCH'
    }
}

function Add-Junction([string]$Path, [string]$Target, [Collections.Generic.List[string]]$Junctions) {
    if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
        throw "JUNCTION_TARGET_MISSING: $Target"
    }
    [void](New-Item -ItemType Junction -Path $Path -Target $Target)
    $realTarget = (Get-Item -LiteralPath $Path -Force).Target
    if ($null -eq $realTarget -or @($realTarget).Count -ne 1) {
        throw "JUNCTION_TARGET_AMBIGUOUS: $Path"
    }
    $Junctions.Add($Path)
}

function Add-SnapshotNodeModules(
    [string]$SnapshotRoot,
    [Collections.Generic.List[string]]$Junctions
) {
    $liveNodeModules = Join-Path $Repository 'node_modules'
    $snapshotNodeModules = Join-Path $SnapshotRoot 'node_modules'
    New-Item -ItemType Directory -Path $snapshotNodeModules | Out-Null

    foreach ($entry in Get-ChildItem -LiteralPath $liveNodeModules -Force) {
        if ($entry.Name -eq $WorkspaceScope) {
            continue
        }
        if ($entry.PSIsContainer) {
            Add-Junction (Join-Path $snapshotNodeModules $entry.Name) $entry.FullName $Junctions
        }
    }

    $liveScope = Join-Path $liveNodeModules $WorkspaceScope
    $snapshotScope = Join-Path $snapshotNodeModules $WorkspaceScope
    New-Item -ItemType Directory -Path $snapshotScope | Out-Null
    foreach ($workspaceEntry in Get-ChildItem -LiteralPath $liveScope -Force) {
        $targets = @($workspaceEntry.Target)
        if ($targets.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$targets[0])) {
            throw "WORKSPACE_TARGET_AMBIGUOUS: $($workspaceEntry.FullName)"
        }
        $liveTarget = Get-CanonicalPath ([string]$targets[0])
        if (-not (Test-IsWithin $liveTarget $Repository)) {
            throw "WORKSPACE_TARGET_OUTSIDE_REPOSITORY: $liveTarget"
        }
        $relativeTarget = [IO.Path]::GetRelativePath((Get-CanonicalPath $Repository), $liveTarget)
        if ($relativeTarget.StartsWith('..')) {
            throw "WORKSPACE_TARGET_RELATIVE_ESCAPE: $relativeTarget"
        }
        $snapshotTarget = Get-CanonicalPath (Join-Path $SnapshotRoot $relativeTarget)
        if (-not (Test-IsWithin $snapshotTarget $SnapshotRoot)) {
            throw "SNAPSHOT_TARGET_ESCAPE: $snapshotTarget"
        }
        if (-not (Test-Path -LiteralPath $snapshotTarget -PathType Container)) {
            throw "SNAPSHOT_WORKSPACE_TARGET_MISSING: $snapshotTarget"
        }
        $newLink = Join-Path $snapshotScope $workspaceEntry.Name
        Add-Junction $newLink $snapshotTarget $Junctions
        $rebuiltTarget = @((Get-Item -LiteralPath $newLink -Force).Target)
        if ($rebuiltTarget.Count -ne 1 -or -not (Test-IsWithin ([string]$rebuiltTarget[0]) $SnapshotRoot)) {
            throw "REBUILT_WORKSPACE_LINK_ESCAPES_SNAPSHOT: $newLink"
        }
    }
}

function Assert-SharedResolution([string]$SnapshotRoot) {
    $probeDirectory = Join-Path $SnapshotRoot 'apps\api\tests'
    $probePath = Join-Path $probeDirectory '.qualification-resolve-workspace.mts'
    if (Test-Path -LiteralPath $probePath) {
        throw "RESOLUTION_PROBE_PREEXISTS: $probePath"
    }
    $probe = @(
        "import { realpathSync } from 'node:fs';",
        "const resolved = import.meta.resolve('$RequiredWorkspaceModule');",
        'process.stdout.write(realpathSync(new URL(resolved)));'
    ) -join "`n"
    [IO.File]::WriteAllText($probePath, $probe + "`n", [Text.UTF8Encoding]::new($false))
    try {
        $result = Invoke-ExactProcess $ExpectedNode.Path @('--import', 'tsx', $probePath) $probeDirectory @{
            NODE_NO_WARNINGS = '1'
        }
    } finally {
        if (Test-Path -LiteralPath $probePath) {
            Remove-Item -LiteralPath $probePath -Force
        }
    }
    if ($result.ExitCode -ne 0) {
        throw "SHARED_RESOLUTION_FAILED: $($result.Stderr)"
    }
    $resolved = Get-CanonicalPath $result.Stdout.Trim()
    $expectedPackageRoot = Get-CanonicalPath (Join-Path $SnapshotRoot 'packages\shared')
    if (-not (Test-IsWithin $resolved $expectedPackageRoot)) {
        throw "SHARED_RESOLUTION_ESCAPES_SNAPSHOT: $resolved"
    }
    return $resolved
}

function Get-NodeTestExecution([string]$Output, [int]$ExitCode, [string]$CaseName, [string]$SnapshotName) {
    $targetHeaders = [regex]::Matches($Output, '(?m)^# Subtest: ' + [regex]::Escape($CaseName) + '\r?$')
    $passMatch = [regex]::Match($Output, '(?m)^# pass (\d+)\r?$')
    $failMatch = [regex]::Match($Output, '(?m)^# fail (\d+)\r?$')
    $cancelledMatch = [regex]::Match($Output, '(?m)^# cancelled (\d+)\r?$')
    if ($targetHeaders.Count -ne 1 -or -not $passMatch.Success -or -not $failMatch.Success -or -not $cancelledMatch.Success) {
        throw "A5_EXECUTION_PROOF_MISSING: $SnapshotName`:$CaseName"
    }
    $passed = [int]$passMatch.Groups[1].Value
    $failed = [int]$failMatch.Groups[1].Value
    $cancelled = [int]$cancelledMatch.Groups[1].Value
    if (($passed + $failed) -ne 1 -or $cancelled -ne 0) {
        throw "A5_EXECUTION_SET_MISMATCH: $SnapshotName`:$CaseName"
    }
    if (($passed -eq 1 -and $ExitCode -ne 0) -or ($failed -eq 1 -and $ExitCode -eq 0)) {
        throw "A5_EXIT_STATUS_MISMATCH: $SnapshotName`:$CaseName"
    }
    return [pscustomobject]@{
        Status = if ($passed -eq 1) { 'passed' } else { 'failed' }
        ExecutionCount = 1
    }
}

function Remove-Junctions([Collections.Generic.List[string]]$Junctions) {
    for ($index = $Junctions.Count - 1; $index -ge 0; $index--) {
        $path = $Junctions[$index]
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force
        }
    }
}

$selfPath = Get-CanonicalPath $PSCommandPath
$selfHash = (Get-FileHash -LiteralPath $selfPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($selfHash -ne $ExpectedSourceSha256) {
    throw 'HARNESS_SOURCE_IDENTITY_MISMATCH'
}
if ((Get-CanonicalPath (Get-Location).Path) -ne (Get-CanonicalPath $ExpectedLaunchCwd)) {
    throw 'LAUNCH_CWD_MISMATCH'
}

Assert-FileIdentity $ExpectedPowerShell
Assert-FileIdentity $ExpectedGit
Assert-FileIdentity $ExpectedTar
Assert-FileIdentity $ExpectedNode
foreach ($tsxFile in $ExpectedTsx) {
    Assert-FileIdentity $tsxFile
}

Assert-GitTopology
Assert-GitObject $BaseCommit 'commit'
Assert-GitObject $FixCommit 'commit'
foreach ($oracleFile in $OracleFiles) {
    Assert-GitObject ([string]$oracleFile.Blob) 'blob'
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('solo-a5-' + [guid]::NewGuid().ToString('N'))
$baseRoot = Join-Path $tempRoot 'base'
$fixRoot = Join-Path $tempRoot 'fix'
$baseArchive = Join-Path $tempRoot 'base.tar'
$fixArchive = Join-Path $tempRoot 'fix.tar'
$junctions = [Collections.Generic.List[string]]::new()

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    New-HearthSnapshot $BaseCommit $baseRoot $baseArchive
    New-HearthSnapshot $FixCommit $fixRoot $fixArchive
    foreach ($oracleFile in $OracleFiles) {
        $baseOracle = Join-Path $baseRoot ([string]$oracleFile.Path)
        $fixOracle = Join-Path $fixRoot ([string]$oracleFile.Path)
        Remove-Item -LiteralPath $baseOracle -Force
        Remove-Item -LiteralPath $fixOracle -Force
        Write-GitBlob ([string]$oracleFile.Blob) $baseOracle
        Write-GitBlob ([string]$oracleFile.Blob) $fixOracle
    }

    Add-SnapshotNodeModules $baseRoot $junctions
    Add-SnapshotNodeModules $fixRoot $junctions
    $baseSharedResolution = Assert-SharedResolution $baseRoot
    $fixSharedResolution = Assert-SharedResolution $fixRoot

    $results = @()
    foreach ($snapshot in @(@{ Name = 'base'; Root = $baseRoot }, @{ Name = 'fix'; Root = $fixRoot })) {
        foreach ($requiredCase in $RequiredCases) {
            $caseName = [string]$requiredCase.Name
            $oraclePath = [string]$requiredCase.Path
            $pattern = '^' + [regex]::Escape($caseName) + '$'
            $result = Invoke-ExactProcess $ExpectedNode.Path @(
                '--test', '--test-reporter=tap', '--import', 'tsx', "--test-name-pattern=$pattern", $oraclePath
            ) $snapshot.Root @{
                NODE_NO_WARNINGS = '1'
            }
            $combined = $result.Stdout + "`n" + $result.Stderr
            $execution = Get-NodeTestExecution $combined $result.ExitCode $caseName $snapshot.Name
            $results += [pscustomobject]@{
                Snapshot = $snapshot.Name
                Oracle = $oraclePath
                Case = $caseName
                Status = $execution.Status
                ExecutionCount = $execution.ExecutionCount
                ExitCode = $result.ExitCode
                Output = $combined.Trim()
            }
        }
    }
    $baseResults = @($results | Where-Object Snapshot -eq 'base')
    $fixResults = @($results | Where-Object Snapshot -eq 'fix')
    $qualified = (
        $baseResults.Count -eq $RequiredCases.Count -and
        $fixResults.Count -eq $RequiredCases.Count -and
        @($baseResults | Where-Object Status -ne 'failed').Count -eq 0 -and
        @($fixResults | Where-Object Status -ne 'passed').Count -eq 0
    )
    [pscustomobject]@{
        HarnessSha256 = $selfHash
        Disposition = if ($qualified) { 'QUALIFIED' } else { 'NOT_QUALIFIED' }
        ResolvedWorkspaceModules = @(
            @{ Snapshot = 'base'; Path = $baseSharedResolution },
            @{ Snapshot = 'fix'; Path = $fixSharedResolution }
        )
        Results = $results
    } | ConvertTo-Json -Depth 5
    if (-not $qualified) { exit 3 }
} finally {
    Remove-Junctions $junctions
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
