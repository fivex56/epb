# Schedule Twitter auto-poster to run daily at 10:00 AM
# Run this PowerShell script as Administrator once

$taskName = "EnergyPriceBoard-TwitterPoster"
$python = "C:\Users\fivex\AppData\Local\Programs\Python\Python313\python.exe"
$script = "c:\Users\fivex\Desktop\Projects\Energy_sbor\twitter_poster.py"
$workDir = "c:\Users\fivex\Desktop\Projects\Energy_sbor"

$action = New-ScheduledTaskAction -Execute $python -Argument $script -WorkingDirectory $workDir

# Run daily at 10:00, 14:00, 18:00 (3 random times per day)
$trigger1 = New-ScheduledTaskTrigger -Daily -At "10:00"
$trigger2 = New-ScheduledTaskTrigger -Daily -At "16:00"

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Limited

Register-ScheduledTask -TaskName $taskName `
    -Action $action `
    -Trigger $trigger1, $trigger2 `
    -Principal $principal `
    -Description "Posts next tweet from Energy Price Board twitter_posts.md" `
    -Force

Write-Host "✅ Scheduled! Twitter poster will run daily at 10:00 and 16:00"
Write-Host "   Check: taskschd.msc → $taskName"
Write-Host ""
Write-Host "To run once now (test):"
Write-Host "  python twitter_poster.py"
Write-Host ""
Write-Host "Dry run (no actual posting):"
Write-Host "  set TWITTER_DRY_RUN=1 && python twitter_poster.py"
