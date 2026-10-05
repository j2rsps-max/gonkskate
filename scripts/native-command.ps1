function Invoke-GonkNative {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [scriptblock]$Command,

        [Parameter(Mandatory=$true)]
        [string]$LogPath,

        [string]$Description = "native command"
    )

    $parent = Split-Path -Parent $LogPath
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    # Windows PowerShell 5.1 can turn perfectly normal native stderr output into
    # NativeCommandError records.  That is especially common with Cargo progress
    # messages such as "Updating crates.io index".
    #
    # Native programs should be judged by their process exit code, not by whether
    # they wrote to stderr.
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    try {
        Remove-Item -LiteralPath $LogPath -Force -ErrorAction SilentlyContinue

        # Do not let pipeline output escape the function; otherwise callers that
        # assign the result would receive log lines as well as the integer exit code.
        & $Command 2>&1 | ForEach-Object {
            $line = $_.ToString()
            Add-Content -LiteralPath $LogPath -Value $line
            Write-Host $line
        }

        $exitCode = $LASTEXITCODE
        if ($null -eq $exitCode) {
            $exitCode = 0
        }
    }
    catch {
        Add-Content -LiteralPath $LogPath -Value ("PowerShell wrapper exception: " + $_.Exception.Message)
        Write-Host ("PowerShell wrapper exception: " + $_.Exception.Message)
        return 9001
    }
    finally {
        $ErrorActionPreference = $oldPreference
    }

    return [int]$exitCode
}
