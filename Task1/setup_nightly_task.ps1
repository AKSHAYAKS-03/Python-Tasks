param(
    [string]$PythonPath = "python",
    [string]$TaskName = "Task1NightlyScraper",
    [string]$RunTime = "02:00"
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $projectRoot "main.py"

$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "`"$scriptPath`"" `
    -WorkingDirectory $projectRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $RunTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Runs the Task1 product scraper every night." `
    -Force

Write-Host "Scheduled task '$TaskName' created for daily execution at $RunTime."
