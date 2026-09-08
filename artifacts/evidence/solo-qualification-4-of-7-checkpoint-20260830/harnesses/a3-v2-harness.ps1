param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{64}$')]
    [string]$ExpectedSourceSha256,

    [Parameter(Mandatory = $true)]
    [ValidateSet('Diagnostic', 'Qualification')]
    [string]$ExecutionMode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExpectedLaunchCwd = 'D:\ai-governance-framework'
$ExpectedPowerShell = @{ Path = 'C:\Users\daish\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'; Length = 301368; Sha256 = 'db6dd81183fe57d22e03b911ec9a30a2fd7c40542e97743615355a6fb44f458f' }
$ExpectedGit = @{ Path = 'C:\Program Files\Git\cmd\git.exe'; Length = 46480; Sha256 = '3cbd024d9d11ef08bd6a0cb5a973613c50825b4952bc6006f3f4222f436091e5' }
$ExpectedTar = @{ Path = 'C:\Windows\System32\tar.exe'; Length = 92176; Sha256 = '9b77d4c912f2edae8c241d0ece1094d2ac068b084269ceaf85d7c7b085d2ae86' }
$ExpectedNode = @{ Path = 'C:\Program Files\nodejs\node.exe'; Length = 89953280; Sha256 = 'd14ba95cdce1ef7dc9ad3ac74949ca5db38b27378ee30f30a23cf26f9e875a11' }

$ExpectedRuntimeFiles = @(
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\package.json'; Length = 5932; Sha256 = 'caa41f04799bd42f3cfd100c4282e630d77ffc7deb1e7e4927794fcb7f137f34' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\vitest.mjs'; Length = 43; Sha256 = '39db22f579acf5639bbb17a261408debbde03f4692c0c439e77e7f13aeba74d6' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\dist\cli.js'; Length = 284; Sha256 = '2aa6bcb906e952ee722fe631dd34c9f87d28e4244716197156c6274d17f28aac' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\dist\node.js'; Length = 4398; Sha256 = '8f979608f2da7790d4009ab5e06e354ae8351e357f74ca6825f27e0c2b340c4e' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\cac.DdICfEr1.js'; Length = 96007; Sha256 = '9516d4611b7f7ce624d66d41de5eb67093ad6f95690d41cddc8e1ed318e0a499' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\cli-api.BK8pd4xc.js'; Length = 495252; Sha256 = 'a2d629ec07fbaf58055bca9858076c6c13763042d97196272c45ccfdb727f498' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\coverage.DM_a_rWm.js'; Length = 54974; Sha256 = 'e509f3cc1bd81ae6426265253fa926cbde02be5cebfe35b1df422017bffdca31' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\defaults.9aQKnqFk.js'; Length = 2190; Sha256 = 'e500ba917d0d320a037b4ad92ae691462b50a939e21b1f98d0073c45d55466ab' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\@vitest\runner\dist\utils.js'; Length = 679; Sha256 = 'f778f89df543143d276dc6e9233feb749531512dae30b29f80cb229560f19490' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\@vitest\runner\dist\chunk-artifact.js'; Length = 119048; Sha256 = 'c10a7a80fca65fb42e27eabf7655c5ce5ecf36e8aaeb1811499efd063df62556' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vite\package.json'; Length = 5084; Sha256 = '2f482c846a1c5b9e5883b458b3e54a171a320c2e8d9b924c7383c4baef607b09' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vite\dist\node\index.js'; Length = 2670; Sha256 = 'c7ea52906f843318d7971209ce62bd24bab60590275e8f415c5564fa35cb82dc' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vite\dist\node\chunks\node.js'; Length = 1319608; Sha256 = '3968fab97a9d0882f0e2e754bd0d5b417f0a84596e293179a9a6e585919f041c' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\@vitejs\plugin-react\package.json'; Length = 2108; Sha256 = '48c5cd6c4ca97c01a869e3a931e8d8cf7e77977d14e2818cbeaaf8cc4d27de82' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\@vitejs\plugin-react\dist\index.js'; Length = 7013; Sha256 = '57513401a0960733e0604371f9136a8c89a3adf070878d65b8cc0f5c826de921' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vite-plugin-pwa\package.json'; Length = 4649; Sha256 = '5b4084e795255aa038f2554b6481535d6a91f791e6cfe28cf8a07b474e310a15' },
    @{ Path = 'D:\english-vocab-trainer\node_modules\vite-plugin-pwa\dist\index.cjs'; Length = 74056; Sha256 = 'c5c86832e0aac86e662762900a42e067023fe2c2b25d34daed0c96ee9e1a3d72' }
)

