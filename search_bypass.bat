@echo off
echo SERP Analyzer - Bypass Edition
echo ===========================
echo.

if "%~1"=="" (
    echo Usage: search_bypass.bat "your search query"
    echo Example: search_bypass.bat "python tutorial"
    echo.
    set /p QUERY=Enter your search query: 
) else (
    set QUERY=%~1
)

echo.
echo Searching for: %QUERY%
echo.
echo Please wait, this may take a moment...
echo.

python bypass_cli.py "%QUERY%"

echo.
echo Search complete!
echo.
pause
