param(
    [Parameter(Mandatory=$true)]
    [string]$Root,
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Stop"
$repo = Join-Path $Root "external\kisak-thug"

$required = @(
    "Code\Sk\Components\SkaterCorePhysicsComponent.cpp",
    "Code\Sk\Components\SkaterCorePhysicsComponent.h",
    "Code\Sk\Components\SkaterStateComponent.cpp",
    "Code\Sk\Components\SkaterPhysicsControlComponent.cpp",
    "Code\Sk\Components\SkaterRotateComponent.cpp",
    "Code\Sk\Engine\feeler.cpp",
    "Code\Sk\Engine\feeler.h",
    "Code\Sk\Objects\skater.cpp",
    "Scripts\game\skater\physics.q"
)

$missing = @()
foreach ($rel in $required) {
    $full = Join-Path $repo $rel
    if (-not (Test-Path $full)) { $missing += $rel }
}

$core = Get-Content (Join-Path $repo "Code\Sk\Components\SkaterCorePhysicsComponent.cpp") -Raw
$needles = @(
    "CSkaterCorePhysicsComponent::Update",
    "do_on_ground_physics",
    "do_in_air_physics",
    "do_wallride_physics",
    "do_wallplant_physics",
    "do_lip_physics",
    "do_rail_physics",
    "maybe_stick_to_rail",
    "got_rail"
)

$signatureResults = @()
foreach ($n in $needles) {
    $found = $core.Contains($n)
    $signatureResults += [pscustomobject]@{ Symbol=$n; Found=$found }
    if (-not $found) { $missing += "symbol:$n" }
}

$signatureResults | Format-Table -AutoSize | Out-String |
    Set-Content (Join-Path $LogDir "thug-source-symbols.txt")

if ($missing.Count -gt 0) {
    "Missing:" | Set-Content (Join-Path $LogDir "thug-source-errors.txt")
    $missing | Add-Content (Join-Path $LogDir "thug-source-errors.txt")
    throw "THUG source validation failed. See thug-source-errors.txt"
}

"PASS" | Set-Content (Join-Path $LogDir "thug-source-validation.txt")
Write-Host "THUG source layout/signature validation: PASS"
