@echo off
REM SERP Analyzer CLI wrapper
REM Usage: search.bat "your search query" [num_results] [output_format]

setlocal EnableDelayedExpansion

REM Set default values
set QUERY=%1
set NUM_RESULTS=6
set OUTPUT_FORMAT=terminal

REM Check if query is provided
if "%QUERY%"=="" (
    echo Error: Search query is required.
    echo Usage: search.bat "your search query" [num_results] [output_format]
    exit /b 1
)

REM Check if number of results is provided
if not "%2"=="" (
    set NUM_RESULTS=%2
)

REM Check if output format is provided
if not "%3"=="" (
    set OUTPUT_FORMAT=%3
)

REM Run the Python script
echo Running SERP search for: %QUERY%
python serp_cli.py "%QUERY%" -n %NUM_RESULTS% -o %OUTPUT_FORMAT%

endlocal
