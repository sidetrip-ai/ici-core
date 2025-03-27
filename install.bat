@echo off
setlocal enabledelayedexpansion

:: Colors for output
set GREEN=[92m
set YELLOW=[93m
set RED=[91m
set NC=[0m

:: Repository details
set REPO_URL=https://github.com/sidetrip-ai/ici-core.git
set REPO_NAME=ici-core

:: Check if git is installed
call :check_git || exit /b 1

:: Check if Python is installed
call :check_python || exit /b 1

:: Check if repository exists and clone if needed
call :check_repo || exit /b 1

:: Run the setup script
echo %YELLOW%Running setup script...%NC%
if exist "./setup.bat" (
    call setup.bat
) else (
    echo %RED%Setup script not found.%NC%
    exit /b 1
)

goto :eof

:check_git
:: Check if git is installed
where git >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%Git is not installed.%NC%
    echo %YELLOW%Please install git first:%NC%
    echo   For Windows: %GREEN%https://git-scm.com/download/win%NC%
    exit /b 1
)
echo %GREEN%Git is installed.%NC%
exit /b 0
goto :eof

:check_python
:: Check if Python is installed
where python3 >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%Python 3 is not installed.%NC%
    echo %YELLOW%Please install Python 3 first:%NC%
    echo   For Windows: %GREEN%https://www.python.org/downloads/%NC%
    exit /b 1
)
echo %GREEN%Python is installed.%NC%
exit /b 0
goto :eof

:find_repo
:: First check current directory
if exist "%REPO_NAME%" (
    set REPO_PATH=%CD%\%REPO_NAME%
    exit /b 0
)

:: Then check parent directory
if exist "..\%REPO_NAME%" (
    pushd ..
    set REPO_PATH=!CD!\%REPO_NAME%
    popd
    exit /b 0
)

:: Then check user home directory
if exist "%USERPROFILE%\%REPO_NAME%" (
    set REPO_PATH=%USERPROFILE%\%REPO_NAME%
    exit /b 0
)

exit /b 1
goto :eof

:check_repo
:: Check if repository is already cloned
call :find_repo
if %ERRORLEVEL% equ 0 (
    echo %GREEN%Repository found at: %REPO_PATH%%NC%
    cd /d "%REPO_PATH%"
    exit /b 0
) else (
    echo %YELLOW%Repository not found. Cloning from %REPO_URL%...%NC%
    
    :: Check if directory exists and is empty
    if exist "%REPO_NAME%" (
        echo %YELLOW%Directory %REPO_NAME% exists but is not a git repository.%NC%
        echo %YELLOW%Removing existing directory...%NC%
        rmdir /s /q "%REPO_NAME%"
    )
    
    :: Clone the repository
    git clone "%REPO_URL%"
    if %ERRORLEVEL% neq 0 (
        echo %RED%Failed to clone repository.%NC%
        echo %YELLOW%Please try the manual installation method from the README.%NC%
        exit /b 1
    )
    
    :: Change to the repository directory
    cd /d "%REPO_NAME%"
    if %ERRORLEVEL% neq 0 (
        echo %RED%Failed to change to repository directory.%NC%
        exit /b 1
    )
    
    echo %GREEN%Repository cloned successfully!%NC%
    exit /b 0
)
goto :eof 
