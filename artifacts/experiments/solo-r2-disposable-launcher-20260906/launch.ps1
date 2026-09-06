param(
    [ValidateSet('check','phase-a','phase-b','refresh-payload-pin-candidate','controlled-readiness-and-wait')][string]$Mode = 'check',
    [ValidatePattern('^[a-f0-9]{64}$')][string]$StateSha256,
    [ValidatePattern('^[a-f0-9]{64}$')][string]$RefreshedPinSha256
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = 'D:\ai-governance-framework'
$Here = Join-Path $Root 'artifacts\experiments\solo-r2-disposable-launcher-20260906'
$ManifestSha = '45e7eb2b2ed05a341cd17b11031172077b3458976e2173c181c8746f1c82a548'
$ControllerSha = 'eec6d6d84f110ff16a2f46a15be46782afe090fa1b789ced250d554de616268f'

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
if ($Mode -in @('phase-b','refresh-payload-pin-candidate','controlled-readiness-and-wait') -and -not $StateSha256) { throw 'Requires the Phase A STATE_SHA256' }
if ($RefreshedPinSha256 -and $Mode -notin @('phase-b','controlled-readiness-and-wait')) { throw 'Refreshed pin is for Phase B or controlled rerun only' }
if ($Mode -eq 'controlled-readiness-and-wait' -and -not $RefreshedPinSha256) { throw 'Explicit adopted refreshed pin required' }

$Start = [Diagnostics.ProcessStartInfo]::new()
$Start.FileName = $Manifest.executables.python.path
$Start.WorkingDirectory = $Root
$Start.UseShellExecute = $false
$Start.Arguments = '-I -S -B "' + (Join-Path $Here 'controller.py') + '" --manifest-sha256 ' + $ManifestSha + ' --mode ' + $Mode
if ($StateSha256) { $Start.Arguments += ' --state-sha256 ' + $StateSha256 }
if ($RefreshedPinSha256) { $Start.Arguments += ' --refreshed-pin-sha256 ' + $RefreshedPinSha256 }
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
