#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default virtual environment directory name
VENV_DIR="venv"

# Check if the script is being run from the project root directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found.${NC}"
    echo -e "${YELLOW}Please run this script from the project root directory.${NC}"
    exit 1
fi

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

# Function to verify if a package is installed with correct version
function verify_package() {
    local package=$1
    local required_version=$2
    
    # Check if package is installed
    if ! pip show "$package" > /dev/null 2>&1; then
        echo -e "${RED}Package $package is not installed.${NC}"
        return 1
    fi
    
    # If version is specified, check if it meets the requirement
    if [ ! -z "$required_version" ]; then
        local installed_version=$(pip show "$package" | grep "Version:" | cut -d' ' -f2)
        if [ -z "$installed_version" ]; then
            echo -e "${RED}Could not determine installed version of $package.${NC}"
            return 1
        fi
        
        # Compare versions using sort -V (version sort)
        # If installed version is greater than or equal to required version, it should be last in sorted order
        if ! printf "%s\n%s\n" "$required_version" "$installed_version" | sort -V | tail -n1 | grep -q "$installed_version"; then
            echo -e "${RED}Package $package version $installed_version is older than required version $required_version.${NC}"
            return 1
        fi
    fi
    
    return 0
}

# Function to install dependencies
function install_dependencies() {
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -q -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install dependencies.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Dependencies installed successfully!${NC}"
}

# Function to verify all dependencies
function verify_dependencies() {
    echo -e "${YELLOW}Verifying installed dependencies...${NC}"
    
    local missing_packages=()
    local version_mismatches=()
    
    # Read requirements.txt and check each package
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ $line =~ ^#.*$ ]] && continue
        [[ -z $line ]] && continue
        
        # Extract package name and version
        if [[ $line =~ ^([^>=]+)(>=)?([^>=]+)?$ ]]; then
            package="${BASH_REMATCH[1]}"
            package=$(echo "$package" | tr -d ' ')  # Remove any whitespace
            version="${BASH_REMATCH[3]}"
            
            if ! pip show "$package" > /dev/null 2>&1; then
                missing_packages+=("$line")
            elif [ ! -z "$version" ]; then
                local installed_version=$(pip show "$package" | grep "Version:" | cut -d' ' -f2)
                if [ -z "$installed_version" ] || ! printf "%s\n%s\n" "$version" "$installed_version" | sort -V | tail -n1 | grep -q "$installed_version"; then
                    version_mismatches+=("$line")
                fi
            fi
        fi
    done < requirements.txt
    
    # Report issues if any
    if [ ${#missing_packages[@]} -ne 0 ] || [ ${#version_mismatches[@]} -ne 0 ]; then
        echo -e "${RED}Some dependencies are missing or have incorrect versions.${NC}"
        
        if [ ${#missing_packages[@]} -ne 0 ]; then
            echo -e "${YELLOW}Missing packages:${NC}"
            for pkg in "${missing_packages[@]}"; do
                echo -e "  - $pkg"
            done
        fi
        
        if [ ${#version_mismatches[@]} -ne 0 ]; then
            echo -e "${YELLOW}Packages with version mismatches:${NC}"
            for pkg in "${version_mismatches[@]}"; do
                echo -e "  - $pkg"
            done
        fi
        
        echo -e "${YELLOW}Please run the following command to install/upgrade packages:${NC}"
        echo -e "pip install -r requirements.txt"
        exit 1
    fi
    
    echo -e "${GREEN}All dependencies verified successfully!${NC}"
}

# Main execution
echo -e "${YELLOW}========== ICI Core Setup Script ==========${NC}"

# Check if we're in a virtual environment
if ! check_venv; then
    setup_venv
fi

# Install dependencies
install_dependencies

# Verify all dependencies are installed
verify_dependencies

echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${YELLOW}You can now run the application.${NC}"

# Ensure virtual environment remains activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source "$VENV_DIR/bin/activate"
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to activate virtual environment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment activated!${NC}"
fi

# Print next steps
echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. To activate the virtual environment in a new terminal:"
echo -e "   ${GREEN}source venv/bin/activate${NC}"
echo -e "2. To run the Telegram Application:"
echo -e "   ${GREEN}python main.py${NC}"
echo -e "\n${YELLOW}Note: Make sure you have configured your Telegram API credentials in the config file before running the application.${NC}" 