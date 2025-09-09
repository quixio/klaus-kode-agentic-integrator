#!/bin/bash

# Quix Coding Agent Startup Script for Linux/Mac
# This script handles environment setup and launches the application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Quix Coding Agent - Klaus Kode     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Function to check Python version
check_python_version() {
    local python_cmd=$1
    if command -v "$python_cmd" &> /dev/null; then
        local version=$($python_cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        if [ "$major" -eq 3 ] && [ "$minor" -ge 12 ]; then
            echo "$python_cmd"
            return 0
        fi
    fi
    return 1
}

# Find suitable Python executable
echo -e "${BLUE}🔍 Checking Python version...${NC}"
PYTHON_CMD=""

# Check common Python commands
for cmd in python3.12 python3.13 python3.14 python3 python; do
    if check_python_version "$cmd"; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Python 3.12 or higher is required but not found!${NC}"
    echo -e "${YELLOW}Current Python versions found:${NC}"
    for cmd in python3 python; do
        if command -v "$cmd" &> /dev/null; then
            $cmd --version
        fi
    done
    echo ""
    echo -e "${YELLOW}Please install Python 3.12 or higher, or provide the path to a valid Python executable:${NC}"
    read -p "Python path (or press Enter to exit): " custom_python
    if [ -z "$custom_python" ]; then
        echo -e "${RED}Exiting...${NC}"
        exit 1
    fi
    if check_python_version "$custom_python"; then
        PYTHON_CMD="$custom_python"
    else
        echo -e "${RED}❌ The provided Python executable is not version 3.12 or higher${NC}"
        $custom_python --version 2>/dev/null || echo "Invalid Python path"
        exit 1
    fi
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
echo -e "${GREEN}✅ Using Python $PYTHON_VERSION at: $(which $PYTHON_CMD)${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}🔧 First-time setup detected...${NC}"
    echo -e "${GREEN}📦 Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv .venv
    
    # Activate virtual environment
    source .venv/bin/activate
    
    echo -e "${GREEN}📥 Installing requirements...${NC}"
    pip install --upgrade pip
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to upgrade pip${NC}"
        exit 1
    fi
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install requirements${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Virtual environment created and packages installed${NC}"
else
    # Check Python version in existing virtual environment
    echo -e "${BLUE}🔍 Checking existing virtual environment Python version...${NC}"
    if [ -f ".venv/bin/python" ]; then
        VENV_PYTHON_VERSION=$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
        VENV_MAJOR=$(echo $VENV_PYTHON_VERSION | cut -d. -f1)
        VENV_MINOR=$(echo $VENV_PYTHON_VERSION | cut -d. -f2)
        
        if [ "$VENV_MAJOR" -ne 3 ] || [ "$VENV_MINOR" -lt 12 ]; then
            echo -e "${RED}❌ Existing virtual environment uses Python $VENV_PYTHON_VERSION${NC}"
            echo -e "${YELLOW}Python 3.12+ is required. Recreating virtual environment...${NC}"
            rm -rf .venv
            $PYTHON_CMD -m venv .venv
            source .venv/bin/activate
            echo -e "${GREEN}📥 Installing requirements...${NC}"
            pip install --upgrade pip
            if [ $? -ne 0 ]; then
                echo -e "${RED}❌ Failed to upgrade pip${NC}"
                exit 1
            fi
            pip install -r requirements.txt
            if [ $? -ne 0 ]; then
                echo -e "${RED}❌ Failed to install requirements${NC}"
                exit 1
            fi
            echo -e "${GREEN}✅ Virtual environment recreated with Python $PYTHON_VERSION${NC}"
        else
            echo -e "${GREEN}✅ Existing virtual environment uses Python $VENV_PYTHON_VERSION${NC}"
            # Activate existing virtual environment
            source .venv/bin/activate
        fi
    else
        # Activate existing virtual environment
        source .venv/bin/activate
    fi
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ No .env file found!${NC}"
    echo -e "${YELLOW}Please create a .env file using .env.example as a guide:${NC}"
    echo -e "${GREEN}  cp .env.example .env${NC}"
    echo -e "${YELLOW}Then edit the .env file and add your API keys.${NC}"
    echo ""
    echo -e "${RED}Exiting...${NC}"
    exit 1
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check required environment variables
echo -e "${BLUE}🔍 Checking environment variables...${NC}"
MISSING_VARS=()

if [ -z "$ANTHROPIC_API_KEY" ] || [[ "$ANTHROPIC_API_KEY" == *"your_"* ]]; then
    MISSING_VARS+=("ANTHROPIC_API_KEY")
fi

if [ -z "$QUIX_TOKEN" ] || [[ "$QUIX_TOKEN" == *"your_"* ]]; then
    MISSING_VARS+=("QUIX_TOKEN")
fi

# Check if QUIX_BASE_URL is missing and add it to .env if needed
if [ -z "$QUIX_BASE_URL" ]; then
    echo -e "${YELLOW}⚠️  QUIX_BASE_URL not found. Adding default to .env...${NC}"
    if echo -e "\nQUIX_BASE_URL=https://portal-api.cloud.quix.io" >> .env 2>/dev/null; then
        echo -e "${GREEN}✅ Added QUIX_BASE_URL to .env${NC}"
        export QUIX_BASE_URL="https://portal-api.cloud.quix.io"
    else
        echo -e "${RED}❌ Could not write to .env file${NC}"
        echo -e "${YELLOW}Please manually add the following line to your .env file:${NC}"
        echo -e "${GREEN}QUIX_BASE_URL=https://portal-api.cloud.quix.io${NC}"
        exit 1
    fi
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing or invalid environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "${RED}   - $var${NC}"
    done
    echo ""
    echo -e "${YELLOW}Please edit the .env file and add your API keys:${NC}"
    echo -e "${YELLOW}   nano .env  (or use your preferred editor)${NC}"
    echo ""
    echo -e "${YELLOW}To get the required keys:${NC}"
    echo -e "   • Anthropic API Key: https://console.anthropic.com/account/keys"
    echo -e "   • Quix Token: https://portal.cloud.quix.io/settings/tokens"
    exit 1
fi

echo -e "${GREEN}✅ All required environment variables are set${NC}"

# Check if Claude Code SDK is installed
echo -e "${BLUE}🔍 Checking Claude Code SDK...${NC}"
if ! command -v claude &> /dev/null; then
    echo -e "${YELLOW}⚠️  Claude Code SDK not found in PATH${NC}"
    
    # Check common installation locations
    CLAUDE_PATHS=(
        "$HOME/.claude/local/node_modules/.bin/claude"
        "$HOME/.npm-global/bin/claude"
        "/usr/local/bin/claude"
        "./node_modules/.bin/claude"
    )
    
    FOUND_CLAUDE=false
    for path in "${CLAUDE_PATHS[@]}"; do
        if [ -f "$path" ]; then
            echo -e "${GREEN}✅ Found Claude Code SDK at: $path${NC}"
            FOUND_CLAUDE=true
            break
        fi
    done
    
    if [ "$FOUND_CLAUDE" = false ]; then
        echo -e "${YELLOW}📦 Claude Code SDK not installed. Would you like to install it? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Installing Claude Code SDK...${NC}"
            npm install -g claude-code-sdk
        else
            echo -e "${YELLOW}⚠️  Warning: Some features may not work without Claude Code SDK${NC}"
            echo -e "${YELLOW}   Install manually with: npm install -g claude-code-sdk${NC}"
        fi
    fi
else
    echo -e "${GREEN}✅ Claude Code SDK is installed${NC}"
fi

# Create necessary directories if they don't exist
mkdir -p working_files/current
mkdir -p working_files/cache
mkdir -p logging

# Start the application
echo ""
echo -e "${GREEN}🚀 Starting Quix Coding Agent...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the main application
python main.py "$@"

# Deactivate virtual environment on exit
deactivate 2>/dev/null || true