$out = @()
try {
    $sr = Get-CimInstance -Namespace root\default -ClassName SystemRestore -ErrorAction Stop
    $out += "SystemRestore class: ok"
} catch {
    $out += "SystemRestore class: " + $_.Exception.Message
}
try {
    $cfg = Get-CimInstance -Namespace root\default -ClassName SystemRestoreConfig -ErrorAction Stop
    $out += "SystemRestoreConfig: ok"
} catch {
    $out += "SystemRestoreConfig: " + $_.Exception.Message
}
try {
    Enable-ComputerRestore -Drive "C:\" -ErrorAction Stop
    $out += "Enable-ComputerRestore C: ok"
} catch {
    $out += "Enable-ComputerRestore failed: " + $_.Exception.Message
}
try {
    Checkpoint-Computer -Description "tcc-g15 before hardware tests" -RestorePointType MODIFY_SETTINGS -ErrorAction Stop
    $out += "Checkpoint-Computer: ok"
} catch {
    $out += "Checkpoint-Computer failed: " + $_.Exception.Message
}
try {
    $pts = Get-ComputerRestorePoint -ErrorAction Stop
    $out += "restore points: " + ($pts | Measure-Object).Count
    foreach ($p in $pts | Select-Object -Last 3) { $out += ("  " + $p.Description + " | " + $p.CreationTime) }
} catch {
    $out += "Get-ComputerRestorePoint failed: " + $_.Exception.Message
}
$out | Out-File -FilePath "C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default\tcc-g15\docs\restorepoint.txt" -Encoding utf8