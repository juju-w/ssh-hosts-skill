param(
    [string]$HostAlias = "",
    [string]$ConfigPath = (Join-Path $HOME ".ssh\config"),
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONUTF8 = "1"

Write-Output "system=Windows"

$sshCommand = Get-Command ssh.exe -ErrorAction SilentlyContinue
if (-not $sshCommand) {
    Write-Error "OpenSSH Client is missing. Enable the Windows OpenSSH Client optional feature, then reopen the terminal."
    exit 2
}
Write-Output ("openssh=available (" + $sshCommand.Source + ")")

$pythonCommand = $null
$pythonPrefix = @()
if ($PythonPath) {
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        Write-Error ("The requested Python executable does not exist: " + $PythonPath)
        exit 2
    }
    $pythonCommand = Get-Item -LiteralPath $PythonPath
}
else {
    foreach ($candidate in @("python.exe", "python3.exe", "py.exe")) {
        $resolved = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($resolved) {
            $pythonCommand = $resolved
            if ($candidate -eq "py.exe") {
                $pythonPrefix = @("-3")
            }
            break
        }
    }
}

if (-not $pythonCommand) {
    Write-Output "python=missing"
    if (Test-Path -LiteralPath $ConfigPath) {
        Write-Output ("ssh_config=found (" + $ConfigPath + ")")
    }
    else {
        Write-Output ("ssh_config=missing (" + $ConfigPath + ")")
    }
    Write-Output "next=Install Python 3 for the current user, reopen PowerShell, then run this script again."
    Write-Output "note=Ordinary ssh.exe connections still work without Python; only the Skill helper scripts require it."
    exit 1
}

$pythonExecutable = $pythonCommand.Source
if (-not $pythonExecutable) {
    $pythonExecutable = $pythonCommand.FullName
}
Write-Output ("python=available (" + $pythonExecutable + ")")
$setupScript = Join-Path $PSScriptRoot "setup_ssh_hosts.py"
$arguments = @() + $pythonPrefix + @($setupScript, "--config", $ConfigPath)
if ($HostAlias) {
    $arguments += @("--host", $HostAlias)
}
& $pythonExecutable @arguments
exit $LASTEXITCODE
