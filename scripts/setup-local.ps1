[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
if ($env:OS -ne "Windows_NT") {
    throw "This helper prepares a local Windows checkout. Linux uses scripts/setup-cloud.sh."
}
$projectRoot = Split-Path -Parent $PSScriptRoot
$taskTemp = Join-Path ([IO.Path]::GetTempPath()) ("gonkskate-v066-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
$setupLog = Join-Path $taskTemp "setup-local.txt"
Start-Transcript -Path $setupLog | Out-Null

try {
    $archiveName = "GonkSkate-v0.6.6-Windows-Playable-Full-Package.zip"
    $downloadUrl = "https://raw.githubusercontent.com/j2rsps-max/gonkskate/downloads/$archiveName"
    $expectedHash = "6d3c49861ea42d5f9edcdeba2fd10091338e7509e7a73dea271610f5c5f2e9eb"
    $archivePath = Join-Path $taskTemp $archiveName
    # Preserve existing protocol choices while allowing TLS 1.2 in PowerShell 5.1.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Write-Host "Downloading the verified v0.6.6 Windows tools from GitHub..."
    Invoke-WebRequest -UseBasicParsing -Uri $downloadUrl -OutFile $archivePath -TimeoutSec 600
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
        throw "ZIP SHA256 differs from the verified release. Nothing has been installed."
    }
    $expanded = Join-Path $taskTemp "expanded"
    Expand-Archive -LiteralPath $archivePath -DestinationPath $expanded
    $package = Join-Path $expanded "GonkSkate-v0.6.6"
    foreach ($relative in @("build\thug-headless-windows", "build\skate3-input-windows", "bin\godot")) {
        $source = Join-Path $package $relative
        $destination = Join-Path $projectRoot $relative
        if (!(Test-Path -LiteralPath $source -PathType Container)) { throw "Package folder missing: $relative" }
        # Preserve existing local tools. Source and user files are never copied over.
        if (Test-Path -LiteralPath $destination) {
            Write-Host "Keeping existing tools at $destination"
        } else {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
            Copy-Item -LiteralPath $source -Destination $destination -Recurse
        }
    }
    Write-Host "Local project: $projectRoot"
    Write-Host "Open this folder as a LOCAL project in Codex desktop. Python 3 is required."
    Write-Host "First test: .\RUN_PLAYABLE.cmd --world worlds\courtyard.json"
    Write-Host "Read LOCAL_HANDOFF.md before continuing development."
} finally {
    Stop-Transcript | Out-Null
    Write-Host "Setup log and downloaded package: $taskTemp"
}
