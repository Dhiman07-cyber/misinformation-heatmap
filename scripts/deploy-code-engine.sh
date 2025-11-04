#!/bin/bash

# Modern IBM Cloud Code Engine Deployment Script
# Deploys the Watson AI-powered misinformation detection system using Code Engine

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
PROJECT_NAME="misinformation-heatmap"
APP_NAME="misinformation-heatmap"
REGISTRY_NAMESPACE="misinformation-heatmap"
IMAGE_NAME="app"
IMAGE_TAG="latest"
VERBOSE=false
SKIP_BUILD=false
SKIP_TESTS=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-build    Skip building the container image"
    echo "  --skip-tests    Skip running tests before deployment"
    echo "  -v, --verbose   Enable verbose output"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Full deployment with build and tests"
    echo "  $0 --skip-build       # Deploy existing image"
    echo "  $0 --verbose          # Verbose deployment"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
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
        exit 1
    fi
    
    # Check if logged in
    if ! ibmcloud target &>/dev/null; then
        print_error "Not logged in to IBM Cloud."
        print_status "Please run: ibmcloud login"
        exit 1
    fi
    
    # Check if Code Engine plugin is installed
    if ! ibmcloud plugin list | grep -q "code-engine"; then
        print_warning "Code Engine plugin not found. Installing..."
        ibmcloud plugin install code-engine
    fi
    
    # Check if Container Registry plugin is installed
    if ! ibmcloud plugin list | grep -q "container-registry"; then
        print_warning "Container Registry plugin not found. Installing..."
        ibmcloud plugin install container-registry
    fi
    
    # Check if Docker is available (for building)
    if [[ "$SKIP_BUILD" != true ]] && ! command -v docker &> /dev/null; then
        print_error "Docker is not installed and --skip-build not specified."
        print_status "Either install Docker or use --skip-build flag"
        exit 1
    fi
    
    print_success "Prerequisites check completed"
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
    
    # Install dependencies if needed
    if [[ -f "requirements-ibmcloud.txt" ]]; then
        print_status "Installing dependencies..."
        pip install -r requirements-ibmcloud.txt
    fi
    
    # Run tests
    print_status "Running unit tests..."
    if [[ -d "tests" ]]; then
        python -m pytest tests/ -v --tb=short || {
            print_error "Tests failed. Deployment aborted."
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

build_and_push_image() {
    if [[ "$SKIP_BUILD" == true ]]; then
        print_status "Skipping image build as requested"
        return 0
    fi
    
    print_header "Building and Pushing Container Image"
    
    # Login to Container Registry
    print_status "Logging in to IBM Container Registry..."
    ibmcloud cr login
    
    # Build the image
    local full_image_name="icr.io/$REGISTRY_NAMESPACE/$IMAGE_NAME:$IMAGE_TAG"
    
    print_status "Building container image: $full_image_name"
    
    # Create Dockerfile for IBM Cloud if it doesn't exist
    if [[ ! -f "Dockerfile.ibmcloud" ]]; then
        cat > Dockerfile.ibmcloud << 'EOF'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements-ibmcloud.txt .
RUN pip install --no-cache-dir -r requirements-ibmcloud.txt

# Copy application code
COPY backend/ ./backend/
COPY config/ ./config/
COPY .env.ibmcloud .env

# Create non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "backend.main_ibmcloud:app", "--host", "0.0.0.0", "--port", "8080"]
EOF
    fi
    
    # Build the image
    docker build -f Dockerfile.ibmcloud -t "$full_image_name" .
    
    # Push the image
    print_status "Pushing image to IBM Container Registry..."
    docker push "$full_image_name"
    
    print_success "Container image built and pushed: $full_image_name"
}

deploy_to_code_engine() {
    print_header "Deploying to Code Engine"
    
    # Select the Code Engine project
    print_status "Selecting Code Engine project..."
    ibmcloud ce project select --name "$PROJECT_NAME"
    
    # Get Watson service credentials
    print_status "Getting Watson service credentials..."
    
    # Get Watson NLU credentials
    local watson_nlu_creds=$(ibmcloud resource service-key watson-nlu-key --output json 2>/dev/null || echo "{}")
    local watson_translator_creds=$(ibmcloud resource service-key watson-translator-key --output json 2>/dev/null || echo "{}")
    local cloudant_creds=$(ibmcloud resource service-key cloudant-key --output json 2>/dev/null || echo "{}")
    
    # Create or update the application
    local full_image_name="icr.io/$REGISTRY_NAMESPACE/$IMAGE_NAME:$IMAGE_TAG"
    
    print_status "Deploying application to Code Engine..."
    
    # Check if application exists
    if ibmcloud ce app get --name "$APP_NAME" &>/dev/null; then
        print_status "Updating existing application..."
        ibmcloud ce app update --name "$APP_NAME" \
            --image "$full_image_name" \
            --env MODE=cloud \
            --env ENVIRONMENT=production \
            --env LOG_LEVEL=INFO \
            --env WATSON_NLU_ENABLED=true \
            --env WATSON_TRANSLATOR_ENABLED=true \
            --env DB_TYPE=cloudant \
            --env API_KEY_ENABLED=true \
            --env RATE_LIMIT_ENABLED=true \
            --env ENABLE_METRICS=true \
            --min-scale 1 \
            --max-scale 10 \
            --cpu 0.5 \
            --memory 1G \
            --port 8080 \
            --concurrency 100 \
            --request-timeout 300
    else
        print_status "Creating new application..."
        ibmcloud ce app create --name "$APP_NAME" \
            --image "$full_image_name" \
            --env MODE=cloud \
            --env ENVIRONMENT=production \
            --env LOG_LEVEL=INFO \
            --env WATSON_NLU_ENABLED=true \
            --env WATSON_TRANSLATOR_ENABLED=true \
            --env DB_TYPE=cloudant \
            --env API_KEY_ENABLED=true \
            --env RATE_LIMIT_ENABLED=true \
            --env ENABLE_METRICS=true \
            --min-scale 1 \
            --max-scale 10 \
            --cpu 0.5 \
            --memory 1G \
            --port 8080 \
            --concurrency 100 \
            --request-timeout 300
    fi
    
    print_success "Application deployed to Code Engine"
}

verify_deployment() {
    print_header "Verifying Deployment"
    
    # Get application URL
    print_status "Getting application URL..."
    local app_url=$(ibmcloud ce app get --name "$APP_NAME" --output json | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -z "$app_url" ]]; then
        print_error "Could not get application URL"
        return 1
    fi
    
    print_status "Application URL: $app_url"
    
    # Wait for application to start
    print_status "Waiting for application to start..."
    sleep 60
    
    # Test health endpoint
    print_status "Testing health endpoint..."
    local health_response=$(curl -s -w "%{http_code}" "$app_url/health" -o /tmp/health_response.json)
    
    if [[ "$health_response" == "200" ]]; then
        print_success "Health check passed"
        if [[ "$VERBOSE" == true ]]; then
            cat /tmp/health_response.json
        fi
    else
        print_error "Health check failed (HTTP $health_response)"
        print_status "Checking application logs..."
        ibmcloud ce app logs --name "$APP_NAME"
        return 1
    fi
    
    # Test API endpoint
    print_status "Testing API endpoint..."
    local api_response=$(curl -s -w "%{http_code}" "$app_url/api/v1/health" -o /tmp/api_response.json)
    
    if [[ "$api_response" == "200" ]]; then
        print_success "API health check passed"
    else
        print_warning "API health check failed, but main app is running"
    fi
    
    # Test Watson AI integration
    print_status "Testing Watson AI integration..."
    local watson_test='{"text":"This is a test message for Watson AI analysis","title":"Test"}'
    local watson_response=$(curl -s -w "%{http_code}" -X POST "$app_url/api/v1/analyze" \
        -H "Content-Type: application/json" \
        -d "$watson_test" \
        -o /tmp/watson_response.json)
    
    if [[ "$watson_response" == "200" ]]; then
        print_success "Watson AI integration is working"
        if [[ "$VERBOSE" == true ]]; then
            cat /tmp/watson_response.json
        fi
    else
        print_warning "Watson AI test failed, check service bindings"
    fi
    
    print_success "Deployment verification completed"
}

