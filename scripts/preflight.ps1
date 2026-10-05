param(
    [Parameter(Mandatory=$true)]
    [string]$LogDir
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Find-Cmd([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Run-Version([string]$Exe, [string[]]$Arguments) {
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $Exe @Arguments 2>&1
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            return "ERROR(exit $code): " + (($output | Select-Object -First 3) -join " ")
        }
        return (($output | Select-Object -First 3) -join " ")
    } catch {
        return "ERROR: $($_.Exception.Message)"
    } finally {
        $ErrorActionPreference = $oldPreference
    }
}

$info = [ordered]@{}
$info.timestamp = (Get-Date).ToString("o")
$info.windows = [System.Environment]::OSVersion.VersionString
$info.architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
$info.powershell = $PSVersionTable.PSVersion.ToString()

$checks = @(
    @{name="git"; exe="git"; arguments=@("--version"); required=$true},
    @{name="rustup"; exe="rustup"; arguments=@("--version"); required=$true},
    @{name="rustc"; exe="rustc"; arguments=@("--version"); required=$true},
    @{name="cargo"; exe="cargo"; arguments=@("--version"); required=$true},
    @{name="cmake"; exe="cmake"; arguments=@("--version"); required=$true},
    @{name="python"; exe="python"; arguments=@("--version"); required=$false},
    @{name="py"; exe="py"; arguments=@("--version"); required=$false},
    @{name="ninja"; exe="ninja"; arguments=@("--version"); required=$false}
)

$missingRequired = @()
$rows = @()

foreach ($c in $checks) {
    $path = Find-Cmd $c.exe
    if ($path) {
        $ver = Run-Version $c.exe $c.arguments
        $rows += [pscustomobject]@{
            Tool=$c.name; Required=$c.required; Found=$true; Path=$path; Version=$ver
        }
    } else {
        $rows += [pscustomobject]@{
            Tool=$c.name; Required=$c.required; Found=$false; Path=""; Version=""
        }
        if ($c.required) { $missingRequired += $c.name }
    }
}

$vswhereCandidates = @(
    "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe",
    "${env:ProgramFiles}\Microsoft Visual Studio\Installer\vswhere.exe"
)
$vswhere = $vswhereCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
$vsInstall = $null
if ($vswhere) {
    try {
        $vsInstall = (& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>$null | Select-Object -First 1)
    } catch {}
}

$info.vswhere = $vswhere
$info.visual_studio_cpp_install = $vsInstall

if (-not $vsInstall) {
    $missingRequired += "Visual Studio C++ Build Tools"
}

$rows | Format-Table -AutoSize | Out-String | Set-Content (Join-Path $LogDir "preflight-tools.txt")
$info.tools = $rows
$info.missing_required = $missingRequired
$info | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $LogDir "preflight.json")

Write-Host ""
Write-Host "=== Toolchain preflight ==="
$rows | Format-Table -AutoSize
if ($vsInstall) {
    Write-Host "Visual Studio C++ tools: FOUND"
    Write-Host "  $vsInstall"
} else {
    Write-Host "Visual Studio C++ tools: MISSING"
}

if ($missingRequired.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing required items:"
    $missingRequired | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    Write-Host "See INSTALL_REQUIREMENTS.md."
    exit 2
}

exit 0
