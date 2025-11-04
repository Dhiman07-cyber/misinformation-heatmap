#!/bin/bash

# Modern IBM Cloud Setup Script for Misinformation Heatmap
# Uses Code Engine instead of Cloud Foundry for modern deployment

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

# Configuration variables
RESOURCE_GROUP="misinformation-heatmap"
REGION="us-south"
PROJECT_NAME="misinformation-heatmap"
APP_NAME="misinformation-heatmap"
ADMIN_EMAIL=""
VERBOSE=false
DRY_RUN=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -e, --email EMAIL           Administrator email address"
    echo ""
    echo "Optional Options:"
    echo "  -r, --region REGION         IBM Cloud region (default: us-south)"
    echo "  -g, --resource-group GROUP  Resource group name (default: misinformation-heatmap)"
    echo "  -p, --project PROJECT       Code Engine project name (default: misinformation-heatmap)"
    echo "  -a, --app-name NAME         Application name (default: misinformation-heatmap)"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e 'admin@university.edu'"
    echo "  $0 -e 'admin@company.com' -r 'eu-gb'"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--email)
                ADMIN_EMAIL="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -g|--resource-group)
                RESOURCE_GROUP="$2"
                shift 2
                ;;
            -p|--project)
                PROJECT_NAME="$2"
                shift 2
                ;;
            -a|--app-name)
                APP_NAME="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
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

