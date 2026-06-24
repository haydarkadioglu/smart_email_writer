@echo off
echo SEW AI - Starting...
echo.

IF NOT EXIST "%~dp0venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

call "%~dp0venv\Scripts\activate.bat"

echo Starting SEW AI Desktop...
echo.
python main.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application encountered an error. Press any key to exit...
    pause
)
