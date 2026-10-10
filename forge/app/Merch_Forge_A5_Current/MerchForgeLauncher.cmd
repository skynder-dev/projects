@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "MERCH_FORGE_PACKAGE_ROOT=%ROOT%"
set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "PS_EXE=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"

if not exist "%PS_EXE%" exit /b 42
if not exist "%ROOT%\MerchForgePreflight.ps1" exit /b 43

if /I "%~1"=="--verify-only" (
  "%PS_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%ROOT%\MerchForgePreflight.ps1" -PackageRoot "%ROOT%"
) else (
  "%PS_EXE%" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%ROOT%\MerchForgePreflight.ps1" -PackageRoot "%ROOT%"
)
set "PF=%ERRORLEVEL%"
if not "%PF%"=="0" (
  if defined MERCH_FORGE_LAUNCH_LOG >>"%MERCH_FORGE_LAUNCH_LOG%" echo Unified preflight failed with code %PF%.
  if defined MERCH_FORGE_EXIT_FILE >"%MERCH_FORGE_EXIT_FILE%" echo %PF%
  exit /b %PF%
)

if /I "%~1"=="--verify-only" exit /b 0

if not defined MERCH_FORGE_LAUNCH_LOG exit /b 90
if not defined MERCH_FORGE_EXIT_FILE exit /b 91
if not defined MERCH_FORGE_READY_FILE (
  >>"%MERCH_FORGE_LAUNCH_LOG%" echo Startup guardian is incomplete: ready file is not configured.
  >"%MERCH_FORGE_EXIT_FILE%" echo 92
  exit /b 92
)
if not exist "%ROOT%\MerchForgeWorkbench.ps1" (
  >>"%MERCH_FORGE_LAUNCH_LOG%" echo MerchForgeWorkbench.ps1 is missing after unified preflight.
  >"%MERCH_FORGE_EXIT_FILE%" echo 88
  exit /b 88
)

"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File "%ROOT%\MerchForgeWorkbench.ps1" 1>>"%MERCH_FORGE_LAUNCH_LOG%" 2>&1
set "EC=%ERRORLEVEL%"
>"%MERCH_FORGE_EXIT_FILE%" echo %EC%
exit /b %EC%
