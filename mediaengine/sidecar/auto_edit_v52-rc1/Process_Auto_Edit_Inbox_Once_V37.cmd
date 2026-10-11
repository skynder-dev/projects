@echo off
setlocal
set "ROOT=D:\Archivist"
set "PTR=%ROOT%\sidecars\auto_edit\current.txt"
if not exist "%PTR%" (echo V37 sidecar not activated&exit /b 2)
set /p SLOT=<"%PTR%"
set "PS=%ROOT%\sidecars\auto_edit\releases\%SLOT%\RUN_AUTO_EDIT_QUEUE_V37.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS%" -ArchivistRoot "%ROOT%" -Once
exit /b %ERRORLEVEL%
