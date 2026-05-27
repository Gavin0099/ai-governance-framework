$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$framework = 'E:\BackUp\Git_EE\ai-governance-framework'
$py = Join-Path $framework '.venv\Scripts\python.exe'
$requiredVersions = Join-Path $framework 'governance\runtime\required_versions.yaml'
$dirtyGateMode = if ($env:GOV_MATRIX_DIRTY_MODE) { $env:GOV_MATRIX_DIRTY_MODE } else { 'strict' }
$governanceScopePath = Join-Path $framework 'governance\fleet\governance_scope.yaml'
$governanceBaselinePath = Join-Path $framework 'governance\fleet\governance_baseline.yaml'
$evidenceWindowDays = if ($env:GOV_MATRIX_EVIDENCE_WINDOW_DAYS) { [int]$env:GOV_MATRIX_EVIDENCE_WINDOW_DAYS } else { 7 }
if ($evidenceWindowDays -lt 1) { $evidenceWindowDays = 1 }

function Get-EvidenceTier {
	param([string]$Repo)
	$policyPath = Join-Path $Repo 'governance\gate_policy.yaml'
	if (-not (Test-Path $policyPath)) { return 'unknown' }
	try {
		$content = Get-Content -Path $policyPath -Raw -Encoding UTF8
		$m = [regex]::Match($content, '^evidence_tier:\s*(\S+)', [System.Text.RegularExpressions.RegexOptions]::Multiline)
		if ($m.Success) { return $m.Groups[1].Value.Trim() }
		# Fall back to inferring from fail_mode + skip_type
		$failMode = [regex]::Match($content, '^fail_mode:\s*(\S+)', [System.Text.RegularExpressions.RegexOptions]::Multiline)
		$skipType = [regex]::Match($content, '^skip_type:\s*(\S+)', [System.Text.RegularExpressions.RegexOptions]::Multiline)
		if ($failMode.Success -and $failMode.Groups[1].Value.Trim() -eq 'audit') {
			if ($skipType.Success -and $skipType.Groups[1].Value.Trim() -eq 'structural') { return 'hw_or_build' }
			return 'audit_mode'
		}
		return 'ci_strict'
	} catch { return 'unknown' }
}

function Get-GovernanceScope {
	param([string]$ScopePath)
	$scope = @{}
	if (-not (Test-Path $ScopePath)) { return $scope }
	try {
		$content = Get-Content -Path $ScopePath -Raw -Encoding UTF8
		# Parse tier blocks: required / recommended / exempt
		foreach ($tier in @('required', 'recommended', 'exempt')) {
			$tierBlock = [regex]::Match($content, "(?s)${tier}:\s*\n.*?meaning:.*?\n\s*repos:(.*?)(?=\n  \w+:|$)", [System.Text.RegularExpressions.RegexOptions]::Singleline)
			if ($tierBlock.Success) {
				$pathMatches = [regex]::Matches($tierBlock.Groups[1].Value, '- path:\s*(.+)')
				foreach ($m in $pathMatches) {
					$p = $m.Groups[1].Value.Trim()
					$scope[$p] = $tier
				}
			}
		}
	} catch {
		# fail-open: unknown scope if YAML unreadable
	}
	return $scope
}

$governanceScope = Get-GovernanceScope -ScopePath $governanceScopePath
function Get-GovernanceBaseline {
	param([string]$BaselinePath)
	$fallback = [pscustomobject]@{
		baseline_version = ''
		required_surfaces = @{}
	}
	if (-not (Test-Path $BaselinePath)) { return $fallback }

	# Prefer native YAML parser if available.
	if (Get-Command ConvertFrom-Yaml -ErrorAction SilentlyContinue) {
		try {
			$raw = Get-Content -Path $BaselinePath -Raw -Encoding UTF8
			$doc = $raw | ConvertFrom-Yaml
			$required = @{}
			if ($doc.required_surfaces) {
				foreach ($k in $doc.required_surfaces.Keys) {
					$v = $doc.required_surfaces[$k]
					$required[$k] = [pscustomobject]@{
						remediation_key = [string]$v.remediation_key
						hard_required = [bool]$v.hard_required
					}
				}
			}
			return [pscustomobject]@{
				baseline_version = [string]$doc.baseline_version
				required_surfaces = $required
			}
		} catch {
			return $fallback
		}
	}

	# Fallback parser (minimal): baseline_version only.
	try {
		$text = Get-Content -Path $BaselinePath -Raw -Encoding UTF8
		$m = [regex]::Match($text, '(?m)^baseline_version:\s*"?([^"\r\n]+)"?')
		$version = if ($m.Success) { [string]$m.Groups[1].Value.Trim() } else { '' }
		$required = @{}
		$lines = $text -split "`r?`n"
		$inRequired = $false
		$currentKey = ''
		foreach ($line in $lines) {
			if ($line -match '^\s*required_surfaces:\s*$') {
				$inRequired = $true
				$currentKey = ''
				continue
			}
			if (-not $inRequired) { continue }
			if ($line -match '^\S') { break } # next root-level key
			if ($line -match '^\s{2}([A-Za-z0-9_]+):\s*$') {
				$currentKey = [string]$matches[1]
				$required[$currentKey] = [pscustomobject]@{
					remediation_key = ''
					hard_required = $false
				}
				continue
			}
			if ([string]::IsNullOrWhiteSpace($currentKey)) { continue }
			if ($line -match '^\s{4}remediation_key:\s*"?([^"\r\n]+)"?\s*$') {
				$tmp = $required[$currentKey]
				$required[$currentKey] = [pscustomobject]@{
					remediation_key = [string]$matches[1].Trim()
					hard_required = [bool]$tmp.hard_required
				}
				continue
			}
			if ($line -match '^\s{4}hard_required:\s*(true|false)\s*$') {
				$tmp = $required[$currentKey]
				$required[$currentKey] = [pscustomobject]@{
					remediation_key = [string]$tmp.remediation_key
					hard_required = ([string]$matches[1] -eq 'true')
				}
			}
		}
		return [pscustomobject]@{
			baseline_version = $version
			required_surfaces = $required
		}
	} catch {
		return $fallback
	}
}

