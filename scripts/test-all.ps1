$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogDir = Join-Path $Root "logs\$stamp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

. (Join-Path $PSScriptRoot "native-command.ps1")

$masterLog = Join-Path $LogDir "master.log"
Start-Transcript -Path $masterLog -Force | Out-Null

$failed = $false
$failureReason = ""

try {
    Write-Host ""
    Write-Host "============================================"
    Write-Host " GonkSkate v0.6.0-dev Integration Readiness Test"
    Write-Host "============================================"
    Write-Host "Root: $Root"
    Write-Host "Logs: $LogDir"

    Write-Host ""
    Write-Host "[0/7] Harness stderr/exit-code self-test"
    $harnessLog = Join-Path $LogDir "harness-selftest.txt"
    $code = Invoke-GonkNative `
        -Command { cmd.exe /d /c "echo HARNESS_STDOUT_OK & echo HARNESS_STDERR_OK 1>&2 & exit /b 0" } `
        -LogPath $harnessLog `
        -Description "stderr self-test"
    if ($code -ne 0) {
        throw "Harness self-test failed with exit code $code"
    }
    $harnessText = Get-Content $harnessLog -Raw
    if (-not $harnessText.Contains("HARNESS_STDOUT_OK") -or -not $harnessText.Contains("HARNESS_STDERR_OK")) {
        throw "Harness self-test did not capture both stdout and stderr."
    }
    Write-Host "Harness stderr/exit-code behavior: PASS"

    Write-Host ""
    Write-Host "[1/7] Toolchain preflight"
    & (Join-Path $PSScriptRoot "preflight.ps1") -LogDir $LogDir
    if ($LASTEXITCODE -ne 0) {
        throw "Prerequisite check failed. Install missing items from INSTALL_REQUIREMENTS.md, then rerun."
    }

    Write-Host ""
    Write-Host "[2/7] Rust workspace test"
    Push-Location $Root
    try {
        $code = Invoke-GonkNative `
            -Command { cargo test --workspace } `
            -LogPath (Join-Path $LogDir "cargo-test.txt") `
            -Description "cargo test --workspace"
        if ($code -ne 0) { throw "cargo test failed with exit code $code" }
    } finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "[3/7] Native C/C++ ABI smoke build"
    $nativeBuild = Join-Path $Root "build\native-smoke"
    if (Test-Path $nativeBuild) { Remove-Item -Recurse -Force $nativeBuild }

    $code = Invoke-GonkNative `
        -Command { cmake -S (Join-Path $Root "native\smoke") -B $nativeBuild -A x64 } `
        -LogPath (Join-Path $LogDir "cmake-configure.txt") `
        -Description "cmake configure"
    if ($code -ne 0) { throw "CMake configure failed with exit code $code" }

    $code = Invoke-GonkNative `
        -Command { cmake --build $nativeBuild --config Release } `
        -LogPath (Join-Path $LogDir "cmake-build.txt") `
        -Description "cmake build"
    if ($code -ne 0) { throw "Native ABI smoke build failed with exit code $code" }

    $smoke = Get-ChildItem $nativeBuild -Recurse -Filter "gonkskate_abi_smoke.exe" |
        Select-Object -First 1
    if (-not $smoke) { throw "Could not find gonkskate_abi_smoke.exe" }

    $smokePath = $smoke.FullName
    $code = Invoke-GonkNative `
        -Command { & $smokePath } `
        -LogPath (Join-Path $LogDir "native-smoke-run.txt") `
        -Description "native ABI smoke executable"
    if ($code -ne 0) { throw "Native ABI smoke executable failed with exit code $code" }

    $code = Invoke-GonkNative `
        -Command { ctest --test-dir $nativeBuild -C Release --output-on-failure } `
        -LogPath (Join-Path $LogDir "native-parameter-tests.txt") `
        -Description "native parameter tests"
    if ($code -ne 0) { throw "Native parameter tests failed with exit code $code" }

    Write-Host ""
    Write-Host "[4/7] Fetch THUG reference source"
    & (Join-Path $PSScriptRoot "bootstrap-upstream.ps1") -Root $Root -LogDir $LogDir

    Write-Host ""
    Write-Host "[5/7] Validate THUG physics source layout"
    & (Join-Path $PSScriptRoot "validate-thug-source.ps1") -Root $Root -LogDir $LogDir

    Write-Host ""
    Write-Host "[6/7] Compare captured THUG physics defaults"
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $code = Invoke-GonkNative `
            -Command { & python (Join-Path $Root "tools\compare_thug_params.py") $Root $LogDir } `
            -LogPath (Join-Path $LogDir "thug-param-compare.txt") `
            -Description "THUG parameter comparison"
        if ($code -ne 0) { throw "Python parameter comparison failed with exit code $code" }
    } else {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if ($py) {
            $code = Invoke-GonkNative `
                -Command { & py -3 (Join-Path $Root "tools\compare_thug_params.py") $Root $LogDir } `
                -LogPath (Join-Path $LogDir "thug-param-compare.txt") `
                -Description "THUG parameter comparison"
            if ($code -ne 0) { throw "Python parameter comparison failed with exit code $code" }
        } else {
            "Python unavailable; parameter comparison skipped." |
                Set-Content (Join-Path $LogDir "thug-param-compare.txt")
        }
    }

    Write-Host ""
    Write-Host "[7/7] Result bundle"
    "PASS" | Set-Content (Join-Path $LogDir "OVERALL_RESULT.txt")
}
catch {
    $failed = $true
    $failureReason = $_.Exception.Message
    Write-Host ""
    Write-Host "TEST FAILED: $failureReason"
    "FAIL`n$failureReason" | Set-Content (Join-Path $LogDir "OVERALL_RESULT.txt")
}
finally {
    Stop-Transcript | Out-Null

    Copy-Item (Join-Path $Root "VERSION") $LogDir -ErrorAction SilentlyContinue
    Copy-Item (Join-Path $Root "native\thug_adapter\config\thug_core_physics_defaults.json") $LogDir -ErrorAction SilentlyContinue

    $resultZip = Join-Path $Root ("logs\GonkSkate-v0.6.0-dev-results-" + $stamp + ".zip")
    Compress-Archive -Path (Join-Path $LogDir "*") -DestinationPath $resultZip -Force

    Write-Host ""
    Write-Host "============================================"
    if ($failed) {
        Write-Host " TEST COMPLETE - FAILURE CAPTURED"
        Write-Host " Reason: $failureReason"
    } else {
        Write-Host " TEST COMPLETE - PASS"
    }
    Write-Host "============================================"
    Write-Host ""
    Write-Host "Send this file back to ChatGPT:"
    Write-Host "  $resultZip"
    Write-Host ""
}

if ($failed) { exit 1 } else { exit 0 }
