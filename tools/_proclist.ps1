$res = "C:\Users\morsh\AppData\Roaming\AutoClaw-oversea-official\accounts\98e17ebcdf311a8f97d63ba37e0764ae6703014cbe59f58a71e626853184e80c\projects\Default\tcc-g15\docs\baseline\proc.list.txt"
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Select-Object ProcessId, ParentProcessId, CommandLine |
  Format-List | Out-File -FilePath $res -Encoding utf8