function Get-LockSurfaceInfo {
	param([string]$Repo)
	$path = Join-Path $Repo 'governance\framework.lock.json'
	if (-not (Test-Path $path)) {
		return [pscustomobject]@{
			lock_path = $path
			lock_exists = $false
			lock_valid = $false
			repo_baseline_version = ''
			adopted_surfaces = @()
		}
	}
	try {
		$obj = Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
		$surfaces = @()
		if ($obj.adopted_surfaces) {
			$surfaces = @($obj.adopted_surfaces | ForEach-Object { [string]$_ } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
		}
		return [pscustomobject]@{
			lock_path = $path
			lock_exists = $true
			lock_valid = $true
			repo_baseline_version = [string]$obj.framework_baseline_version
			adopted_surfaces = $surfaces
		}
	} catch {
		return [pscustomobject]@{
			lock_path = $path
			lock_exists = $true
			lock_valid = $false
			repo_baseline_version = ''
			adopted_surfaces = @()
		}
	}
}

function Compare-BaselineVersion {
	param(
		[string]$RepoVersion,
		[string]$FrameworkVersion
	)
	if ([string]::IsNullOrWhiteSpace($RepoVersion) -or [string]::IsNullOrWhiteSpace($FrameworkVersion)) { return 'unknown' }
	try {
		$r = [datetime]::Parse($RepoVersion)
		$f = [datetime]::Parse($FrameworkVersion)
		if ($r -lt $f) { return 'drift_behind' }
		if ($r -gt $f) { return 'drift_ahead' }
		return 'current'
	} catch {
		if ($RepoVersion -eq $FrameworkVersion) { return 'current' }
		return 'unknown'
	}
}

function Get-ObservedSurfaceStatus {
	param($Detail)
	return @{
		hooks_config = [bool]$Detail.hooks_ready
		framework_lock = [bool]$Detail.framework_version_known
		agents_calibration = [bool]$Detail.agents_repo_specific
		expected_dirty = [bool]$Detail.dirty_explainable
		closeout_evidence = [bool]$Detail.repo_native_hook_evidence_exists
		head_commit_match = [bool]$Detail.repo_native_hook_head_match
		timestamp_freshness = [bool]$Detail.repo_native_hook_timestamp_in_window
	}
}

function Get-RemediationCatalog {
	param([string]$FrameworkRoot)
	$manage = Join-Path $FrameworkRoot 'governance_tools\manage_agent_closeout.py'
	$closeout = Join-Path $FrameworkRoot 'governance_tools\session_closeout_entry.py'

	$catalog = @{
		hooks = [pscustomobject]@{
			remediation_type = 'manual_action'
			command = ''
			action = 'Install/verify hooks using the repo''s existing validated onboarding workflow.'
			human_required = $false
			verification_source = ''
		}
		fw = [pscustomobject]@{
			remediation_type = 'manual_action'
			command = ''
			action = 'Update repo governance/framework.lock.json through existing adoption/update path (do not blind-copy).'
			human_required = $true
			verification_source = ''
		}
		agents = [pscustomobject]@{
			remediation_type = 'human_required'
			command = ''
			action = 'Update repo-specific AGENTS.md after human review.'
			human_required = $true
			verification_source = ''
		}
		dirty_ok = [pscustomobject]@{
			remediation_type = 'human_required'
			command = ''
			action = 'Review dirty state and expected_dirty TTL before declaring explainable dirty.'
			human_required = $true
			verification_source = ''
		}
		evidence = [pscustomobject]@{
			remediation_type = 'unknown'
			command = ''
			action = 'No verified command inventory found.'
			human_required = $false
			verification_source = ''
		}
		head_ok = [pscustomobject]@{
			remediation_type = 'unknown'
			command = ''
			action = 'No verified command inventory found.'
			human_required = $false
			verification_source = ''
		}
		ts_ok = [pscustomobject]@{
			remediation_type = 'unknown'
			command = ''
			action = 'No verified command inventory found.'
			human_required = $false
			verification_source = ''
		}
	}

	if (Test-Path $manage) {
		$catalog.hooks = [pscustomobject]@{
			remediation_type = 'verified_command'
			command = 'python -m governance_tools.manage_agent_closeout --project-root "<repo>" install --agent all; python -m governance_tools.manage_agent_closeout --project-root "<repo>" verify --agent all'
			action = ''
			human_required = $false
			verification_source = $manage
		}
	}
	if (Test-Path $closeout) {
		$entry = [pscustomobject]@{
			remediation_type = 'verified_command'
			command = 'python -m governance_tools.session_closeout_entry --project-root "<repo>"'
			action = ''
			human_required = $false
			verification_source = $closeout
		}
		$catalog.evidence = $entry
		$catalog.head_ok = $entry
		$catalog.ts_ok = $entry
	}

	return $catalog
}

$governanceBaseline = Get-GovernanceBaseline -BaselinePath $governanceBaselinePath
$remediationCatalog = Get-RemediationCatalog -FrameworkRoot $framework

$companyRepos = @(
	'E:\BackUp\Git_EE\hp-firmware-stresstest-tool',
	'E:\BackUp\Git_EE\cli',
	'E:\BackUp\Git_EE\CFU',
	'E:\BackUp\IsptoolRefine2018_EndUser_Tool',
	'E:\BackUp\Git_EE\lenoveo-isp-tool-avalonia',
	'E:\BackUp\Git_EE\gl_electron_tool',
	'E:\BackUp\Git_EE\Command_Line_Tool',
	'E:\BackUp\Git_EE\General_End_User_Tool',
	'E:\BackUp\Git_EE\SpecAuthority'
)

$privateRepos = @(
	'E:\BackUp\Git_EE\ai-governance-framework',
	'E:\BackUp\Git_EE\Bookstore-Scraper',
	'E:\BackUp\Git_EE\Enumd',
	'E:\BackUp\Git_EE\FinancialAdvisorGPT',
	'E:\BackUp\Git_EE\Hearth',
	'E:\BackUp\Git_EE\Kernel-Driver-Contract',
	'E:\BackUp\Git_EE\Mirra',
	'E:\BackUp\Git_EE\SpecAuthority',
	'E:\BackUp\Git_EE\verilog-domain-contract',
	'E:\BackUp\Git_EE\writing-contract',
	'E:\BackUp\Git_EE\ZoneTruth'
)

$snapshotDir = Join-Path $framework 'artifacts\session'
if (-not (Test-Path $snapshotDir)) {
	New-Item -Path $snapshotDir -ItemType Directory | Out-Null
}

$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$snapshotJsonPath = Join-Path $snapshotDir ("governance_repo_matrix_snapshot_{0}.json" -f $timestamp)
$snapshotMdPath = Join-Path $snapshotDir ("governance_repo_matrix_snapshot_{0}.md" -f $timestamp)
$matrixWindowStartUtc = (Get-Date).ToUniversalTime().AddDays(-$evidenceWindowDays)  # rolling freshness window (UTC)

function Invoke-PythonJson {
	param(
		[string[]]$CommandArgs
	)
	$quotedArgs = @()
	foreach ($a in $CommandArgs) {
		$quotedArgs += ('"{0}"' -f ($a -replace '"', '\\"'))
	}
	$cmdLine = ('set PYTHONIOENCODING=utf-8&& "{0}" {1}' -f $py, ($quotedArgs -join ' '))
	$oldEa = $ErrorActionPreference
	$ErrorActionPreference = 'Continue'
	try {
		$out = cmd /c $cmdLine 2>&1
		$exit = $LASTEXITCODE
	} finally {
		$ErrorActionPreference = $oldEa
	}
	$raw = ($out -join "`n")
	$obj = $null
	try {
		if ($raw.Trim()) {
			$obj = $raw | ConvertFrom-Json -Depth 30
		}
	} catch {
		$obj = $null
	}
	return [pscustomobject]@{
		exit = $exit
		raw = $raw
		obj = $obj
	}
}

function Get-GitState {
	param([string]$Repo)

	if (-not (Test-Path $Repo)) {
		return [pscustomobject]@{
			repo = $Repo
			exists = $false
			branch = ''
			head = ''
			upstream = ''
			dirty = $false
			contract_status = 'missing_repo'
		}
	}

	Push-Location $Repo
	try {
		$branch = (cmd /c "git rev-parse --abbrev-ref HEAD 2>nul")
		$head = (cmd /c "git rev-parse HEAD 2>nul")
		$upstream = (cmd /c "git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>nul")
		$dirty = ((cmd /c "git status --porcelain 2>nul" | Measure-Object -Line).Lines -gt 0)
	} finally {
		Pop-Location
	}

	$contractPath = Join-Path $Repo 'contract.yaml'
	$contractStatus = if (Test-Path $contractPath) { 'present' } else { 'missing' }

	return [pscustomobject]@{
		repo = $Repo
		exists = $true
		branch = [string]$branch
		head = [string]$head
		upstream = [string]$upstream
		dirty = [bool]$dirty
		contract_status = $contractStatus
	}
}

function Get-ReadinessAndSmoke {
	param([string]$Repo)

	$contractPath = Join-Path $Repo 'contract.yaml'

	$readiness = Invoke-PythonJson -CommandArgs @(
		(Join-Path $framework 'governance_tools\external_repo_readiness.py'),
		'--repo', $Repo,
		'--framework-root', $framework,
		'--format', 'json'
	)

	$smokeExit = $null
	$smokeObj = $null
	$smokeRaw = ''
	if (Test-Path $contractPath) {
		$smoke = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\external_repo_smoke.py'),
			'--repo', $Repo,
			'--contract', $contractPath,
			'--format', 'json'
		)
		$smokeExit = $smoke.exit
		$smokeObj = $smoke.obj
		$smokeRaw = $smoke.raw
	}

	$manifestPath = Join-Path $Repo '.governance\version_manifest.yaml'
	$versionCheck = $null
	if (Test-Path $manifestPath) {
		$versionCheck = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\governance_version_check.py'),
			'--required-versions', $requiredVersions,
			'--version-manifest', $manifestPath,
			'--json'
		)
	}

	return [pscustomobject]@{
		repo = $Repo
		readiness_exit = $readiness.exit
		readiness = $readiness.obj
		readiness_raw = $readiness.raw
		smoke_exit = $smokeExit
		smoke = $smokeObj
		smoke_raw = $smokeRaw
		version_check = if ($versionCheck) { $versionCheck.obj } else { $null }
		version_check_exit = if ($versionCheck) { $versionCheck.exit } else { $null }
	}
}

