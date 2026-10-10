@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul || (echo Install Node.js LTS & pause & exit /b 1)
if "%ANTHROPIC_API_KEY%"=="" set /p ANTHROPIC_API_KEY=Paste Anthropic API key: 
node src\cli.js smoke --config config.json || (echo Smoke test FAILED. See runs folder. & pause & exit /b 1)
node src\cli.js run --config config.json
pause
