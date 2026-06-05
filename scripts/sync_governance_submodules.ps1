param(
    [string]$ScopeFile = "governance/fleet/governance_scope.yaml",
    [string]$LocalScopeFile = "governance/fleet/governance_scope.local.yaml",
    [string]$SubmodulePath = "ai-governance-framework",
    [switch]$VerifyModelOnly,
    [switch]$IncludeRecommended,
    [switch]$IncludeExempt
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function ConvertTo-CleanScalar {
    param([string]$Value)

    $clean = $Value.Trim()
    if (($clean.StartsWith('"') -and $clean.EndsWith('"')) -or
        ($clean.StartsWith("'") -and $clean.EndsWith("'"))) {
        return $clean.Substring(1, $clean.Length - 2)
    }
    return $clean
}

function Get-RepoNameFromPath {
    param([string]$Path)

    $normalized = $Path.TrimEnd('\', '/')
    $leaf = Split-Path -Path $normalized -Leaf
    if ([string]::IsNullOrWhiteSpace($leaf)) {
        return $normalized
    }
    return $leaf
}

function Read-FleetScope {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "scope file not found: $Path"
    }

    $repos = @()
    $currentTier = $null
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s{2}(required|recommended|exempt):\s*$') {
            $currentTier = $Matches[1]
            continue
        }

        if ($null -eq $currentTier) {
            continue
        }

        if ($line -match '^\s{6}-\s+path:\s*(.+?)\s*$') {
            $repoPath = ConvertTo-CleanScalar $Matches[1]
            $repos += [pscustomobject]@{
                Name = Get-RepoNameFromPath $repoPath
                Tier = $currentTier
                CanonicalPath = $repoPath
            }
        }
    }

    return $repos
}

function Read-LocalScope {
    param([string]$Path)

    $overlay = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $overlay
    }

    $currentName = $null
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s{2}-\s+name:\s*(.+?)\s*$') {
            $currentName = ConvertTo-CleanScalar $Matches[1]
            continue
        }

        if ($null -ne $currentName -and $line -match '^\s{4}local_path:\s*(.+?)\s*$') {
            $overlay[$currentName] = ConvertTo-CleanScalar $Matches[1]
            $currentName = $null
        }
    }

    return $overlay
}