function Set-PlanHeader {
	param(
		[string]$PlanPath,
		[string]$LastUpdated,
		[string]$Owner,
		[string]$Freshness
	)

	$lines = Get-Content -Path $PlanPath -Encoding UTF8
	$idx = 0
	while ($idx -lt $lines.Count -and $lines[$idx] -match '^>\s*\*\*') {
		$idx += 1
		if ($idx -ge 8) { break }
	}

	$rest = ''
	if ($idx -lt $lines.Count) {
		$rest = ($lines[$idx..($lines.Count - 1)] -join "`r`n").TrimStart()
	}

	$header = "> **Last Updated**: $LastUpdated`r`n> **Owner**: $Owner`r`n> **Freshness**: $Freshness`r`n`r`n"
	Set-Content -Path $PlanPath -Value ($header + $rest) -Encoding UTF8
}

function Invoke-NegativeContractMissing {
	param([string]$Repo)

	$contract = Join-Path $Repo 'contract.yaml'
	if (-not (Test-Path $contract)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_contract' }
	}

	$bak = "$contract.__tmpbak"
	Move-Item -Path $contract -Destination $bak -Force
	try {
		$smoke = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\external_repo_smoke.py'),
			'--repo', $Repo,
			'--contract', $contract,
			'--format', 'json'
		)
		$summary = if ($smoke.obj -and $smoke.obj.summary) { $smoke.obj.summary } else { $null }
		return [pscustomobject]@{
			repo = $Repo
			executed = $true
			smoke_exit = $smoke.exit
			summary = $summary
			pass = ($smoke.exit -ne 0)
			raw = $smoke.raw
		}
	} finally {
		Move-Item -Path $bak -Destination $contract -Force
	}
}

function Invoke-NegativeManifestMissing {
	param([string]$Repo)

	$manifest = Join-Path $Repo '.governance\version_manifest.yaml'
	if (-not (Test-Path $manifest)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_manifest' }
	}

	$contract = Join-Path $Repo 'contract.yaml'
	if (-not (Test-Path $contract)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_contract' }
	}

	$bak = "$manifest.__tmpbak"
	Move-Item -Path $manifest -Destination $bak -Force
	try {
		$smoke = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\external_repo_smoke.py'),
			'--repo', $Repo,
			'--contract', $contract,
			'--format', 'json'
		)
		$raw = $smoke.raw
		$hasUnsupported = ($raw -match 'version_compatibility_unsupported')
		return [pscustomobject]@{
			repo = $Repo
			executed = $true
			smoke_exit = $smoke.exit
			has_version_compatibility_unsupported = $hasUnsupported
			pass = ($smoke.exit -ne 0 -and $hasUnsupported)
		}
	} finally {
		Move-Item -Path $bak -Destination $manifest -Force
	}
}

function Invoke-PlanStaleDrift {
	param([string]$Repo)

	$plan = Join-Path $Repo 'PLAN.md'
	if (-not (Test-Path $plan)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_plan' }
	}

	$original = Get-Content -Path $plan -Raw -Encoding UTF8
	try {
		Set-PlanHeader -PlanPath $plan -LastUpdated '2020-01-01' -Owner 'DriftProbe' -Freshness 'Sprint (7d)'
		$fresh = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\plan_freshness.py'),
			'--file', $plan,
			'--format', 'json'
		)
		$status = if ($fresh.obj -and $fresh.obj.status) { [string]$fresh.obj.status } else { '' }
		return [pscustomobject]@{
			repo = $Repo
			executed = $true
			exit = $fresh.exit
			status = $status
			pass = ($fresh.exit -ne 0)
		}
	} finally {
		Set-Content -Path $plan -Value $original -Encoding UTF8
	}
}

function Invoke-ManifestVersionDrift {
	param([string]$Repo)

	$manifest = Join-Path $Repo '.governance\version_manifest.yaml'
	if (-not (Test-Path $manifest)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_manifest' }
	}

	$contract = Join-Path $Repo 'contract.yaml'
	if (-not (Test-Path $contract)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_contract' }
	}

	$orig = Get-Content -Path $manifest -Raw -Encoding UTF8
	try {
		$mut = [regex]::Replace($orig, '(?m)^runtime_entrypoint_version\s*:\s*("?[0-9][^\r\n"]*"?)\s*$', 'runtime_entrypoint_version: "0.0.0"')
		$mut = [regex]::Replace($mut, '(?m)^contract_schema_version\s*:\s*("?[0-9][^\r\n"]*"?)\s*$', 'contract_schema_version: "0.0.0"')
		Set-Content -Path $manifest -Value $mut -Encoding UTF8

		$ver = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\governance_version_check.py'),
			'--required-versions', $requiredVersions,
			'--version-manifest', $manifest,
			'--json'
		)
		$verdict = if ($ver.obj -and $ver.obj.verdict) { [string]$ver.obj.verdict } else { '' }
		return [pscustomobject]@{
			repo = $Repo
			executed = $true
			version_check_exit = $ver.exit
			verdict = $verdict
			pass = ($ver.exit -ne 0)
		}
	} finally {
		Set-Content -Path $manifest -Value $orig -Encoding UTF8
	}
}

function Invoke-ContractSchemaDrift {
	param([string]$Repo)

	$contract = Join-Path $Repo 'contract.yaml'
	if (-not (Test-Path $contract)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_contract' }
	}

	$orig = Get-Content -Path $contract -Raw -Encoding UTF8
	try {
		$mut = "  malformed-indented-line`n" + $orig
		Set-Content -Path $contract -Value $mut -Encoding UTF8
		$smoke = Invoke-PythonJson -CommandArgs @(
			(Join-Path $framework 'governance_tools\external_repo_smoke.py'),
			'--repo', $Repo,
			'--contract', $contract,
			'--format', 'json'
		)
		return [pscustomobject]@{
			repo = $Repo
			executed = $true
			smoke_exit = $smoke.exit
			pass = ($smoke.exit -ne 0)
		}
	} finally {
		Set-Content -Path $contract -Value $orig -Encoding UTF8
	}
}

function Invoke-DirtyStateProbe {
	param([string]$Repo)

	$contract = Join-Path $Repo 'contract.yaml'
	if (-not (Test-Path $contract)) {
		return [pscustomobject]@{ repo = $Repo; executed = $false; reason = 'no_contract' }
	}

	$probe = Join-Path $Repo '.tmp_dirty_probe.txt'
	Set-Content -Path $probe -Value 'dirty-state-probe' -Encoding UTF8
	try {
		$result = Get-ReadinessAndSmoke -Repo $Repo
		$smokePass = ($result.smoke_exit -eq 0)
		$classification = if ($smokePass) { 'PASS_WITH_WARNING' } else { 'STRICT_BLOCKED' }
		$pass = if ($dirtyGateMode -eq 'warning') { $true } else { -not $smokePass }
		return [pscustomobject]@{
			repo = $Repo
			executed = $true
			readiness_exit = $result.readiness_exit
			smoke_exit = $result.smoke_exit
			mode = $dirtyGateMode
			classification = $classification
			pass = $pass
		}
	} finally {
		if (Test-Path $probe) { Remove-Item -Path $probe -Force }
	}
}

function Invoke-EnumdRegression {
	$adapter = 'E:\BackUp\Git_EE\Enumd\lib\adapters\gitlab-wiki-adapter.ts'
	if (-not (Test-Path $adapter)) {
		return [pscustomobject]@{ executed = $false; reason = 'adapter_missing' }
	}

	$raw = Get-Content -Path $adapter -Raw -Encoding UTF8
	$hasMapDecl = ($raw -match 'slugToProject\s*=\s*new\s+Map')
	$hasSet = ($raw -match 'slugToProject\.set\(')
	$hasGet = ($raw -match 'slugToProject\.get\(')
	$hasFallback = ($raw -match '\?\?\s*this\.projectId' -or $raw -match '\|\|\s*this\.projectId')

	return [pscustomobject]@{
		executed = $true
		adapter_file = $adapter
		collision_test = if ($hasMapDecl -and $hasSet -and $hasGet) { 'PASS' } else { 'FAIL' }
		unknown_slug_fallback = if ($hasFallback) { 'FAIL_UNSCOPED_DEFAULT_PROJECT_FALLBACK' } else { 'PASS_NO_DEFAULT_PROJECT_FALLBACK' }
		mapping_consistency = if ($hasMapDecl -and $hasSet -and $hasGet) { 'PASS' } else { 'FAIL' }
	}
}

