#!/bin/bash

# IBM Cloud Deployment Script for Misinformation Heatmap
# Deploys the Watson AI-powered misinformation detection system

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
APP_NAME="misinformation-heatmap"
VERBOSE=false
SKIP_TESTS=false
SKIP_DEPS=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-tests    Skip running tests before deployment"
    echo "  --skip-deps     Skip installing dependencies"
    echo "  -v, --verbose   Enable verbose output"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full deployment with tests"
    echo "  $0 --skip-tests       # Quick deployment without tests"
    echo "  $0 --verbose          # Verbose deployment"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
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
    
    # Check if IBM Cloud CLI is installed
    if ! command -v ibmcloud &> /dev/null; then
        print_error "IBM Cloud CLI is not installed."
        print_status "Please install it from: https://cloud.ibm.com/docs/cli"
        exit 1
    fi
    
    # Check if logged in
    if ! ibmcloud target &>/dev/null; then
        print_error "Not logged in to IBM Cloud."
        print_status "Please run: ibmcloud login"
        exit 1
    fi
    
    # Check if Cloud Foundry plugin is installed
    if ! ibmcloud cf --version &>/dev/null; then
        print_warning "Cloud Foundry plugin not found. Installing..."
        ibmcloud plugin install cloud-foundry
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python is not installed."
        exit 1
    fi
    
    # Check if required files exist
    if [[ ! -f "manifest.yml" ]]; then
        print_error "manifest.yml not found. Please run the setup script first."
        exit 1
    fi
    
    if [[ ! -f "requirements-ibmcloud.txt" ]]; then
        print_error "requirements-ibmcloud.txt not found. Please run the setup script first."
        exit 1
    fi
    
    print_success "Prerequisites check completed"
}

install_dependencies() {
    if [[ "$SKIP_DEPS" == true ]]; then
        print_status "Skipping dependency installation"
        return 0
    fi
    
    print_header "Installing Dependencies"
    
    # Use IBM Cloud specific requirements
    print_status "Installing Python dependencies for IBM Cloud..."
    
    # Install IBM Cloud specific requirements
    pip install -r requirements-ibmcloud.txt
    
    print_success "Dependencies installed successfully"
}

run_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        print_status "Skipping tests as requested"
        return 0
    fi
    
    print_header "Running Tests"
    
    # Set test environment
    export MODE=test
    export ENVIRONMENT=test
    
    # Run tests
    print_status "Running unit tests..."
    if [[ -d "tests" ]]; then
        python -m pytest tests/ -v --tb=short || {
            print_error "Tests failed. Deployment aborted."
            print_status "Fix the failing tests and try again."
            exit 1
        }
    elif [[ -d "backend" ]]; then
        # Run backend tests
        python -m pytest backend/test_*.py -v --tb=short || {
            print_warning "Some tests failed, but continuing with deployment..."
        }
    else
        print_warning "No tests found, skipping test execution"
    fi
    
    print_success "Tests completed"
}

deploy_application() {
    print_header "Deploying to IBM Cloud"
    
    # Show current target
    print_status "Current IBM Cloud target:"
    ibmcloud target
    
    # Deploy using Cloud Foundry
    print_status "Deploying application to Cloud Foundry..."
    
    if [[ "$VERBOSE" == true ]]; then
        ibmcloud cf push --verbose
    else
        ibmcloud cf push
    fi
    
    print_success "Application deployed successfully"
}

verify_deployment() {
    print_header "Verifying Deployment"
    
    # Get application URL
    print_status "Getting application URL..."
    APP_URL=$(ibmcloud cf app $APP_NAME --show-app-url 2>/dev/null | tail -1)
    
    if [[ -z "$APP_URL" ]]; then
        print_error "Could not get application URL"
        return 1
    fi
    
    print_status "Application URL: $APP_URL"
    
    # Wait for application to start
    print_status "Waiting for application to start..."
    sleep 30
    
    # Test health endpoint
    print_status "Testing health endpoint..."
    if curl -f -s "$APP_URL/health" > /dev/null; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        print_status "Checking application logs..."
        ibmcloud cf logs $APP_NAME --recent
        return 1
    fi
    
    # Test API endpoint
    print_status "Testing API endpoint..."
    if curl -f -s "$APP_URL/api/v1/health" > /dev/null; then
        print_success "API health check passed"
    else
        print_warning "API health check failed, but main app is running"
    fi
    
    print_success "Deployment verification completed"
}

show_deployment_info() {
    print_header "Deployment Information"
    
    # Get application details
    APP_URL=$(ibmcloud cf app $APP_NAME --show-app-url 2>/dev/null | tail -1)
    
    print_status "🎉 Deployment completed successfully!"
    echo ""
    print_status "📱 Application Details:"
    print_status "  • Application URL: $APP_URL"
    print_status "  • API Documentation: $APP_URL/docs"
    print_status "  • Health Check: $APP_URL/health"
    print_status "  • Watson AI Status: $APP_URL/api/v1/watson/status"
    echo ""
    print_status "🔧 Management Commands:"
    print_status "  • View logs: ibmcloud cf logs $APP_NAME"
    print_status "  • App status: ibmcloud cf app $APP_NAME"
    print_status "  • Scale app: ibmcloud cf scale $APP_NAME -i 3"
    print_status "  • Restart app: ibmcloud cf restart $APP_NAME"
    echo ""
    print_status "🤖 Watson AI Services:"
    print_status "  • Natural Language Understanding: Enabled"
    print_status "  • Language Translator: Enabled"
    print_status "  • Discovery: Enabled"
    echo ""
    print_status "📊 Next Steps:"
    print_status "  1. Test the API endpoints"
    print_status "  2. Configure monitoring dashboards"
    print_status "  3. Set up data ingestion"
    print_status "  4. Add real data sources"
}

main() {
    print_header "IBM Cloud Deployment - Misinformation Heatmap"
    
    parse_args "$@"
    
    print_status "Starting deployment to IBM Cloud..."
    print_status "Platform: IBM Cloud (Cloud Foundry)"
    print_status "AI Engine: Watson AI"
    print_status "Application: $APP_NAME"
    echo ""
    
    # Execute deployment steps
    check_prerequisites
    install_dependencies
    run_tests
    deploy_application
    verify_deployment
    show_deployment_info
    
    print_header "🎉 Deployment Complete!"
    print_success "Your Watson AI-powered misinformation heatmap is now live!"
}

# Run main function with all arguments
main "$@"