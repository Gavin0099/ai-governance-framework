param(
    [string]$OutputPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "materialize-sidecar-inputs.ps1")

$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("c1-sidecar-materialization-self-test-" + [guid]::NewGuid().ToString("N"))
$source = Join-Path $testRoot "source"
$destination = Join-Path $testRoot "destination"

try {
    New-Item -ItemType Directory -Path (Join-Path $source "nested\deep") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $source "empty-directory") -Force | Out-Null
    [System.IO.File]::WriteAllBytes((Join-Path $source "plain.txt"), [byte[]](0, 1, 2, 10, 13, 255))
    [System.IO.File]::WriteAllText((Join-Path $source ".hidden-input"), "hidden`r`n", [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText((Join-Path $source "nested\deep\payload.json"), '{"value":"* literal"}' + "`n", [System.Text.UTF8Encoding]::new($false))

    $copyResult = Copy-ExactDirectoryChildren -Source $source -Destination $destination
    $sourceInventory = @(Get-ExactTreeInventory -Root $source)
    $destinationInventory = @(Get-ExactTreeInventory -Root $destination)

    if ($copyResult.file_count -ne 3) {
        throw "SELF_TEST_FILE_COUNT:$($copyResult.file_count)"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $destination ".hidden-input"))) {
        throw "SELF_TEST_HIDDEN_FILE_MISSING"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $destination "empty-directory") -PathType Container)) {
        throw "SELF_TEST_EMPTY_DIRECTORY_MISSING"
    }
    if ((ConvertTo-Json $sourceInventory -Depth 5 -Compress) -cne (ConvertTo-Json $destinationInventory -Depth 5 -Compress)) {
        throw "SELF_TEST_INVENTORY_MISMATCH"
    }

    $nonEmptyDestinationRejected = $false
    try {
        Copy-ExactDirectoryChildren -Source $source -Destination $destination | Out-Null
    }
    catch {
        if ($_.Exception.Message -like "SIDECAR_RESOLUTION_FAILED:MATERIALIZATION_DESTINATION_NOT_EMPTY:*") {
            $nonEmptyDestinationRejected = $true
        }
        else {
            throw
        }
    }
    if (-not $nonEmptyDestinationRejected) {
        throw "SELF_TEST_NON_EMPTY_DESTINATION_ACCEPTED"
    }

    $result = [ordered]@{
        schema = "c1-stryker-sidecar-materialization-self-test.v1"
        status = "PASS"
        file_count = $copyResult.file_count
        hidden_file_preserved = $true
        nested_file_preserved = $true
        empty_directory_preserved = $true
        inventory_equal = $true
        non_empty_destination_rejected = $true
    }
    $json = ConvertTo-Json $result -Depth 5
    if ($OutputPath) {
        [System.IO.File]::WriteAllText($OutputPath, $json + "`n", [System.Text.UTF8Encoding]::new($false))
    }
    $json
}
finally {
    if (Test-Path -LiteralPath $testRoot) {
        Remove-Item -LiteralPath $testRoot -Recurse -Force
    }
}