function Get-RepoSetResults {
	param([string[]]$Repos)
	$results = @()
	foreach ($r in $Repos) {
		if (-not (Test-Path $r)) {
			$results += [pscustomobject]@{ repo = $r; missing = $true }
			continue
		}
		$results += (Get-ReadinessAndSmoke -Repo $r)
	}
	return $results
}

function Get-UniqueRepoRows {
	param($Rows)
	$seen = @{}
	$results = @()
	foreach ($row in $Rows) {
		if (-not $row -or -not $row.repo) { continue }
		$key = [string]$row.repo
		if ($seen.ContainsKey($key)) { continue }
		$seen[$key] = $true
		$results += $row
	}
	return $results
}

$allRepos = @($companyRepos + $privateRepos | Select-Object -Unique)

# Phase 1: inventory + baseline
$inventory = @()
foreach ($r in $allRepos) {
	$inventory += (Get-GitState -Repo $r)
}

$companyBaseline = Get-RepoSetResults -Repos $companyRepos
$privateBaseline = Get-RepoSetResults -Repos $privateRepos

# Phase 2/3: metadata and negative-path checks
$negativeContractCompany = Invoke-NegativeContractMissing -Repo $companyRepos[0]
$negativeContractPrivate = Invoke-NegativeContractMissing -Repo $privateRepos[0]

$metadataCorruption = @()
foreach ($r in $allRepos) {
	if (-not (Test-Path $r)) { continue }
	$metadataCorruption += (Invoke-NegativeManifestMissing -Repo $r)
}

$dirtyProbeCompany = Invoke-DirtyStateProbe -Repo $companyRepos[1]
$dirtyProbePrivate = Invoke-DirtyStateProbe -Repo $privateRepos[1]

# Phase 4: Enumd regression
$enumdRegression = Invoke-EnumdRegression

# Phase 6: drift tests
$planDrift = Invoke-PlanStaleDrift -Repo $companyRepos[2]
$manifestDrift = Invoke-ManifestVersionDrift -Repo $companyRepos[3]
$contractDrift = Invoke-ContractSchemaDrift -Repo $companyRepos[4]

# Phase 7: company rerun after all checks
$companyRerun = Get-RepoSetResults -Repos $companyRepos

function Count-SmokePass {
	param($rows)
	return ($rows | Where-Object { $_.smoke_exit -eq 0 }).Count
}

function Count-SmokeTotal {
	param($rows)
	return ($rows | Where-Object { $_.smoke_exit -ne $null }).Count
}

function Get-ReadinessSignalsFromRaw {
	param($Row)

	$raw = if ($Row -and $Row.readiness_raw) { [string]$Row.readiness_raw } else { '' }
	if ([string]::IsNullOrWhiteSpace($raw)) {
		return [pscustomobject]@{
			evaluable = $false
			hooks_ready = $false
			framework_version_known = $false
			agents_status = ''
		}
	}

	$hooksReady = ($raw -match '"hooks_ready"\s*:\s*true')
	$frameworkKnown = ($raw -match '"framework_version_known"\s*:\s*true')
	$agentsStatus = ''
	$agentsMatch = [regex]::Match($raw, '"agents_calibration"\s*:\s*\{.*?"status"\s*:\s*"([^"]+)"', [System.Text.RegularExpressions.RegexOptions]::Singleline)
	if ($agentsMatch.Success -and $agentsMatch.Groups.Count -gt 1) {
		$agentsStatus = [string]$agentsMatch.Groups[1].Value
	}

	return [pscustomobject]@{
		evaluable = $true
		hooks_ready = $hooksReady
		framework_version_known = $frameworkKnown
		agents_status = $agentsStatus
	}
}

function Get-RepoInventoryMap {
	param($InventoryRows)
	$map = @{}
	foreach ($item in $InventoryRows) {
		if ($item -and $item.repo) {
			$map[[string]$item.repo] = $item
		}
	}
	return $map
}

function Get-DirtyExplainability {
	param(
		[string]$Repo,
		[bool]$IsDirty
	)

	if (-not $IsDirty) {
		return [pscustomobject]@{
			explainable = $true
			reason = 'clean_workspace'
			source = 'git_status'
		}
	}

	$candidates = @(
		(Join-Path $Repo '.governance\expected_dirty.json'),
		(Join-Path $Repo 'governance\expected_dirty.json')
	)

	foreach ($path in $candidates) {
		if (-not (Test-Path $path)) { continue }
		try {
			$obj = Get-Content -Path $path -Raw -Encoding UTF8 | ConvertFrom-Json
			$reason = ''
			if ($obj -and $obj.reason) { $reason = [string]$obj.reason }
			if ([string]::IsNullOrWhiteSpace($reason) -and $obj -and $obj.expected_dirty_reason) { $reason = [string]$obj.expected_dirty_reason }
			if ([string]::IsNullOrWhiteSpace($reason) -and $obj -and $obj.expected -and $obj.expected.reason) { $reason = [string]$obj.expected.reason }
			if (-not [string]::IsNullOrWhiteSpace($reason)) {
				# TTL enforcement: if expires_at is present and past, treat as unexplained
				if ($obj -and $obj.expires_at) {
					try {
						$expiresAt = [datetimeoffset]::Parse([string]$obj.expires_at)
						if ([datetimeoffset]::UtcNow -gt $expiresAt) {
							# TTL expired: fail-closed even though reason field is present
							continue
						}
					} catch {
						# unparseable expires_at: fail-closed
						continue
					}
				}
				return [pscustomobject]@{
					explainable = $true
					reason = $reason.Trim()
					source = $path
				}
			}
		} catch {
			# ignore parse errors and continue fail-closed
		}
	}

	return [pscustomobject]@{
		explainable = $false
		reason = ''
		source = ''
	}
}

function Get-RepoNativeHookEvidence {
	param(
		[string]$Repo,
		[string]$RepoHead,
		[datetime]$MatrixWindowStartUtc,
		[bool]$DirtyState,
		[string]$DirtyReason
	)

	function Parse-JsonLine {
		param([string]$Line)
		if ([string]::IsNullOrWhiteSpace($Line)) { return $null }
		try {
			return ($Line | ConvertFrom-Json)
		} catch {
			return $null
		}
	}

	function Parse-IsoTime {
		param([string]$Value)
		if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
		try {
			return [datetimeoffset]::Parse($Value)
		} catch {
			return $null
		}
	}

	function Build-Evidence {
		param(
			[string]$Type,
			[string]$ArtifactPath,
			$Payload
		)

		$ts = $null
		$linkedHead = ''
		$exitCode = $null

		if ($Payload) {
			if ($Payload.timestamp) { $ts = Parse-IsoTime -Value ([string]$Payload.timestamp) }
			if (-not $ts -and $Payload.generated_at) { $ts = Parse-IsoTime -Value ([string]$Payload.generated_at) }
			if (-not $ts -and $Payload.created_at) { $ts = Parse-IsoTime -Value ([string]$Payload.created_at) }

			if ($Payload.linked_head_commit) { $linkedHead = [string]$Payload.linked_head_commit }
			elseif ($Payload.head_commit) { $linkedHead = [string]$Payload.head_commit }
			elseif ($Payload.repo_head) { $linkedHead = [string]$Payload.repo_head }
			elseif ($Payload.commit) { $linkedHead = [string]$Payload.commit }

			if ($null -ne $Payload.exit_code) { $exitCode = $Payload.exit_code }
			elseif ($null -ne $Payload.return_code) { $exitCode = $Payload.return_code }
		}

		return [pscustomobject]@{
			source = 'repo_local'
			evidence_type = $Type
			artifact_path = $ArtifactPath
			timestamp = if ($ts) { $ts.ToString('o') } else { '' }
			exit_code = $exitCode
			linked_head_commit = $linkedHead
			dirty_state = $DirtyState
			dirty_reason = if ($DirtyReason) { $DirtyReason } else { '' }
			timestamp_in_window = if ($ts) { ($ts.UtcDateTime -ge $MatrixWindowStartUtc) } else { $false }
			head_commit_match = (-not [string]::IsNullOrWhiteSpace($linkedHead) -and -not [string]::IsNullOrWhiteSpace($RepoHead) -and $linkedHead -eq $RepoHead)
		}
	}

	$canonicalAudit = Join-Path $Repo 'artifacts\runtime\canonical-audit-log.jsonl'
	$closeoutReceipts = Join-Path $Repo 'artifacts\runtime\closeout-receipts'
	$evidenceList = @()

	if (Test-Path $canonicalAudit) {
		try {
			$line = (Get-Content -Path $canonicalAudit -Encoding UTF8 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1)
			$payload = Parse-JsonLine -Line $line
			if ($payload -and -not [bool]$payload.gate_blocked) {
				# fail-closed: gate_blocked=True entries are rejected — blocked session cannot serve as evidence
				$evidenceList += (Build-Evidence -Type 'canonical_audit_log' -ArtifactPath $canonicalAudit -Payload $payload)
			}
		} catch {
			# fail-closed: ignore malformed artifact
		}
	}

	if (Test-Path $closeoutReceipts) {
		$latestReceipt = Get-ChildItem -Path $closeoutReceipts -Filter '*.json' -File -ErrorAction SilentlyContinue |
			Sort-Object LastWriteTimeUtc -Descending |
			Select-Object -First 1
		if ($latestReceipt) {
			try {
				$payload = Get-Content -Path $latestReceipt.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
				$evidenceList += (Build-Evidence -Type 'closeout_receipt' -ArtifactPath $latestReceipt.FullName -Payload $payload)
			} catch {
				# fail-closed: ignore malformed artifact
			}
		}
	}

	$selectedEvidence = $null
	if ($evidenceList.Count -gt 0) {
		$selectedEvidence = $evidenceList |
			Sort-Object @{Expression = { if ([string]::IsNullOrWhiteSpace($_.timestamp)) { [datetimeoffset]::MinValue } else { try { [datetimeoffset]::Parse($_.timestamp) } catch { [datetimeoffset]::MinValue } } }; Descending = $true } |
			Select-Object -First 1
	}

	$exists = ($null -ne $selectedEvidence)
	return [pscustomobject]@{
		exists = $exists
		evidence = $selectedEvidence
		evidence_list = $evidenceList
		has_canonical_audit_log = @($evidenceList | Where-Object { $_.evidence_type -eq 'canonical_audit_log' }).Count -gt 0
		has_closeout_receipt = @($evidenceList | Where-Object { $_.evidence_type -eq 'closeout_receipt' }).Count -gt 0
	}
}

