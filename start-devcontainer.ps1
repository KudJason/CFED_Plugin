# PowerShell script to start the CFED Dev Container

Write-Host "Starting CFED Development Container setup..." -ForegroundColor Cyan

# Check if Docker Desktop is running
$dockerRunning = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (-not $dockerRunning) {
    Write-Host "Docker Desktop is not running. Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    
    # Wait for Docker to start (up to 60 seconds)
    $timeout = 60
    $elapsed = 0
    $dockerReady = $false
    
    Write-Host "Waiting for Docker to start..." -ForegroundColor Yellow
    while (-not $dockerReady -and $elapsed -lt $timeout) {
        try {
            docker info | Out-Null
            $dockerReady = $true
        }
        catch {
            Start-Sleep -Seconds 5
            $elapsed += 5
            Write-Host "." -NoNewline
        }
    }
    
    if (-not $dockerReady) {
        Write-Host "`nError: Docker did not start within $timeout seconds. Please start Docker Desktop manually and try again." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`nDocker Desktop started successfully!" -ForegroundColor Green
}

# Check if the current directory contains .devcontainer
if (-not (Test-Path ".devcontainer")) {
    Write-Host "Error: The .devcontainer directory is not found in the current location. Please run this script from the root of your CFED_Plugin project." -ForegroundColor Red
    exit 1
}

# Check network connectivity to the Docker registry
Write-Host "Checking network connectivity to Docker registry..." -ForegroundColor Cyan
$networkOk = $false
try {
    $response = Invoke-WebRequest -Uri "https://registry.hub.docker.com/v2/" -UseBasicParsing -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        $networkOk = $true
        Write-Host "Network connectivity to Docker registry confirmed!" -ForegroundColor Green
    }
}
catch {
    Write-Host "Warning: Unable to connect to Docker registry. The container may need to be built locally." -ForegroundColor Yellow
}

# Pull the base image if network is available
if ($networkOk) {
    Write-Host "Pulling the base image mcr.microsoft.com/devcontainers/base:ubuntu-20.04..." -ForegroundColor Cyan
    docker pull mcr.microsoft.com/devcontainers/base:ubuntu-20.04
}

# Open the folder in VS Code with Dev Containers
Write-Host "Opening the project in VS Code with Dev Containers..." -ForegroundColor Cyan
code --folder-uri "vscode-remote://dev-container+$((Get-Location).Path -replace '\\', '/')"

Write-Host "Setup complete! VS Code should be opening with Dev Containers." -ForegroundColor Green
Write-Host "Note: If this is the first time running the container, it may take some time to build." -ForegroundColor Yellow 