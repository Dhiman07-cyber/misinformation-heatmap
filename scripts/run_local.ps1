# Local Development Setup Script (PowerShell)
# Starts all services required for the misinformation heatmap application

param(
    [string]$Mode = "local",
    [switch]$SkipDeps,
    [switch]$SkipDb,
    [switch]$SkipFrontend,
    [switch]$Verbose,
    [switch]$Detached,
    [switch]$Stop,
    [switch]$Status,
    [switch]$Logs,
    [switch]$Help
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"
$Purple = "Magenta"

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DataDir = Join-Path $ProjectRoot "data"
$LogsDir = Join-Path $ProjectRoot "logs"

function Write-Header {
    param([string]$Message)
    Write-Host "================================" -ForegroundColor $Purple
    Write-Host $Message -ForegroundColor $Purple
    Write-Host "================================" -ForegroundColor $Purple
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

function Show-Usage {
    Write-Host "Usage: .\run_local.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Help               Show this help message"
    Write-Host "  -Mode MODE          Set deployment mode (local|cloud) [default: local]"
    Write-Host "  -SkipDeps           Skip dependency installation"
    Write-Host "  -SkipDb             Skip database initialization"
    Write-Host "  -SkipFrontend       Skip frontend serving"
    Write-Host "  -Verbose            Enable verbose output"
    Write-Host "  -Detached           Run services in detached mode"
    Write-Host "  -Stop               Stop all running services"
    Write-Host "  -Status             Show status of running services"
    Write-Host "  -Logs               Show logs from all services"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_local.ps1                     Start all services in local mode"
    Write-Host "  .\run_local.ps1 -Mode cloud         Start with cloud configuration"
    Write-Host "  .\run_local.ps1 -SkipDeps           Start without installing dependencies"
    Write-Host "  .\run_local.ps1 -Detached           Start services in background"
    Write-Host "  .\run_local.ps1 -Stop               Stop all running services"
}

function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Status "Python version: $pythonVersion"
    } catch {
        Write-Error "Python is not installed. Please install Python 3.8 or higher."
        exit 1
    }
    
    # Check pip
    try {
        pip --version | Out-Null
    } catch {
        Write-Error "pip is not installed. Please install pip."
        exit 1
    }
    
    # Check Node.js (for frontend)
    if (-not $SkipFrontend) {
        try {
            $nodeVersion = node --version
            Write-Status "Node.js version: $nodeVersion"
        } catch {
            Write-Warning "Node.js not found. Frontend serving will be disabled."
            $script:SkipFrontend = $true
        }
    }
    
    # Check required directories
    $requiredDirs = @($BackendDir, $FrontendDir, $DataDir)
    foreach ($dir in $requiredDirs) {
        if (-not (Test-Path $dir)) {
            Write-Error "Required directory not found: $dir"
            exit 1
        }
    }
    
    Write-Success "Prerequisites check completed"
}

function New-Directories {
    Write-Status "Creating necessary directories..."
    
    @($LogsDir, $DataDir, (Join-Path $ProjectRoot ".env")) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
        }
    }
    
    Write-Success "Directories created"
}

function Install-Dependencies {
    if ($SkipDeps) {
        Write-Warning "Skipping dependency installation"
        return
    }
    
    Write-Status "Installing Python dependencies..."
    
    Set-Location $BackendDir
    
    # Create virtual environment if it doesn't exist
    if (-not (Test-Path "venv")) {
        Write-Status "Creating Python virtual environment..."
        python -m venv venv
    }
    
    # Activate virtual environment
    & ".\venv\Scripts\Activate.ps1"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
    } else {
        Write-Error "requirements.txt not found in backend directory"
        exit 1
    }
    
    Write-Success "Python dependencies installed"
    
    # Install frontend dependencies if needed
    if (-not $SkipFrontend -and (Test-Path (Join-Path $FrontendDir "package.json"))) {
        Write-Status "Installing frontend dependencies..."
        Set-Location $FrontendDir
        npm install
        Write-Success "Frontend dependencies installed"
    }
}

function Initialize-Database {
    if ($SkipDb) {
        Write-Warning "Skipping database initialization"
        return
    }
    
    Write-Status "Initializing database..."
    
    Set-Location $BackendDir
    & ".\venv\Scripts\Activate.ps1"
    
    # Run database initialization script
    if (Test-Path "init_db.py") {
        python init_db.py --mode $Mode
        Write-Success "Database initialized"
    } else {
        Write-Warning "Database initialization script not found, skipping..."
    }
}

