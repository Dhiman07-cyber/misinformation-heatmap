# End-to-End Test Runner Script (PowerShell)
# Runs comprehensive end-to-end tests for the misinformation heatmap system

param(
    [string]$Mode = "local",
    [string]$OutputFile = "",
    [switch]$Verbose = $false,
    [switch]$NoCleanup = $false,
    [switch]$NoHeadless = $false,
    [int]$Timeout = 300,
    [switch]$Help = $false
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$Magenta = "Magenta"

function Write-Header {
    param([string]$Message)
    Write-Host "================================" -ForegroundColor $Magenta
    Write-Host $Message -ForegroundColor $Magenta
    Write-Host "================================" -ForegroundColor $Magenta
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
    Write-Host "Usage: .\run_e2e_tests.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Mode MODE              Testing mode: local or cloud (default: local)"
    Write-Host "  -OutputFile FILE        Output file for test results (JSON)"
    Write-Host "  -Verbose               Enable verbose output"
    Write-Host "  -NoCleanup             Don't cleanup test data after tests"
    Write-Host "  -NoHeadless            Run browser tests in visible mode"
    Write-Host "  -Timeout SECONDS       Test timeout in seconds (default: 300)"
    Write-Host "  -Help                  Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run_e2e_tests.ps1 -Mode local -Verbose"
    Write-Host "  .\run_e2e_tests.ps1 -Mode cloud -OutputFile results.json"
    Write-Host "  .\run_e2e_tests.ps1 -NoHeadless -Timeout 600"
}

function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Python is not installed or not in PATH."
            exit 1
        }
        Write-Status "Python found: $pythonVersion"
    }
    catch {
        Write-Error "Python is not installed."
        exit 1
    }
    
    # Check if we're in the right directory
    if (-not (Test-Path "..\..\backend\api.py")) {
        Write-Error "Please run this script from the tests\e2e directory."
        exit 1
    }
    
    # Install Python dependencies
    Write-Status "Installing Python dependencies..."
    try {
        pip install -r requirements.txt | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install Python dependencies."
            exit 1
        }
    }
    catch {
        Write-Error "Failed to install Python dependencies."
        exit 1
    }
    
    # Check Chrome for Selenium
    $chromeFound = $false
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
    )
    
    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            Write-Status "Chrome found at: $path"
            $chromeFound = $true
            break
        }
    }
    
    if (-not $chromeFound) {
        Write-Warning "Chrome not found. Browser tests may be skipped."
    }
    
    Write-Success "Prerequisites check completed"
}

function Initialize-TestEnvironment {
    Write-Status "Setting up test environment..."
    
    # Set environment variables
    $env:MODE = $Mode
    $env:PYTHONPATH = "..\..\backend;$env:PYTHONPATH"
    
    if ($NoHeadless) {
        $env:SELENIUM_HEADLESS = "false"
    } else {
        $env:SELENIUM_HEADLESS = "true"
    }
    
    # Create test directories
    if (-not (Test-Path "test_data")) {
        New-Item -ItemType Directory -Path "test_data" | Out-Null
    }
    if (-not (Test-Path "test_results")) {
        New-Item -ItemType Directory -Path "test_results" | Out-Null
    }
    
    Write-Success "Test environment setup completed"
}

function Start-Services {
    Write-Status "Starting services for testing..."
    
    if ($Mode -eq "local") {
        Write-Status "Starting local backend service..."
        
        # Start backend in background
        $backendProcess = Start-Process -FilePath "python" -ArgumentList "..\..\backend\api.py" -PassThru -WindowStyle Hidden
        $script:BackendPID = $backendProcess.Id
        
        # Start frontend in background
        Push-Location "..\..\frontend"
        $frontendProcess = Start-Process -FilePath "python" -ArgumentList "-m", "http.server", "3000" -PassThru -WindowStyle Hidden
        $script:FrontendPID = $frontendProcess.Id
        Pop-Location
        
        # Wait for services to start
        Write-Status "Waiting for services to start..."
        Start-Sleep -Seconds 10
        
        # Check if services are running
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -ne 200) {
                Write-Error "Backend service failed to start"
                Stop-Services
                exit 1
            }
        }
        catch {
            Write-Error "Backend service failed to start"
            Stop-Services
            exit 1
        }
        
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -ne 200) {
                Write-Error "Frontend service failed to start"
                Stop-Services
                exit 1
            }
        }
        catch {
            Write-Error "Frontend service failed to start"
            Stop-Services
            exit 1
        }
        
        Write-Success "Local services started successfully"
    }
    else {
        Write-Status "Using cloud services (assuming they are already running)"
    }
}

function Stop-Services {
    if ($Mode -eq "local") {
        Write-Status "Cleaning up local services..."
        
        if ($script:BackendPID) {
            try {
                Stop-Process -Id $script:BackendPID -Force -ErrorAction SilentlyContinue
            }
            catch {
                # Process may have already stopped
            }
        }
        
        if ($script:FrontendPID) {
            try {
                Stop-Process -Id $script:FrontendPID -Force -ErrorAction SilentlyContinue
            }
            catch {
                # Process may have already stopped
            }
        }
        
        # Kill any remaining processes
        Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*api.py*" } | Stop-Process -Force -ErrorAction SilentlyContinue
        Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*http.server*" } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        Write-Success "Services cleanup completed"
    }
}

