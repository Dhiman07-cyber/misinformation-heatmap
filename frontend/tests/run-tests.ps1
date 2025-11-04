# Frontend Integration Test Runner (PowerShell)
# Runs comprehensive tests for the misinformation heatmap frontend

param(
    [string]$TestSuite = "all"
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

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

Write-Host "🧪 Starting Frontend Integration Tests..." -ForegroundColor $Blue
Write-Host "========================================" -ForegroundColor $Blue

# Check if Node.js is installed
try {
    $nodeVersion = node --version
    Write-Status "Node.js version: $nodeVersion"
} catch {
    Write-Error "Node.js is not installed. Please install Node.js to run tests."
    exit 1
}

# Check if npm is installed
try {
    $npmVersion = npm --version
    Write-Status "npm version: $npmVersion"
} catch {
    Write-Error "npm is not installed. Please install npm to run tests."
    exit 1
}

# Navigate to test directory
$testDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $testDir

Write-Status "Installing test dependencies..."
try {
    npm install | Out-Host
    Write-Success "Dependencies installed successfully"
} catch {
    Write-Error "Failed to install dependencies"
    exit 1
}

# Run different test suites based on arguments
switch ($TestSuite.ToLower()) {
    "map" {
        Write-Status "Running map integration tests..."
        npm test -- --testPathPattern=map.test.js
    }
    "api" {
        Write-Status "Running API integration tests..."
        npm test -- --testPathPattern=api.test.js
    }
    "responsive" {
        Write-Status "Running responsive design tests..."
        npm test -- --testPathPattern=responsive.test.js
    }
    "app" {
        Write-Status "Running application integration tests..."
        npm test -- --testPathPattern=app.test.js
    }
    "coverage" {
        Write-Status "Running all tests with coverage report..."
        npm run test:coverage
    }
    "ci" {
        Write-Status "Running tests in CI mode..."
        npm run test:ci
    }
    "watch" {
        Write-Status "Running tests in watch mode..."
        npm run test:watch
    }
    default {
        Write-Status "Running all integration tests..."
        npm test
    }
}

# Check test results
if ($LASTEXITCODE -eq 0) {
    Write-Success "All tests passed! ✅"
    
    # Generate coverage report if available
    if (Test-Path "coverage") {
        Write-Status "Coverage report generated in coverage/ directory"
        
        # Try to open coverage report in browser (optional)
        $coverageFile = "coverage/lcov-report/index.html"
        if (Test-Path $coverageFile) {
            try {
                Start-Process $coverageFile
            } catch {
                Write-Status "Coverage report available at: $coverageFile"
            }
        }
    }
    
    Write-Host ""
    Write-Host "🎉 Frontend integration tests completed successfully!" -ForegroundColor $Green
    Write-Host "   All components are working correctly across different scenarios." -ForegroundColor $Green
    Write-Host ""
} else {
    Write-Error "Some tests failed! ❌"
    Write-Host ""
    Write-Host "💡 Tips for debugging test failures:" -ForegroundColor $Yellow
    Write-Host "   - Check the test output above for specific error messages" -ForegroundColor $Yellow
    Write-Host "   - Run tests in watch mode: .\run-tests.ps1 watch" -ForegroundColor $Yellow
    Write-Host "   - Run specific test suites: .\run-tests.ps1 map|api|responsive|app" -ForegroundColor $Yellow
    Write-Host "   - Check browser console for additional error details" -ForegroundColor $Yellow
    Write-Host ""
    exit 1
}