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
$ExpectedPython = @{
    Path = 'D:\Bookstore-Scraper\.venv\Scripts\python.exe'
    Length = 262144
    Sha256 = '5912d0884b23c0343983a864c6064242391e2265536f50b88624857e353882c9'
}
$ExpectedPytest = @(
    @{
        Path = 'D:\Bookstore-Scraper\.venv\Lib\site-packages\pytest\__init__.py'
        Length = 5582
        Sha256 = '7be7a1e2218dc59a19d1ad131e4abe21172a295087efc72898938248782e8766'
    },
    @{
        Path = 'D:\Bookstore-Scraper\.venv\Lib\site-packages\_pytest\config\__init__.py'
        Length = 79300
        Sha256 = '2ea44f1539ed6b72eb61402d4633b92e9fef99895c41ac6347860690516e46cf'
    }
)

$Repository = 'D:\Bookstore-Scraper'
$GitSafeDirectory = 'D:/Bookstore-Scraper'
$ExpectedGitDirectory = 'D:\Bookstore-Scraper\.git'
$GitConfigArguments = @('-c', "safe.directory=$GitSafeDirectory", '-c', 'core.hooksPath=')
$BaseCommit = 'e478409971dd8e72335966350fcfaee2a6cdb8b0'
$FixCommit = 'c9cd494bfa087a86d5e1c34702a2ad7997ad7b7b'
$OraclePath = 'tests/test_scraper_regressions.py'
$OracleBlob = '93ad7d9d56b1534bd180af83ba69ad23e64f3c6b'
$RequiredCases = @(
    'test_grimm_parse_price_preserves_thousands_separator_value',
    'test_grimm_parse_price_prefers_original_price_with_thousands_separator'
)

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

function New-BookstoreSnapshot([string]$Revision, [string]$Destination, [string]$ArchivePath) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
    $archive = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @(
        'archive', '--format=tar', "--output=$ArchivePath",
        $Revision, '--', '.', ':(exclude)exports', ':(exclude)exports/**'
    )) $Repository
    if ($archive.ExitCode -ne 0) {
        throw "GIT_ARCHIVE_FAILED: $($archive.Stderr)"
    }
    $extract = Invoke-ExactProcess $ExpectedTar.Path @('-xf', $ArchivePath, '-C', $Destination) $Repository
    if ($extract.ExitCode -ne 0) {
        throw "TAR_EXTRACT_FAILED: $($extract.Stderr)"
    }
    if (Test-Path -LiteralPath (Join-Path $Destination 'exports')) {
        throw 'EXPORTS_EXCLUSION_FAILED'
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

$selfPath = Get-CanonicalPath $PSCommandPath
$selfHash = (Get-FileHash -LiteralPath $selfPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($selfHash -ne $ExpectedSourceSha256) {
    throw 'HARNESS_SOURCE_IDENTITY_MISMATCH'
}

Assert-FileIdentity $ExpectedPowerShell
Assert-FileIdentity $ExpectedGit
Assert-FileIdentity $ExpectedTar
Assert-FileIdentity $ExpectedPython
foreach ($pytestFile in $ExpectedPytest) {
    Assert-FileIdentity $pytestFile
}

Assert-GitTopology
Assert-GitObject $BaseCommit 'commit'
Assert-GitObject $FixCommit 'commit'
Assert-GitObject $OracleBlob 'blob'

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('solo-pair0-' + [guid]::NewGuid().ToString('N'))
$baseRoot = Join-Path $tempRoot 'base'
$fixRoot = Join-Path $tempRoot 'fix'
$baseArchive = Join-Path $tempRoot 'base.tar'
$fixArchive = Join-Path $tempRoot 'fix.tar'

try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    New-BookstoreSnapshot $BaseCommit $baseRoot $baseArchive
    New-BookstoreSnapshot $FixCommit $fixRoot $fixArchive
    $baseOracle = Join-Path $baseRoot $OraclePath
    $fixOracle = Join-Path $fixRoot $OraclePath
    Remove-Item -LiteralPath $baseOracle -Force
    Remove-Item -LiteralPath $fixOracle -Force
    Write-GitBlob $OracleBlob $baseOracle
    Write-GitBlob $OracleBlob $fixOracle

    $results = @()
    foreach ($snapshot in @(@{ Name = 'base'; Root = $baseRoot }, @{ Name = 'fix'; Root = $fixRoot })) {
        foreach ($caseName in $RequiredCases) {
            $selector = "$OraclePath`::$caseName"
            $result = Invoke-ExactProcess $ExpectedPython.Path @('-I', '-m', 'pytest', '-q', $selector) $snapshot.Root @{
                PYTHONNOUSERSITE = '1'
                PYTHONDONTWRITEBYTECODE = '1'
            }
            $combined = $result.Stdout + "`n" + $result.Stderr
            if ($combined -notmatch '1 (passed|failed)') {
                throw "PAIR0_CASE_NOT_EXECUTED: $($snapshot.Name):$caseName"
            }
            $results += [pscustomobject]@{
                Snapshot = $snapshot.Name
                Case = $caseName
                ExitCode = $result.ExitCode
                Output = $combined.Trim()
            }
        }
    }
    $baseResults = @($results | Where-Object Snapshot -eq 'base')
    $fixResults = @($results | Where-Object Snapshot -eq 'fix')
    if (@($baseResults | Where-Object ExitCode -eq 0).Count -ne 0) {
        throw 'PAIR0_SELF_TEST_BASE_DID_NOT_FAIL'
    }
    if (@($fixResults | Where-Object ExitCode -ne 0).Count -ne 0) {
        throw 'PAIR0_SELF_TEST_FIX_DID_NOT_PASS'
    }
    [pscustomobject]@{
        HarnessSha256 = $selfHash
        Disposition = 'HARNESS_SELF_TEST_REPRODUCED'
        Results = $results
    } | ConvertTo-Json -Depth 5
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force
    }
}
