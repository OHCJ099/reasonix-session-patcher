@echo off
setlocal
cd /d "%~dp0"
set SHORTCUT=%USERPROFILE%\Desktop\Reasonix Session Patcher.lnk
powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell=New-Object -ComObject WScript.Shell; $sc=$shell.CreateShortcut('%SHORTCUT%'); $sc.TargetPath=(Join-Path (Get-Location) 'start_reasonix_session_patcher.bat'); $sc.WorkingDirectory=(Get-Location).Path; $sc.Description='Reasonix Session Patcher Web UI'; $icon=Join-Path $env:LOCALAPPDATA 'Programs\Reasonix\reasonix-desktop.exe'; if(Test-Path $icon){$sc.IconLocation=$icon + ',0'}; $sc.Save()"
echo Desktop shortcut created: %SHORTCUT%
pause
