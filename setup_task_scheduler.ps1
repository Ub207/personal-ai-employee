# Windows Task Scheduler Setup for AI Employee
# ==============================================
# Run this script to create scheduled tasks for the AI Employee system.
# Requires Administrator privileges.

param(
    [string]$VaultPath = "D:\bronze_tier",
    [string]$PythonPath = "python"
)

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  AI Employee — Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "  Silver Tier — Scheduled Tasks" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(`
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Task 1: Daily Briefing at 8 AM
Write-Host "Creating Daily Briefing task (8:00 AM daily)..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction -Execute $PythonPath `
    -Argument "daily_briefing_scheduler.py --vault-path `"$VaultPath`"" `
    -WorkingDirectory "$VaultPath\watchers"

$trigger = New-ScheduledTaskTrigger -Daily -At 8am
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "AI Employee Daily Briefing" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Generates daily CEO briefing every morning at 8 AM" `
    -Force

Write-Host "✓ Daily Briefing task created" -ForegroundColor Green

# Task 2: Weekly Audit on Sunday at 10 PM
Write-Host "Creating Weekly Audit task (Sunday 10:00 PM)..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction -Execute $PythonPath `
    -Argument "daily_briefing_scheduler.py --vault-path `"$VaultPath`"" `
    -WorkingDirectory "$VaultPath\watchers"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 10pm
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "AI Employee Weekly Audit" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Generates weekly CEO briefing every Sunday night" `
    -Force

Write-Host "✓ Weekly Audit task created" -ForegroundColor Green

# Task 3: Watcher Health Check every hour
Write-Host "Creating Watcher Health Check task (Every hour)..." -ForegroundColor Yellow

$scriptContent = @"
# Health Check Script
`$vaultPath = "$VaultPath"
`$watchers = @("filesystem_watcher.py", "gmail_imap_watcher.py", "whatsapp_watcher.py")
`$logFile = "`$vaultPath\Logs\health_check.log"

`$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
`$logEntry = "`$timestamp - Health Check`n"

foreach (`$watcher in `$watchers) {
    `$processes = Get-Process | Where-Object { `$_.Path -like "*`$watcher*" }
    if (`$processes) {
        `$logEntry += "  ✓ `$watcher - Running`n"
    } else {
        `$logEntry += "  ⚠ `$watcher - Not running`n"
    }
}

Add-Content -Path `$logFile -Value `$logEntry
"@

$logDir = "$VaultPath\Logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$healthScriptPath = "$VaultPath\health_check.ps1"
Set-Content -Path $healthScriptPath -Value $scriptContent

$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$healthScriptPath`"" `
    -WorkingDirectory $VaultPath

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet

Register-ScheduledTask -TaskName "AI Employee Watcher Health Check" `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Checks watcher processes every hour" `
    -Force

Write-Host "✓ Health Check task created" -ForegroundColor Green

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Created tasks:" -ForegroundColor White
Write-Host "  1. AI Employee Daily Briefing (8:00 AM daily)"
Write-Host "  2. AI Employee Weekly Audit (Sunday 10:00 PM)"
Write-Host "  3. AI Employee Watcher Health Check (Every hour)"
Write-Host ""
Write-Host "To view tasks: Open Task Scheduler → Task Scheduler Library"
Write-Host "To run manually: Right-click task → Run"
Write-Host "To disable: Right-click task → Disable"
Write-Host ""
