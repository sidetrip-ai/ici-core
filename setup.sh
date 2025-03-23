#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if the script is being run from the project root directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found.${NC}"
    echo -e "${YELLOW}Please run this script from the project root directory.${NC}"
    exit 1
fi

# Default virtual environment directory name
VENV_DIR="venv"

# Function to check if running in an active virtual environment
function check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}No active virtual environment detected.${NC}"
        return 1
    else
        echo -e "${GREEN}Active virtual environment detected: $VIRTUAL_ENV${NC}"
        return 0
    fi
}

# Function to create and activate virtual environment if it doesn't exist
function setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment in $VENV_DIR...${NC}"
        python3 -m venv $VENV_DIR
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to create virtual environment.${NC}"
            echo -e "${YELLOW}Please ensure python3 and venv are installed.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Virtual environment already exists in $VENV_DIR.${NC}"
    fi

    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to activate virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment activated!${NC}"
}

# Function to install dependencies
function install_dependencies() {
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install dependencies.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Dependencies installed successfully!${NC}"
}

# Main execution
echo -e "${YELLOW}========== ICI Core Setup Script ==========${NC}"

# Check if we're in a virtual environment
if ! check_venv; then
    setup_venv
fi

# Install dependencies
install_dependencies

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${YELLOW}You can now run the application.${NC}" 