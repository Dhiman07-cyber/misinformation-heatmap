#!/bin/bash

# Comprehensive Testing Pipeline
# Runs all tests for the misinformation heatmap application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_RESULTS_DIR="$PROJECT_ROOT/test-results"
COVERAGE_DIR="$PROJECT_ROOT/coverage"

# Test configuration
RUN_UNIT_TESTS=true
RUN_INTEGRATION_TESTS=true
RUN_E2E_TESTS=true
RUN_PERFORMANCE_TESTS=true
RUN_SECURITY_TESTS=false
GENERATE_COVERAGE=true
VERBOSE=false
PARALLEL=true
FAIL_FAST=false

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

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  --unit-only             Run only unit tests"
    echo "  --integration-only      Run only integration tests"
    echo "  --e2e-only              Run only end-to-end tests"
    echo "  --performance-only      Run only performance tests"
    echo "  --no-coverage           Skip coverage generation"
    echo "  --sequential            Run tests sequentially"
    echo "  --fail-fast             Stop on first test failure"
    echo "  -v, --verbose           Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0                      Run all tests"
    echo "  $0 --unit-only         Run only unit tests"
    echo "  $0 --fail-fast         Stop on first failure"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            --unit-only)
                RUN_INTEGRATION_TESTS=false
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                shift
                ;;
            --integration-only)
                RUN_UNIT_TESTS=false
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                shift
                ;;
            --e2e-only)
                RUN_UNIT_TESTS=false
                RUN_INTEGRATION_TESTS=false
                RUN_PERFORMANCE_TESTS=false
                shift
                ;;
            --performance-only)
                RUN_UNIT_TESTS=false
                RUN_INTEGRATION_TESTS=false
                RUN_E2E_TESTS=false
                RUN_PERFORMANCE_TESTS=true
                shift
                ;;
            --no-coverage)
                GENERATE_COVERAGE=false
                shift
                ;;
            --sequential)
                PARALLEL=false
                shift
                ;;
            --fail-fast)
                FAIL_FAST=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

setup_test_environment() {
    print_status "Setting up test environment..."
    
    # Create test directories
    mkdir -p "$TEST_RESULTS_DIR"
    mkdir -p "$COVERAGE_DIR"
    
    # Set test environment variables
    export NODE_ENV=test
    export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"
    export TEST_MODE=true
    
    print_success "Test environment setup completed"
}

run_backend_unit_tests() {
    if [[ "$RUN_UNIT_TESTS" == false ]]; then
        return 0
    fi
    
    print_status "Running backend unit tests..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Activate virtual environment if it exists
    if [[ -d "venv" ]]; then
        source venv/bin/activate
    fi
    
    local test_cmd="python -m pytest tests/ -v"
    
    if [[ "$GENERATE_COVERAGE" == true ]]; then
        test_cmd="$test_cmd --cov=. --cov-report=html:$COVERAGE_DIR/backend --cov-report=xml:$COVERAGE_DIR/backend-coverage.xml"
    fi
    
    if [[ "$FAIL_FAST" == true ]]; then
        test_cmd="$test_cmd -x"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        test_cmd="$test_cmd -s"
    fi
    
    eval "$test_cmd" > "$TEST_RESULTS_DIR/backend-unit-tests.log" 2>&1
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "Backend unit tests passed"
    else
        print_error "Backend unit tests failed"
        if [[ "$VERBOSE" == true ]]; then
            cat "$TEST_RESULTS_DIR/backend-unit-tests.log"
        fi
    fi
    
    return $exit_code
}

run_frontend_tests() {
    if [[ "$RUN_INTEGRATION_TESTS" == false ]]; then
        return 0
    fi
    
    print_status "Running frontend integration tests..."
    
    cd "$PROJECT_ROOT/frontend/tests"
    
    # Install dependencies if needed
    if [[ ! -d "node_modules" ]]; then
        npm install
    fi
    
    local test_cmd="npm test"
    
    if [[ "$GENERATE_COVERAGE" == true ]]; then
        test_cmd="npm run test:coverage"
    fi
    
    eval "$test_cmd" > "$TEST_RESULTS_DIR/frontend-tests.log" 2>&1
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "Frontend tests passed"
    else
        print_error "Frontend tests failed"
        if [[ "$VERBOSE" == true ]]; then
            cat "$TEST_RESULTS_DIR/frontend-tests.log"
        fi
    fi
    
    return $exit_code
}

