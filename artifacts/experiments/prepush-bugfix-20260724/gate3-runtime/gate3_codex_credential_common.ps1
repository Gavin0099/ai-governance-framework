# Shared credential-handling primitives for the Gate 3 Codex runners.
#
# Extracted so the pair runner and the single-session calibration runner use
# one implementation rather than two copies. Credential seeding, ACL narrowing
# and the user-Temp confinement check are the parts of this system where a
# second copy would be most expensive to get wrong, and where a divergence
# between copies would be hardest to notice.
#
# This file has no side effects at load: it defines functions only, so both
# runners can dot-source it before they have decided anything.
#
# Its SHA-256 is verified by every caller against the value the route plan
# pins. A shared file that nothing pins would be a new unverified execution
# surface, which is the opposite of what extracting it is for.

function Get-UserTempRoot {
    return [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
}

function Write-Utf8Atomic {
    param([string]$Path, [string]$Text)
    $temporary = "$Path.tmp-$PID"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($temporary, $Text, $utf8)
    Move-Item -LiteralPath $temporary -Destination $Path
}

function Assert-UserTempPath {
    param([string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $tempPrefix = $script:userTemp.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith(
        $tempPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        throw 'Credential runner private runtime path is outside user Temp.'
    }
}

function Set-CurrentUserOnlyAcl {
    param(
        [string]$Path,
        [switch]$Container
    )
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    if ($Container) {
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            (
                [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
                [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
            ),
            [System.Security.AccessControl.PropagationFlags]::None,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
    }
    else {
        $acl = New-Object System.Security.AccessControl.FileSecurity
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $sid,
            [System.Security.AccessControl.FileSystemRights]::FullControl,
            [System.Security.AccessControl.AccessControlType]::Allow
        )
    }
    $acl.SetAccessRuleProtection($true, $false)
    [void]$acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
    $observed = Get-Acl -LiteralPath $Path
    $allowRules = @(
        $observed.Access |
            Where-Object {
                $_.AccessControlType -eq
                    [System.Security.AccessControl.AccessControlType]::Allow
            }
    )
    if (
        -not $observed.AreAccessRulesProtected -or
        $allowRules.Count -ne 1 -or
        $allowRules[0].IdentityReference.Translate(
            [System.Security.Principal.SecurityIdentifier]
        ).Value -ne $sid.Value -or
        $allowRules[0].FileSystemRights -ne
            [System.Security.AccessControl.FileSystemRights]::FullControl
    ) {
        throw 'Private credential ACL verification failed.'
    }
}

function Copy-PrivateCredential {
    param([string]$Source, [string]$Destination)
    $temporary = "$Destination.tmp-$PID"
    try {
        [System.IO.File]::Copy($Source, $temporary, $false)
        Set-CurrentUserOnlyAcl -Path $temporary
        Move-Item -LiteralPath $temporary -Destination $Destination
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force
        }
    }
}

function Test-ExactBytes {
    param([string]$Left, [string]$Right)
    $leftBytes = [System.IO.File]::ReadAllBytes($Left)
    $rightBytes = [System.IO.File]::ReadAllBytes($Right)
    if ($leftBytes.Length -ne $rightBytes.Length) {
        return $false
    }
    $difference = 0
    for ($index = 0; $index -lt $leftBytes.Length; $index++) {
        $difference = $difference -bor ($leftBytes[$index] -bxor $rightBytes[$index])
    }
    return $difference -eq 0
}

function Test-ChatGptLogin {
    param(
        [string]$CodexCommand,
        [string]$CodexHome,
        [string]$StdoutPath,
        [string]$StderrPath
    )
    $priorCodexHome = $env:CODEX_HOME
    try {
        $env:CODEX_HOME = $CodexHome
        $process = Start-Process `
            -FilePath $CodexCommand `
            -ArgumentList @('login', 'status') `
            -RedirectStandardOutput $StdoutPath `
            -RedirectStandardError $StderrPath `
            -WindowStyle Hidden `
            -Wait `
            -PassThru
    }
    finally {
        if ($null -eq $priorCodexHome) {
            Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
        }
        else {
            $env:CODEX_HOME = $priorCodexHome
        }
    }
    if ($process.ExitCode -ne 0) {
        return $false
    }
    $statusText = (
        (Get-Content -Raw -LiteralPath $StdoutPath) + "`n" +
        (Get-Content -Raw -LiteralPath $StderrPath)
    )
    return $statusText -match '(?i)ChatGPT'
}
