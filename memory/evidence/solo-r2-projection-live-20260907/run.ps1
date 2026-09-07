$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Repo='D:\ai-governance-framework'
$Evidence=$Repo+'\memory\evidence\solo-r2-projection-live-20260907'
$Root='D:\r2-final-disposable-shakedown-20260907\scorer-isolation-probe-1'
$Exe=$Root+'\Probe.exe'
$Archive=$Root+'\Probe.pre-callbacks.exe'
$Source=$Repo+'\memory\evidence\solo-r2-split-verifiers-20260907\Probe.split.exe'
$Sid='S-1-15-2-131220624-4122180277-3555119406-1414502418-3096179838-1091309190-3293210637'
$Owner='S-1-5-21-4017902291-1272973841-664929404-1001'
function Hash($p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
if([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -cne $Owner){throw 'Owner mismatch'}
if((Hash $Exe) -cne 'ce63475a9e17e903ad5fccc3d9adfe1c78611f8176c08977f78bc4b0434c3642'){throw 'Historical executable mismatch'}
if((Hash $Source) -cne '6bcc03dd0ceb27baf7112e42c11483d19de69ec56ccb7efbd09dea9e10bfb3f8'){throw 'Corrected executable mismatch'}
if((Hash ($Repo+'\memory\evidence\solo-r2-appcontainer-isolation-20260907\Probe.cs')) -cne 'aed2e952f7f947882bb95d5593a4ae288aadfda509a244eec13dd1a3e4e3c41a'){throw 'Corrected source mismatch'}
if((Hash $Archive) -cne (Hash $Exe)){throw 'Preserved executable mismatch'}
if(Test-Path -LiteralPath ($Evidence+'\result.json')){throw 'No replay'}
$all=@($Root,($Root+'\inputs'),$Exe,($Root+'\inputs\projection.json'))
$before=@()
foreach($Path in $all){
 $Node=Get-Item -LiteralPath $Path -Force
 while($null -ne $Node){if(($Node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse path'};if($Node -is [IO.FileInfo]){$Node=$Node.Directory}else{$Node=$Node.Parent}}
 $Acl=Get-Acl -LiteralPath $Path
 if($Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne $Owner){throw 'Wrong owner'}
 foreach($Ace in $Acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){
  if($Ace.IdentityReference.Value -notin @($Owner,'S-1-5-18','S-1-5-32-544',$Sid) -or $Ace.AccessControlType -ne 'Allow'){throw 'Unexpected ACL'}
  if($Ace.IdentityReference.Value -ceq $Sid -and (([long]$Ace.FileSystemRights -band 0xD0116) -ne 0)){throw 'Scorer writable'}
 }
 $before+=@{path=$Path;sddl=$Acl.Sddl}
}
if((Hash ($Root+'\inputs\projection.json')) -cne '8f5c5e52d297484ca3e87b835976a837c1f7971ba3cb371ce464c57f9c7f530e'){throw 'Canary mismatch'}
$history=Get-Content -LiteralPath ($Repo+'\memory\evidence\solo-r2-appcontainer-env-fix-20260907\validation.json') -Raw | ConvertFrom-Json
foreach($h in $history.history){if((Hash $h.path) -cne $h.sha){throw 'History mismatch'}}
$originalAcl=Get-Acl -LiteralPath $Exe
$originalSddl=$originalAcl.Sddl
if((Get-Acl -LiteralPath $Archive).Sddl -cne $originalSddl){throw 'Archive ACL differs'}
Copy-Item -LiteralPath $Source -Destination $Exe -Force
$NativeExit=$null;$Output=@();$Failure=$null
try {
 $acl=Get-Acl -LiteralPath $Exe
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($Sid),[Security.AccessControl.FileSystemRights]::ReadAndExecute,[Security.AccessControl.AccessControlType]::Allow))
 [IO.File]::SetAccessControl($Exe,$acl)
 if((Hash $Exe) -cne '6bcc03dd0ceb27baf7112e42c11483d19de69ec56ccb7efbd09dea9e10bfb3f8'){throw 'Deployment mismatch'}
 $ErrorActionPreference='Continue'
 $Output=@(& $Exe --probe 2>&1 | ForEach-Object {$_.ToString()})
 $NativeExit=$LASTEXITCODE
 $ErrorActionPreference='Stop'
} catch {$Failure=$_.Exception.Message}
finally {
 @{native_exit=$NativeExit;output=$Output;error=$Failure} | ConvertTo-Json | Set-Content -LiteralPath ($Evidence+'\native-result.json') -Encoding UTF8
 $acl=Get-Acl -LiteralPath $Exe
 $acl.PurgeAccessRules([Security.Principal.SecurityIdentifier]::new($Sid))
 [IO.File]::SetAccessControl($Exe,$acl)
}
foreach($h in $history.history){if((Hash $h.path) -cne $h.sha){throw 'History changed'}}
$restored=((Get-Acl -LiteralPath $Exe).Sddl -ceq $originalSddl)
if(-not $restored){throw 'Executable ACL restoration failed'}
foreach($prior in $before){if((Get-Acl -LiteralPath $prior.path).Sddl -cne $prior.sddl){throw 'ACL changed'}}
$ok=($NativeExit -eq 0 -and ($Output -join '') -ceq '2047')
$r=[ordered]@{status=$(if($ok){'FRESH_SCORER_ISOLATION_READY'}else{'FRESH_SCORER_ISOLATION_BLOCKED'});native_exit=$NativeExit;output=$Output;error=$Failure;host_custody_pass=$ok;appcontainer_projection_pass=$ok;forbidden_read_denial_pass=$ok;sid=$Sid;root=$Root;projection_sha256=(Hash ($Root+'\inputs\projection.json'));deployed_sha256=(Hash $Exe);temporary_rx_revoked=$restored;acl_before=$before;history_unchanged=$true;scoring_run=$false;bundle_created=$false;claim_ceiling='Synthetic projection OS isolation and native verifier entry only; no actual bundle semantic validation, Python consumer integration or scorer model execution'}
$r | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath ($Evidence+'\result.json') -Encoding UTF8
$r | ConvertTo-Json -Depth 8