function Get-RepoNativeStats {
	param(
		$Rows,
		$InventoryMap,
		[datetime]$MatrixWindowStartUtc
	)

	$details = @()
	foreach ($row in $Rows) {
		$signals = Get-ReadinessSignalsFromRaw -Row $row
		if (-not $signals.evaluable) {
			$details += [pscustomobject]@{
				repo = $row.repo
				evaluable = $false
				classification = 'unknown'
				hooks_ready = $false
				framework_version_known = $false
				agents_repo_specific = $false
				signals_passed = 0
			}
			continue
		}

		$hooksReady = [bool]$signals.hooks_ready
		$frameworkKnown = [bool]$signals.framework_version_known
		$agentStatus = [string]$signals.agents_status
		$agentsRepoSpecific = ($agentStatus -ne 'scaffold_only' -and $agentStatus -ne 'generic_filled' -and $agentStatus -ne '')
		$inventory = $null
		if ($InventoryMap.ContainsKey([string]$row.repo)) {
			$inventory = $InventoryMap[[string]$row.repo]
		}
		$isDirty = if ($inventory -ne $null) { [bool]$inventory.dirty } else { $false }
		$repoHead = if ($inventory -ne $null -and $inventory.head) { [string]$inventory.head } else { '' }
		$dirtyExplainability = Get-DirtyExplainability -Repo ([string]$row.repo) -IsDirty $isDirty
		$hookEvidence = Get-RepoNativeHookEvidence -Repo ([string]$row.repo) -RepoHead $repoHead -MatrixWindowStartUtc $MatrixWindowStartUtc -DirtyState $isDirty -DirtyReason ([string]$dirtyExplainability.reason)

		$signalsPassed = 0
		if ($hooksReady) { $signalsPassed += 1 }
		if ($frameworkKnown) { $signalsPassed += 1 }
		if ($agentsRepoSpecific) { $signalsPassed += 1 }

		$candidate = ($signalsPassed -eq 3)
		$evidenceExists = [bool]$hookEvidence.exists
		$headMatch = ($evidenceExists -and [bool]$hookEvidence.evidence.head_commit_match)
		$timestampInWindow = ($evidenceExists -and [bool]$hookEvidence.evidence.timestamp_in_window)
		$verified = ($candidate -and $dirtyExplainability.explainable -and $evidenceExists -and $headMatch -and $timestampInWindow)

		$classification = 'matrix_only'
		if ($verified) {
			$classification = 'repo_native_verified'
		} elseif ($candidate) {
			$classification = 'repo_native_candidate'
		} elseif ($signalsPassed -ge 2) {
			$classification = 'partial'
		}

		$details += [pscustomobject]@{
			repo = $row.repo
			evaluable = $true
			classification = $classification
			hooks_ready = $hooksReady
			framework_version_known = $frameworkKnown
			agents_repo_specific = $agentsRepoSpecific
			signals_passed = $signalsPassed
			is_dirty = $isDirty
			repo_head = $repoHead
			dirty_explainable = [bool]$dirtyExplainability.explainable
			dirty_reason = [string]$dirtyExplainability.reason
			dirty_reason_source = [string]$dirtyExplainability.source
			repo_native_hook_evidence = if ($hookEvidence.evidence) { $hookEvidence.evidence } else { $null }
			repo_native_hook_evidence_exists = $evidenceExists
			repo_native_hook_head_match = $headMatch
			repo_native_hook_timestamp_in_window = $timestampInWindow
			repo_native_hook_smoke_pass = ($evidenceExists -and $headMatch -and $timestampInWindow)
			has_canonical_audit_log = [bool]$hookEvidence.has_canonical_audit_log
			has_closeout_receipt = [bool]$hookEvidence.has_closeout_receipt
		}
	}

	$evaluable = @($details | Where-Object { $_.evaluable })
	$total = $evaluable.Count
	$repoNativeCandidateCount = @($evaluable | Where-Object { $_.classification -eq 'repo_native_candidate' -or $_.classification -eq 'repo_native_verified' }).Count
	$repoNativeVerifiedCount = @($evaluable | Where-Object { $_.classification -eq 'repo_native_verified' }).Count
	$partialCount = @($evaluable | Where-Object { $_.classification -eq 'partial' }).Count
	$matrixOnlyCount = @($evaluable | Where-Object { $_.classification -eq 'matrix_only' }).Count
	$candidateRatio = if ($total -gt 0) { [math]::Round($repoNativeCandidateCount / $total, 4) } else { 0.0 }
	$verifiedRatio = if ($total -gt 0) { [math]::Round($repoNativeVerifiedCount / $total, 4) } else { 0.0 }

	return [pscustomobject]@{
		repo_native_candidate_count = $repoNativeCandidateCount
		repo_native_verified_count = $repoNativeVerifiedCount
		partial_count = $partialCount
		matrix_only_count = $matrixOnlyCount
		total = $total
		candidate_ratio = $candidateRatio
		verified_ratio = $verifiedRatio
		details = $details
	}
}

function Get-Confidence {
	param(
		[int]$SmokePass,
		[int]$SmokeTotal,
		[int]$MetadataFail,
		[int]$NegativeFail,
		[int]$RegressionFail,
		[int]$DriftFail
	)

	if ($SmokeTotal -eq 0) { return 'LOW' }
	$smokeRate = $SmokePass / $SmokeTotal
	if ($smokeRate -ge 0.95 -and $MetadataFail -eq 0 -and $NegativeFail -eq 0 -and $RegressionFail -eq 0 -and $DriftFail -eq 0) {
		return 'HIGH'
	}
	if ($smokeRate -ge 0.80 -and $MetadataFail -le 1 -and $NegativeFail -le 1 -and $RegressionFail -eq 0 -and $DriftFail -le 1) {
		return 'MEDIUM'
	}
	return 'LOW'
}

$companySmokePass = Count-SmokePass -rows $companyRerun
$companySmokeTotal = Count-SmokeTotal -rows $companyRerun
$privateSmokePass = Count-SmokePass -rows $privateBaseline
$privateSmokeTotal = Count-SmokeTotal -rows $privateBaseline

