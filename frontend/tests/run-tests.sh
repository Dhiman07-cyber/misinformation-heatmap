#!/bin/bash

# Frontend Integration Test Runner
# Runs comprehensive tests for the misinformation heatmap frontend

set -e

echo "🧪 Starting Frontend Integration Tests..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js to run tests."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm to run tests."
    exit 1
fi

# Navigate to test directory
cd "$(dirname "$0")"

print_status "Installing test dependencies..."
if npm install; then
    print_success "Dependencies installed successfully"
else
    print_error "Failed to install dependencies"
    exit 1
fi

# Run different test suites based on arguments
case "${1:-all}" in
    "map")
        print_status "Running map integration tests..."
        npm test -- --testPathPattern=map.test.js
        ;;
    "api")
        print_status "Running API integration tests..."
        npm test -- --testPathPattern=api.test.js
        ;;
    "responsive")
        print_status "Running responsive design tests..."
        npm test -- --testPathPattern=responsive.test.js
        ;;
    "app")
        print_status "Running application integration tests..."
        npm test -- --testPathPattern=app.test.js
        ;;
    "coverage")
        print_status "Running all tests with coverage report..."
        npm run test:coverage
        ;;
    "ci")
        print_status "Running tests in CI mode..."
        npm run test:ci
        ;;
    "watch")
        print_status "Running tests in watch mode..."
        npm run test:watch
        ;;
    "all"|*)
        print_status "Running all integration tests..."
        npm test
        ;;
esac

# Check test results
if [ $? -eq 0 ]; then
    print_success "All tests passed! ✅"
    
    # Generate coverage report if available
    if [ -d "coverage" ]; then
        print_status "Coverage report generated in coverage/ directory"
        
        # Try to open coverage report in browser (optional)
        if command -v xdg-open &> /dev/null; then
            xdg-open coverage/lcov-report/index.html 2>/dev/null || true
        elif command -v open &> /dev/null; then
            open coverage/lcov-report/index.html 2>/dev/null || true
        fi
    fi
    
    echo ""
    echo "🎉 Frontend integration tests completed successfully!"
    echo "   All components are working correctly across different scenarios."
    echo ""
else
    print_error "Some tests failed! ❌"
    echo ""
    echo "💡 Tips for debugging test failures:"
    echo "   - Check the test output above for specific error messages"
    echo "   - Run tests in watch mode: ./run-tests.sh watch"
    echo "   - Run specific test suites: ./run-tests.sh map|api|responsive|app"
    echo "   - Check browser console for additional error details"
    echo ""
    exit 1
fi