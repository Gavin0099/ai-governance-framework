param(
    [ValidateSet('check','phase-a','phase-b')][string]$Mode = 'check',
    [string]$AdoptionCommit = '',
    [string]$AdoptionSha256 = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = 'D:\ai-governance-framework'
$Here = Join-Path $Root 'artifacts\experiments\solo-r2-final-disposable-launcher-20260907'
$ManifestSha = '65760c13aeecaf17a10ec5c77af5f5d8f354a3dd0c18b154a38d92018d938645'
$ControllerSha = 'acc109b7fbd8de4d143fb5441efb53f9a873467f63202b4c4179eb1cb7faebf9'

function Assert-Pin([string]$Path, [string]$Sha, [long]$Size = -1) {
    if (-not [IO.Path]::IsPathRooted($Path)) { throw 'Relative trust path' }
    $File = [IO.FileInfo]::new($Path)
    if (-not $File.Exists -or $File.FullName -cne $Path) { throw 'Missing or noncanonical trust path' }
    $Node = $File
    while ($null -ne $Node) {
        if (($Node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected trust path' }
        if ($Node -is [IO.FileInfo]) { $Node = $Node.Directory } else { $Node = $Node.Parent }
    }
    if ($Size -ge 0 -and $File.Length -ne $Size) { throw "Size mismatch: $Path" }
    $Stream = [IO.File]::OpenRead($Path)
    $Hasher = [Security.Cryptography.SHA256]::Create()
    try { $Actual = [BitConverter]::ToString($Hasher.ComputeHash($Stream)).Replace('-','').ToLowerInvariant() }
    finally { $Stream.Dispose(); $Hasher.Dispose() }
    if ($Actual -cne $Sha) { throw "Digest mismatch: $Path" }
}

Assert-Pin 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' '7600ffe12da441fe89d035b13801e8e91d064bc544a27b19a5cf49f6ab8b18f5' 454656
if ([Diagnostics.Process]::GetCurrentProcess().MainModule.FileName -cne 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe') { throw 'Use the fixed Windows PowerShell host' }
Assert-Pin (Join-Path $Here 'controller.py') $ControllerSha
Assert-Pin (Join-Path $Here 'manifest.json') $ManifestSha
$Manifest = [IO.File]::ReadAllText((Join-Path $Here 'manifest.json')) | ConvertFrom-Json
function Get-Inventory([string]$Directory) {
    $Dir = [IO.DirectoryInfo]::new($Directory)
    if (($Dir.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Redirected library directory' }
    foreach ($File in $Dir.GetFiles()) { $File.FullName }
    foreach ($ChildDir in $Dir.GetDirectories()) {
        if ($ChildDir.Name -cne 'site-packages') { Get-Inventory $ChildDir.FullName }
    }
}
foreach ($Tree in $Manifest.trees) {
    $Actual = @(Get-Inventory $Tree.path | Sort-Object -CaseSensitive)
    $Expected = @($Tree.files | Sort-Object -CaseSensitive)
    if ($Actual.Count -ne $Expected.Count -or [string]::Join("`n",$Actual) -cne [string]::Join("`n",$Expected)) { throw 'Standard library inventory changed' }
}
foreach ($Pin in $Manifest.pins) { Assert-Pin $Pin.path $Pin.sha256 $Pin.bytes }

$Start = [Diagnostics.ProcessStartInfo]::new()
$Start.FileName = $Manifest.executables.python.path
$Start.WorkingDirectory = $Root
$Start.UseShellExecute = $false
$Start.Arguments = '-I -S -B "' + (Join-Path $Here 'controller.py') + '" --manifest-sha256 ' + $ManifestSha + ' --mode ' + $Mode
if ($Mode -ceq 'phase-b') {
    if ($AdoptionCommit -cnotmatch '^[0-9a-f]{40}$' -or $AdoptionSha256 -cnotmatch '^[0-9a-f]{64}$') { throw 'Exact owner adoption commit/digest required' }
    $Start.Arguments += ' --adoption-commit ' + $AdoptionCommit + ' --adoption-sha256 ' + $AdoptionSha256
} elseif ($AdoptionCommit -ne '' -or $AdoptionSha256 -ne '') { throw 'Adoption inputs apply only to Phase B' }
$Start.EnvironmentVariables.Clear()
# Fixed owner/machine environment. No PATH, PYTHON*, GIT*, or shell selectors.
$Allowed = @{
    SystemRoot='C:\Windows'; WINDIR='C:\Windows'; COMSPEC='C:\Windows\System32\cmd.exe';
    USERPROFILE='C:\Users\daish'; LOCALAPPDATA='C:\Users\daish\AppData\Local';
    APPDATA='C:\Users\daish\AppData\Roaming'; USERNAME='daish';
    HOMEDRIVE='C:'; HOMEPATH='\Users\daish';
    TEMP='C:\Users\daish\AppData\Local\Temp'; TMP='C:\Users\daish\AppData\Local\Temp'
}
foreach ($Key in $Allowed.Keys) { $Start.EnvironmentVariables[$Key] = $Allowed[$Key] }
# Inherit the ordinary external console, including explicit owner input.
$Child = [Diagnostics.Process]::Start($Start)
$Child.WaitForExit()
exit $Child.ExitCode
