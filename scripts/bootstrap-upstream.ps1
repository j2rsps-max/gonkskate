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
    # A reference checkout may contain adapter work. Never reset it during tests.
    Write-Host "Using existing kisak-thug checkout without changing its HEAD or files."

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