function Set-Environment {
    Write-Status "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) {
        Write-Status "Creating .env file..."
        
        $envContent = @"
# Misinformation Heatmap Configuration
MODE=$Mode
DEBUG=true
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=sqlite:///./data/heatmap.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# NLP Configuration
HUGGINGFACE_TOKEN=
MODEL_CACHE_DIR=./models

# Pub/Sub Configuration (Local)
PUBSUB_EMULATOR_HOST=localhost:8085
PUBSUB_PROJECT_ID=misinformation-heatmap-local

# Google Cloud Configuration (for cloud mode)
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=

# IBM Watson Configuration (for cloud mode)
WATSON_DISCOVERY_API_KEY=
WATSON_DISCOVERY_URL=

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
"@
        
        Set-Content -Path $envFile -Value $envContent
        Write-Success ".env file created"
    } else {
        Write-Status ".env file already exists"
    }
}

function Start-PubSubEmulator {
    if ($Mode -ne "local") {
        return
    }
    
    Write-Status "Starting Pub/Sub emulator..."
    
    # Check if gcloud is installed
    try {
        gcloud version | Out-Null
    } catch {
        Write-Warning "gcloud CLI not found. Installing Pub/Sub emulator..."
        pip install google-cloud-pubsub
    }
    
    # Start emulator
    $pubsubLog = Join-Path $LogsDir "pubsub-emulator.log"
    
    if ($Detached) {
        $pubsubProcess = Start-Process -FilePath "gcloud" -ArgumentList "beta", "emulators", "pubsub", "start", "--host-port=localhost:8085" -RedirectStandardOutput $pubsubLog -RedirectStandardError $pubsubLog -PassThru
        $pubsubProcess.Id | Out-File (Join-Path $LogsDir "pubsub.pid")
        Write-Success "Pub/Sub emulator started (PID: $($pubsubProcess.Id))"
    } else {
        Write-Status "Starting Pub/Sub emulator (press Ctrl+C to stop all services)"
        $pubsubProcess = Start-Process -FilePath "gcloud" -ArgumentList "beta", "emulators", "pubsub", "start", "--host-port=localhost:8085" -PassThru
        $pubsubProcess.Id | Out-File (Join-Path $LogsDir "pubsub.pid")
    }
    
    # Wait for emulator to start
    Start-Sleep -Seconds 3
    
    # Create topics and subscriptions
    $env:PUBSUB_EMULATOR_HOST = "localhost:8085"
    
    $createTopicsScript = @"
import os
from google.cloud import pubsub_v1

os.environ['PUBSUB_EMULATOR_HOST'] = 'localhost:8085'
project_id = 'misinformation-heatmap-local'

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Create topics
topics = ['events-raw', 'events-processed', 'events-validated']
for topic_name in topics:
    topic_path = publisher.topic_path(project_id, topic_name)
    try:
        publisher.create_topic(request={'name': topic_path})
        print(f'Created topic: {topic_name}')
    except Exception as e:
        print(f'Topic {topic_name} may already exist: {e}')

# Create subscriptions
subscriptions = [
    ('events-raw', 'events-raw-sub'),
    ('events-processed', 'events-processed-sub'),
    ('events-validated', 'events-validated-sub')
]

for topic_name, sub_name in subscriptions:
    topic_path = publisher.topic_path(project_id, topic_name)
    subscription_path = subscriber.subscription_path(project_id, sub_name)
    try:
        subscriber.create_subscription(
            request={'name': subscription_path, 'topic': topic_path}
        )
        print(f'Created subscription: {sub_name}')
    except Exception as e:
        print(f'Subscription {sub_name} may already exist: {e}')
"@
    
    python -c $createTopicsScript
}

