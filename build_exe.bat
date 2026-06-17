@echo off
echo =================================================
echo Smart Email Writer - Building Executable
echo =================================================
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    echo [1/2] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [1/2] Virtual environment not found. Building with system python...
)

echo.
echo [2/2] Running build script...
python build.py

if errorlevel 1 (
    echo.
    echo ❌ Build failed. Press any key to exit...
    pause > nul
    exit /b 1
)

echo.
echo Press any key to exit...
pause > nul
