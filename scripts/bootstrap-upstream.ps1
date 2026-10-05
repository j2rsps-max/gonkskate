param(
    [Parameter(Mandatory=$true)]
    [string]$Root,
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "native-command.ps1")

$external = Join-Path $Root "external"
$thug = Join-Path $external "kisak-thug"
New-Item -ItemType Directory -Force -Path $external | Out-Null

if (-not (Test-Path $thug)) {
    Write-Host "Cloning kisak-thug reference source..."
    $code = Invoke-GonkNative `
        -Command { git clone --depth 1 https://github.com/SwagSoftware/kisak-thug.git $thug } `
        -LogPath (Join-Path $LogDir "git-clone.txt") `
        -Description "git clone"
    if ($code -ne 0) { throw "git clone failed with exit code $code" }
} else {
    Write-Host "kisak-thug already exists; refreshing it..."
    $code = Invoke-GonkNative `
        -Command { git -C $thug fetch --depth 1 origin master } `
        -LogPath (Join-Path $LogDir "git-fetch.txt") `
        -Description "git fetch"
    if ($code -ne 0) { throw "git fetch failed with exit code $code" }

    $code = Invoke-GonkNative `
        -Command { git -C $thug reset --hard origin/master } `
        -LogPath (Join-Path $LogDir "git-reset.txt") `
        -Description "git reset"
    if ($code -ne 0) { throw "git reset failed with exit code $code" }
}

$oldPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $commit = (& git -C $thug rev-parse HEAD 2>&1 | Select-Object -First 1).ToString().Trim()
    $gitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $oldPreference
}
if ($gitCode -ne 0 -or -not $commit) {
    throw "Could not determine kisak-thug commit."
}

$commit | Set-Content (Join-Path $LogDir "kisak-thug-commit.txt")
Write-Host "kisak-thug commit: $commit"
