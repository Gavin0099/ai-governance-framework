$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo='D:\ai-governance-framework'
$dir=Join-Path $repo 'memory\evidence\solo-r2-appcontainer-env-fix-20260907'
$source=Join-Path $repo 'memory\evidence\solo-r2-appcontainer-isolation-20260907\Probe.cs'
$target='D:\r2-final-disposable-shakedown-20260907\scorer-isolation-probe-1\Probe.exe'
$cwd='D:\r2-final-disposable-shakedown-20260907\scorer-isolation-probe-1\inputs'
$compiler='C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if((Get-FileHash -LiteralPath $compiler -Algorithm SHA256).Hash.ToLowerInvariant() -ne '46809206887326d2d24db1eff1f3064de972c3451abe766b49111450a5e08e00'){throw 'Compiler identity mismatch'}
if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'afcd6f9720a12544cb29fcc5c03098f76e784d41511f02787226283d6f3d6379'){throw 'Historical binary mismatch'}
$text=[IO.File]::ReadAllText($source)
$pattern='env=Marshal.StringToHGlobalUni\("([^"\r\n]+)"\);'
$match=[regex]::Matches($text,$pattern)
if($match.Count -ne 1){throw 'Expected one literal environment'}
$envBlock=[regex]::Unescape($match[0].Groups[1].Value)
$expected="LOCALAPPDATA=C:\Users\daish\AppData\Local`0SystemRoot=C:\Windows`0WINDIR=C:\Windows`0`0"
if($envBlock -cne $expected){throw 'Not the exact three-variable environment'}
$before=[IO.File]::ReadAllText((Join-Path $dir 'Probe.before.cs'))
$oldMatch=[regex]::Matches($before,$pattern)
if($oldMatch.Count -ne 1 -or $text.Replace($match[0].Value,$oldMatch[0].Value) -cne $before){throw 'Unexpected source change'}
$aclPaths=@($target,$cwd,(Split-Path -Parent $cwd))
$aclBefore=@($aclPaths | ForEach-Object {(Get-Acl -LiteralPath $_).Sddl})
& $compiler /nologo /platform:x64 /target:exe /optimize+ ('/out:'+ (Join-Path $dir 'Probe.fixed.checked.exe')) $source
if($LASTEXITCODE -ne 0){throw 'Corrected source did not compile'}
Add-Type -Path (Join-Path $dir 'LaunchVerification.cs')
$command='"'+$target+'" --child'
$positive=[LaunchDiagnosis]::Run($true,$false,$envBlock,$target,$command,$cwd)
$negative=[LaunchDiagnosis]::Run($true,$false,([regex]::Unescape($oldMatch[0].Groups[1].Value)),$target,$command,$cwd)
$expectedSid='S-1-15-2-131220624-4122180277-3555119406-1414502418-3096179838-1091309190-3293210637'
if($positive -cne ('created_suspended=true;token_is_appcontainer=1;terminated_without_resume=true;actual_token_sid='+$expectedSid+';sid='+$expectedSid)){throw ('Positive failed: '+$positive)}
if($negative -cne ('create_error=203;sid='+$expectedSid)){throw ('Negative failed: '+$negative)}
$aclAfter=@($aclPaths | ForEach-Object {(Get-Acl -LiteralPath $_).Sddl})
if(($aclBefore -join "`n") -cne ($aclAfter -join "`n")){throw 'ACL changed'}
$history=@(
@{path=(Join-Path $repo 'artifacts\evidence\solo-r2-final-disposable-mechanism-shakedown-20260907\attempt-ledger.v2.1.ndjson');sha='e471517f5e6e36e2fdce3f42c8e87edf6b87c2cc4a67e47acbf90352140eac77'},
@{path='D:\r2-final-disposable-shakedown-20260907\scoring\2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb.blind-scoring-bundle.json';sha='f0e8af8750182d6dc4bacd5b7f0c280f8b0acccd1dc57ea7844c2fcff5516dce'},
@{path='D:\r2-final-disposable-shakedown-20260907\controller\2a92a1fff13490d92d0f2cec26cd99016a2f82719cee9847297bf0f30b6878fb.scoring-bound.sealed.json';sha='243e6c2defc1272347b940e8ac20786e0e52f626216ff71a43cf34b3a5243558'})
foreach($h in $history){if((Get-FileHash -LiteralPath $h.path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $h.sha){throw 'Historical artifact changed'}}
$result=[ordered]@{status='APP_CONTAINER_PROCESS_START_PASS';positive=$positive;negative=$negative;environment=@('LOCALAPPDATA=C:\Users\daish\AppData\Local','SystemRoot=C:\Windows','WINDIR=C:\Windows');acl_unchanged=$true;history=$history;source_sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant();compiled_sha256=(Get-FileHash -LiteralPath (Join-Path $dir 'Probe.fixed.checked.exe') -Algorithm SHA256).Hash.ToLowerInvariant();external_probe_deployed=$false;child_resumed=$false;read_probes_run=$false;claim_ceiling='Suspended process creation and actual token SID only; child entrypoint not run.'}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $dir 'validation.json') -Encoding UTF8
$result | ConvertTo-Json -Depth 8
