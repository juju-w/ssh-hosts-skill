$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$resultPath = Join-Path $root "windows-smoke-result.txt"
$exitPath = Join-Path $root "windows-smoke-exit.txt"
$smokeScript = Join-Path $PSScriptRoot "windows_python_credential_smoke.py"
$python = Join-Path $env:LOCALAPPDATA "Programs\QMT-MCP\runtime\python\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command python.exe, python3.exe, py.exe -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $pythonCommand) {
        [IO.File]::WriteAllText($resultPath, "python=missing`r`n")
        [IO.File]::WriteAllText($exitPath, "2")
        exit 2
    }
    $python = $pythonCommand.Source
}

try {
    $output = & $python $smokeScript 2>&1
    $code = $LASTEXITCODE
    $output | Out-File -LiteralPath $resultPath -Encoding utf8
}
catch {
    $_ | Out-File -LiteralPath $resultPath -Encoding utf8
    $code = 1
}

[IO.File]::WriteAllText($exitPath, [string]$code)
exit $code
