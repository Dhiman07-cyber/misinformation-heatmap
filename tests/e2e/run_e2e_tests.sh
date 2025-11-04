#!/bin/bash

# End-to-End Test Runner Script
# Runs comprehensive end-to-end tests for the misinformation heatmap system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
MODE="local"
VERBOSE=false
OUTPUT_FILE=""
CLEANUP=true
HEADLESS=true
TIMEOUT=300

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -m, --mode MODE         Testing mode: local or cloud (default: local)"
    echo "  -o, --output FILE       Output file for test results (JSON)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  --no-cleanup            Don't cleanup test data after tests"
    echo "  --no-headless           Run browser tests in visible mode"
    echo "  --timeout SECONDS       Test timeout in seconds (default: 300)"
    echo ""
    echo "Examples:"
    echo "  $0 --mode local --verbose"
    echo "  $0 --mode cloud --output results.json"
    echo "  $0 --no-headless --timeout 600"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --no-cleanup)
                CLEANUP=false
                shift
                ;;
            --no-headless)
                HEADLESS=false
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed."
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "../../backend/api.py" ]]; then
        print_error "Please run this script from the tests/e2e directory."
        exit 1
    fi
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    pip3 install -r requirements.txt > /dev/null 2>&1 || {
        print_error "Failed to install Python dependencies."
        exit 1
    }
    
    # Check Chrome/Chromium for Selenium
    if command -v google-chrome &> /dev/null || command -v chromium-browser &> /dev/null; then
        print_status "Chrome/Chromium found for browser testing"
    else
        print_warning "Chrome/Chromium not found. Browser tests will be skipped."
    fi
    
    print_success "Prerequisites check completed"
}

setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Set environment variables
    export MODE="$MODE"
    export PYTHONPATH="../../backend:$PYTHONPATH"
    
    if [[ "$HEADLESS" == "false" ]]; then
        export SELENIUM_HEADLESS="false"
    else
        export SELENIUM_HEADLESS="true"
    fi
    
    # Create test data directory
    mkdir -p test_data
    mkdir -p test_results
    
    print_success "Test environment setup completed"
}

start_services() {
    print_status "Starting services for testing..."
    
    if [[ "$MODE" == "local" ]]; then
        # Start local services
        print_status "Starting local backend service..."
        
        cd ../../
        
        # Start backend in background
        python3 backend/api.py &
        BACKEND_PID=$!
        
        # Start frontend in background
        cd frontend
        python3 -m http.server 3000 &
        FRONTEND_PID=$!
        
        cd ../tests/e2e
        
        # Wait for services to start
        print_status "Waiting for services to start..."
        sleep 10
        
        # Check if services are running
        if ! curl -s http://localhost:8000/health > /dev/null; then
            print_error "Backend service failed to start"
            cleanup_services
            exit 1
        fi
        
        if ! curl -s http://localhost:3000 > /dev/null; then
            print_error "Frontend service failed to start"
            cleanup_services
            exit 1
        fi
        
        print_success "Local services started successfully"
        
    else
        print_status "Using cloud services (assuming they are already running)"
    fi
}

cleanup_services() {
    if [[ "$MODE" == "local" ]]; then
        print_status "Cleaning up local services..."
        
        if [[ -n "$BACKEND_PID" ]]; then
            kill $BACKEND_PID 2>/dev/null || true
        fi
        
        if [[ -n "$FRONTEND_PID" ]]; then
            kill $FRONTEND_PID 2>/dev/null || true
        fi
        
        # Kill any remaining processes
        pkill -f "python3 backend/api.py" 2>/dev/null || true
        pkill -f "python3 -m http.server 3000" 2>/dev/null || true
        
        print_success "Services cleanup completed"
    fi
}

run_tests() {
    print_status "Running end-to-end tests..."
    
    # Prepare test command
    TEST_CMD="python3 test_end_to_end.py --mode $MODE"
    
    if [[ "$VERBOSE" == "true" ]]; then
        TEST_CMD="$TEST_CMD --verbose"
    fi
    
    if [[ -n "$OUTPUT_FILE" ]]; then
        TEST_CMD="$TEST_CMD --output test_results/$OUTPUT_FILE"
    fi
    
    # Run tests with timeout
    print_status "Executing: $TEST_CMD"
    
    if timeout $TIMEOUT $TEST_CMD; then
        print_success "All tests completed successfully"
        return 0
    else
        EXIT_CODE=$?
        if [[ $EXIT_CODE -eq 124 ]]; then
            print_error "Tests timed out after $TIMEOUT seconds"
        else
            print_error "Tests failed with exit code $EXIT_CODE"
        fi
        return $EXIT_CODE
    fi
}

cleanup_test_data() {
    if [[ "$CLEANUP" == "true" ]]; then
        print_status "Cleaning up test data..."
        
        # Remove test database if it exists
        rm -f ../../data/test_heatmap.db
        
        # Clean up any temporary files
        rm -rf test_data/temp_*
        
        print_success "Test data cleanup completed"
    else
        print_status "Skipping test data cleanup (--no-cleanup specified)"
    fi
}

generate_report() {
    print_status "Generating test report..."
    
    if [[ -n "$OUTPUT_FILE" && -f "test_results/$OUTPUT_FILE" ]]; then
        # Generate HTML report from JSON results
        python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('test_results/$OUTPUT_FILE', 'r') as f:
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
    <div class=\"header\">
        <h1>End-to-End Test Results</h1>
        <p>Mode: {mode} | Generated: {timestamp}</p>
    </div>
    
    <div class=\"summary\">
        <div class=\"metric\">
            <h3>{total}</h3>
            <p>Total Tests</p>
        </div>
        <div class=\"metric\">
            <h3>{passed}</h3>
            <p>Passed</p>
        </div>
        <div class=\"metric\">
            <h3>{failed}</h3>
            <p>Failed</p>
        </div>
        <div class=\"metric\">
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
    <div class=\"test {status_class}\">
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
"
        
        print_success "Test report generated: test_results/report.html"
    fi
}

main() {
    print_header "End-to-End Test Runner - Misinformation Heatmap"
    
    parse_args "$@"
    check_prerequisites
    setup_test_environment
    
    # Trap to ensure cleanup on exit
    trap cleanup_services EXIT
    
    start_services
    
    if run_tests; then
        print_success "All tests passed!"
        TEST_EXIT_CODE=0
    else
        print_error "Some tests failed!"
        TEST_EXIT_CODE=1
    fi
    
    cleanup_test_data
    generate_report
    
    print_header "Test Run Complete"
    
    exit $TEST_EXIT_CODE
}

main "$@"