validate_args() {
    if [[ -z "$ADMIN_EMAIL" ]]; then
        print_error "Administrator email is required (--email)"
        exit 1
    fi
    
    # Validate email format
    if [[ ! "$ADMIN_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        print_error "Invalid email format: $ADMIN_EMAIL"
        exit 1
    fi
}

execute_command() {
    local cmd="$1"
    local description="$2"
    
    if [[ "$VERBOSE" == true ]]; then
        print_status "Executing: $cmd"
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would execute: $cmd"
        return 0
    fi
    
    if [[ -n "$description" ]]; then
        print_status "$description"
    fi
    
    if eval "$cmd"; then
        if [[ "$VERBOSE" == true ]]; then
            print_success "Command completed successfully"
        fi
        return 0
    else
        print_error "Command failed: $cmd"
        return 1
    fi
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if IBM Cloud CLI is installed
    if ! command -v ibmcloud &> /dev/null; then
        print_error "IBM Cloud CLI is not installed."
        print_status "Please install it from: https://cloud.ibm.com/docs/cli"
        exit 1
    fi
    
    # Check if user is logged in
    if ! ibmcloud target &>/dev/null; then
        print_error "You are not logged in to IBM Cloud."
        print_status "Please run: ibmcloud login"
        exit 1
    fi
    
    # Install required plugins
    print_status "Installing required plugins..."
    
    # Install Code Engine plugin
    if ! ibmcloud plugin list | grep -q "code-engine"; then
        execute_command "ibmcloud plugin install code-engine" "Installing Code Engine plugin..."
    fi
    
    # Install Container Registry plugin
    if ! ibmcloud plugin list | grep -q "container-registry"; then
        execute_command "ibmcloud plugin install container-registry" "Installing Container Registry plugin..."
    fi
    
    print_success "Prerequisites check completed"
}

setup_resource_group() {
    print_header "Setting up Resource Group"
    
    # Create resource group if it doesn't exist
    if ! ibmcloud resource group "$RESOURCE_GROUP" &>/dev/null; then
        execute_command "ibmcloud resource group-create '$RESOURCE_GROUP'" \
            "Creating resource group..."
    fi
    
    # Target the resource group
    execute_command "ibmcloud target -g '$RESOURCE_GROUP'" \
        "Targeting resource group..."
    
    # Target the region
    execute_command "ibmcloud target -r '$REGION'" \
        "Targeting region..."
    
    print_success "Resource group and region configured"
}

create_watson_services() {
    print_header "Creating Watson AI Services"
    
    # Create Watson Natural Language Understanding service
    execute_command "ibmcloud resource service-instance-create watson-nlu natural-language-understanding free '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Watson Natural Language Understanding service..."
    
    # Create Watson Language Translator service
    execute_command "ibmcloud resource service-instance-create watson-translator language-translator lite '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Watson Language Translator service..."
    
    # Create service keys
    execute_command "ibmcloud resource service-key-create watson-nlu-key Manager --instance-name watson-nlu" \
        "Creating Watson NLU service key..."
    
    execute_command "ibmcloud resource service-key-create watson-translator-key Manager --instance-name watson-translator" \
        "Creating Watson Translator service key..."
    
    print_success "Watson AI services created"
}

create_database_services() {
    print_header "Creating Database Services"
    
    # Create Cloudant NoSQL database
    execute_command "ibmcloud resource service-instance-create misinformation-cloudant cloudantnosqldb lite '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Cloudant NoSQL database..."
    
    # Create service key
    execute_command "ibmcloud resource service-key-create cloudant-key Manager --instance-name misinformation-cloudant" \
        "Creating Cloudant service key..."
    
    print_success "Database services created"
}

create_code_engine_project() {
    print_header "Creating Code Engine Project"
    
    # Create Code Engine project
    execute_command "ibmcloud ce project create --name '$PROJECT_NAME' --resource-group '$RESOURCE_GROUP'" \
        "Creating Code Engine project..."
    
    # Target the project
    execute_command "ibmcloud ce project select --name '$PROJECT_NAME'" \
        "Selecting Code Engine project..."
    
    print_success "Code Engine project created"
}

generate_deployment_config() {
    print_header "Generating Deployment Configuration"
    
    # Create Code Engine application configuration
    cat > code-engine-app.yaml << EOF
apiVersion: codeengine.cloud.ibm.com/v1beta1
kind: Application
metadata:
  name: $APP_NAME
spec:
  imageReference: icr.io/misinformation-heatmap/app:latest
  managedDomainMappings: public
  runServiceAccount: default
  scaleConcurrency: 100
  scaleDownDelay: 300s
  scaleMaxExecutions: 1000
  scaleMinExecutions: 1
  scaleRequestTimeout: 300s
  env:
    - name: MODE
      value: cloud
    - name: ENVIRONMENT
      value: production
    - name: LOG_LEVEL
      value: INFO
    - name: WATSON_NLU_ENABLED
      value: "true"
    - name: WATSON_TRANSLATOR_ENABLED
      value: "true"
    - name: DB_TYPE
      value: cloudant
    - name: API_KEY_ENABLED
      value: "true"
    - name: RATE_LIMIT_ENABLED
      value: "true"
    - name: ENABLE_METRICS
      value: "true"
EOF
    
    # Create IBM Cloud specific environment file
    cat > .env.ibmcloud << EOF
# IBM Cloud Production Environment Configuration
# Generated by IBM Cloud setup script on $(date)

# Application Configuration
MODE=cloud
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8080

# IBM Cloud Configuration
IBM_CLOUD_REGION=$REGION

# Watson AI Configuration
WATSON_NLU_ENABLED=true
WATSON_TRANSLATOR_ENABLED=true

# Database Configuration
DB_TYPE=cloudant
DOCUMENT_STORE=cloudant

# Security Configuration
API_KEY_ENABLED=true
CORS_ORIGINS=["*"]
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Performance Configuration
ENABLE_METRICS=true
ENABLE_TRACING=true
ENABLE_LOGGING=true

# Version
VERSION=latest
EOF
    
    print_success "Deployment configuration created"
}

create_container_registry() {
    print_header "Setting up Container Registry"
    
    # Create namespace in Container Registry
    local namespace="misinformation-heatmap"
    
    execute_command "ibmcloud cr namespace-add '$namespace'" \
        "Creating Container Registry namespace..."
    
    print_success "Container Registry namespace created: $namespace"
}

main() {
    print_header "Modern IBM Cloud Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Starting modern IBM Cloud setup with the following configuration:"
    print_status "  Resource Group: $RESOURCE_GROUP"
    print_status "  Region: $REGION"
    print_status "  Project Name: $PROJECT_NAME"
    print_status "  App Name: $APP_NAME"
    print_status "  Admin Email: $ADMIN_EMAIL"
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with IBM Cloud setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Execute setup steps
    check_prerequisites
    setup_resource_group
    create_watson_services
    create_database_services
    create_code_engine_project
    create_container_registry
    generate_deployment_config
    
    print_header "Modern IBM Cloud Setup Complete!"
    print_success "IBM Cloud infrastructure is ready for modern deployment"
    print_status ""
    print_status "Created resources:"
    print_status "  - Watson AI services (NLU, Translator)"
    print_status "  - Cloudant NoSQL database"
    print_status "  - Code Engine project for containerized deployment"
    print_status "  - Container Registry namespace"
    print_status ""
    print_status "Created files:"
    print_status "  - code-engine-app.yaml (Code Engine deployment config)"
    print_status "  - .env.ibmcloud (IBM Cloud environment variables)"
    print_status ""
    print_status "Next steps:"
    print_status "1. Build and push container image"
    print_status "2. Deploy application to Code Engine"
    print_status "3. Test the deployment"
    print_status "4. Set up monitoring dashboards"
}

# Run main function with all arguments
main "$@"