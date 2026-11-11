@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\create-ai-admin.ps1"
if errorlevel 1 pause
