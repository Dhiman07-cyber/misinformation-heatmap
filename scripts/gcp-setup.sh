#!/bin/bash

# Google Cloud Platform Production Setup Script
# Creates and configures a production-ready GCP environment for the misinformation heatmap

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
PROJECT_ID=""
PROJECT_NAME=""
ORGANIZATION_ID=""
BILLING_ACCOUNT_ID=""
REGION="us-central1"
ZONE="us-central1-a"
ENVIRONMENT="production"
DOMAIN_NAME=""
ADMIN_EMAIL=""
VERBOSE=false
DRY_RUN=false
SKIP_BILLING=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project-id ID         GCP Project ID (must be globally unique)"
    echo "  -n, --project-name NAME     Human-readable project name"
    echo "  -b, --billing-account ID    Billing account ID"
    echo "  -e, --admin-email EMAIL     Administrator email address"
    echo ""
    echo "Optional Options:"
    echo "  -o, --organization-id ID    Organization ID (for enterprise)"
    echo "  -r, --region REGION         GCP region (default: us-central1)"
    echo "  -z, --zone ZONE             GCP zone (default: us-central1-a)"
    echo "  -d, --domain DOMAIN         Custom domain name"
    echo "  --environment ENV           Environment name (default: production)"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  --skip-billing              Skip billing account setup"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -p misinformation-heatmap-prod -n 'Misinformation Heatmap Production' \\"
    echo "     -b 012345-678901-ABCDEF -e admin@company.com"
    echo ""
    echo "  $0 -p my-heatmap-project -n 'My Heatmap' -b BILLING_ID \\"
    echo "     -e admin@example.com -d heatmap.example.com --verbose"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            -n|--project-name)
                PROJECT_NAME="$2"
                shift 2
                ;;
            -o|--organization-id)
                ORGANIZATION_ID="$2"
                shift 2
                ;;
            -b|--billing-account)
                BILLING_ACCOUNT_ID="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -z|--zone)
                ZONE="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            -e|--admin-email)
                ADMIN_EMAIL="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
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
            --skip-billing)
                SKIP_BILLING=true
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
    local errors=0
    
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required (--project-id)"
        errors=$((errors + 1))
    fi
    
    if [[ -z "$PROJECT_NAME" ]]; then
        print_error "Project name is required (--project-name)"
        errors=$((errors + 1))
    fi
    
    if [[ -z "$BILLING_ACCOUNT_ID" && "$SKIP_BILLING" != true ]]; then
        print_error "Billing account ID is required (--billing-account) or use --skip-billing"
        errors=$((errors + 1))
    fi
    
    if [[ -z "$ADMIN_EMAIL" ]]; then
        print_error "Administrator email is required (--admin-email)"
        errors=$((errors + 1))
    fi
    
    # Validate project ID format
    if [[ ! "$PROJECT_ID" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
        print_error "Project ID must be 6-30 characters, start with lowercase letter, contain only lowercase letters, numbers, and hyphens"
        errors=$((errors + 1))
    fi
    
    # Validate email format
    if [[ ! "$ADMIN_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        print_error "Invalid email format: $ADMIN_EMAIL"
        errors=$((errors + 1))
    fi
    
    if [[ $errors -gt 0 ]]; then
        print_error "Please fix the above errors and try again"
        exit 1
    fi
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud SDK is not installed."
        print_status "Please install it from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "You are not authenticated with Google Cloud."
        print_status "Please run: gcloud auth login"
        exit 1
    fi
    
    # Check gcloud version
    local gcloud_version=$(gcloud version --format="value(Google Cloud SDK)")
    print_status "Using Google Cloud SDK version: $gcloud_version"
    
    print_success "Prerequisites check completed"
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

create_project() {
    print_header "Creating GCP Project"
    
    # Check if project already exists
    if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
        print_warning "Project $PROJECT_ID already exists"
        return 0
    fi
    
    # Create project
    local create_cmd="gcloud projects create $PROJECT_ID --name='$PROJECT_NAME'"
    if [[ -n "$ORGANIZATION_ID" ]]; then
        create_cmd="$create_cmd --organization=$ORGANIZATION_ID"
    fi
    
    execute_command "$create_cmd" "Creating project $PROJECT_ID..."
    
    # Set as default project
    execute_command "gcloud config set project $PROJECT_ID" "Setting default project..."
    
    print_success "Project $PROJECT_ID created successfully"
}

setup_billing() {
    if [[ "$SKIP_BILLING" == true ]]; then
        print_warning "Skipping billing setup as requested"
        return 0
    fi
    
    print_header "Setting up Billing"
    
    # Link billing account
    execute_command "gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID" \
        "Linking billing account..."
    
    print_success "Billing setup completed"
}

enable_apis() {
    print_header "Enabling Required APIs"
    
    local apis=(
        "cloudbuild.googleapis.com"          # Cloud Build for CI/CD
        "run.googleapis.com"                 # Cloud Run for container hosting
        "bigquery.googleapis.com"            # BigQuery for data storage
        "pubsub.googleapis.com"              # Pub/Sub for event processing
        "storage-api.googleapis.com"         # Cloud Storage
        "storage-component.googleapis.com"   # Cloud Storage components
        "monitoring.googleapis.com"          # Cloud Monitoring
        "logging.googleapis.com"             # Cloud Logging
        "clouderrorreporting.googleapis.com" # Error Reporting
        "cloudtrace.googleapis.com"          # Cloud Trace
        "cloudprofiler.googleapis.com"       # Cloud Profiler
        "secretmanager.googleapis.com"       # Secret Manager
        "compute.googleapis.com"             # Compute Engine (for networking)
        "dns.googleapis.com"                 # Cloud DNS
        "certificatemanager.googleapis.com"  # Certificate Manager
        "cloudbilling.googleapis.com"        # Billing API
        "cloudresourcemanager.googleapis.com" # Resource Manager
        "iam.googleapis.com"                 # Identity and Access Management
        "iamcredentials.googleapis.com"      # IAM Service Account Credentials
        "serviceusage.googleapis.com"        # Service Usage API
    )
    
    print_status "Enabling ${#apis[@]} APIs..."
    
    for api in "${apis[@]}"; do
        execute_command "gcloud services enable $api" "Enabling $api"
    done
    
    print_success "All APIs enabled successfully"
}

setup_iam() {
    print_header "Setting up IAM and Service Accounts"
    
    # Create service account for the application
    local sa_name="misinformation-heatmap"
    local sa_email="$sa_name@$PROJECT_ID.iam.gserviceaccount.com"
    
    execute_command "gcloud iam service-accounts create $sa_name --display-name='Misinformation Heatmap Service Account' --description='Service account for the misinformation heatmap application'" \
        "Creating application service account..."
    
    # Grant necessary roles to service account
    local roles=(
        "roles/bigquery.dataEditor"          # BigQuery data access
        "roles/bigquery.jobUser"             # BigQuery job execution
        "roles/pubsub.publisher"             # Pub/Sub publishing
        "roles/pubsub.subscriber"            # Pub/Sub subscription
        "roles/storage.objectAdmin"          # Cloud Storage access
        "roles/monitoring.metricWriter"      # Write metrics
        "roles/logging.logWriter"            # Write logs
        "roles/errorreporting.writer"        # Error reporting
        "roles/cloudtrace.agent"             # Tracing
        "roles/secretmanager.secretAccessor" # Secret access
    )
    
    for role in "${roles[@]}"; do
        execute_command "gcloud projects add-iam-policy-binding $PROJECT_ID --member='serviceAccount:$sa_email' --role='$role'" \
            "Granting $role to service account"
    done
    
    # Create and download service account key
    local key_file="$PROJECT_ID-service-account.json"
    execute_command "gcloud iam service-accounts keys create $key_file --iam-account=$sa_email" \
        "Creating service account key..."
    
    print_success "Service account key saved to: $key_file"
    print_warning "Keep this key file secure and do not commit it to version control!"
    
    print_success "IAM setup completed"
}

setup_storage() {
    print_header "Setting up Cloud Storage"
    
    # Create buckets
    local buckets=(
        "$PROJECT_ID-backups:Backups and archives"
        "$PROJECT_ID-logs:Application logs"
        "$PROJECT_ID-static:Static assets and uploads"
        "$PROJECT_ID-config:Configuration files"
    )
    
    for bucket_info in "${buckets[@]}"; do
        local bucket_name=$(echo "$bucket_info" | cut -d: -f1)
        local bucket_desc=$(echo "$bucket_info" | cut -d: -f2)
        
        execute_command "gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$bucket_name" \
            "Creating bucket: $bucket_name ($bucket_desc)"
        
        # Set lifecycle policy for logs bucket
        if [[ "$bucket_name" == *"-logs" ]]; then
            cat > /tmp/lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF
            execute_command "gsutil lifecycle set /tmp/lifecycle.json gs://$bucket_name" \
                "Setting lifecycle policy for logs bucket"
        fi
    done
    
    print_success "Cloud Storage setup completed"
}

setup_secrets() {
    print_header "Setting up Secret Manager"
    
    # Create secrets for sensitive configuration
    local secrets=(
        "api-keys:API keys for authentication"
        "huggingface-token:HuggingFace API token"
        "watson-api-key:IBM Watson API key"
        "database-url:Database connection string"
    )
    
    for secret_info in "${secrets[@]}"; do
        local secret_name=$(echo "$secret_info" | cut -d: -f1)
        local secret_desc=$(echo "$secret_info" | cut -d: -f2)
        
        execute_command "gcloud secrets create $secret_name --replication-policy='automatic' --labels='app=misinformation-heatmap,env=$ENVIRONMENT'" \
            "Creating secret: $secret_name"
    done
    
    print_success "Secret Manager setup completed"
    print_warning "Remember to add actual secret values using: gcloud secrets versions add SECRET_NAME --data-file=FILE"
}

generate_deployment_config() {
    print_header "Generating Deployment Configuration"
    
    # Create production environment file
    cat > ".env.production" << EOF
# Production Environment Configuration
# Generated by GCP setup script on $(date)

# Application Configuration
MODE=cloud
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8080

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
BIGQUERY_DATASET=misinformation_heatmap
BIGQUERY_LOCATION=$REGION

# Pub/Sub Configuration
PUBSUB_EVENTS_RAW_TOPIC=events-raw
PUBSUB_EVENTS_PROCESSED_TOPIC=events-processed
PUBSUB_EVENTS_VALIDATED_TOPIC=events-validated

# Security Configuration
API_KEY_ENABLED=true
# API_KEYS=["your-api-key-1","your-api-key-2"]  # Set via Secret Manager
CORS_ORIGINS=["https://$DOMAIN_NAME"]

# Performance Configuration
CACHE_TYPE=redis
CACHE_TTL=300
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Monitoring Configuration
ENABLE_METRICS=true
ENABLE_TRACING=true
TRACING_SAMPLE_RATE=0.1

# Storage Configuration
DATA_SOURCES_CONFIG_PATH=/app/config/data_sources.yaml

# Version
VERSION=latest
EOF
    
    print_success "Production environment configuration created"
}

main() {
    print_header "GCP Production Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    check_prerequisites
    
    print_status "Starting GCP setup with the following configuration:"
    print_status "  Project ID: $PROJECT_ID"
    print_status "  Project Name: $PROJECT_NAME"
    print_status "  Region: $REGION"
    print_status "  Environment: $ENVIRONMENT"
    print_status "  Admin Email: $ADMIN_EMAIL"
    if [[ -n "$DOMAIN_NAME" ]]; then
        print_status "  Domain: $DOMAIN_NAME"
    fi
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Execute setup steps
    create_project
    setup_billing
    enable_apis
    setup_iam
    setup_storage
    setup_secrets
    generate_deployment_config
    
    print_header "Setup Complete!"
    print_success "GCP project $PROJECT_ID is ready for production deployment"
    print_status ""
    print_status "Next steps:"
    print_status "1. Add secret values: gcloud secrets versions add SECRET_NAME --data-file=FILE"
    print_status "2. Run BigQuery setup: ./scripts/setup_bigquery.sh --project $PROJECT_ID"
    print_status "3. Run Pub/Sub setup: ./scripts/setup_pubsub.sh --project $PROJECT_ID"
    print_status "4. Deploy application: ./scripts/deploy_cloudrun.sh"
    print_status ""
    print_warning "Service account key saved to: $PROJECT_ID-service-account.json"
    print_warning "Keep this file secure and do not commit to version control!"
}

# Run main function with all arguments
main "$@"