function Start-Backend {
    Write-Status "Starting backend API server..."
    
    Set-Location $BackendDir
    & ".\venv\Scripts\Activate.ps1"
    
    $apiLog = Join-Path $LogsDir "api.log"
    
    if ($Detached) {
        $apiProcess = Start-Process -FilePath "python" -ArgumentList "api.py" -RedirectStandardOutput $apiLog -RedirectStandardError $apiLog -PassThru
        $apiProcess.Id | Out-File (Join-Path $LogsDir "api.pid")
        Write-Success "Backend API started (PID: $($apiProcess.Id))"
    } else {
        Write-Status "Starting backend API (press Ctrl+C to stop all services)"
        $apiProcess = Start-Process -FilePath "python" -ArgumentList "api.py" -PassThru
        $apiProcess.Id | Out-File (Join-Path $LogsDir "api.pid")
    }
}

function Start-Frontend {
    if ($SkipFrontend) {
        Write-Warning "Skipping frontend server"
        return
    }
    
    Write-Status "Starting frontend server..."
    
    Set-Location $FrontendDir
    
    $frontendLog = Join-Path $LogsDir "frontend.log"
    
    # Use Python's built-in HTTP server for simplicity
    if ($Detached) {
        $frontendProcess = Start-Process -FilePath "python" -ArgumentList "-m", "http.server", "3000" -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendLog -PassThru
        $frontendProcess.Id | Out-File (Join-Path $LogsDir "frontend.pid")
        Write-Success "Frontend server started (PID: $($frontendProcess.Id))"
    } else {
        Write-Status "Starting frontend server (press Ctrl+C to stop all services)"
        $frontendProcess = Start-Process -FilePath "python" -ArgumentList "-m", "http.server", "3000" -PassThru
        $frontendProcess.Id | Out-File (Join-Path $LogsDir "frontend.pid")
    }
}

function Test-HealthChecks {
    Write-Status "Performing health checks..."
    
    # Wait a moment for services to start
    Start-Sleep -Seconds 5
    
    # Check backend API
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing | Out-Null
        Write-Success "Backend API is healthy"
    } catch {
        Write-Warning "Backend API health check failed"
    }
    
    # Check frontend
    if (-not $SkipFrontend) {
        try {
            Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing | Out-Null
            Write-Success "Frontend server is healthy"
        } catch {
            Write-Warning "Frontend server health check failed"
        }
    }
    
    # Check Pub/Sub emulator (local mode only)
    if ($Mode -eq "local") {
        try {
            Invoke-WebRequest -Uri "http://localhost:8085" -UseBasicParsing | Out-Null
            Write-Success "Pub/Sub emulator is healthy"
        } catch {
            Write-Warning "Pub/Sub emulator health check failed"
        }
    }
}

function Show-Status {
    Write-Header "Service Status"
    
    # Check API
    $apiPidFile = Join-Path $LogsDir "api.pid"
    if (Test-Path $apiPidFile) {
        $apiPid = Get-Content $apiPidFile
        if (Get-Process -Id $apiPid -ErrorAction SilentlyContinue) {
            Write-Success "Backend API running (PID: $apiPid)"
        } else {
            Write-Warning "Backend API not running (stale PID file)"
        }
    } else {
        Write-Warning "Backend API not started"
    }
    
    # Check frontend
    $frontendPidFile = Join-Path $LogsDir "frontend.pid"
    if (Test-Path $frontendPidFile) {
        $frontendPid = Get-Content $frontendPidFile
        if (Get-Process -Id $frontendPid -ErrorAction SilentlyContinue) {
            Write-Success "Frontend server running (PID: $frontendPid)"
        } else {
            Write-Warning "Frontend server not running (stale PID file)"
        }
    } else {
        Write-Warning "Frontend server not started"
    }
    
    # Check Pub/Sub emulator
    $pubsubPidFile = Join-Path $LogsDir "pubsub.pid"
    if (Test-Path $pubsubPidFile) {
        $pubsubPid = Get-Content $pubsubPidFile
        if (Get-Process -Id $pubsubPid -ErrorAction SilentlyContinue) {
            Write-Success "Pub/Sub emulator running (PID: $pubsubPid)"
        } else {
            Write-Warning "Pub/Sub emulator not running (stale PID file)"
        }
    } else {
        Write-Warning "Pub/Sub emulator not started"
    }
}