$Repository = 'D:\english-vocab-trainer'
$GitSafeDirectory = 'D:/english-vocab-trainer'
$ExpectedGitDirectory = 'D:\english-vocab-trainer\.git'
$GitConfigArguments = @('-c', "safe.directory=$GitSafeDirectory", '-c', 'core.hooksPath=')
$LiveNodeModules = 'D:\english-vocab-trainer\node_modules'
$VitestEntry = 'D:\english-vocab-trainer\node_modules\vitest\vitest.mjs'
$ConfigLoaderArgument = '--configLoader=runner'
$BaseCommit = '04e320233efb6ad8d49bf80c59374918ee126bce'
$FixCommit = 'f1da14b857dc3fa8831215360f818f9600042c3e'
$OraclePath = 'src/lib/dailyLearning.test.ts'
$OracleBlob = 'dac278c808d31093382b79737f1392d441bd379d'
$ConfigPath = 'vite.config.ts'
$ConfigBlob = '0bb67e3692b67fd8cadf839450d46df53331e761'
$ExpectedConfigBytes = 2257
$ExpectedConfigSha256 = 'b0e2dc39a6d851094a8b4716e5334f2406aca715e9b6042670a509a24a799e82'
$RequiredCases = @(
    'shows reviewed words first on the Starters route',
    'shows reviewed words first on the Movers route',
    'shows reviewed words first on the cefr-a1 route',
    'shows reviewed words first on the cefr-a2 route',
    'shows reviewed words first on the gept-elementary route'
)

# Frozen before runner output was observed. This is the A3-required projection,
# not every normalized Vite/Vitest field.
$ExpectedRawPluginNames = @(
    'vite:react-babel',
    'vite:react:refresh-wrapper',
    'vite:react:config-post',
    'vite:react-refresh-fbm',
    'vite:react-refresh',
    'vite:react-virtual-preamble',
    'vite-plugin-pwa',
    'vite-plugin-pwa:info',
    'vite-plugin-pwa:build',
    'vite-plugin-pwa:dev-sw',
    'vite-plugin-pwa:pwa-assets'
)
$ExpectedEffectivePluginNames = @(
    'vite:react-babel',
    'vite:react-refresh-fbm',
    'vite:react-refresh',
    'vite-plugin-pwa',
    'vite:react:refresh-wrapper',
    'vite:react-virtual-preamble',
    'vite-plugin-pwa:dev-sw',
    'vite:react:config-post',
    'vite-plugin-pwa:info',
    'vite-plugin-pwa:pwa-assets'
)
$ExpectedConfigProbeSha256 = 'e170cd4af980793060ed6c4eb59f864e4abcc6c61a273ccf906607af1f03bbcc'
$ConfigProbeSource = @'
import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const [root, configPath, outputPath, vitestNodeEntry, viteNodeEntry] = process.argv.slice(2);
const vite = await import(pathToFileURL(viteNodeEntry).href);
const vitestNode = await import(pathToFileURL(vitestNodeEntry).href);
const configEnv = { command: 'serve', mode: 'test', isSsrBuild: false, isPreview: false };
const loaded = await vite.loadConfigFromFile(configEnv, configPath, root, 'silent', undefined, 'runner');
if (!loaded || loaded.path.replaceAll('\\', '/').toLowerCase() !== configPath.replaceAll('\\', '/').toLowerCase()) {
  throw new Error('RAW_CONFIG_PATH_MISMATCH');
}
const flattenPlugins = (value) => (Array.isArray(value) ? value.flat(Infinity) : []).filter(Boolean);
const rawPlugins = flattenPlugins(loaded.config.plugins).map((plugin) => plugin.name);
const { viteConfig, vitestConfig } = await vitestNode.resolveConfig(
  { root, config: configPath, mode: 'test', run: true, watch: false, configLoader: 'runner' },
  { root, configLoader: 'runner', logLevel: 'silent' },
);
const relevant = new Set([
  'vite:react-babel', 'vite:react:refresh-wrapper', 'vite:react:config-post',
  'vite:react-refresh-fbm', 'vite:react-refresh', 'vite:react-virtual-preamble',
  'vite-plugin-pwa', 'vite-plugin-pwa:info', 'vite-plugin-pwa:build',
  'vite-plugin-pwa:dev-sw', 'vite-plugin-pwa:pwa-assets',
]);
const normalizeRoot = (value) => value.replaceAll('\\', '/').replace(root.replaceAll('\\', '/'), '<SNAPSHOT_ROOT>');
const projection = {
  schema: 1,
  configLoader: 'runner',
  raw: {
    base: loaded.config.base ?? null,
    define: loaded.config.define ?? null,
    resolveAlias: loaded.config.resolve?.alias ?? null,
    pluginNames: rawPlugins,
    test: {
      include: loaded.config.test?.include ?? null,
      environment: loaded.config.test?.environment ?? null,
      globals: loaded.config.test?.globals ?? null,
      setupFiles: loaded.config.test?.setupFiles ?? null,
      pool: loaded.config.test?.pool ?? null,
    },
  },
  effective: {
    root: normalizeRoot(viteConfig.root),
    base: viteConfig.base,
    define: vitestConfig.defines,
    relevantPluginNames: viteConfig.plugins.map((plugin) => plugin.name).filter((name) => relevant.has(name)),
    test: {
      include: vitestConfig.include,
      exclude: vitestConfig.exclude,
      environment: vitestConfig.environment,
      globals: vitestConfig.globals,
      setupFiles: vitestConfig.setupFiles.map(normalizeRoot),
      pool: vitestConfig.pool,
      deps: {
        optimizerSsrEnabled: vitestConfig.deps.optimizer.ssr.enabled,
        optimizerClientEnabled: vitestConfig.deps.optimizer.client.enabled,
        transformAssets: vitestConfig.deps.web.transformAssets,
        transformCss: vitestConfig.deps.web.transformCss,
        transformGlobPattern: vitestConfig.deps.web.transformGlobPattern,
      },
    },
  },
};
writeFileSync(outputPath, JSON.stringify(projection), { encoding: 'utf8', flag: 'wx' });
'@

