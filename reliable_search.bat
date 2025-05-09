@echo off
echo Reliable SERP Analyzer - Avoid CAPTCHA Detection
echo ================================================
echo.

if "%~1"=="" (
    python reliable_search.py
) else (
    python reliable_search.py "%~1"
)

pause
