@echo off
setlocal enabledelayedexpansion

REM Quix Coding Agent Startup Script for Windows
REM This script handles environment setup and launches the application

echo.
echo ============================================
echo      Quix Coding Agent - Klaus Kode
echo ============================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [SETUP] First-time setup detected...
    echo [SETUP] Creating virtual environment...
    python -m venv .venv
    
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
    echo [WARNING] No .env file found. Creating from template...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env file from template
    ) else (
        REM Create a basic .env file
        (
            echo # Required API Keys - Please fill these in
            echo ANTHROPIC_API_KEY=your_anthropic_api_key_here
            echo QUIX_TOKEN=your_quix_token_here
            echo QUIX_BASE_URL=https://portal-api.cloud.quix.io
            echo.
            echo # Optional settings
            echo # VERBOSE_MODE=false
        ) > .env
        echo [OK] Created .env template
    )
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

if "%ANTHROPIC_API_KEY%"=="" set "MISSING_VARS=!MISSING_VARS! ANTHROPIC_API_KEY"
if "%ANTHROPIC_API_KEY%"=="your_anthropic_api_key_here" set "MISSING_VARS=!MISSING_VARS! ANTHROPIC_API_KEY"

if "%QUIX_TOKEN%"=="" set "MISSING_VARS=!MISSING_VARS! QUIX_TOKEN"
if "%QUIX_TOKEN%"=="your_quix_token_here" set "MISSING_VARS=!MISSING_VARS! QUIX_TOKEN"

if not "!MISSING_VARS!"=="" (
    echo [ERROR] Missing or invalid environment variables:
    echo         !MISSING_VARS!
    echo.
    echo Please edit the .env file and add your API keys:
    echo    notepad .env  ^(or use your preferred editor^)
    echo.
    echo To get the required keys:
    echo    - Anthropic API Key: https://console.anthropic.com/account/keys
    echo    - Quix Token: https://portal.cloud.quix.io/settings/tokens
    echo.
    pause
    exit /b 1
)

REM Set default QUIX_BASE_URL if not set
if "%QUIX_BASE_URL%"=="" (
    set "QUIX_BASE_URL=https://portal-api.cloud.quix.io"
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
python main.py %*

REM Deactivate virtual environment on exit
call deactivate >nul 2>&1

endlocal