@echo off
echo Smart Email Writer - Starting...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Run the application
echo.
echo Starting Smart Email Writer Desktop...
echo.
python main.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application encountered an error. Press any key to exit...
    pause
)
