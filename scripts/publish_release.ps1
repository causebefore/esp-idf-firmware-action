[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Repository,

    [Parameter(Mandatory = $true)]
    [string]$Target,

    [Parameter(Mandatory = $true)]
    [string]$Tag,

    [Parameter(Mandatory = $true)]
    [string]$Title,

    [Parameter(Mandatory = $true)]
    [string]$FirmwarePath,

    [Parameter(Mandatory = $true)]
    [string]$ManifestPath
)

$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN)) {
    throw "The token input is empty."
}
foreach ($path in @($FirmwarePath, $ManifestPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Release asset does not exist: $path"
    }
}

$releaseLookup = & gh api "repos/$Repository/releases/tags/$Tag" --jq .tag_name 2>&1
$lookupExitCode = $LASTEXITCODE
if ($lookupExitCode -eq 0) {
    $downloadDirectory = Join-Path $env:RUNNER_TEMP ("existing-release-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $downloadDirectory | Out-Null
    try {
        foreach ($assetPath in @($FirmwarePath, $ManifestPath)) {
            $assetName = Split-Path -Leaf $assetPath
            & gh release download $Tag --repo $Repository --pattern $assetName --dir $downloadDirectory
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to download existing release asset: $assetName"
            }
            $existingPath = Join-Path $downloadDirectory $assetName
            $expectedHash = (Get-FileHash -LiteralPath $assetPath -Algorithm SHA256).Hash
            $existingHash = (Get-FileHash -LiteralPath $existingPath -Algorithm SHA256).Hash
            if ($expectedHash -ne $existingHash) {
                throw "Release $Tag already exists with different asset content: $assetName"
            }
        }
        Write-Host "Release $Tag already contains the same immutable assets."
        exit 0
    }
    finally {
        if (Test-Path -LiteralPath $downloadDirectory) {
            Remove-Item -LiteralPath $downloadDirectory -Recurse -Force
        }
    }
}

if (("$releaseLookup") -notmatch "HTTP 404") {
    throw "Unable to query release $Tag in ${Repository}: $releaseLookup"
}

$notes = "Automated ESP-IDF OTA release. The manifest and firmware asset are published together."
& gh release create $Tag $FirmwarePath $ManifestPath `
    --repo $Repository `
    --target $Target `
    --title $Title `
    --notes $notes
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create GitHub Release $Tag."
}
