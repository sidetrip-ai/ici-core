@echo off
REM Simple setup script for ICI Core on Windows

echo Checking Python installation...
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python could not be found. Please install Python 3.8 or newer.
    exit /b 1
)

echo Using Python:
python --version

if not exist ici-env (
    echo Creating virtual environment...
    python -m venv ici-env
) else (
    echo Virtual environment already exists.
)

echo Activating virtual environment...
call ici-env\Scripts\activate.bat

echo Installing dependencies...
pip install -e .[dev]

echo.
echo Setup complete! You can now use the following commands:
echo   pytest                - Run tests
echo   pytest --cov=ici tests/ - Run tests with coverage
echo   black ici tests examples - Format code with black
echo.
echo To activate the virtual environment in the future, run:
echo   ici-env\Scripts\activate.bat

REM Keep the environment activated
cmd /k 