run_api_integration_tests() {
    if [[ "$RUN_INTEGRATION_TESTS" == false ]]; then
        return 0
    fi
    
    print_status "Running API integration tests..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Start test server in background
    python api.py --test-mode &
    local server_pid=$!
    
    # Wait for server to start
    sleep 5
    
    # Run API tests
    python -m pytest tests/test_api.py -v > "$TEST_RESULTS_DIR/api-integration-tests.log" 2>&1
    local exit_code=$?
    
    # Stop test server
    kill $server_pid 2>/dev/null || true
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "API integration tests passed"
    else
        print_error "API integration tests failed"
        if [[ "$VERBOSE" == true ]]; then
            cat "$TEST_RESULTS_DIR/api-integration-tests.log"
        fi
    fi
    
    return $exit_code
}

run_e2e_tests() {
    if [[ "$RUN_E2E_TESTS" == false ]]; then
        return 0
    fi
    
    print_status "Running end-to-end tests..."
    
    # Start full application stack
    "$PROJECT_ROOT/scripts/run_local.sh" --detached --skip-deps
    
    # Wait for services to be ready
    sleep 10
    
    # Run health checks
    python "$PROJECT_ROOT/scripts/health_check.py" --timeout 30 > "$TEST_RESULTS_DIR/e2e-health-check.log" 2>&1
    local health_exit_code=$?
    
    if [[ $health_exit_code -ne 0 ]]; then
        print_error "Health check failed - services not ready"
        "$PROJECT_ROOT/scripts/run_local.sh" --stop
        return 1
    fi
    
    # Run E2E test scenarios
    cd "$PROJECT_ROOT"
    python -m pytest tests/e2e/ -v > "$TEST_RESULTS_DIR/e2e-tests.log" 2>&1
    local exit_code=$?
    
    # Stop services
    "$PROJECT_ROOT/scripts/run_local.sh" --stop
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "End-to-end tests passed"
    else
        print_error "End-to-end tests failed"
        if [[ "$VERBOSE" == true ]]; then
            cat "$TEST_RESULTS_DIR/e2e-tests.log"
        fi
    fi
    
    return $exit_code
}

run_performance_tests() {
    if [[ "$RUN_PERFORMANCE_TESTS" == false ]]; then
        return 0
    fi
    
    print_status "Running performance tests..."
    
    cd "$PROJECT_ROOT"
    
    # Start application for performance testing
    "$PROJECT_ROOT/scripts/run_local.sh" --detached --skip-deps
    sleep 10
    
    # Run performance benchmarks
    python scripts/performance_benchmark.py > "$TEST_RESULTS_DIR/performance-tests.log" 2>&1
    local exit_code=$?
    
    # Stop services
    "$PROJECT_ROOT/scripts/run_local.sh" --stop
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "Performance tests passed"
    else
        print_error "Performance tests failed"
        if [[ "$VERBOSE" == true ]]; then
            cat "$TEST_RESULTS_DIR/performance-tests.log"
        fi
    fi
    
    return $exit_code
}

