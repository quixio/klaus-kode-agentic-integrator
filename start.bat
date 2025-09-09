@echo off
setlocal enabledelayedexpansion

REM Quix Coding Agent Startup Script for Windows
REM This script handles environment setup and launches the application

echo.
echo ============================================
echo      Quix Coding Agent - Klaus Kode
echo ============================================
echo.

REM Check Python version
echo [CHECK] Checking Python version...
set "PYTHON_CMD="
set "PYTHON_FOUND=0"

REM Try common Python commands
for %%p in (python3.12 python3.13 python3.14 python3 python py) do (
    where %%p >nul 2>&1
    if !errorlevel! equ 0 (
        REM Check if this Python meets version requirement
        for /f "tokens=2" %%v in ('%%p --version 2^>^&1') do (
            set "PY_VERSION=%%v"
            REM Extract major and minor version
            for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
                set "PY_MAJOR=%%a"
                set "PY_MINOR=%%b"
            )
            if !PY_MAJOR! equ 3 if !PY_MINOR! geq 12 (
                set "PYTHON_CMD=%%p"
                set "PYTHON_FOUND=1"
                goto :python_found
            )
        )
    )
)

:python_found
if !PYTHON_FOUND! equ 0 (
    echo [ERROR] Python 3.12 or higher is required but not found!
    echo.
    echo Current Python versions found:
    where python >nul 2>&1 && python --version 2>&1
    where python3 >nul 2>&1 && python3 --version 2>&1
    where py >nul 2>&1 && py --version 2>&1
    echo.
    echo Please install Python 3.12 or higher, or provide the path to a valid Python executable:
    set /p "CUSTOM_PYTHON=Python path (or press Enter to exit): "
    if "!CUSTOM_PYTHON!"=="" (
        echo [ERROR] Exiting...
        exit /b 1
    )
    REM Check custom Python version
    for /f "tokens=2" %%v in ('!CUSTOM_PYTHON! --version 2^>^&1') do (
        set "PY_VERSION=%%v"
        for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
            set "PY_MAJOR=%%a"
            set "PY_MINOR=%%b"
        )
        if !PY_MAJOR! equ 3 if !PY_MINOR! geq 12 (
            set "PYTHON_CMD=!CUSTOM_PYTHON!"
            set "PYTHON_FOUND=1"
        ) else (
            echo [ERROR] The provided Python executable is not version 3.12 or higher
            !CUSTOM_PYTHON! --version 2>&1
            exit /b 1
        )
    )
)

echo [OK] Using Python !PY_VERSION! at: !PYTHON_CMD!

REM Check if virtual environment exists
if not exist ".venv" (
    echo [SETUP] First-time setup detected...
    echo [SETUP] Creating virtual environment...
    !PYTHON_CMD! -m venv .venv
    
    REM Activate virtual environment
    call .venv\Scripts\activate.bat
    
    echo [SETUP] Installing requirements...
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
    
    echo [SETUP] Virtual environment created and packages installed
) else (
    REM Activate existing virtual environment
    call .venv\Scripts\activate.bat
)

REM Check for .env file
if not exist ".env" (
    echo [ERROR] No .env file found!
    echo Please create a .env file using .env.example as a guide:
    echo    copy .env.example .env
    echo Then edit the .env file and add your API keys.
    echo.
    echo [ERROR] Exiting...
    exit /b 1
)

REM Load environment variables from .env file
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        REM Skip comment lines and empty lines
        set "line=%%a"
        if not "!line:~0,1!"=="#" if not "!line!"=="" (
            set "%%a=%%b"
        )
    )
)

REM Check required environment variables
echo [CHECK] Checking environment variables...
set "MISSING_VARS="

if "%OPENAI_API_KEY%"=="" set "MISSING_VARS=!MISSING_VARS! OPENAI_API_KEY"
if "%OPENAI_API_KEY%"=="your_openai_api_key_here" set "MISSING_VARS=!MISSING_VARS! OPENAI_API_KEY"

if "%ANTHROPIC_API_KEY%"=="" set "MISSING_VARS=!MISSING_VARS! ANTHROPIC_API_KEY"
if "%ANTHROPIC_API_KEY%"=="your_anthropic_api_key_here" set "MISSING_VARS=!MISSING_VARS! ANTHROPIC_API_KEY"

if "%QUIX_TOKEN%"=="" set "MISSING_VARS=!MISSING_VARS! QUIX_TOKEN"
if "%QUIX_TOKEN%"=="your_quix_token_here" set "MISSING_VARS=!MISSING_VARS! QUIX_TOKEN"

REM Check if QUIX_BASE_URL is missing and add it to .env if needed
if "%QUIX_BASE_URL%"=="" (
    echo [WARNING] QUIX_BASE_URL not found. Adding default to .env...
    echo QUIX_BASE_URL=https://portal-api.cloud.quix.io >> .env 2>nul
    if !errorlevel! equ 0 (
        echo [OK] Added QUIX_BASE_URL to .env
        set "QUIX_BASE_URL=https://portal-api.cloud.quix.io"
    ) else (
        echo [ERROR] Could not write to .env file
        echo Please manually add the following line to your .env file:
        echo QUIX_BASE_URL=https://portal-api.cloud.quix.io
        pause
        exit /b 1
    )
)

if not "!MISSING_VARS!"=="" (
    echo [ERROR] Missing or invalid environment variables:
    echo         !MISSING_VARS!
    echo.
    echo Please edit the .env file and add your API keys:
    echo    notepad .env  ^(or use your preferred editor^)
    echo.
    echo To get the required keys:
    echo    - OpenAI API Key: https://platform.openai.com/api-keys
    echo    - Anthropic API Key: https://console.anthropic.com/account/keys
    echo    - Quix Token: https://portal.cloud.quix.io/settings/tokens
    echo.
    pause
    exit /b 1
)

echo [OK] All required environment variables are set

REM Check if Claude Code SDK is installed
echo [CHECK] Checking Claude Code SDK...
where claude >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Claude Code SDK not found in PATH
    
    REM Check common installation locations on Windows
    set "FOUND_CLAUDE=0"
    
    if exist "%USERPROFILE%\.claude\local\node_modules\.bin\claude.cmd" (
        echo [OK] Found Claude Code SDK at user directory
        set "FOUND_CLAUDE=1"
    ) else if exist "%APPDATA%\npm\claude.cmd" (
        echo [OK] Found Claude Code SDK in npm global
        set "FOUND_CLAUDE=1"
    ) else if exist ".\node_modules\.bin\claude.cmd" (
        echo [OK] Found Claude Code SDK in local node_modules
        set "FOUND_CLAUDE=1"
    )
    
    if "!FOUND_CLAUDE!"=="0" (
        echo [INSTALL] Claude Code SDK not installed. Would you like to install it? (y/n)
        set /p response=
        if /i "!response!"=="y" (
            echo [INSTALL] Installing Claude Code SDK...
            npm install -g claude-code-sdk
        ) else (
            echo [WARNING] Some features may not work without Claude Code SDK
            echo           Install manually with: npm install -g claude-code-sdk
        )
    )
) else (
    echo [OK] Claude Code SDK is installed
)

REM Create necessary directories if they don't exist
if not exist "working_files\current" mkdir "working_files\current"
if not exist "working_files\cache" mkdir "working_files\cache"
if not exist "logging" mkdir "logging"

REM Start the application
echo.
echo [START] Starting Quix Coding Agent...
echo ----------------------------------------
echo.

REM Run the main application with any passed arguments
!PYTHON_CMD! main.py %*

REM Deactivate virtual environment on exit
call deactivate >nul 2>&1

endlocal