function Get-CanonicalPath([string]$Path) { return [IO.Path]::GetFullPath($Path).TrimEnd('\') }

function Test-IsWithin([string]$Child, [string]$Parent) {
    $childPath = (Get-CanonicalPath $Child) + '\'
    $parentPath = (Get-CanonicalPath $Parent) + '\'
    return $childPath.StartsWith($parentPath, [StringComparison]::OrdinalIgnoreCase)
}

function Assert-DirectoryIdentity([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "DIRECTORY_IDENTITY_MISMATCH: $Path" }
    if ((Get-CanonicalPath $item.FullName) -ne (Get-CanonicalPath $Path)) { throw "DIRECTORY_CANONICAL_PATH_MISMATCH: $Path" }
}

function Assert-FileIdentity([hashtable]$Expected) {
    $item = Get-Item -LiteralPath $Expected.Path -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "FILE_IDENTITY_KIND_MISMATCH: $($Expected.Path)" }
    $hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($item.Length -ne $Expected.Length -or $hash -ne $Expected.Sha256) { throw "EXECUTABLE_OR_MODULE_IDENTITY_MISMATCH: $($Expected.Path)" }
}

function Get-DirectoryFingerprint([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return 'ABSENT' }
    Assert-DirectoryIdentity $Path
    $root = Get-CanonicalPath $Path
    $lines = [Collections.Generic.List[string]]::new()
    foreach ($directory in @(Get-ChildItem -LiteralPath $Path -Recurse -Directory -Force | Sort-Object FullName)) {
        if ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "FINGERPRINT_REPARSE_ENTRY_FOUND: $($directory.FullName)" }
        $lines.Add('D|' + $directory.FullName.Substring($root.Length + 1).Replace('\', '/'))
    }
    foreach ($file in @(Get-ChildItem -LiteralPath $Path -Recurse -File -Force | Sort-Object FullName)) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "FINGERPRINT_REPARSE_ENTRY_FOUND: $($file.FullName)" }
        $relative = $file.FullName.Substring($root.Length + 1).Replace('\', '/')
        $sha = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $lines.Add("F|$relative|$($file.Length)|$sha")
    }
    $payload = if ($lines.Count -eq 0) { "EMPTY`n" } else { (($lines -join "`n") + "`n") }
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($payload))).ToLowerInvariant()
}

