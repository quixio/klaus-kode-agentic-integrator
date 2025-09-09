# Quix Coding Agent Startup Script for Windows PowerShell
# This script handles environment setup and launches the application

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput($ForegroundColor, $Message) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Host $Message
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-Host ""
Write-ColorOutput Cyan "╔════════════════════════════════════════╗"
Write-ColorOutput Cyan "║     Quix Coding Agent - Klaus Kode     ║"
Write-ColorOutput Cyan "╚════════════════════════════════════════╝"
Write-Host ""

# Function to check Python version
function Test-PythonVersion {
    param($pythonCmd)
    try {
        $versionOutput = & $pythonCmd --version 2>&1
        if ($versionOutput -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -eq 3 -and $minor -ge 12) {
                return $true
            }
        }
    } catch {
        return $false
    }
    return $false
}

# Find suitable Python executable
Write-ColorOutput Blue "🔍 Checking Python version..."
$pythonCmd = $null

# Check common Python commands
$pythonCommands = @("python3.12", "python3.13", "python3.14", "python3", "python", "py")
foreach ($cmd in $pythonCommands) {
    $pythonExe = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($pythonExe) {
        if (Test-PythonVersion $cmd) {
            $pythonCmd = $cmd
            break
        }
    }
}

if (-not $pythonCmd) {
    Write-ColorOutput Red "❌ Python 3.12 or higher is required but not found!"
    Write-ColorOutput Yellow "Current Python versions found:"
    foreach ($cmd in @("python3", "python", "py")) {
        $pythonExe = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($pythonExe) {
            & $cmd --version 2>&1
        }
    }
    Write-Host ""
    Write-ColorOutput Yellow "Please install Python 3.12 or higher, or provide the path to a valid Python executable:"
    $customPython = Read-Host "Python path (or press Enter to exit)"
    if ([string]::IsNullOrEmpty($customPython)) {
        Write-ColorOutput Red "Exiting..."
        exit 1
    }
    if (Test-PythonVersion $customPython) {
        $pythonCmd = $customPython
    } else {
        Write-ColorOutput Red "❌ The provided Python executable is not version 3.12 or higher"
        & $customPython --version 2>&1
        exit 1
    }
}

$pythonVersion = & $pythonCmd --version 2>&1
$pythonPath = (Get-Command $pythonCmd -ErrorAction SilentlyContinue).Path
if (-not $pythonPath) { $pythonPath = $pythonCmd }
Write-ColorOutput Green "✅ Using $pythonVersion at: $pythonPath"

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-ColorOutput Yellow "🔧 First-time setup detected..."
    Write-ColorOutput Green "📦 Creating virtual environment..."
    & $pythonCmd -m venv .venv
    
    # Activate virtual environment
    & .\.venv\Scripts\Activate.ps1
    
    Write-ColorOutput Green "📥 Installing requirements..."
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements.txt
    
    Write-ColorOutput Green "✅ Virtual environment created and packages installed"
} else {
    # Check Python version in existing virtual environment
    Write-ColorOutput Blue "🔍 Checking existing virtual environment Python version..."
    if (Test-Path ".venv\Scripts\python.exe") {
        $venvVersion = & .venv\Scripts\python.exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($venvVersion -match "(\d+)\.(\d+)") {
            $venvMajor = [int]$matches[1]
            $venvMinor = [int]$matches[2]
            
            if ($venvMajor -ne 3 -or $venvMinor -lt 12) {
                Write-ColorOutput Red "❌ Existing virtual environment uses Python $venvVersion"
                Write-ColorOutput Yellow "Python 3.12+ is required. Recreating virtual environment..."
                Remove-Item -Path ".venv" -Recurse -Force
                & $pythonCmd -m venv .venv
                & .\.venv\Scripts\Activate.ps1
                Write-ColorOutput Green "📥 Installing requirements..."
                python -m pip install --upgrade pip | Out-Null
                pip install -r requirements.txt
                Write-ColorOutput Green "✅ Virtual environment recreated with $pythonVersion"
            } else {
                Write-ColorOutput Green "✅ Existing virtual environment uses Python $venvVersion"
                # Activate existing virtual environment
                & .\.venv\Scripts\Activate.ps1
            }
        } else {
            # Activate existing virtual environment
            & .\.venv\Scripts\Activate.ps1
        }
    } else {
        # Activate existing virtual environment
        & .\.venv\Scripts\Activate.ps1
    }
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-ColorOutput Red "❌ No .env file found!"
    Write-ColorOutput Yellow "Please create a .env file using .env.example as a guide:"
    Write-ColorOutput Green "  Copy-Item .env.example .env"
    Write-ColorOutput Yellow "Then edit the .env file and add your API keys."
    Write-Host ""
    Write-ColorOutput Red "Exiting..."
    exit 1
}

