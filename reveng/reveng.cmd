@echo off
where node >nul 2>nul || (echo Install Node.js 20+ from https://nodejs.org ^& exit /b 1)
node "%~dp0src\cli.js" %*
