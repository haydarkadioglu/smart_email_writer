@echo off
echo Starting Smart Email Writer - Qt6 Desktop Edition...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Install Qt6 dependencies if not already installed
echo Checking Qt6 dependencies...
pip show PyQt6 >nul 2>&1
if errorlevel 1 (
    echo Installing Qt6 dependencies...
    pip install -r requirements-qt.txt
)

REM Run the Qt6 application
echo.
echo Launching Qt6 GUI...
python main_qt.py

pause
