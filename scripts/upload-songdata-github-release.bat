@echo off
setlocal
cd /d "%~dp0.."

rem Do not use non-ASCII in this file: CMD may mis-parse lines and break %GITHUB_TOKEN% etc.
rem Put secrets in upload-songdata-github-release.local.ps1 (gitignored); see docs/github-releases-songdata.md

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-songdata-github-release.ps1" %*
exit /b %ERRORLEVEL%
