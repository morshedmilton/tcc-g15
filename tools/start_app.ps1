# Start the dev build elevated with logs captured, leave it running, write its pid.
$root = "C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default\tcc-g15"
$py   = Join-Path $root ".venv\Scripts\python.exe"
$src  = Join-Path $root "src\tcc-g15.py"
$pidFile = Join-Path $root "docs\baseline\dev.pid"
$out  = Join-Path $root "docs\baseline\dev.out.log"
$err  = Join-Path $root "docs\baseline\dev.err.log"

$p = Start-Process -FilePath $py -ArgumentList $src -WorkingDirectory (Join-Path $root "src") `
     -PassThru -RedirectStandardOutput $out -RedirectStandardError $err

$deadline = (Get-Date).AddSeconds(60)
$app = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 400
    $app = Get-Process -ErrorAction SilentlyContinue |
           Where-Object { $_.MainWindowTitle -eq 'Thermal Control Center for Dell G15' } |
           Select-Object -First 1
    if ($app) { break }
    if ($p.HasExited) { break }
}
if ($app) { "$($app.Id)" | Out-File -FilePath $pidFile -Encoding ascii }
else { "none exited=$($p.HasExited) code=$($p.ExitCode)" | Out-File -FilePath $pidFile -Encoding ascii }