function Invoke-GitReadOnly {
    param(
        [string]$RepoPath,
        [string[]]$Arguments
    )

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & git -C $RepoPath @Arguments 2>&1
        return [pscustomobject]@{
            ExitCode = $LASTEXITCODE
            Output = ($output | Out-String).Trim()
        }
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Test-GitInsideWorkTree {
    param([string]$Output)

    foreach ($line in ($Output -split "`r?`n")) {
        if ($line.Trim() -eq "true") {
            return $true
        }
    }
    return $false
}

function Get-GitReadWarning {
    param([string]$Output)

    $warnings = @()
    foreach ($line in ($Output -split "`r?`n")) {
        if ($line.Trim() -ne "true") {
            $warnings += $line
        }
    }
    return ($warnings | Out-String).Trim()
}

function Test-RepoModel {
    param(
        [pscustomobject]$Repo,
        [hashtable]$LocalOverlay,
        [string]$SubmodulePath
    )

    if (-not $LocalOverlay.ContainsKey($Repo.Name)) {
        return [pscustomobject]@{
            Repo = $Repo.Name
            Tier = $Repo.Tier
            Model = "missing_local_path"
            Dirty = "-"
            Path = ""
            Note = "no local overlay entry"
        }
    }

    $localPath = $LocalOverlay[$Repo.Name]
    if (-not (Test-Path -LiteralPath $localPath)) {
        return [pscustomobject]@{
            Repo = $Repo.Name
            Tier = $Repo.Tier
            Model = "missing_repo"
            Dirty = "-"
            Path = $localPath
            Note = "local path does not exist"
        }
    }

    try {
        $inside = Invoke-GitReadOnly -RepoPath $localPath -Arguments @("rev-parse", "--is-inside-work-tree")
        $insideWorkTree = Test-GitInsideWorkTree $inside.Output
        if ($inside.ExitCode -ne 0 -and -not $insideWorkTree) {
            $model = "git_check_failed"
            if ($inside.Output -match "not a git repository") {
                $model = "not_git_repo"
            }
            return [pscustomobject]@{
                Repo = $Repo.Name
                Tier = $Repo.Tier
                Model = $model
                Dirty = "-"
                Path = $localPath
                Note = $inside.Output
            }
        }

        if (-not $insideWorkTree) {
            return [pscustomobject]@{
                Repo = $Repo.Name
                Tier = $Repo.Tier
                Model = "not_git_repo"
                Dirty = "-"
                Path = $localPath
                Note = $inside.Output
            }
        }

        $readWarning = Get-GitReadWarning $inside.Output
        $dirtyResult = Invoke-GitReadOnly -RepoPath $localPath -Arguments @("status", "--porcelain")
        $dirty = "unknown"
        if ($dirtyResult.ExitCode -eq 0) {
            $dirty = -not [string]::IsNullOrWhiteSpace($dirtyResult.Output)
        }

        $submoduleResult = Invoke-GitReadOnly -RepoPath $localPath -Arguments @("submodule", "status", "--", $SubmodulePath)
        if ($submoduleResult.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($submoduleResult.Output)) {
            return [pscustomobject]@{
                Repo = $Repo.Name
                Tier = $Repo.Tier
                Model = "submodule_based"
                Dirty = $dirty
                Path = $localPath
                Note = (($submoduleResult.Output, $readWarning) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " | "
            }
        }

        $governancePath = Join-Path $localPath $SubmodulePath
        if (-not (Test-Path -LiteralPath $governancePath)) {
            return [pscustomobject]@{
                Repo = $Repo.Name
                Tier = $Repo.Tier
                Model = "missing_governance_path"
                Dirty = $dirty
                Path = $localPath
                Note = (("path missing: $SubmodulePath", $readWarning) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " | "
            }
        }

        return [pscustomobject]@{
            Repo = $Repo.Name
            Tier = $Repo.Tier
            Model = "not_submodule_based"
            Dirty = $dirty
            Path = $localPath
            Note = (("governance path exists but is not a registered submodule", $readWarning) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join " | "
        }
    } catch {
        return [pscustomobject]@{
            Repo = $Repo.Name
            Tier = $Repo.Tier
            Model = "git_check_failed"
            Dirty = "-"
            Path = $localPath
            Note = $_.Exception.Message
        }
    }
}

$scopePath = if ([System.IO.Path]::IsPathRooted($ScopeFile)) { $ScopeFile } else { Join-Path (Get-Location) $ScopeFile }
$localScopePath = if ([System.IO.Path]::IsPathRooted($LocalScopeFile)) { $LocalScopeFile } else { Join-Path (Get-Location) $LocalScopeFile }

$allRepos = @(Read-FleetScope -Path $scopePath)
$selectedTiers = @("required")
if ($IncludeRecommended) {
    $selectedTiers += "recommended"
}
if ($IncludeExempt) {
    $selectedTiers += "exempt"
}

$targets = @($allRepos | Where-Object { $selectedTiers -contains $_.Tier })
if ($targets.Count -eq 0) {
    throw "no repositories selected from scope file"
}

if (-not (Test-Path -LiteralPath $localScopePath)) {
    Write-Warning "local scope overlay not found: $localScopePath"
}

$localOverlay = Read-LocalScope -Path $localScopePath
$rows = @()
foreach ($repo in $targets) {
    $rows += Test-RepoModel -Repo $repo -LocalOverlay $localOverlay -SubmodulePath $SubmodulePath
}

$rows | Format-Table Repo, Tier, Model, Dirty, Path, Note -AutoSize
