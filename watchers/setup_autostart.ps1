$StartupFolder = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$ShortcutPath = "$StartupFolder\AIEmployee_Watcher.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "D:\bronze_tier\watchers\start_watcher.bat"
$Shortcut.WorkingDirectory = "D:\bronze_tier"
$Shortcut.Description = "AI Employee Filesystem Watcher"
$Shortcut.Save()

Write-Host "Auto-start setup complete: $ShortcutPath" -ForegroundColor Green