function Invoke-ExactProcess([string]$Executable, [string[]]$Arguments, [string]$WorkingDirectory, [hashtable]$ExtraEnvironment = @{}) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Executable
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($argument in $Arguments) { [void]$psi.ArgumentList.Add($argument) }
    $psi.Environment.Clear()
    $psi.Environment['SystemRoot'] = $env:SystemRoot
    $psi.Environment['WINDIR'] = $env:WINDIR
    $psi.Environment['TEMP'] = $env:TEMP
    $psi.Environment['TMP'] = $env:TMP
    foreach ($entry in $ExtraEnvironment.GetEnumerator()) { $psi.Environment[$entry.Key] = [string]$entry.Value }
    $process = [Diagnostics.Process]::new(); $process.StartInfo = $psi
    if (-not $process.Start()) { throw "PROCESS_START_FAILED: $Executable" }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync(); $stderrTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    return [pscustomobject]@{ ExitCode = $process.ExitCode; Stdout = $stdoutTask.GetAwaiter().GetResult(); Stderr = $stderrTask.GetAwaiter().GetResult() }
}

function Resolve-NodeSpecifier([string]$Specifier) {
    $script = "const{createRequire}=require('module');const r=createRequire('D:/english-vocab-trainer/package.json');process.stdout.write(r.resolve(process.argv[1]));"
    $result = Invoke-ExactProcess $ExpectedNode.Path @('-e', $script, $Specifier) $Repository
    if ($result.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($result.Stdout)) { throw "NODE_SPECIFIER_RESOLUTION_FAILED: $Specifier" }
    return Get-CanonicalPath $result.Stdout.Trim()
}

function Assert-ImportEdge([string]$ParentPath, [string]$Needle) {
    $source = [IO.File]::ReadAllText($ParentPath, [Text.Encoding]::UTF8)
    if (-not $source.Contains($Needle)) { throw "RUNTIME_IMPORT_EDGE_MISSING: $ParentPath -> $Needle" }
}

function Resolve-GitReportedPath([string]$Path) {
    $trimmed = $Path.Trim()
    if ([IO.Path]::IsPathRooted($trimmed)) { return Get-CanonicalPath $trimmed }
    return Get-CanonicalPath (Join-Path $Repository $trimmed)
}

function Assert-GitTopology {
    Assert-DirectoryIdentity $Repository; Assert-DirectoryIdentity $ExpectedGitDirectory
    $top = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('rev-parse', '--show-toplevel')) $Repository
    $gitDirectory = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('rev-parse', '--absolute-git-dir')) $Repository
    $commonDirectory = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('rev-parse', '--git-common-dir')) $Repository
    if ($top.ExitCode -ne 0 -or (Resolve-GitReportedPath $top.Stdout) -ne (Get-CanonicalPath $Repository)) { throw 'GIT_WORKTREE_IDENTITY_MISMATCH' }
    if ($gitDirectory.ExitCode -ne 0 -or (Resolve-GitReportedPath $gitDirectory.Stdout) -ne (Get-CanonicalPath $ExpectedGitDirectory)) { throw 'GIT_DIRECTORY_IDENTITY_MISMATCH' }
    if ($commonDirectory.ExitCode -ne 0 -or (Resolve-GitReportedPath $commonDirectory.Stdout) -ne (Get-CanonicalPath $ExpectedGitDirectory)) { throw 'GIT_COMMON_DIRECTORY_IDENTITY_MISMATCH' }
}

function Assert-GitObject([string]$Object, [string]$ExpectedType) {
    $result = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('cat-file', '-t', $Object)) $Repository
    if ($result.ExitCode -ne 0 -or $result.Stdout.Trim() -ne $ExpectedType) { throw "GIT_OBJECT_MISMATCH: $Object" }
}

function Write-GitBlob([string]$Blob, [string]$Destination) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $ExpectedGit.Path; $psi.WorkingDirectory = $Repository; $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
    foreach ($argument in $GitConfigArguments + @('cat-file', 'blob', $Blob)) { [void]$psi.ArgumentList.Add($argument) }
    $psi.Environment.Clear(); $psi.Environment['SystemRoot'] = $env:SystemRoot; $psi.Environment['WINDIR'] = $env:WINDIR; $psi.Environment['TEMP'] = $env:TEMP; $psi.Environment['TMP'] = $env:TMP
    $process = [Diagnostics.Process]::new(); $process.StartInfo = $psi
    if (-not $process.Start()) { throw 'GIT_BLOB_START_FAILED' }
    $stream = [IO.File]::Open($Destination, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $process.StandardOutput.BaseStream.CopyTo($stream) } finally { $stream.Dispose() }
    $stderr = $process.StandardError.ReadToEnd(); $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "GIT_BLOB_FAILED: $stderr" }
}

