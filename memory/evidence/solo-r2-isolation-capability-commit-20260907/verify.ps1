$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Repo='D:\ai-governance-framework'
$Out=$Repo+'\memory\evidence\solo-r2-isolation-capability-commit-20260907'
$Compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$Verifier=$Repo+'\governance_tools\solo_r2_scoring_host_verifiers.cs'
$Bridge=$Repo+'\memory\evidence\solo-r2-split-verifiers-20260907\Probe.split.cs'
$Tests=$Repo+'\memory\evidence\solo-r2-split-verifiers-20260907\SplitTests.cs'
function Hash($Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
if((Hash $Compiler) -cne '46809206887326d2d24db1eff1f3064de972c3451abe766b49111450a5e08e00'){throw 'Compiler mismatch'}
if((Hash $Verifier) -cne '7c9db92d00fca3cadaa6861bee1e3fbf8ae65d4112f1864860f0df566738f56e'){throw 'Verifier mismatch'}
if((Hash $Bridge) -cne 'bca291fc6ef817f34554f6f94040ec2da045c9f3ba19e3def5c27ca7d445c810'){throw 'Bridge mismatch'}
# Build only. Neither compiled Main entrypoint is invoked.
& $Compiler /nologo /target:exe /platform:x64 ('/out:'+$Out+'\Probe.build.exe') $Verifier $Bridge
if($LASTEXITCODE -ne 0){throw 'Bridge build failed'}
& $Compiler /nologo /target:exe /platform:x64 ('/out:'+$Out+'\Rules.build.exe') $Verifier $Tests
if($LASTEXITCODE -ne 0){throw 'Rules build failed'}
# Invoke only the five existing pure ACL cases. The historical Main also
# expects the former broad parent ACL and must not run against repaired state.
$Assembly=[Reflection.Assembly]::LoadFile($Out+'\Rules.build.exe')
$Check=$Assembly.GetType('SplitTests').GetMethod('Check',[Reflection.BindingFlags]'NonPublic,Static')
$Cases=@(
 @('S-1-5-11',[Security.AccessControl.FileSystemRights]::ReadAndExecute,$false),
 @('S-1-5-11',[Security.AccessControl.FileSystemRights]::Modify,$true),
 @('S-1-5-11',[Security.AccessControl.FileSystemRights]::ChangePermissions,$true),
 @('S-1-5-32-544',[Security.AccessControl.FileSystemRights]::FullControl,$false),
 @('S-1-5-21-4017902291-1272973841-664929404-1001',[Security.AccessControl.FileSystemRights]::Modify,$false)
)
foreach($Case in $Cases){$Check.Invoke($null,[object[]]$Case) | Out-Null}
$Live=Get-Content -LiteralPath ($Repo+'\memory\evidence\solo-r2-projection-live-20260907\result.json') -Raw | ConvertFrom-Json
if($Live.native_exit -ne 0 -or ($Live.output -join '') -cne '2047' -or -not $Live.temporary_rx_revoked){throw 'Saved live evidence mismatch'}
$Result=[ordered]@{status='PASS';builds=2;targeted_acl_cases_passed=5;verifier_sha256=(Hash $Verifier);bridge_sha256=(Hash $Bridge);tests_sha256=(Hash $Tests);compiler_sha256=(Hash $Compiler);live_evidence_sha256=(Hash ($Repo+'\memory\evidence\solo-r2-projection-live-20260907\result.json'));live_rerun=$false;acl_mutation=$false;probe_deployed=$false;claim_ceiling='Build and existing pure ACL cases; previously recorded synthetic live result preserved, not rerun.'}
$Result | ConvertTo-Json | Set-Content -LiteralPath ($Out+'\validation.json') -Encoding UTF8
$Result | ConvertTo-Json
