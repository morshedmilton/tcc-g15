# Stop the dev app and its watchdog (matched by command line).
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'"
foreach ($p in $procs) {
    if ($p.CommandLine -like '*tcc-g15.py*' -or $p.CommandLine -like '*tcc-watchdog.py*') {
        & taskkill /F /T /PID $p.ProcessId | Out-Null
        "killed $($p.ProcessId)"
    }
}
Start-Sleep -Seconds 3
