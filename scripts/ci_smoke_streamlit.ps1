param(
    [Parameter(Mandatory = $true)]
    [string]$Label,

    [Parameter(Mandatory = $true)]
    [int]$Port,

    [Parameter(Mandatory = $true)]
    [string]$Executable,

    [string[]]$Arguments = @(),

    [int]$StartupTimeoutSeconds = 45
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-LogPreview {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return "<missing>"
    }

    $content = Get-Content -LiteralPath $Path -Raw
    if ([string]::IsNullOrWhiteSpace($content)) {
        return "<empty>"
    }
    return $content.Trim()
}

$safeLabel = ($Label -replace "[^A-Za-z0-9_-]", "-").ToLowerInvariant()
$tempRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [System.IO.Path]::GetTempPath() }
$runToken = [guid]::NewGuid().ToString("N")
$stdoutPath = Join-Path $tempRoot ("paperbanana-{0}-{1}-stdout.log" -f $safeLabel, $runToken)
$stderrPath = Join-Path $tempRoot ("paperbanana-{0}-{1}-stderr.log" -f $safeLabel, $runToken)

$commandText = @($Executable) + $Arguments
Write-Host ("[smoke:{0}] 启动命令: {1}" -f $Label, ($commandText -join " "))
Write-Host ("[smoke:{0}] 目标端口: {1}" -f $Label, $Port)

$previousHeadless = $env:STREAMLIT_SERVER_HEADLESS
$previousPort = $env:STREAMLIT_SERVER_PORT
$previousBrowser = $env:BROWSER
$previousUsageStats = $env:STREAMLIT_BROWSER_GATHER_USAGE_STATS
$previousPythonUnbuffered = $env:PYTHONUNBUFFERED

$env:STREAMLIT_SERVER_HEADLESS = "true"
$env:STREAMLIT_SERVER_PORT = [string]$Port
$env:BROWSER = "none"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
$env:PYTHONUNBUFFERED = "1"

$process = $null

try {
    $startProcessParams = @{
        FilePath               = $Executable
        ArgumentList           = $Arguments
        RedirectStandardOutput = $stdoutPath
        RedirectStandardError  = $stderrPath
        PassThru               = $true
        WindowStyle            = "Hidden"
    }
    $process = Start-Process @startProcessParams

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $started = $false

    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            $stdoutPreview = Get-LogPreview -Path $stdoutPath
            $stderrPreview = Get-LogPreview -Path $stderrPath
            throw (
                "[smoke:{0}] 进程提前退出，exit={1}`nstdout:`n{2}`n`nstderr:`n{3}" -f
                $Label,
                $process.ExitCode,
                $stdoutPreview,
                $stderrPreview
            )
        }

        try {
            $response = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/" -f $Port) -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                $started = $true
                break
            }
        }
        catch {
        }

        Start-Sleep -Seconds 1
        $process.Refresh()
    }

    if (-not $started) {
        $stdoutPreview = Get-LogPreview -Path $stdoutPath
        $stderrPreview = Get-LogPreview -Path $stderrPath
        throw (
            "[smoke:{0}] 在 {1} 秒内未探活成功`nstdout:`n{2}`n`nstderr:`n{3}" -f
            $Label,
            $StartupTimeoutSeconds,
            $stdoutPreview,
            $stderrPreview
        )
    }

    Write-Host ("[smoke:{0}] 探活成功" -f $Label)
}
finally {
    if ($null -ne $process) {
        $process.Refresh()
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
            try {
                Wait-Process -Id $process.Id -Timeout 10
            }
            catch {
            }
        }
    }

    $env:STREAMLIT_SERVER_HEADLESS = $previousHeadless
    $env:STREAMLIT_SERVER_PORT = $previousPort
    $env:BROWSER = $previousBrowser
    $env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = $previousUsageStats
    $env:PYTHONUNBUFFERED = $previousPythonUnbuffered
}
