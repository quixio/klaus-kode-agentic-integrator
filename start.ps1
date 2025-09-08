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

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-ColorOutput Yellow "🔧 First-time setup detected..."
    Write-ColorOutput Green "📦 Creating virtual environment..."
    python -m venv .venv
    
    # Activate virtual environment
    & .\.venv\Scripts\Activate.ps1
    
    Write-ColorOutput Green "📥 Installing requirements..."
    python -m pip install --upgrade pip | Out-Null
    pip install -r requirements.txt
    
    Write-ColorOutput Green "✅ Virtual environment created and packages installed"
} else {
    # Activate existing virtual environment
    & .\.venv\Scripts\Activate.ps1
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-ColorOutput Yellow "⚠️  No .env file found. Creating from template..."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-ColorOutput Green "✅ Created .env file from template"
    } else {
        # Create a basic .env file
        @"
# Required API Keys - Please fill these in
ANTHROPIC_API_KEY=your_anthropic_api_key_here
QUIX_TOKEN=your_quix_token_here
QUIX_BASE_URL=https://portal-api.cloud.quix.io

# Optional settings
# VERBOSE_MODE=false
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-ColorOutput Green "✅ Created .env template"
    }
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

$anthropicKey = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "Process")
if ([string]::IsNullOrEmpty($anthropicKey) -or $anthropicKey -like "*your_*") {
    $missingVars += "ANTHROPIC_API_KEY"
}

$quixToken = [System.Environment]::GetEnvironmentVariable("QUIX_TOKEN", "Process")
if ([string]::IsNullOrEmpty($quixToken) -or $quixToken -like "*your_*") {
    $missingVars += "QUIX_TOKEN"
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
    Write-Host "   • Anthropic API Key: https://console.anthropic.com/account/keys"
    Write-Host "   • Quix Token: https://portal.cloud.quix.io/settings/tokens"
    exit 1
}

# Set default QUIX_BASE_URL if not set
$quixBaseUrl = [System.Environment]::GetEnvironmentVariable("QUIX_BASE_URL", "Process")
if ([string]::IsNullOrEmpty($quixBaseUrl)) {
    [System.Environment]::SetEnvironmentVariable("QUIX_BASE_URL", "https://portal-api.cloud.quix.io", "Process")
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
python main.py $args

# Note: PowerShell automatically deactivates the virtual environment when the script ends