# Load environment variables from .env file
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Check required environment variables
Write-ColorOutput Blue "🔍 Checking environment variables..."
$missingVars = @()

$openaiKey = [System.Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "Process")
if ([string]::IsNullOrEmpty($openaiKey) -or $openaiKey -like "*your_*") {
    $missingVars += "OPENAI_API_KEY"
}

$anthropicKey = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "Process")
if ([string]::IsNullOrEmpty($anthropicKey) -or $anthropicKey -like "*your_*") {
    $missingVars += "ANTHROPIC_API_KEY"
}

$quixToken = [System.Environment]::GetEnvironmentVariable("QUIX_TOKEN", "Process")
if ([string]::IsNullOrEmpty($quixToken) -or $quixToken -like "*your_*") {
    $missingVars += "QUIX_TOKEN"
}

# Check if QUIX_BASE_URL is missing and add it to .env if needed
$quixBaseUrl = [System.Environment]::GetEnvironmentVariable("QUIX_BASE_URL", "Process")
if ([string]::IsNullOrEmpty($quixBaseUrl)) {
    Write-ColorOutput Yellow "⚠️  QUIX_BASE_URL not found. Adding default to .env..."
    try {
        Add-Content -Path ".env" -Value "QUIX_BASE_URL=https://portal-api.cloud.quix.io"
        Write-ColorOutput Green "✅ Added QUIX_BASE_URL to .env"
        [System.Environment]::SetEnvironmentVariable("QUIX_BASE_URL", "https://portal-api.cloud.quix.io", "Process")
    }
    catch {
        Write-ColorOutput Red "❌ Could not write to .env file"
        Write-ColorOutput Yellow "Please manually add the following line to your .env file:"
        Write-ColorOutput Green "QUIX_BASE_URL=https://portal-api.cloud.quix.io"
        exit 1
    }
}

if ($missingVars.Count -gt 0) {
    Write-ColorOutput Red "❌ Missing or invalid environment variables:"
    foreach ($var in $missingVars) {
        Write-ColorOutput Red "   - $var"
    }
    Write-Host ""
    Write-ColorOutput Yellow "Please edit the .env file and add your API keys:"
    Write-ColorOutput Yellow "   notepad .env  (or use your preferred editor)"
    Write-Host ""
    Write-ColorOutput Yellow "To get the required keys:"
    Write-Host "   • OpenAI API Key: https://platform.openai.com/api-keys"
    Write-Host "   • Anthropic API Key: https://console.anthropic.com/account/keys"
    Write-Host "   • Quix Token: https://portal.cloud.quix.io/settings/tokens"
    exit 1
}

Write-ColorOutput Green "✅ All required environment variables are set"

# Check if Claude Code SDK is installed
Write-ColorOutput Blue "🔍 Checking Claude Code SDK..."
$claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claudeCmd) {
    Write-ColorOutput Yellow "⚠️  Claude Code SDK not found in PATH"
    
    # Check common installation locations
    $claudePaths = @(
        "$env:USERPROFILE\.claude\local\node_modules\.bin\claude.cmd",
        "$env:APPDATA\npm\claude.cmd",
        ".\node_modules\.bin\claude.cmd"
    )
    
    $foundClaude = $false
    foreach ($path in $claudePaths) {
        if (Test-Path $path) {
            Write-ColorOutput Green "✅ Found Claude Code SDK at: $path"
            $foundClaude = $true
            break
        }
    }
    
    if (-not $foundClaude) {
        $response = Read-Host "📦 Claude Code SDK not installed. Would you like to install it? (y/n)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Write-ColorOutput Green "Installing Claude Code SDK..."
            npm install -g claude-code-sdk
        } else {
            Write-ColorOutput Yellow "⚠️  Warning: Some features may not work without Claude Code SDK"
            Write-ColorOutput Yellow "   Install manually with: npm install -g claude-code-sdk"
        }
    }
} else {
    Write-ColorOutput Green "✅ Claude Code SDK is installed"
}

# Create necessary directories if they don't exist
if (-not (Test-Path "working_files\current")) { New-Item -ItemType Directory -Path "working_files\current" -Force | Out-Null }
if (-not (Test-Path "working_files\cache")) { New-Item -ItemType Directory -Path "working_files\cache" -Force | Out-Null }
if (-not (Test-Path "logging")) { New-Item -ItemType Directory -Path "logging" -Force | Out-Null }

# Start the application
Write-Host ""
Write-ColorOutput Green "🚀 Starting Quix Coding Agent..."
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# Run the main application with any passed arguments
& $pythonCmd main.py $args

# Note: PowerShell automatically deactivates the virtual environment when the script ends