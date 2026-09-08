Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ExactTreeInventory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
    $items = Get-ChildItem -LiteralPath $resolvedRoot -Force -File -Recurse |
        Sort-Object { $_.FullName.Substring($resolvedRoot.Length).TrimStart('\', '/').Replace('\', '/') }

    $inventory = foreach ($item in $items) {
        $relative = $item.FullName.Substring($resolvedRoot.Length).TrimStart('\', '/').Replace('\', '/')
        [ordered]@{
            path = $relative
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $item.FullName).Hash.ToLowerInvariant()
            bytes = [int64]$item.Length
        }
    }
    return @($inventory)
}
function Copy-ExactDirectoryChildren {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,

        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    $resolvedSource = (Resolve-Path -LiteralPath $Source).Path
    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path $Destination | Out-Null
    }
    $resolvedDestination = (Resolve-Path -LiteralPath $Destination).Path

    if ((Get-ChildItem -LiteralPath $resolvedDestination -Force | Measure-Object).Count -ne 0) {
        throw "SIDECAR_RESOLUTION_FAILED:MATERIALIZATION_DESTINATION_NOT_EMPTY:$resolvedDestination"
    }

    $sourceInventory = @(Get-ExactTreeInventory -Root $resolvedSource)
    if ($sourceInventory.Count -eq 0) {
        throw "SIDECAR_RESOLUTION_FAILED:MATERIALIZATION_SOURCE_EMPTY:$resolvedSource"
    }

    foreach ($child in @(Get-ChildItem -LiteralPath $resolvedSource -Force)) {
        Copy-Item -LiteralPath $child.FullName -Destination $resolvedDestination -Recurse -Force
    }

    $destinationInventory = @(Get-ExactTreeInventory -Root $resolvedDestination)
    $sourceJson = ConvertTo-Json -InputObject $sourceInventory -Depth 5 -Compress
    $destinationJson = ConvertTo-Json -InputObject $destinationInventory -Depth 5 -Compress
    if ($sourceJson -cne $destinationJson) {
        throw "SIDECAR_RESOLUTION_FAILED:MATERIALIZATION_INVENTORY_MISMATCH"
    }

    [ordered]@{
        schema = "c1-stryker-sidecar-materialization.v1"
        source = $resolvedSource
        destination = $resolvedDestination
        file_count = $sourceInventory.Count
        inventory = $sourceInventory
    }
}