generate_test_report() {
    print_status "Generating test report..."
    
    local report_file="$TEST_RESULTS_DIR/test-report.html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Test Report - Misinformation Heatmap</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .pass { color: green; }
        .fail { color: red; }
        .skip { color: orange; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Report - Misinformation Heatmap</h1>
        <p>Generated on: $(date)</p>
    </div>
    
    <div class="section">
        <h2>Test Summary</h2>
        <ul>
EOF

    # Add test results to report
    if [[ "$RUN_UNIT_TESTS" == true ]]; then
        if [[ -f "$TEST_RESULTS_DIR/backend-unit-tests.log" ]]; then
            echo "            <li>Backend Unit Tests: <span class=\"pass\">PASS</span></li>" >> "$report_file"
        else
            echo "            <li>Backend Unit Tests: <span class=\"fail\">FAIL</span></li>" >> "$report_file"
        fi
    fi
    
    if [[ "$RUN_INTEGRATION_TESTS" == true ]]; then
        if [[ -f "$TEST_RESULTS_DIR/frontend-tests.log" ]]; then
            echo "            <li>Frontend Tests: <span class=\"pass\">PASS</span></li>" >> "$report_file"
        else
            echo "            <li>Frontend Tests: <span class=\"fail\">FAIL</span></li>" >> "$report_file"
        fi
    fi
    
    cat >> "$report_file" << EOF
        </ul>
    </div>
    
    <div class="section">
        <h2>Coverage Reports</h2>
        <p>Coverage reports are available in the <code>coverage/</code> directory.</p>
    </div>
</body>
</html>
EOF

    print_success "Test report generated: $report_file"
}

main() {
    print_header "Comprehensive Testing Pipeline"
    
    parse_args "$@"
    setup_test_environment
    
    local total_failures=0
    
    # Run tests based on configuration
    if [[ "$PARALLEL" == true && "$FAIL_FAST" == false ]]; then
        # Run tests in parallel
        (
            run_backend_unit_tests
            echo $? > "$TEST_RESULTS_DIR/backend-unit-exit-code"
        ) &
        
        (
            run_frontend_tests
            echo $? > "$TEST_RESULTS_DIR/frontend-exit-code"
        ) &
        
        (
            run_api_integration_tests
            echo $? > "$TEST_RESULTS_DIR/api-integration-exit-code"
        ) &
        
        # Wait for parallel tests to complete
        wait
        
        # Check exit codes
        if [[ -f "$TEST_RESULTS_DIR/backend-unit-exit-code" ]]; then
            local backend_exit=$(cat "$TEST_RESULTS_DIR/backend-unit-exit-code")
            ((total_failures += backend_exit))
        fi
        
        if [[ -f "$TEST_RESULTS_DIR/frontend-exit-code" ]]; then
            local frontend_exit=$(cat "$TEST_RESULTS_DIR/frontend-exit-code")
            ((total_failures += frontend_exit))
        fi
        
        if [[ -f "$TEST_RESULTS_DIR/api-integration-exit-code" ]]; then
            local api_exit=$(cat "$TEST_RESULTS_DIR/api-integration-exit-code")
            ((total_failures += api_exit))
        fi
        
        # Run sequential tests
        run_e2e_tests || ((total_failures++))
        run_performance_tests || ((total_failures++))
        
    else
        # Run tests sequentially
        run_backend_unit_tests || ((total_failures++))
        
        if [[ "$FAIL_FAST" == true && $total_failures -gt 0 ]]; then
            print_error "Stopping due to test failure (fail-fast mode)"
            exit 1
        fi
        
        run_frontend_tests || ((total_failures++))
        
        if [[ "$FAIL_FAST" == true && $total_failures -gt 0 ]]; then
            print_error "Stopping due to test failure (fail-fast mode)"
            exit 1
        fi
        
        run_api_integration_tests || ((total_failures++))
        run_e2e_tests || ((total_failures++))
        run_performance_tests || ((total_failures++))
    fi
    
    # Generate test report
    generate_test_report
    
    # Summary
    print_header "Test Results Summary"
    
    if [[ $total_failures -eq 0 ]]; then
        print_success "All tests passed! ✅"
        echo ""
        echo "📊 Test artifacts:"
        echo "  - Results: $TEST_RESULTS_DIR/"
        echo "  - Coverage: $COVERAGE_DIR/"
        echo "  - Report: $TEST_RESULTS_DIR/test-report.html"
    else
        print_error "$total_failures test suite(s) failed ❌"
        echo ""
        echo "Check the following for details:"
        echo "  - Test logs: $TEST_RESULTS_DIR/"
        echo "  - Verbose output: Use -v flag"
        exit 1
    fi
}

main "$@"