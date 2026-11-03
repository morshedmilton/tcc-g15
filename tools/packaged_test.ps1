# Verify the packaged build: window appears, watchdog exe starts, RAM is comparable to baseline.
$root = "C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default\tcc-g15"
$exe  = Join-Path $root "dist\tcc-g15\tcc-g15.exe"
$res  = Join-Path $root "docs\baseline\packaged.result.txt"

"run at " + (Get-Date -Format o) | Out-File -FilePath $res -Encoding utf8
if (-not (Test-Path $exe)) { Add-Content $res "exe missing"; exit 1 }

Start-Process -FilePath $exe | Out-Null

$deadline = (Get-Date).AddSeconds(60)
$app = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    $app = Get-Process -ErrorAction SilentlyContinue |
           Where-Object { $_.MainWindowTitle -eq 'Thermal Control Center for Dell G15' } |
           Select-Object -First 1
    if ($app) { break }
}
if (-not $app) { Add-Content $res "window: NOT FOUND"; exit 1 }
Add-Content $res ("window: ok pid=" + $app.Id)

Start-Sleep -Seconds 8
$wd = Get-CimInstance Win32_Process -Filter "Name='tcc-watchdog.exe'"
Add-Content $res ("watchdog exe: " + $(if ($wd) { "running pid " + ($wd | Select-Object -First 1).ProcessId } else { "NOT FOUND" }))

# RAM samples 30 s apart
$s1 = [math]::Round((Get-Process -Id $app.Id).WorkingSet64/1MB, 1)
Start-Sleep -Seconds 30
$s2 = [math]::Round((Get-Process -Id $app.Id).WorkingSet64/1MB, 1)
Add-Content $res ("ram_mb: $s1 -> $s2")
Add-Content $res ("threads: " + (Get-Process -Id $app.Id).Threads.Count)
Add-Content $res ("path: " + (Get-Process -Id $app.Id).Path)