function Invoke-Tests {
    Write-Status "Running end-to-end tests..."
    
    # Prepare test command
    $testArgs = @("test_end_to_end.py", "--mode", $Mode)
    
    if ($Verbose) {
        $testArgs += "--verbose"
    }
    
    if ($OutputFile) {
        $testArgs += @("--output", "test_results\$OutputFile")
    }
    
    Write-Status "Executing: python $($testArgs -join ' ')"
    
    # Run tests with timeout
    try {
        $job = Start-Job -ScriptBlock {
            param($args)
            Set-Location $using:PWD
            $env:MODE = $using:Mode
            $env:PYTHONPATH = $using:env:PYTHONPATH
            $env:SELENIUM_HEADLESS = $using:env:SELENIUM_HEADLESS
            & python @args
        } -ArgumentList $testArgs
        
        $completed = Wait-Job -Job $job -Timeout $Timeout
        
        if ($completed) {
            $result = Receive-Job -Job $job
            $exitCode = $job.State -eq "Completed" ? 0 : 1
            Remove-Job -Job $job
            
            if ($exitCode -eq 0) {
                Write-Success "All tests completed successfully"
                return 0
            }
            else {
                Write-Error "Tests failed"
                return 1
            }
        }
        else {
            Stop-Job -Job $job
            Remove-Job -Job $job
            Write-Error "Tests timed out after $Timeout seconds"
            return 124
        }
    }
    catch {
        Write-Error "Failed to run tests: $_"
        return 1
    }
}

function Remove-TestData {
    if (-not $NoCleanup) {
        Write-Status "Cleaning up test data..."
        
        # Remove test database if it exists
        if (Test-Path "..\..\data\test_heatmap.db") {
            Remove-Item "..\..\data\test_heatmap.db" -Force
        }
        
        # Clean up any temporary files
        Get-ChildItem -Path "test_data" -Filter "temp_*" -Recurse | Remove-Item -Force -Recurse
        
        Write-Success "Test data cleanup completed"
    }
    else {
        Write-Status "Skipping test data cleanup (-NoCleanup specified)"
    }
}

function New-Report {
    Write-Status "Generating test report..."
    
    if ($OutputFile -and (Test-Path "test_results\$OutputFile")) {
        # Generate HTML report from JSON results
        $pythonScript = @"
import json
import sys
from datetime import datetime

try:
    with open('test_results/$OutputFile', 'r') as f:
        results = json.load(f)
    
    html_report = '''
<!DOCTYPE html>
<html>
<head>
    <title>E2E Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f8f9fa; padding: 20px; border-radius: 5px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .metric { background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }
        .test { margin: 10px 0; padding: 15px; border-radius: 5px; }
        .passed { background: #d4edda; border-left: 5px solid #28a745; }
        .failed { background: #f8d7da; border-left: 5px solid #dc3545; }
        .skipped { background: #fff3cd; border-left: 5px solid #ffc107; }
    </style>
</head>
<body>
    <div class="header">
        <h1>End-to-End Test Results</h1>
        <p>Mode: {mode} | Generated: {timestamp}</p>
    </div>
    
    <div class="summary">
        <div class="metric">
            <h3>{total}</h3>
            <p>Total Tests</p>
        </div>
        <div class="metric">
            <h3>{passed}</h3>
            <p>Passed</p>
        </div>
        <div class="metric">
            <h3>{failed}</h3>
            <p>Failed</p>
        </div>
        <div class="metric">
            <h3>{success_rate:.1f}%</h3>
            <p>Success Rate</p>
        </div>
    </div>
    
    <h2>Test Details</h2>
'''.format(
    mode=results['mode'].upper(),
    timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    total=results['summary']['total'],
    passed=results['summary']['passed'],
    failed=results['summary']['failed'],
    success_rate=results['success_rate']
)
    
    for test in results['tests']:
        status_class = test['status']
        html_report += f'''
    <div class="test {status_class}">
        <h3>{test['name']} - {test['status'].upper()}</h3>
        <p>{test['message']}</p>
        <small>Duration: {test['duration']:.2f}s | Time: {test['timestamp']}</small>
    </div>
'''
    
    html_report += '''
</body>
</html>
'''
    
    with open('test_results/report.html', 'w') as f:
        f.write(html_report)
    
    print('HTML report generated: test_results/report.html')
    
except Exception as e:
    print(f'Failed to generate HTML report: {e}')
"@
        
        python -c $pythonScript
        Write-Success "Test report generated: test_results\report.html"
    }
}

# Main execution
function Main {
    if ($Help) {
        Show-Usage
        exit 0
    }
    
    Write-Header "End-to-End Test Runner - Misinformation Heatmap"
    
    Test-Prerequisites
    Initialize-TestEnvironment
    
    try {
        Start-Services
        
        $testExitCode = Invoke-Tests
        
        if ($testExitCode -eq 0) {
            Write-Success "All tests passed!"
        }
        else {
            Write-Error "Some tests failed!"
        }
        
        Remove-TestData
        New-Report
        
        Write-Header "Test Run Complete"
        
        exit $testExitCode
    }
    finally {
        Stop-Services
    }
}

# Run main function
Main