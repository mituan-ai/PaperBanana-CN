param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ""
    Write-Host ("=" * 20 + " " + $Title + " " + "=" * 20)
}

function Format-Duration {
    param(
        [Parameter(Mandatory = $true)]
        [TimeSpan]$Duration
    )

    return ("{0:N2}s" -f $Duration.TotalSeconds)
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Section $Label
    $startedAt = Get-Date
    & $Command
    $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
    $elapsed = (Get-Date) - $startedAt
    Write-Host ("[diag] {0} 结束，exit={1}，耗时={2}" -f $Label, $exitCode, (Format-Duration -Duration $elapsed))
    return $exitCode
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$testFiles = Get-ChildItem -Path "tests" -Filter "test_*.py" -File | Sort-Object Name
$testModules = @(
    foreach ($file in $testFiles) {
        "tests.{0}" -f [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
    }
)

Write-Section "CI 单测诊断概览"
Write-Host ("[diag] 工作目录: {0}" -f $repoRoot)
Write-Host ("[diag] 测试文件数: {0}" -f $testFiles.Count)
Write-Host ("[diag] 测试模块: {0}" -f ($testModules -join ", "))

$envSnapshot = [ordered]@{
    "CI" = $env:CI
    "GITHUB_ACTIONS" = $env:GITHUB_ACTIONS
    "GITHUB_WORKSPACE" = $env:GITHUB_WORKSPACE
    "RUNNER_TEMP" = $env:RUNNER_TEMP
    "PAPERBANANA_LOG_LEVEL" = $env:PAPERBANANA_LOG_LEVEL
    "PAPERBANANA_LOG_FILE" = $env:PAPERBANANA_LOG_FILE
    "PAPERBANANA_LOG_TO_FILE" = $env:PAPERBANANA_LOG_TO_FILE
}
foreach ($entry in $envSnapshot.GetEnumerator()) {
    $value = if ([string]::IsNullOrWhiteSpace($entry.Value)) { "<empty>" } else { $entry.Value }
    Write-Host ("[diag] env {0}={1}" -f $entry.Key, $value)
}

$versionExit = Invoke-LoggedCommand -Label "版本信息" -Command {
    uv --version
    uv run python -c "import os, platform, sys; print('[diag] python=' + sys.version.replace('\n', ' ')); print('[diag] executable=' + sys.executable); print('[diag] platform=' + platform.platform()); print('[diag] cwd=' + os.getcwd())"
}
if ($versionExit -ne 0) {
    exit $versionExit
}

$discoverExit = Invoke-LoggedCommand -Label "整套单测（verbose）" -Command {
    uv run python -X faulthandler -m unittest discover -s tests -p "test_*.py" -v
}
if ($discoverExit -eq 0) {
    Write-Section "单测结论"
    Write-Host "[diag] 整套 verbose 单测通过。"
    exit 0
}

Write-Section "失败后按文件重跑"
Write-Warning "整套 discover 失败，开始按测试文件逐个重跑以缩小范围。"

$failedModules = New-Object System.Collections.Generic.List[string]
$passedModules = New-Object System.Collections.Generic.List[string]

foreach ($module in $testModules) {
    $moduleExit = Invoke-LoggedCommand -Label ("逐文件重跑: {0}" -f $module) -Command {
        uv run python -X faulthandler -m unittest -v $module
    }
    if ($moduleExit -eq 0) {
        $passedModules.Add($module) | Out-Null
    }
    else {
        $failedModules.Add($module) | Out-Null
    }
}

Write-Section "逐文件重跑总结"
Write-Host ("[diag] 逐文件通过模块数: {0}" -f $passedModules.Count)
Write-Host ("[diag] 逐文件失败模块数: {0}" -f $failedModules.Count)

if ($failedModules.Count -gt 0) {
    Write-Host ("[diag] 失败模块: {0}" -f ($failedModules -join ", "))
    exit 1
}

Write-Warning "整套 discover 失败，但按文件逐个重跑全部通过。"
Write-Warning "这通常意味着测试顺序依赖、共享全局状态、后台线程/日志竞态，或磁盘清理时序问题。"
exit 1
