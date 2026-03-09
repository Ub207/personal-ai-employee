Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*bronze_tier*' } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "Killed PID $($_.ProcessId): $($_.CommandLine.Substring(0, [Math]::Min(80, $_.CommandLine.Length)))"
}
Write-Host "All bronze_tier watcher processes killed."
