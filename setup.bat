@echo off
setlocal enabledelayedexpansion

:: Colors for output
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

:: Default virtual environment directory name
set "VENV_DIR=venv"

:: Check if the script is being run from the project root directory
if not exist "requirements.txt" (
    echo %RED%Error: requirements.txt not found.%NC%
    echo %YELLOW%Please run this script from the project root directory.%NC%
    exit /b 1
)

:: Function to check if running in an active virtual environment
call :check_venv
if %ERRORLEVEL% neq 0 (
    call :setup_venv
)

:: Install dependencies
call :install_dependencies

:: Verify all dependencies are installed
call :verify_dependencies

echo %GREEN%Setup completed successfully!%NC%
echo %YELLOW%You can now run the application.%NC%

:: Print next steps
echo.
echo %YELLOW%Next Steps:%NC%
echo 1. To activate the virtual environment in a new terminal:
echo    %GREEN%%VENV_DIR%\Scripts\activate%NC%
echo 2. To run the Telegram Application:
echo    %GREEN%python main.py%NC%
echo.
echo %YELLOW%Note: Make sure you have configured your Telegram API credentials in the config file before running the application.%NC%

goto :eof

:check_venv
:: Check if running in an active virtual environment
if "%VIRTUAL_ENV%"=="" (
    echo %YELLOW%No active virtual environment detected.%NC%
    exit /b 1
) else (
    echo %GREEN%Active virtual environment detected: %VIRTUAL_ENV%%NC%
    exit /b 0
)
goto :eof

:setup_venv
:: Create and activate virtual environment if it doesn't exist
if not exist "%VENV_DIR%\" (
    echo %YELLOW%Creating virtual environment in %VENV_DIR%...%NC%
    python -m venv %VENV_DIR%
    if %ERRORLEVEL% neq 0 (
        echo %RED%Failed to create virtual environment.%NC%
        echo %YELLOW%Please ensure Python 3 and venv are installed.%NC%
        exit /b 1
    )
) else (
    echo %GREEN%Virtual environment already exists in %VENV_DIR%.%NC%
)

echo %YELLOW%Activating virtual environment...%NC%
call %VENV_DIR%\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo %RED%Failed to activate virtual environment.%NC%
    exit /b 1
)
echo %GREEN%Virtual environment activated!%NC%
goto :eof

:install_dependencies
:: Install dependencies from requirements.txt
echo %YELLOW%Installing dependencies from requirements.txt...%NC%
pip install -q -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo %RED%Failed to install dependencies.%NC%
    exit /b 1
)
echo %GREEN%Dependencies installed successfully!%NC%
goto :eof

:verify_dependencies
:: Verify all dependencies are installed
echo %YELLOW%Verifying installed dependencies...%NC%

set has_missing=0
set has_mismatch=0
set missing_packages=

:: Read requirements.txt and check each package
for /f "tokens=*" %%a in (requirements.txt) do (
    set line=%%a
    
    :: Skip comments and empty lines
    echo !line! | findstr /r "^#" > nul
    if !ERRORLEVEL! neq 0 (
        if not "!line!"=="" (
            :: Extract package name and version
            for /f "tokens=1,2 delims=>=" %%b in ("!line!") do (
                set package=%%b
                set package=!package: =!
                set version=%%c
                
                :: Check if package is installed
                pip show !package! > nul 2>&1
                if !ERRORLEVEL! neq 0 (
                    set has_missing=1
                    set missing_packages=!missing_packages!  - !line!
                ) else if not "!version!"=="" (
                    :: Version check is simplified in batch - just report the version
                    for /f "tokens=2" %%i in ('pip show !package! ^| findstr "Version"') do (
                        set installed_version=%%i
                        echo %YELLOW%Package !package! installed version: !installed_version!, required: !version!%NC%
                    )
                )
            )
        )
    )
)

:: Report issues if any
if !has_missing! neq 0 (
    echo %RED%Some dependencies are missing.%NC%
    
    if not "!missing_packages!"=="" (
        echo %YELLOW%Missing packages:%NC%
        echo !missing_packages!
    )
    
    echo %YELLOW%Please run the following command to install packages:%NC%
    echo pip install -r requirements.txt
    exit /b 1
)

echo %GREEN%All dependencies verified successfully!%NC%
goto :eof 
