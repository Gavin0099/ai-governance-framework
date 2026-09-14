$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path
$hookPath = Join-Path $repoRoot ".git/hooks/pre-push"
$fragmentPath = Join-Path $repoRoot "scripts/hooks/pre-push.memory-quality.fragment.sh"
if (-not (Test-Path $hookPath)) {
    Write-Error "pre-push hook not found: $hookPath"
    exit 1
}
if (-not (Test-Path $fragmentPath)) {
    Write-Error "memory quality hook fragment not found: $fragmentPath"
    exit 1
}

$content = Get-Content -Raw $hookPath
$beginMarker = "# BEGIN LENOVO_ISP_MEMORY_QUALITY_GATE"
$endMarker = "# END LENOVO_ISP_MEMORY_QUALITY_GATE"

if ($content.Contains($beginMarker)) {
    Write-Host "[wire-pre-push] memory quality gate already wired"
    exit 0
}

$block = Get-Content -Raw $fragmentPath
$anchor = "# Fail-closed structured memory freshness gate."
if ($content.Contains($anchor)) {
    $updated = $content.Replace($anchor, "$block$anchor")
}
else {
    $exitAnchor = "exit 0"
    $exitIndex = $content.LastIndexOf($exitAnchor, [System.StringComparison]::Ordinal)
    if ($exitIndex -lt 0) {
        Write-Error "unable to find a stable insertion point in pre-push hook"
        exit 1
    }

    $insertion = $block.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine
    $updated = $content.Insert($exitIndex, $insertion)
}

Set-Content -Path $hookPath -Value $updated -NoNewline
Write-Host "[wire-pre-push] wired memory quality gate into .git/hooks/pre-push"