$metadataFailCount = ($metadataCorruption | Where-Object { $_.executed -and -not $_.pass }).Count
$negativeFailCount = @($negativeContractCompany, $negativeContractPrivate, $dirtyProbeCompany, $dirtyProbePrivate | Where-Object { $_.executed -and $_.pass -eq $false }).Count
$regressionFailCount = if (
	$enumdRegression.executed -and (
		$enumdRegression.collision_test -ne 'PASS' -or
		$enumdRegression.mapping_consistency -ne 'PASS' -or
		$enumdRegression.unknown_slug_fallback -ne 'PASS_NO_DEFAULT_PROJECT_FALLBACK'
	)
) { 1 } else { 0 }
$driftFailCount = @($planDrift, $manifestDrift, $contractDrift | Where-Object { $_.executed -and -not $_.pass }).Count

$repoInventoryMap = Get-RepoInventoryMap -InventoryRows $inventory
$companyRepoNative = Get-RepoNativeStats -Rows $companyRerun -InventoryMap $repoInventoryMap -MatrixWindowStartUtc $matrixWindowStartUtc
$privateRepoNative = Get-RepoNativeStats -Rows $privateBaseline -InventoryMap $repoInventoryMap -MatrixWindowStartUtc $matrixWindowStartUtc
$allRowsUnique = Get-UniqueRepoRows -Rows @($companyRerun + $privateBaseline)
$allRepoNative = Get-RepoNativeStats -Rows $allRowsUnique -InventoryMap $repoInventoryMap -MatrixWindowStartUtc $matrixWindowStartUtc

# Scope-normalized metrics (required tier only)
$requiredDetails = @($allRepoNative.details | Where-Object { $governanceScope[[string]$_.repo] -eq 'required' })
$requiredTotal = $requiredDetails.Count
$requiredVerified = @($requiredDetails | Where-Object { [string]$_.classification -eq 'repo_native_verified' }).Count
$requiredVerifiedRatio = if ($requiredTotal -gt 0) { [math]::Round($requiredVerified / $requiredTotal, 4) } else { 0 }
$requiredVerifiedDetails = @($requiredDetails | Where-Object { [string]$_.classification -eq 'repo_native_verified' })
$requiredCandidateOrAbove = @(
	$requiredDetails |
	Where-Object { [string]$_.classification -eq 'repo_native_candidate' -or [string]$_.classification -eq 'repo_native_verified' }
).Count
$requiredFreshnessBlocked = @(
	$requiredDetails |
	Where-Object {
		([string]$_.classification -eq 'repo_native_candidate') -and
		[bool]$_.repo_native_hook_evidence_exists -and
		[bool]$_.repo_native_hook_head_match -and
		(-not [bool]$_.repo_native_hook_timestamp_in_window)
	}
).Count
$requiredVerifiedDirtyTrue = @($requiredVerifiedDetails | Where-Object { [bool]$_.is_dirty }).Count
$requiredVerifiedDirtyFalse = @($requiredVerifiedDetails | Where-Object { -not [bool]$_.is_dirty }).Count
$requiredVerifiedExpectedDirtyTtlValid = @(
	$requiredVerifiedDetails |
	Where-Object { [bool]$_.is_dirty -and [bool]$_.dirty_explainable }
).Count

function Get-BlockerRemediation {
	param(
		[string]$RemediationKey,
		$Catalog
	)
	if (-not $Catalog.ContainsKey($RemediationKey)) {
		return [pscustomobject]@{
			remediation_type = 'unknown_mapping'
			command = ''
			action = "No mapping for remediation key '$RemediationKey'"
			verification_source = ''
		}
	}
	return $Catalog[$RemediationKey]
}

$requiredSurfaceKeys = @($governanceBaseline.required_surfaces.Keys)
$perRepoBaselineDrift = @()
$perRepoRemediation = @()
foreach ($d in $allRepoNative.details) {
	$lock = Get-LockSurfaceInfo -Repo ([string]$d.repo)
	$driftStatus = 'unknown'
	if ($lock.lock_valid) {
		$driftStatus = Compare-BaselineVersion -RepoVersion ([string]$lock.repo_baseline_version) -FrameworkVersion ([string]$governanceBaseline.baseline_version)
	}

	$observed = Get-ObservedSurfaceStatus -Detail $d
	$adopted = @($lock.adopted_surfaces)
	$missingRequired = @()
	$adoptedObservedMissing = @()
	foreach ($surface in $requiredSurfaceKeys) {
		if ($adopted -notcontains $surface) {
			$missingRequired += $surface
		} elseif ($observed.ContainsKey($surface) -and -not [bool]$observed[$surface]) {
			$adoptedObservedMissing += $surface
		}
	}

	$driftWarning = ''
	if ($driftStatus -eq 'drift_ahead') {
		$driftWarning = 'repo baseline newer than framework baseline; review governance_baseline.yaml update necessity'
	}

	$perRepoBaselineDrift += [pscustomobject]@{
		repo = $d.repo
		drift_status = $driftStatus
		repo_baseline = [string]$lock.repo_baseline_version
		framework_baseline = [string]$governanceBaseline.baseline_version
		lock_exists = [bool]$lock.lock_exists
		lock_valid = [bool]$lock.lock_valid
		adopted_surfaces = $adopted
		missing_required_surfaces = $missingRequired
		adopted_but_observed_missing_surfaces = $adoptedObservedMissing
		warning = $driftWarning
	}

	# Build blocker remediation suggestions from observed signals only.
	$blockers = @()
	if (-not [bool]$d.hooks_ready) { $blockers += 'hooks' }
	if (-not [bool]$d.framework_version_known) { $blockers += 'fw' }
	if (-not [bool]$d.agents_repo_specific) { $blockers += 'agents' }
	if (-not [bool]$d.dirty_explainable) { $blockers += 'dirty_ok' }
	if (-not [bool]$d.repo_native_hook_evidence_exists) { $blockers += 'evidence' }
	if ([bool]$d.repo_native_hook_evidence_exists -and -not [bool]$d.repo_native_hook_head_match) { $blockers += 'head_ok' }
	if ([bool]$d.repo_native_hook_evidence_exists -and -not [bool]$d.repo_native_hook_timestamp_in_window) { $blockers += 'ts_ok' }

	$suggestions = @()
	foreach ($b in $blockers | Select-Object -Unique) {
		$r = Get-BlockerRemediation -RemediationKey $b -Catalog $remediationCatalog
		$suggestions += [pscustomobject]@{
			blocker = $b
			remediation_type = $r.remediation_type
			command = $r.command
			action = $r.action
			human_required = [bool]$r.human_required
			verification_source = $r.verification_source
		}
	}

	$perRepoRemediation += [pscustomobject]@{
		repo = $d.repo
		classification = $d.classification
		suggestions = $suggestions
	}
}

