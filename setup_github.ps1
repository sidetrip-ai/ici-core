# Check if GitHub CLI is installed
try {
    $ghVersion = gh --version
    Write-Host "GitHub CLI is installed: $ghVersion"
} catch {
    Write-Host "GitHub CLI is not installed or not in PATH. Please run install_gh.ps1 first."
    exit 1
}

# Authenticate with GitHub using token
Write-Host "Please follow these steps to authenticate:"
Write-Host "1. Go to https://github.com/settings/tokens"
Write-Host "2. Click 'Generate new token'"
Write-Host "3. Give it a name (e.g., 'Cursor')"
Write-Host "4. Select these scopes:"
Write-Host "   - repo"
Write-Host "   - workflow"
Write-Host "   - write:packages"
Write-Host "   - delete:packages"
Write-Host "   - admin:org"
Write-Host "   - admin:public_key"
Write-Host "   - admin:repo_hook"
Write-Host "   - admin:org_hook"
Write-Host "   - gist"
Write-Host "   - notifications"
Write-Host "   - user"
Write-Host "   - delete_repo"
Write-Host "   - write:discussion"
Write-Host "   - admin:enterprise"
Write-Host "5. Click 'Generate token'"
Write-Host "6. Copy the token and paste it below:"

$token = Read-Host "Enter your GitHub token"
gh auth login --with-token $token

# Test GitHub connection
try {
    $userInfo = gh api user
    Write-Host "Successfully connected to GitHub as: $($userInfo.login)"
    
    # Test repository access
    $repoInfo = gh repo view iRahulJadhav/ici-core
    Write-Host "Successfully accessed repository: ici-core"
    
    # Configure Git
    git config --global user.name "iRahulJadhav"
    git config --global user.email "rahuljrark@gmail.com"
    
    Write-Host "GitHub setup completed successfully!"
    Write-Host "You can now use GitHub features in Cursor."
} catch {
    Write-Host "Error: $_"
    Write-Host "Please check your GitHub authentication and try again."
} 