function New-Snapshot([string]$Revision, [string]$Destination, [string]$ArchivePath) {
    New-Item -ItemType Directory -Path $Destination | Out-Null
    $archive = Invoke-ExactProcess $ExpectedGit.Path ($GitConfigArguments + @('archive', '--format=tar', "--output=$ArchivePath", $Revision)) $Repository
    if ($archive.ExitCode -ne 0) { throw "GIT_ARCHIVE_FAILED: $($archive.Stderr)" }
    $extract = Invoke-ExactProcess $ExpectedTar.Path @('-xf', $ArchivePath, '-C', $Destination) $Repository
    if ($extract.ExitCode -ne 0) { throw "TAR_EXTRACT_FAILED: $($extract.Stderr)" }
}

function Add-DependencyJunction([string]$SnapshotRoot) {
    Assert-DirectoryIdentity $LiveNodeModules
    $externalLinks = @(Get-ChildItem -LiteralPath $LiveNodeModules -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
    if ($externalLinks.Count -ne 0) { throw 'LIVE_NODE_MODULES_REPARSE_ENTRY_FOUND' }
    $junction = Join-Path $SnapshotRoot 'node_modules'
    [void](New-Item -ItemType Junction -Path $junction -Target $LiveNodeModules)
    $targets = @((Get-Item -LiteralPath $junction -Force).Target)
    if ($targets.Count -ne 1 -or (Get-CanonicalPath ([string]$targets[0])) -ne (Get-CanonicalPath $LiveNodeModules)) { throw 'NODE_MODULES_JUNCTION_IDENTITY_MISMATCH' }
    return $junction
}

function Assert-ArrayEqual([object[]]$Actual, [object[]]$Expected, [string]$Name) {
    if ($Actual.Count -ne $Expected.Count) { throw "CONFIG_PROJECTION_COUNT_MISMATCH: $Name" }
    for ($i = 0; $i -lt $Expected.Count; $i++) {
        if ([string]$Actual[$i] -cne [string]$Expected[$i]) { throw "CONFIG_PROJECTION_VALUE_MISMATCH: $Name[$i]" }
    }
}

function Invoke-ConfigProjection([string]$SnapshotRoot, [string]$ProbePath, [string]$OutputPath) {
    $probeBytes = [Text.UTF8Encoding]::new($false).GetBytes($ConfigProbeSource)
    [IO.File]::WriteAllBytes($ProbePath, $probeBytes)
    $probeHash = (Get-FileHash -LiteralPath $ProbePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($probeHash -ne $ExpectedConfigProbeSha256) { throw 'CONFIG_PROBE_IDENTITY_MISMATCH' }
    $result = Invoke-ExactProcess $ExpectedNode.Path @(
        $ProbePath, $SnapshotRoot, (Join-Path $SnapshotRoot $ConfigPath), $OutputPath,
        (Resolve-NodeSpecifier 'vitest/node'), (Resolve-NodeSpecifier 'vite')
    ) $SnapshotRoot @{ NODE_NO_WARNINGS = '1' }
    if ($result.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $OutputPath)) { throw "CONFIG_PROJECTION_EXECUTION_FAILED: $($result.Stderr)" }
    try { $projection = Get-Content -LiteralPath $OutputPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { throw 'CONFIG_PROJECTION_JSON_INVALID' }
    if ($projection.schema -ne 1 -or $projection.configLoader -cne 'runner') { throw 'CONFIG_PROJECTION_SCHEMA_MISMATCH' }
    if ($projection.raw.base -cne '/' -or $null -ne $projection.raw.resolveAlias) { throw 'RAW_CONFIG_BASE_OR_ALIAS_MISMATCH' }
    if ($projection.raw.define.__APP_VERSION__ -cne '"0.1.0-beta.3"' -or $projection.raw.define.__BUILD_ID__ -cne '"local"' -or $projection.raw.define.__PHONICS_ENABLED__ -cne 'true') { throw 'RAW_CONFIG_DEFINE_MISMATCH' }
    Assert-ArrayEqual @($projection.raw.pluginNames) $ExpectedRawPluginNames 'raw.pluginNames'
    Assert-ArrayEqual @($projection.raw.test.include) @('src/**/*.test.ts') 'raw.test.include'
    if ($projection.raw.test.environment -cne 'node' -or $null -ne $projection.raw.test.globals -or $null -ne $projection.raw.test.setupFiles -or $null -ne $projection.raw.test.pool) { throw 'RAW_TEST_CONFIG_MISMATCH' }
    if ($projection.effective.root -cne '<SNAPSHOT_ROOT>' -or $projection.effective.base -cne '/') { throw 'EFFECTIVE_ROOT_OR_BASE_MISMATCH' }
    if ($projection.effective.define.__APP_VERSION__ -cne '0.1.0-beta.3' -or $projection.effective.define.__BUILD_ID__ -cne 'local' -or $projection.effective.define.__PHONICS_ENABLED__ -ne $true) { throw 'EFFECTIVE_CONFIG_DEFINE_MISMATCH' }
    Assert-ArrayEqual @($projection.effective.relevantPluginNames) $ExpectedEffectivePluginNames 'effective.relevantPluginNames'
    Assert-ArrayEqual @($projection.effective.test.include) @('src/**/*.test.ts') 'effective.test.include'
    Assert-ArrayEqual @($projection.effective.test.exclude) @('**/node_modules/**', '**/.git/**') 'effective.test.exclude'
    if (@($projection.effective.test.setupFiles).Count -ne 0) { throw 'EFFECTIVE_TEST_SETUP_FILES_MISMATCH' }
    if (@($projection.effective.test.deps.transformGlobPattern).Count -ne 0) { throw 'EFFECTIVE_TEST_TRANSFORM_GLOB_MISMATCH' }
    if ($projection.effective.test.environment -cne 'node' -or $projection.effective.test.globals -ne $false -or $projection.effective.test.pool -cne 'forks') { throw 'EFFECTIVE_TEST_CORE_MISMATCH' }
    if ($projection.effective.test.deps.optimizerSsrEnabled -ne $false -or $projection.effective.test.deps.optimizerClientEnabled -ne $false -or $projection.effective.test.deps.transformAssets -ne $true -or $projection.effective.test.deps.transformCss -ne $true) { throw 'EFFECTIVE_TEST_DEPS_MISMATCH' }
    return $projection
}

function Get-VitestAssertion([pscustomobject]$Result, [string]$CaseName, [string]$SnapshotName) {
    if ([string]::IsNullOrWhiteSpace($Result.Stdout)) { throw "VITEST_REPORT_MISSING: $SnapshotName`:$CaseName" }
    try { $report = $Result.Stdout | ConvertFrom-Json } catch { throw "VITEST_REPORT_INVALID: $SnapshotName`:$CaseName" }
    $assertions = @(); foreach ($testResult in @($report.testResults)) { $assertions += @($testResult.assertionResults) }
    $allowed = @('passed', 'failed', 'skipped', 'todo', 'pending')
    foreach ($assertion in $assertions) { if ([string]::IsNullOrWhiteSpace([string]$assertion.title) -or [string]$assertion.status -notin $allowed) { throw "VITEST_ASSERTION_SCHEMA_OR_STATUS_UNKNOWN: $SnapshotName`:$CaseName" } }
    $matching = @($assertions | Where-Object { $_.title -ceq $CaseName })
    if ($matching.Count -ne 1 -or [string]$matching[0].status -notin @('passed', 'failed')) { throw "VITEST_TARGET_NOT_EXACTLY_EXECUTED: $SnapshotName`:$CaseName" }
    $executed = @($assertions | Where-Object { [string]$_.status -in @('passed', 'failed') })
    if ($executed.Count -ne 1 -or [string]$executed[0].title -cne $CaseName) { throw "VITEST_EXECUTION_SET_MISMATCH: $SnapshotName`:$CaseName" }
    $passedCount = @($executed | Where-Object { [string]$_.status -eq 'passed' }).Count
    $failedCount = @($executed | Where-Object { [string]$_.status -eq 'failed' }).Count
    if ([int]$report.numPassedTests -ne $passedCount -or [int]$report.numFailedTests -ne $failedCount) { throw "VITEST_REPORT_COUNTER_MISMATCH: $SnapshotName`:$CaseName" }
    if (($matching[0].status -eq 'passed' -and $Result.ExitCode -ne 0) -or ($matching[0].status -eq 'failed' -and $Result.ExitCode -eq 0)) { throw "VITEST_EXIT_STATUS_MISMATCH: $SnapshotName`:$CaseName" }
    return [pscustomobject]@{ Snapshot = $SnapshotName; Case = $CaseName; Status = [string]$matching[0].status; ExitCode = $Result.ExitCode; ExecutedAssertionTitles = @([string]$executed[0].title) }
}

$selfPath = Get-CanonicalPath $PSCommandPath
$selfHash = (Get-FileHash -LiteralPath $selfPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($selfHash -ne $ExpectedSourceSha256) { throw 'HARNESS_SOURCE_IDENTITY_MISMATCH' }
if ((Get-CanonicalPath (Get-Location).Path) -ne (Get-CanonicalPath $ExpectedLaunchCwd)) { throw 'LAUNCH_CWD_MISMATCH' }
Assert-FileIdentity $ExpectedPowerShell; Assert-FileIdentity $ExpectedGit; Assert-FileIdentity $ExpectedTar; Assert-FileIdentity $ExpectedNode
foreach ($runtimeFile in $ExpectedRuntimeFiles) { Assert-FileIdentity $runtimeFile }
if ((Resolve-NodeSpecifier 'vitest/node') -ne (Get-CanonicalPath 'D:\english-vocab-trainer\node_modules\vitest\dist\node.js')) { throw 'VITEST_NODE_RUNTIME_RESOLUTION_MISMATCH' }
if ((Resolve-NodeSpecifier '@vitest/runner/utils') -ne (Get-CanonicalPath 'D:\english-vocab-trainer\node_modules\@vitest\runner\dist\utils.js')) { throw 'VITEST_RUNNER_RUNTIME_RESOLUTION_MISMATCH' }
if ((Resolve-NodeSpecifier 'vite') -ne (Get-CanonicalPath 'D:\english-vocab-trainer\node_modules\vite\dist\node\index.js')) { throw 'VITE_RUNTIME_RESOLUTION_MISMATCH' }
if ((Resolve-NodeSpecifier '@vitejs/plugin-react') -ne (Get-CanonicalPath 'D:\english-vocab-trainer\node_modules\@vitejs\plugin-react\dist\index.js')) { throw 'REACT_PLUGIN_RUNTIME_RESOLUTION_MISMATCH' }
if ((Resolve-NodeSpecifier 'vite-plugin-pwa') -ne (Get-CanonicalPath 'D:\english-vocab-trainer\node_modules\vite-plugin-pwa\dist\index.cjs')) { throw 'PWA_PLUGIN_RUNTIME_RESOLUTION_MISMATCH' }
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\vitest.mjs' "import './dist/cli.js'"
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\cli.js' "from './chunks/cac.DdICfEr1.js'"
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\node.js' "from './chunks/cli-api.BK8pd4xc.js'"
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\node.js' "from './chunks/coverage.DM_a_rWm.js'"
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\@vitest\runner\dist\utils.js' "from './chunk-artifact.js'"
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vite\dist\node\index.js' 'from "./chunks/node.js"'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\cac.DdICfEr1.js' 'testNamePattern:'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\cac.DdICfEr1.js' 'configLoader:'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\cli-api.BK8pd4xc.js' 'configLoader: options.configLoader'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vitest\dist\chunks\cli-api.BK8pd4xc.js' 'testNamePattern,'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\@vitest\runner\dist\chunk-artifact.js' 'getTaskFullName(t).match(namePattern)'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\@vitest\runner\dist\chunk-artifact.js' '`${task.suite ? `${getTaskFullName(task.suite)} ` : ""}${task.name}`'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vite\dist\node\chunks\node.js' 'configLoader === "runner" ? runnerImportConfigFile'
Assert-ImportEdge 'D:\english-vocab-trainer\node_modules\vite\dist\node\chunks\node.js' 'const { module, dependencies } = await runnerImport(resolvedPath)'
if ($ConfigLoaderArgument -ne '--configLoader=runner') { throw 'CONFIG_LOADER_AUTHORITY_MISMATCH' }

$misroutedArtifacts = Join-Path $PSScriptRoot 'artifacts'
$misroutedMemory = Join-Path $PSScriptRoot 'memory'
$misroutedArtifactsBefore = Get-DirectoryFingerprint $misroutedArtifacts
$misroutedMemoryBefore = Get-DirectoryFingerprint $misroutedMemory
Assert-GitTopology; Assert-GitObject $BaseCommit 'commit'; Assert-GitObject $FixCommit 'commit'; Assert-GitObject $OracleBlob 'blob'; Assert-GitObject $ConfigBlob 'blob'

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('solo-a3-v2-' + [guid]::NewGuid().ToString('N'))
$junctions = [Collections.Generic.List[string]]::new()
try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    $snapshotPlans = if ($ExecutionMode -eq 'Diagnostic') {
        @(@{ Name = 'base'; Revision = $BaseCommit; Root = (Join-Path $tempRoot 'base'); Archive = (Join-Path $tempRoot 'base.tar'); Cases = @($RequiredCases[0]) })
    } else {
        @(
            @{ Name = 'base'; Revision = $BaseCommit; Root = (Join-Path $tempRoot 'base'); Archive = (Join-Path $tempRoot 'base.tar'); Cases = $RequiredCases },
            @{ Name = 'fix'; Revision = $FixCommit; Root = (Join-Path $tempRoot 'fix'); Archive = (Join-Path $tempRoot 'fix.tar'); Cases = $RequiredCases }
        )
    }
    foreach ($snapshot in $snapshotPlans) {
        New-Snapshot $snapshot.Revision $snapshot.Root $snapshot.Archive
        $oracle = Join-Path $snapshot.Root $OraclePath
        Remove-Item -LiteralPath $oracle -Force
        Write-GitBlob $OracleBlob $oracle
        $configFile = Join-Path $snapshot.Root $ConfigPath
        # git archive + Windows tar materializes this text file with CRLF in
        # this environment. Rebind the executable config to the exact Git blob.
        Remove-Item -LiteralPath $configFile -Force
        Write-GitBlob $ConfigBlob $configFile
        $configInfo = Get-Item -LiteralPath $configFile
        if ($configInfo.Length -ne $ExpectedConfigBytes -or (Get-FileHash -LiteralPath $configFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedConfigSha256) { throw "SNAPSHOT_CONFIG_IDENTITY_MISMATCH: $($snapshot.Name)" }
        $junctions.Add((Add-DependencyJunction $snapshot.Root))
    }
    $baseSnapshot = @($snapshotPlans)[0]
    $baseProjection = Invoke-ConfigProjection $baseSnapshot.Root (Join-Path $baseSnapshot.Root '.a3-config-probe-v2.mjs') (Join-Path $baseSnapshot.Root '.a3-config-projection-v2.json')
    $results = @()
    foreach ($snapshot in $snapshotPlans) {
        foreach ($caseName in $snapshot.Cases) {
            $pattern = [regex]::Escape($caseName) + '$'
            $result = Invoke-ExactProcess $ExpectedNode.Path @($VitestEntry, 'run', $OraclePath, '-t', $pattern, '--reporter=json', $ConfigLoaderArgument) $snapshot.Root @{ NODE_NO_WARNINGS = '1' }
            $results += Get-VitestAssertion $result $caseName $snapshot.Name
        }
    }
    if ((Get-DirectoryFingerprint $misroutedArtifacts) -ne $misroutedArtifactsBefore -or (Get-DirectoryFingerprint $misroutedMemory) -ne $misroutedMemoryBefore) { throw 'NESTED_GOVERNANCE_OUTPUT_MUTATION_DETECTED' }
    if ($ExecutionMode -eq 'Diagnostic') {
        if ($results.Count -ne 1 -or $results[0].Snapshot -ne 'base' -or $results[0].Case -ne $RequiredCases[0]) { throw 'DIAGNOSTIC_EXECUTION_SCOPE_MISMATCH' }
        [pscustomobject]@{
            HarnessSha256 = $selfHash
            ExecutionMode = $ExecutionMode
            Disposition = 'DIAGNOSTIC_ONLY_NO_QUALIFICATION_DISPOSITION'
            ConfigLoader = 'runner'
            ConfigProjection = $baseProjection
            Results = $results
        } | ConvertTo-Json -Depth 9
    } else {
        $baseResults = @($results | Where-Object Snapshot -eq 'base'); $fixResults = @($results | Where-Object Snapshot -eq 'fix')
        $qualified = (@($baseResults | Where-Object Status -ne 'failed').Count -eq 0 -and @($fixResults | Where-Object Status -ne 'passed').Count -eq 0)
        [pscustomobject]@{ HarnessSha256 = $selfHash; ExecutionMode = $ExecutionMode; Disposition = if ($qualified) { 'QUALIFIED' } else { 'NOT_QUALIFIED' }; ConfigLoader = 'runner'; ConfigProjection = $baseProjection; Results = $results } | ConvertTo-Json -Depth 9
        if (-not $qualified) { exit 3 }
    }
} finally {
    for ($index = $junctions.Count - 1; $index -ge 0; $index--) { if (Test-Path -LiteralPath $junctions[$index]) { Remove-Item -LiteralPath $junctions[$index] -Force } }
    if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
    if ((Get-DirectoryFingerprint $misroutedArtifacts) -ne $misroutedArtifactsBefore -or (Get-DirectoryFingerprint $misroutedMemory) -ne $misroutedMemoryBefore) { throw 'NESTED_GOVERNANCE_OUTPUT_MUTATION_DETECTED_DURING_CLEANUP' }
}