$snapshot = [ordered]@{
	matrix_version = 'v1'
	generated_at = (Get-Date).ToString('s')
	matrix_window_start_utc = $matrixWindowStartUtc.ToString('o')
	evidence_window_days = $evidenceWindowDays
	framework_repo = $framework
	repo_inventory = $inventory
	baseline = [ordered]@{
		company = $companyBaseline
		private = $privateBaseline
	}
	metadata_validation = [ordered]@{
		corruption_sample = $metadataCorruption
	}
	negative_path = [ordered]@{
		contract_missing_company = $negativeContractCompany
		contract_missing_private = $negativeContractPrivate
		dirty_state_company = $dirtyProbeCompany
		dirty_state_private = $dirtyProbePrivate
	}
	enumd_regression = $enumdRegression
	drift_resistance = [ordered]@{
		plan_stale = $planDrift
		manifest_version = $manifestDrift
		contract_schema = $contractDrift
	}
	rerun_company = $companyRerun
	confidence = [ordered]@{
		company = [ordered]@{
			grade = (Get-Confidence -SmokePass $companySmokePass -SmokeTotal $companySmokeTotal -MetadataFail $metadataFailCount -NegativeFail $negativeFailCount -RegressionFail $regressionFailCount -DriftFail $driftFailCount)
			smoke_pass = $companySmokePass
			smoke_total = $companySmokeTotal
			metadata_fail = $metadataFailCount
			negative_fail = $negativeFailCount
			regression_fail = $regressionFailCount
			drift_fail = $driftFailCount
			repo_native_governance_candidate_ratio = $companyRepoNative.candidate_ratio
			repo_native_governance_verified_ratio = $companyRepoNative.verified_ratio
		}
		private = [ordered]@{
			grade = (Get-Confidence -SmokePass $privateSmokePass -SmokeTotal $privateSmokeTotal -MetadataFail $metadataFailCount -NegativeFail $negativeFailCount -RegressionFail $regressionFailCount -DriftFail $driftFailCount)
			smoke_pass = $privateSmokePass
			smoke_total = $privateSmokeTotal
			metadata_fail = $metadataFailCount
			negative_fail = $negativeFailCount
			regression_fail = $regressionFailCount
			drift_fail = $driftFailCount
			repo_native_governance_candidate_ratio = $privateRepoNative.candidate_ratio
			repo_native_governance_verified_ratio = $privateRepoNative.verified_ratio
		}
	}
	operational_maturity = [ordered]@{
		repo_native_governance_candidate_ratio = [ordered]@{
			overall = $allRepoNative.candidate_ratio
			company = $companyRepoNative.candidate_ratio
			private = $privateRepoNative.candidate_ratio
		}
		repo_native_governance_verified_ratio = [ordered]@{
			overall = $allRepoNative.verified_ratio
			company = $companyRepoNative.verified_ratio
			private = $privateRepoNative.verified_ratio
		}
		scope_normalized_verified_ratio = [ordered]@{
			required_verified = $requiredVerified
			required_total = $requiredTotal
			ratio = $requiredVerifiedRatio
		}
		structural_readiness = [ordered]@{
			required_candidate_or_above = $requiredCandidateOrAbove
			required_total = $requiredTotal
			ratio = if ($requiredTotal -gt 0) { [math]::Round($requiredCandidateOrAbove / $requiredTotal, 4) } else { 0 }
			freshness_blocked_count = $requiredFreshnessBlocked
		}
		verified_dirty_dependency = [ordered]@{
			required_verified_total = $requiredVerified
			dirty_true_verified = $requiredVerifiedDirtyTrue
			dirty_false_verified = $requiredVerifiedDirtyFalse
			expected_dirty_ttl_valid = $requiredVerifiedExpectedDirtyTtlValid
		}
		repo_native_governance_breakdown = [ordered]@{
			overall = $allRepoNative
			company = $companyRepoNative
			private = $privateRepoNative
		}
		baseline_drift = [ordered]@{
			framework_baseline_version = $governanceBaseline.baseline_version
			required_surfaces = $governanceBaseline.required_surfaces
			per_repo = $perRepoBaselineDrift
		}
		remediation_suggestions = $perRepoRemediation
	}
}

$json = $snapshot | ConvertTo-Json -Depth 30
Set-Content -Path $snapshotJsonPath -Value $json -Encoding UTF8

$md = @()
$md += '# Governance Repo Matrix Snapshot'
$md += ""
$md += "- generated_at: $($snapshot.generated_at)"
$md += "- json: $snapshotJsonPath"
$md += ""
$md += '## Confidence'
$md += "- company: $($snapshot.confidence.company.grade) ($companySmokePass/$companySmokeTotal smoke pass)"
$md += "- private: $($snapshot.confidence.private.grade) ($privateSmokePass/$privateSmokeTotal smoke pass)"
$md += "- repo-native governance candidate ratio (overall): $($allRepoNative.repo_native_candidate_count)/$($allRepoNative.total) ($($allRepoNative.candidate_ratio))"
$md += "- repo-native governance verified ratio (overall): $($allRepoNative.repo_native_verified_count)/$($allRepoNative.total) ($($allRepoNative.verified_ratio))"
$md += "- repo-native governance candidate ratio (company): $($companyRepoNative.repo_native_candidate_count)/$($companyRepoNative.total) ($($companyRepoNative.candidate_ratio))"
$md += "- repo-native governance verified ratio (company): $($companyRepoNative.repo_native_verified_count)/$($companyRepoNative.total) ($($companyRepoNative.verified_ratio))"
$md += "- repo-native governance candidate ratio (private): $($privateRepoNative.repo_native_candidate_count)/$($privateRepoNative.total) ($($privateRepoNative.candidate_ratio))"
$md += "- repo-native governance verified ratio (private): $($privateRepoNative.repo_native_verified_count)/$($privateRepoNative.total) ($($privateRepoNative.verified_ratio))"
$md += "- scope-normalized verified ratio (required only): $requiredVerified/$requiredTotal ($requiredVerifiedRatio)"
$md += "- structural readiness (required candidate_or_above): $requiredCandidateOrAbove/$requiredTotal ($(if ($requiredTotal -gt 0) { [math]::Round($requiredCandidateOrAbove / $requiredTotal, 4) } else { 0 }))"
$md += "- freshness blocked count (required): $requiredFreshnessBlocked"
$md += "- evidence freshness window (days): $evidenceWindowDays"
$md += "- verified dirty dependency (required verified only): total=$requiredVerified, dirty_true=$requiredVerifiedDirtyTrue, dirty_false=$requiredVerifiedDirtyFalse, expected_dirty_ttl_valid=$requiredVerifiedExpectedDirtyTtlValid"
$md += ""
$md += '## Notes'
$md += '- Negative-path and drift tests run with temporary mutation and restoration.'
$md += '- Enumd regression checks use static adapter consistency probes plus fallback detection.'
$md += '- repo-native candidate ratio uses hooks/framework-lock/agents signals only.'
$md += '- repo-native verified ratio is fail-closed: candidate plus repo-local evidence linked to repo HEAD and within current matrix window, with dirty state explained.'
$md += ''
$md += '## Per-Repo Classification'
$md += '| repo | tier | ev_tier | class | hooks | fw | agents | dirty_ok | evidence | head_ok | ts_ok | blockers -> action |'
$md += '|---|---|---|---|---|---|---|---|---|---|---|---|'
foreach ($d in $allRepoNative.details) {
	$name = [System.IO.Path]::GetFileName([string]$d.repo)
	$tierCol = if ($governanceScope.ContainsKey([string]$d.repo)) { $governanceScope[[string]$d.repo] } else { 'unknown' }
	$evTierCol = Get-EvidenceTier -Repo ([string]$d.repo)
	$cl = [string]$d.classification
	$hooks = if ([bool]$d.hooks_ready) { 'Y' } else { 'N' }
	$fw = if ([bool]$d.framework_version_known) { 'Y' } else { 'N' }
	$ag = if ([bool]$d.agents_repo_specific) { 'Y' } else { 'N' }
	$dok = if ([bool]$d.dirty_explainable) { 'Y' } else { 'N' }
	$ev = if ([bool]$d.repo_native_hook_evidence_exists) { 'Y' } else { 'N' }
	$hok = if ([bool]$d.repo_native_hook_head_match) { 'Y' } else { 'N' }
	$tok = if ([bool]$d.repo_native_hook_timestamp_in_window) { 'Y' } else { 'N' }
	$blockers = @()
	$repoSuggest = $perRepoRemediation | Where-Object { [string]$_.repo -eq [string]$d.repo } | Select-Object -First 1
	if ($repoSuggest -and $repoSuggest.suggestions) {
		foreach ($s in $repoSuggest.suggestions) {
			if ($s.remediation_type -eq 'verified_command' -and -not [string]::IsNullOrWhiteSpace([string]$s.command)) {
				$blockers += ("{0} -> {1}" -f [string]$s.blocker, [string]$s.command)
			} elseif (-not [string]::IsNullOrWhiteSpace([string]$s.action)) {
				$blockers += ("{0} -> {1}" -f [string]$s.blocker, [string]$s.action)
			} else {
				$blockers += ("{0} -> unknown_mapping" -f [string]$s.blocker)
			}
		}
	}
	$blockerStr = if ($blockers.Count -eq 0) { 'none' } else { ($blockers -join '; ') }
	$md += "| $name | $tierCol | $evTierCol | $cl | $hooks | $fw | $ag | $dok | $ev | $hok | $tok | $blockerStr |"
}
$md += ''
$md += '## Baseline Drift'
foreach ($b in $perRepoBaselineDrift) {
	$repoName = [System.IO.Path]::GetFileName([string]$b.repo)
	$md += "### $repoName"
	$md += "- drift_status: $($b.drift_status)"
	$md += "- repo_baseline: $($b.repo_baseline)"
	$md += "- framework_baseline: $($b.framework_baseline)"
	if ($b.warning) { $md += "- warning: $($b.warning)" }
	$ad = if ($b.adopted_surfaces.Count -gt 0) { ($b.adopted_surfaces -join ', ') } else { '(none)' }
	$mr = if ($b.missing_required_surfaces.Count -gt 0) { ($b.missing_required_surfaces -join ', ') } else { '(none)' }
	$am = if ($b.adopted_but_observed_missing_surfaces.Count -gt 0) { ($b.adopted_but_observed_missing_surfaces -join ', ') } else { '(none)' }
	$md += "- adopted_surfaces: $ad"
	$md += "- missing_required_surfaces: $mr"
	$md += "- adopted_but_observed_missing_surfaces: $am"
}
$md += ''
$md += '## Remediation Suggestions'
foreach ($r in $perRepoRemediation) {
	if (-not $r.suggestions -or $r.suggestions.Count -eq 0) { continue }
	$repoName = [System.IO.Path]::GetFileName([string]$r.repo)
	$md += "### $repoName"
	$md += '| blocker | remediation_type | command | action | human_required | verification_source |'
	$md += '|---|---|---|---|---|---|'
	foreach ($s in $r.suggestions) {
		$cmd = if ([string]::IsNullOrWhiteSpace([string]$s.command)) { '(none)' } else { [string]$s.command }
		$act = if ([string]::IsNullOrWhiteSpace([string]$s.action)) { '(none)' } else { [string]$s.action }
		$vrf = if ([string]::IsNullOrWhiteSpace([string]$s.verification_source)) { '(none)' } else { [string]$s.verification_source }
		$hr = if ($s.remediation_type -eq 'human_required') { 'true' } else { 'false' }
		$md += "| $($s.blocker) | $($s.remediation_type) | $cmd | $act | $hr | $vrf |"
	}
}

