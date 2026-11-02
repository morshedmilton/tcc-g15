# Launch the dev build elevated, wait for the Qt window, report, then close it.
$root = "C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default\tcc-g15"
$py   = Join-Path $root ".venv\Scripts\python.exe"
$src  = Join-Path $root "src\tcc-g15.py"
$res  = Join-Path $root "docs\baseline\devexe.result.txt"
$out  = Join-Path $root "docs\baseline\devexe.log"
$err  = Join-Path $root "docs\baseline\devexe.err"

"run at " + (Get-Date -Format o) | Out-File -FilePath $res -Encoding utf8

$p = Start-Process -FilePath $py -ArgumentList $src -WorkingDirectory (Join-Path $root "src") `
     -PassThru -RedirectStandardOutput $out -RedirectStandardError $err

$deadline = (Get-Date).AddSeconds(50)
$hit = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    $alive = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
    if (-not $alive) { break }
    $qt = Get-Process -ErrorAction SilentlyContinue |
          Where-Object { $_.MainWindowTitle -eq 'Thermal Control Center for Dell G15' } |
          Select-Object -First 1
    if ($qt) { $hit = $qt; break }
}

Add-Content -Path $res -Value ("process_alive: " + ($null -ne (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)))
if ($hit) {
    Add-Content -Path $res -Value ("qt_window: ok pid=" + $hit.Id + " ram_mb=" + [math]::Round($hit.WorkingSet64/1MB,0) + " threads=" + $hit.Threads.Count)
    Add-Content -Path $res -Value ("title: " + $hit.MainWindowTitle)
    Stop-Process -Id $hit.Id -Force -ErrorAction SilentlyContinue
} else {
    Add-Content -Path $res -Value "qt_window: NOT FOUND"
}
Start-Sleep -Seconds 3
Add-Content -Path $res -Value ("stopped: " + ($null -eq (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)))
