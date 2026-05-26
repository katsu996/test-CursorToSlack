@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

if not defined GITHUB_TOKEN (
  if not defined GH_TOKEN (
    echo [ERROR] GITHUB_TOKEN または GH_TOKEN を設定してください。
    exit /b 2
  )
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-songdata-github-release.ps1" %*
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" exit /b %ERR%
exit /b 0
