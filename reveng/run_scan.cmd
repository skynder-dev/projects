@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js not found. Install LTS from https://nodejs.org and run again. & pause & exit /b 1)
if "%ANTHROPIC_API_KEY%"=="" set /p ANTHROPIC_API_KEY=Paste your Anthropic API key and press Enter: 
echo.
node src\cli.js doctor --config config.json
echo.
echo Scan started. Spend is capped at 15 USD in config.json. Ctrl+C stops it.
node src\cli.js run --config config.json
echo.
echo Finished. Send runs\(newest folder)\REPORT.md to Claude.
pause