function Show-Logs {
    Write-Header "Service Logs"
    
    $apiLog = Join-Path $LogsDir "api.log"
    if (Test-Path $apiLog) {
        Write-Host "=== Backend API Logs ===" -ForegroundColor $Blue
        Get-Content $apiLog -Tail 20
        Write-Host ""
    }
    
    $frontendLog = Join-Path $LogsDir "frontend.log"
    if (Test-Path $frontendLog) {
        Write-Host "=== Frontend Server Logs ===" -ForegroundColor $Blue
        Get-Content $frontendLog -Tail 20
        Write-Host ""
    }
    
    $pubsubLog = Join-Path $LogsDir "pubsub-emulator.log"
    if (Test-Path $pubsubLog) {
        Write-Host "=== Pub/Sub Emulator Logs ===" -ForegroundColor $Blue
        Get-Content $pubsubLog -Tail 20
        Write-Host ""
    }
}

function Stop-Services {
    Write-Header "Stopping Services"
    
    # Stop API
    $apiPidFile = Join-Path $LogsDir "api.pid"
    if (Test-Path $apiPidFile) {
        $apiPid = Get-Content $apiPidFile
        if (Get-Process -Id $apiPid -ErrorAction SilentlyContinue) {
            Stop-Process -Id $apiPid -Force
            Write-Success "Backend API stopped"
        }
        Remove-Item $apiPidFile -Force
    }
    
    # Stop frontend
    $frontendPidFile = Join-Path $LogsDir "frontend.pid"
    if (Test-Path $frontendPidFile) {
        $frontendPid = Get-Content $frontendPidFile
        if (Get-Process -Id $frontendPid -ErrorAction SilentlyContinue) {
            Stop-Process -Id $frontendPid -Force
            Write-Success "Frontend server stopped"
        }
        Remove-Item $frontendPidFile -Force
    }
    
    # Stop Pub/Sub emulator
    $pubsubPidFile = Join-Path $LogsDir "pubsub.pid"
    if (Test-Path $pubsubPidFile) {
        $pubsubPid = Get-Content $pubsubPidFile
        if (Get-Process -Id $pubsubPid -ErrorAction SilentlyContinue) {
            Stop-Process -Id $pubsubPid -Force
            Write-Success "Pub/Sub emulator stopped"
        }
        Remove-Item $pubsubPidFile -Force
    }
    
    Write-Success "All services stopped"
}

function Show-ServiceUrls {
    Write-Header "Service URLs"
    Write-Host "Backend API:      http://localhost:8000" -ForegroundColor $Green
    Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor $Green
    Write-Host "Health Check:     http://localhost:8000/health" -ForegroundColor $Green
    
    if (-not $SkipFrontend) {
        Write-Host "Frontend:         http://localhost:3000" -ForegroundColor $Green
    }
    
    if ($Mode -eq "local") {
        Write-Host "Pub/Sub Emulator:  http://localhost:8085" -ForegroundColor $Green
    }
    
    Write-Host ""
    Write-Host "Logs Directory:   $LogsDir" -ForegroundColor $Yellow
    Write-Host "Data Directory:   $DataDir" -ForegroundColor $Yellow
}

# Main execution
function Main {
    if ($Help) {
        Show-Usage
        return
    }
    
    if ($Stop) {
        Stop-Services
        return
    }
    
    if ($Status) {
        Show-Status
        return
    }
    
    if ($Logs) {
        Show-Logs
        return
    }
    
    Write-Header "Misinformation Heatmap - Local Development Setup"
    
    Test-Prerequisites
    New-Directories
    Set-Environment
    Install-Dependencies
    Initialize-Database
    
    # Start services
    if ($Mode -eq "local") {
        Start-PubSubEmulator
    }
    
    Start-Backend
    Start-Frontend
    
    # Perform health checks
    Test-HealthChecks
    
    # Show service information
    Show-ServiceUrls
    
    if ($Detached) {
        Write-Success "All services started in detached mode"
        Write-Status "Use '.\run_local.ps1 -Status' to check service status"
        Write-Status "Use '.\run_local.ps1 -Logs' to view service logs"
        Write-Status "Use '.\run_local.ps1 -Stop' to stop all services"
    } else {
        Write-Success "All services started successfully!"
        Write-Status "Press Ctrl+C to stop all services"
        
        # Wait for user interrupt
        try {
            while ($true) {
                Start-Sleep -Seconds 1
            }
        } finally {
            if (-not $Detached) {
                Write-Status "Cleaning up..."
                Stop-Services
            }
        }
    }
}

# Run main function
Main