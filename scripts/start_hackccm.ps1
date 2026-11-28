# hack.CCM laptop hub — starts the console and the Studio watcher, restarts them if they stop.
#
# Run once by hand:   powershell -ExecutionPolicy Bypass -File scripts\start_hackccm.ps1
# Autostart:          Task Scheduler → Create Task → Trigger "At log on" → Action:
#                       Program:   powershell.exe
#                       Arguments: -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\path\to\repo\scripts\start_hackccm.ps1"
#                     Settings: "If the task fails, restart every 1 minute".
# Logs: logs\console.log, logs\studio-watch.log (and *.err.log) — overwritten on each (re)start
# Uses $env:HACKCCM_PYTHON if set (e.g. a venv's python.exe), else "python".
# See docs/console/REMOTE_ACCESS.md.

$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo
$Python = if ($env:HACKCCM_PYTHON) { $env:HACKCCM_PYTHON } else { "python" }
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"
New-Item -ItemType Directory -Force -Path (Join-Path $Repo "logs") | Out-Null

function Start-HackProcess([string]$Name, [string]$Arguments) {
    $log = Join-Path $Repo "logs\$Name.log"
    $err = Join-Path $Repo "logs\$Name.err.log"
    return Start-Process -FilePath $Python -ArgumentList $Arguments -WorkingDirectory $Repo `
        -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden -PassThru
}

$procs = @{
    "console"      = "dashboard_app.py --no-reload";
    "studio-watch" = "studio.py watch";
}
$running = @{}
foreach ($name in $procs.Keys) { $running[$name] = Start-HackProcess $name $procs[$name] }

while ($true) {
    Start-Sleep -Seconds 30
    foreach ($name in $procs.Keys) {
        if ($running[$name].HasExited) {
            Start-Sleep -Seconds 5
            $running[$name] = Start-HackProcess $name $procs[$name]
        }
    }
}
