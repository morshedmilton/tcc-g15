# Hard-kill test: the watchdog must restore Balanced when the GUI dies without cleanup.
$root = "C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default\tcc-g15"
$py   = Join-Path $root ".venv\Scripts\python.exe"
$src  = Join-Path $root "src\tcc-g15.py"
$res  = Join-Path $root "docs\baseline\watchdog.result.txt"
$hb   = Join-Path $env:TEMP "tcc-g15.heartbeat"
$mark = "$hb.restored"

"run at " + (Get-Date -Format o) | Out-File -FilePath $res -Encoding utf8
Remove-Item $mark -ErrorAction SilentlyContinue
Remove-Item $hb -ErrorAction SilentlyContinue

$p = Start-Process -FilePath $py -ArgumentList $src -WorkingDirectory (Join-Path $root "src") -PassThru
$deadline = (Get-Date).AddSeconds(50)
$gui = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    $gui = Get-Process -ErrorAction SilentlyContinue |
           Where-Object { $_.MainWindowTitle -eq 'Thermal Control Center for Dell G15' } |
           Select-Object -First 1
    if ($gui) { break }
}
if (-not $gui) {
    Add-Content $res "gui: NOT FOUND"
    exit 1
}
Add-Content $res ("gui: pid " + $gui.Id)

Start-Sleep -Seconds 4
$wd = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
      Where-Object { $_.CommandLine -like '*tcc-watchdog.py*' }
Add-Content $res ("watchdog: " + $(if ($wd) { "running pid " + ($wd | Select-Object -First 1).ProcessId } else { "NOT FOUND" }))
Add-Content $res ("heartbeat exists: " + (Test-Path $hb))

# hard kill the whole tree: venv python.exe is a shim that re-execs the real interpreter
& taskkill /F /T /PID $gui.Id | Out-Null
Add-Content $res "gui killed (force, tree)"

$deadline = (Get-Date).AddSeconds(40)
while ((Get-Date) -lt $deadline -and -not (Test-Path $mark)) { Start-Sleep -Milliseconds 500 }
if (Test-Path $mark) {
    Add-Content $res ("restored: " + (Get-Content $mark -Raw))
} else {
    Add-Content $res "restored: NO MARKER (watchdog did not fire)"
}
Start-Sleep -Seconds 2
$wd2 = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
       Where-Object { $_.CommandLine -like '*tcc-watchdog.py*' }
Add-Content $res ("watchdog still running: " + [bool]$wd2)