$md += ''
$md += '## Adoption Task Packets'
foreach ($b in $perRepoBaselineDrift) {
	$repo = [string]$b.repo
	$repoName = [System.IO.Path]::GetFileName($repo)
	$detail = $allRepoNative.details | Where-Object { [string]$_.repo -eq $repo } | Select-Object -First 1
	$observedNow = if ($detail) { Get-ObservedSurfaceStatus -Detail $detail } else { @{} }
	$rem = $perRepoRemediation | Where-Object { [string]$_.repo -eq $repo } | Select-Object -First 1
	$hasBlockers = ($rem -and $rem.suggestions -and $rem.suggestions.Count -gt 0)
	$hasMissingSurface = ($b.missing_required_surfaces -and $b.missing_required_surfaces.Count -gt 0)
	$hasObservedMissing = ($b.adopted_but_observed_missing_surfaces -and $b.adopted_but_observed_missing_surfaces.Count -gt 0)
	$hasDrift = ($b.drift_status -eq 'drift_behind' -or $b.drift_status -eq 'drift_ahead' -or $b.drift_status -eq 'unknown')
	if (-not ($hasBlockers -or $hasMissingSurface -or $hasObservedMissing -or $hasDrift)) { continue }

	$triggerReason = if (($hasBlockers -or $hasMissingSurface -or $hasObservedMissing) -and $hasDrift) { 'both' } elseif ($hasBlockers -or $hasMissingSurface -or $hasObservedMissing) { 'blockers' } else { 'baseline_drift' }
	$blockerList = if ($hasBlockers) { (@($rem.suggestions | ForEach-Object { [string]$_.blocker } | Select-Object -Unique) -join ', ') } else { '(none)' }
	$missingList = if ($hasMissingSurface) { ($b.missing_required_surfaces -join ', ') } else { '(none)' }
	$obsMissingList = if ($hasObservedMissing) { ($b.adopted_but_observed_missing_surfaces -join ', ') } else { '(none)' }

	$md += "### Adoption Task Packet: $repoName"
	$md += ''
	$md += '#### Target Repo'
	$md += "- Repo: $repoName"
	$md += "- Path: $repo"
	$md += ''
	$md += '#### Goal'
	$md += 'Bring this repo''s AI Governance surfaces back in sync with the current framework baseline and matrix findings.'
	$md += ''
	$md += '#### Current Findings'
	$md += "- trigger_reason: $triggerReason"
	$md += "- drift_status: $($b.drift_status)"
	$md += "- blockers: $blockerList"
	$md += "- missing_required_surfaces: $missingList"
	$md += "- adopted_but_observed_missing: $obsMissingList"
	$md += ''
	$md += '#### Allowed Changes'
	$md += '- repo-specific AGENTS.md fleet overlay section'
	$md += '- governance/framework.lock.json'
	$md += '- governance metadata required by the current baseline'
	$md += '- evidence / closeout artifacts generated by verified commands'
	$md += ''
	$md += '#### Forbidden Changes'
	$md += '- domain contract content above fleet overlay boundary'
	$md += '- framework global rules or rule precedence'
	$md += '- application source code unrelated to governance adoption'
	$md += '- enforcement behavior unless explicitly requested and verified'
	$md += ''
	$md += 'Fleet overlay boundary rule:'
	$md += '- You may modify content below: `<!-- governance:section_start=fleet_overlay -->`'
	$md += '- You must not modify domain contract content above that boundary.'
	$md += ''
	$md += '#### Required Actions'
	$md += '1. Fix only listed blockers/missing surfaces/observed-missing surfaces.'
	$md += '2. Use only `verified_command` items from remediation suggestions as copy-paste commands.'
	$md += '3. For `human_required` items, document required review and stop short of speculative automation.'
	$md += '4. Update `adopted_surfaces` only when the surface is actually installed/verified.'
	$md += '5. Do not change forbidden files/sections.'
	$md += ''
	$md += '#### Done Definition'
	$md += '- targeted blockers resolved or explicitly marked human-required'
	$md += '- missing required surfaces resolved or explicitly human-required'
	$md += '- no previously passing signal has regressed to failing'
	$md += '- framework.lock.json adopted_surfaces matches installed surfaces'
	$md += '- forbidden files/sections unchanged'
	$md += ''
	$md += '#### Before/After Signal Table (required output)'
	$md += '| Signal | Before | After | Status |'
	$md += '|---|---|---|---|'
	foreach ($sig in @('hooks_config','framework_lock','agents_calibration','expected_dirty','closeout_evidence','head_commit_match','timestamp_freshness')) {
		$before = if ($observedNow.ContainsKey($sig) -and [bool]$observedNow[$sig]) { 'Y' } else { 'N' }
		$md += "| $sig | $before | rerun_required | pending |"
	}
	$md += ''
	$md += '#### Non-Claims'
	$md += '- do not claim permanent verified status'
	$md += '- do not claim all future runs will pass'
	$md += '- do not claim semantic correctness proof'
	$md += '- do not claim authority boundary changes'
}
Set-Content -Path $snapshotMdPath -Value ($md -join "`r`n") -Encoding UTF8

# Auto-append one entry to scope_normalized_trend.jsonl
$trendPath = Join-Path $framework 'governance\fleet\scope_normalized_trend.jsonl'
$trendSnapshotName = [System.IO.Path]::GetFileNameWithoutExtension($snapshotMdPath)
$trendEntry = [ordered]@{
	date               = (Get-Date).ToString('yyyy-MM-dd')
	snapshot           = $trendSnapshotName
	required_verified  = $requiredVerified
	candidate_or_above = $requiredCandidateOrAbove
	freshness_blocked_count = $requiredFreshnessBlocked
	required_total     = $requiredTotal
	ratio              = $requiredVerifiedRatio
	evidence_window_days = $evidenceWindowDays
	closeout_maintenance_mode = 'event-driven+stale-warning'
	dirty_true_count   = $requiredVerifiedDirtyTrue
	note               = 'auto'
}
$trendLine = ($trendEntry | ConvertTo-Json -Compress -Depth 5)
Add-Content -Path $trendPath -Value $trendLine -Encoding UTF8

Write-Output "SNAPSHOT_JSON=$snapshotJsonPath"
Write-Output "SNAPSHOT_MD=$snapshotMdPath"
Write-Output "COMPANY_SMOKE_PASS=$companySmokePass/$companySmokeTotal"
Write-Output "PRIVATE_SMOKE_PASS=$privateSmokePass/$privateSmokeTotal"
Write-Output "COMPANY_CONFIDENCE=$($snapshot.confidence.company.grade)"
Write-Output "PRIVATE_CONFIDENCE=$($snapshot.confidence.private.grade)"
Write-Output "REPO_NATIVE_CANDIDATE_RATIO_OVERALL=$($allRepoNative.repo_native_candidate_count)/$($allRepoNative.total)"
Write-Output "REPO_NATIVE_VERIFIED_RATIO_OVERALL=$($allRepoNative.repo_native_verified_count)/$($allRepoNative.total)"
