#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Repository details
REPO_URL="https://github.com/sidetrip-ai/ici-core.git"
REPO_NAME="ici-core"

# Function to check if git is installed
function check_git() {
    if ! command -v git &> /dev/null; then
        echo -e "${RED}Git is not installed.${NC}"
        echo -e "${YELLOW}Please install git first:${NC}"
        echo -e "  For Ubuntu/Debian: ${GREEN}sudo apt-get install git${NC}"
        echo -e "  For macOS: ${GREEN}brew install git${NC}"
        echo -e "  For Windows: ${GREEN}https://git-scm.com/download/win${NC}"
        exit 1
    fi
}

# Function to check if Python is installed
function check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python 3 is not installed.${NC}"
        echo -e "${YELLOW}Please install Python 3 first:${NC}"
        echo -e "  For Ubuntu/Debian: ${GREEN}sudo apt-get install python3 python3-venv${NC}"
        echo -e "  For macOS: ${GREEN}brew install python3${NC}"
        echo -e "  For Windows: ${GREEN}https://www.python.org/downloads/${NC}"
        exit 1
    fi
}

# Function to find repository location
function find_repo() {
    # First check current directory
    if [ -d "$REPO_NAME" ]; then
        echo "$(pwd)/$REPO_NAME"
        return 0
    fi
    
    # Then check parent directory
    if [ -d "../$REPO_NAME" ]; then
        echo "$(cd .. && pwd)/$REPO_NAME"
        return 0
    fi
    
    # Then check home directory
    if [ -d "$HOME/$REPO_NAME" ]; then
        echo "$HOME/$REPO_NAME"
        return 0
    fi
    
    return 1
}

# Function to check if repository is already cloned
function check_repo() {
    local repo_path=$(find_repo)
    
    if [ ! -z "$repo_path" ]; then
        echo -e "${GREEN}Repository found at: $repo_path${NC}"
        cd "$repo_path"
        return 0
    else
        echo -e "${YELLOW}Repository not found. Cloning from $REPO_URL...${NC}"
        git clone "$REPO_URL"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Failed to clone repository.${NC}"
            exit 1
        fi
        cd "$REPO_NAME"
        return 1
    fi
}

# Main execution
echo -e "${YELLOW}========== ICI Core Installation Script ==========${NC}"

# Check if git is installed
check_git

# Check if Python is installed
check_python

# Check if repository exists and clone if needed
check_repo

# Run the setup script
echo -e "${YELLOW}Running setup script...${NC}"
if [ -f "./setup.sh" ]; then
    bash ./setup.sh
else
    echo -e "${RED}Setup script not found.${NC}"
    exit 1
fi 