# Run as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {  
    $arguments = "& '" + $myinvocation.mycommand.definition + "'"
    Start-Process powershell -Verb runAs -ArgumentList $arguments
    Break
}

# Download GitHub CLI installer
$url = "https://github.com/cli/cli/releases/download/v2.69.0/gh_2.69.0_windows_amd64.msi"
$output = "gh_installer.msi"
Write-Host "Downloading GitHub CLI..."
Invoke-WebRequest -Uri $url -OutFile $output

# Install GitHub CLI
Write-Host "Installing GitHub CLI..."
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i $output /quiet" -Wait

# Add to PATH
$ghPath = "C:\Program Files\GitHub CLI"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if (-not $currentPath.Contains($ghPath)) {
    $newPath = $currentPath + ";" + $ghPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
}

# Clean up installer
Remove-Item $output -ErrorAction SilentlyContinue

# Configure Git
git config --global user.name "iRahulJadhav"
git config --global user.email "rahuljrark@gmail.com"

Write-Host "GitHub CLI installed and configured successfully!"
Write-Host "Please restart Cursor to apply changes." 