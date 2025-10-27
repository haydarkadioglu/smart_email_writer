@echo off
echo Smart Email Writer - Starting...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)



REM Run the application
echo.
echo Starting Smart Email Writer...
echo.
streamlit run main.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application encountered an error. Press any key to exit...
    pause
)
