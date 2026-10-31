@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0.") do set "ROOT=%%~fI"
set "MERCH_FORGE_PACKAGE_ROOT=%ROOT%"
rem NEW reconciliation: the recovered strict JSON contract requires PowerShell 7.5+.
rem Only the existing native stable machine installation is supported; never search PATH.
set "PS_EXE="
if defined ProgramFiles set "PS_EXE=%ProgramFiles%\PowerShell\7\pwsh.exe"
if defined ProgramW6432 set "PS_EXE=%ProgramW6432%\PowerShell\7\pwsh.exe"

if not defined PS_EXE goto runtime_unavailable
if not exist "%PS_EXE%" goto runtime_unavailable
if not exist "%ROOT%\MerchForgePreflight.ps1" (
  set "FAIL_CODE=43"
  set "FAIL_MESSAGE=MerchForgePreflight.ps1 is missing."
  goto startup_failure
)

rem Do not override execution policy. Capture host errors even if the script cannot start.
if defined MERCH_FORGE_LAUNCH_LOG (
  "%PS_EXE%" -NoLogo -NoProfile -NonInteractive -STA -File "%ROOT%\MerchForgePreflight.ps1" -PackageRoot "%ROOT%" 2>>"%MERCH_FORGE_LAUNCH_LOG%"
) else (
  "%PS_EXE%" -NoLogo -NoProfile -NonInteractive -STA -File "%ROOT%\MerchForgePreflight.ps1" -PackageRoot "%ROOT%"
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

"%PS_EXE%" -NoLogo -NoProfile -STA -File "%ROOT%\MerchForgeWorkbench.ps1" 1>>"%MERCH_FORGE_LAUNCH_LOG%" 2>&1
set "EC=%ERRORLEVEL%"
>"%MERCH_FORGE_EXIT_FILE%" echo %EC%
exit /b %EC%

:runtime_unavailable
set "FAIL_CODE=42"
set "FAIL_MESSAGE=PowerShell 7.5 or newer is required at the native Program Files PowerShell 7 location. No runtime was installed or substituted."
goto startup_failure

:startup_failure
>&2 echo %FAIL_MESSAGE%
if defined MERCH_FORGE_LAUNCH_LOG >>"%MERCH_FORGE_LAUNCH_LOG%" echo %FAIL_MESSAGE%
if defined MERCH_FORGE_EXIT_FILE >"%MERCH_FORGE_EXIT_FILE%" echo %FAIL_CODE%
exit /b %FAIL_CODE%