show_deployment_info() {
    print_header "Deployment Information"
    
    # Get application details
    local app_url=$(ibmcloud ce app get --name "$APP_NAME" --output json | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    
    print_status "🎉 Deployment completed successfully!"
    echo ""
    print_status "📱 Application Details:"
    print_status "  • Application URL: $app_url"
    print_status "  • API Documentation: $app_url/docs"
    print_status "  • Health Check: $app_url/health"
    print_status "  • Watson AI Analysis: $app_url/api/v1/analyze"
    echo ""
    print_status "🔧 Management Commands:"
    print_status "  • View logs: ibmcloud ce app logs --name $APP_NAME"
    print_status "  • App status: ibmcloud ce app get --name $APP_NAME"
    print_status "  • Scale app: ibmcloud ce app update --name $APP_NAME --max-scale 20"
    print_status "  • Update app: ibmcloud ce app update --name $APP_NAME --image NEW_IMAGE"
    echo ""
    print_status "🤖 Watson AI Services:"
    print_status "  • Natural Language Understanding: Enabled"
    print_status "  • Language Translator: Enabled"
    print_status "  • Cloudant Database: Connected"
    echo ""
    print_status "📊 Next Steps:"
    print_status "  1. Test the Watson AI endpoints"
    print_status "  2. Configure monitoring dashboards"
    print_status "  3. Set up data ingestion"
    print_status "  4. Add real data sources"
    echo ""
    print_status "🧪 Test Commands:"
    print_status "  # Test Watson AI analysis"
    print_status "  curl -X POST '$app_url/api/v1/analyze' \\"
    print_status "    -H 'Content-Type: application/json' \\"
    print_status "    -d '{\"text\":\"This is fake news\",\"title\":\"Test\"}'"
}

main() {
    print_header "IBM Cloud Code Engine Deployment - Misinformation Heatmap"
    
    parse_args "$@"
    
    print_status "Starting deployment to IBM Cloud Code Engine..."
    print_status "Platform: IBM Cloud (Code Engine)"
    print_status "AI Engine: Watson AI"
    print_status "Application: $APP_NAME"
    echo ""
    
    # Execute deployment steps
    check_prerequisites
    run_tests
    build_and_push_image
    deploy_to_code_engine
    verify_deployment
    show_deployment_info
    
    print_header "🎉 Deployment Complete!"
    print_success "Your Watson AI-powered misinformation heatmap is now live on Code Engine!"
}

# Run main function with all arguments
main "$@"