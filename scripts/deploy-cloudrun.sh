#!/bin/bash

# Cloud Run Deployment Script for Misinformation Heatmap
# Deploys the containerized application to Google Cloud Run

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
REGION="us-central1"
SERVICE_NAME="misinformation-heatmap"
IMAGE_NAME="misinformation-heatmap"
ENVIRONMENT="production"
DOMAIN_NAME=""
MIN_INSTANCES=1
MAX_INSTANCES=10
CPU_LIMIT="2"
MEMORY_LIMIT="4Gi"
TIMEOUT="300"
CONCURRENCY=100
PORT=8000
VERBOSE=false
DRY_RUN=false
BUILD_ONLY=false
DEPLOY_ONLY=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project-id ID         GCP Project ID"
    echo ""
    echo "Optional Options:"
    echo "  -r, --region REGION         GCP region (default: us-central1)"
    echo "  -s, --service-name NAME     Cloud Run service name (default: misinformation-heatmap)"
    echo "  -i, --image-name NAME       Container image name (default: misinformation-heatmap)"
    echo "  -e, --environment ENV       Environment (default: production)"
    echo "  -d, --domain DOMAIN         Custom domain name"
    echo "  --min-instances NUM         Minimum instances (default: 1)"
    echo "  --max-instances NUM         Maximum instances (default: 10)"
    echo "  --cpu-limit CPU             CPU limit (default: 2)"
    echo "  --memory-limit MEM          Memory limit (default: 4Gi)"
    echo "  --timeout SECONDS           Request timeout (default: 300)"
    echo "  --concurrency NUM           Max concurrent requests per instance (default: 100)"
    echo "  --port PORT                 Container port (default: 8000)"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be deployed without deploying"
    echo "  --build-only                Only build the container image"
    echo "  --deploy-only               Only deploy (skip build)"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --project-id misinformation-heatmap-prod"
    echo "  $0 -p my-project --domain heatmap.example.com --max-instances 20"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -s|--service-name)
                SERVICE_NAME="$2"
                shift 2
                ;;
            -i|--image-name)
                IMAGE_NAME="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            --min-instances)
                MIN_INSTANCES="$2"
                shift 2
                ;;
            --max-instances)
                MAX_INSTANCES="$2"
                shift 2
                ;;
            --cpu-limit)
                CPU_LIMIT="$2"
                shift 2
                ;;
            --memory-limit)
                MEMORY_LIMIT="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --concurrency)
                CONCURRENCY="$2"
                shift 2
                ;;
            --port)
                PORT="$2"
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
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            --deploy-only)
                DEPLOY_ONLY=true
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
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required. Use --project-id flag."
        exit 1
    fi
    
    if [[ "$BUILD_ONLY" == true && "$DEPLOY_ONLY" == true ]]; then
        print_error "Cannot use --build-only and --deploy-only together."
        exit 1
    fi
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
        print_error "Not authenticated with gcloud. Please run 'gcloud auth login' first."
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    # Check if required APIs are enabled
    local required_apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "containerregistry.googleapis.com"
    )
    
    for api in "${required_apis[@]}"; do
        if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_error "Required API $api is not enabled. Please enable it first."
            exit 1
        fi
    done
    
    print_success "Prerequisites check completed"
}

build_image() {
    if [[ "$DEPLOY_ONLY" == true ]]; then
        print_status "Skipping build (deploy-only mode)"
        return
    fi
    
    print_header "Building Container Image"
    
    local image_tag="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest"
    local build_tag="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S)"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would build image: $image_tag"
        return
    fi
    
    print_status "Building image: $image_tag"
    
    # Build using Cloud Build for better performance and caching
    local build_config="/tmp/cloudbuild.yaml"
    
    cat > "$build_config" << EOF
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', '$image_tag',
      '-t', '$build_tag',
      '--cache-from', '$image_tag',
      '.'
    ]
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '$image_tag']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '$build_tag']

# Store images in Container Registry
images:
  - '$image_tag'
  - '$build_tag'

# Build options
options:
  machineType: 'E2_HIGHCPU_8'
  diskSizeGb: 100
  logging: CLOUD_LOGGING_ONLY

# Timeout for the build
timeout: '1200s'
EOF
    
    if [[ "$VERBOSE" == true ]]; then
        print_status "Using build configuration:"
        cat "$build_config"
    fi
    
    # Submit build to Cloud Build
    gcloud builds submit --config="$build_config" .
    
    # Clean up
    rm -f "$build_config"
    
    print_success "Container image built successfully"
    
    if [[ "$BUILD_ONLY" == true ]]; then
        print_status "Build-only mode complete"
        exit 0
    fi
}

create_env_file() {
    print_status "Creating environment configuration..."
    
    local env_file="/tmp/cloudrun-env.yaml"
    
    cat > "$env_file" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ${SERVICE_NAME}-config
data:
  ENVIRONMENT: "${ENVIRONMENT}"
  PROJECT_ID: "${PROJECT_ID}"
  REGION: "${REGION}"
  PORT: "${PORT}"
  # Database configuration
  DATABASE_URL: "projects/${PROJECT_ID}/secrets/database-url/versions/latest"
  
  # API configuration
  API_KEY: "projects/${PROJECT_ID}/secrets/api-key/versions/latest"
  JWT_SECRET: "projects/${PROJECT_ID}/secrets/jwt-secret/versions/latest"
  
  # External service configuration
  WATSON_API_KEY: "projects/${PROJECT_ID}/secrets/watson-api-key/versions/latest"
  SATELLITE_API_KEY: "projects/${PROJECT_ID}/secrets/satellite-api-key/versions/latest"
  
  # BigQuery configuration
  BIGQUERY_DATASET: "misinformation_heatmap"
  
  # Pub/Sub configuration
  PUBSUB_TOPIC_RAW: "events-raw"
  PUBSUB_TOPIC_PROCESSED: "events-processed"
  PUBSUB_TOPIC_VALIDATED: "events-validated"
  PUBSUB_TOPIC_ALERTS: "alerts"
  
  # Storage configuration
  STORAGE_BUCKET_LOGS: "${PROJECT_ID}-logs"
  STORAGE_BUCKET_STATIC: "${PROJECT_ID}-static"
  STORAGE_BUCKET_BACKUPS: "${PROJECT_ID}-backups"
  
  # Performance configuration
  MAX_WORKERS: "4"
  CACHE_TTL: "300"
  RATE_LIMIT_PER_MINUTE: "1000"
  
  # Monitoring configuration
  ENABLE_METRICS: "true"
  ENABLE_TRACING: "true"
  LOG_LEVEL: "INFO"
EOF
    
    echo "$env_file"
}

deploy_service() {
    if [[ "$BUILD_ONLY" == true ]]; then
        return
    fi
    
    print_header "Deploying to Cloud Run"
    
    local image_tag="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest"
    local service_account="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would deploy service: $SERVICE_NAME"
        print_status "[DRY RUN] Image: $image_tag"
        print_status "[DRY RUN] Service account: $service_account"
        return
    fi
    
    print_status "Deploying service: $SERVICE_NAME"
    print_status "Image: $image_tag"
    print_status "Region: $REGION"
    
    # Build deployment command
    local deploy_cmd=(
        "gcloud" "run" "deploy" "$SERVICE_NAME"
        "--image=$image_tag"
        "--region=$REGION"
        "--platform=managed"
        "--service-account=$service_account"
        "--port=$PORT"
        "--memory=$MEMORY_LIMIT"
        "--cpu=$CPU_LIMIT"
        "--timeout=${TIMEOUT}s"
        "--concurrency=$CONCURRENCY"
        "--min-instances=$MIN_INSTANCES"
        "--max-instances=$MAX_INSTANCES"
        "--allow-unauthenticated"
        "--set-env-vars=ENVIRONMENT=$ENVIRONMENT,PROJECT_ID=$PROJECT_ID,REGION=$REGION,PORT=$PORT"
        "--set-secrets=DATABASE_URL=database-url:latest"
        "--set-secrets=API_KEY=api-key:latest"
        "--set-secrets=JWT_SECRET=jwt-secret:latest"
        "--set-secrets=WATSON_API_KEY=watson-api-key:latest"
        "--set-secrets=SATELLITE_API_KEY=satellite-api-key:latest"
    )
    
    if [[ "$VERBOSE" == true ]]; then
        print_status "Executing: ${deploy_cmd[*]}"
    fi
    
    # Execute deployment
    "${deploy_cmd[@]}"
    
    # Get service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    print_success "Service deployed successfully!"
    print_status "Service URL: $service_url"
    
    # Configure custom domain if specified
    if [[ -n "$DOMAIN_NAME" ]]; then
        configure_custom_domain "$service_url"
    fi
    
    # Set up traffic allocation (100% to latest revision)
    print_status "Configuring traffic allocation..."
    gcloud run services update-traffic "$SERVICE_NAME" \
        --region="$REGION" \
        --to-latest
    
    print_success "Traffic allocation configured"
}

configure_custom_domain() {
    local service_url="$1"
    
    print_header "Configuring Custom Domain"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would configure domain: $DOMAIN_NAME"
        return
    fi
    
    print_status "Configuring domain: $DOMAIN_NAME"
    
    # Create domain mapping
    gcloud run domain-mappings create \
        --service="$SERVICE_NAME" \
        --domain="$DOMAIN_NAME" \
        --region="$REGION"
    
    # Get DNS records that need to be configured
    local dns_records=$(gcloud run domain-mappings describe "$DOMAIN_NAME" \
        --region="$REGION" \
        --format="value(status.resourceRecords[].name,status.resourceRecords[].rrdata)")
    
    print_success "Domain mapping created"
    print_warning "Please configure the following DNS records:"
    echo "$dns_records"
}

setup_monitoring() {
    print_header "Setting up Monitoring"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would setup monitoring"
        return
    fi
    
    # Create uptime check
    print_status "Creating uptime check..."
    
    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    local uptime_config="/tmp/uptime-check.json"
    
    cat > "$uptime_config" << EOF
{
  "displayName": "Misinformation Heatmap Uptime Check",
  "monitoredResource": {
    "type": "uptime_url",
    "labels": {
      "project_id": "$PROJECT_ID",
      "host": "$(echo $service_url | sed 's|https://||' | sed 's|/.*||')"
    }
  },
  "httpCheck": {
    "path": "/health",
    "port": 443,
    "useSsl": true,
    "validateSsl": true
  },
  "period": "60s",
  "timeout": "10s"
}
EOF
    
    gcloud alpha monitoring uptime create --config-from-file="$uptime_config"
    
    rm -f "$uptime_config"
    
    print_success "Monitoring setup completed"
}

run_health_check() {
    print_header "Running Health Check"
    
    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [[ -z "$service_url" ]]; then
        print_warning "Service not found or not deployed yet"
        return
    fi
    
    print_status "Checking service health: $service_url/health"
    
    # Wait for service to be ready
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "$service_url/health" > /dev/null 2>&1; then
            print_success "Service is healthy!"
            break
        else
            print_status "Attempt $attempt/$max_attempts: Service not ready yet..."
            sleep 10
            ((attempt++))
        fi
    done
    
    if [[ $attempt -gt $max_attempts ]]; then
        print_error "Service health check failed after $max_attempts attempts"
        return 1
    fi
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    
    local endpoints=(
        "/health"
        "/api/v1/events"
        "/api/v1/states"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="$service_url$endpoint"
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        
        if [[ "$status_code" =~ ^[23] ]]; then
            print_success "✓ $endpoint (HTTP $status_code)"
        else
            print_warning "✗ $endpoint (HTTP $status_code)"
        fi
    done
}

main() {
    print_header "Cloud Run Deployment for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    check_prerequisites
    
    print_status "Configuration:"
    print_status "  Project ID: $PROJECT_ID"
    print_status "  Region: $REGION"
    print_status "  Service Name: $SERVICE_NAME"
    print_status "  Environment: $ENVIRONMENT"
    [[ -n "$DOMAIN_NAME" ]] && print_status "  Domain: $DOMAIN_NAME"
    print_status "  Min/Max Instances: $MIN_INSTANCES/$MAX_INSTANCES"
    print_status "  CPU/Memory: $CPU_LIMIT/$MEMORY_LIMIT"
    [[ "$DRY_RUN" == true ]] && print_warning "DRY RUN MODE - No actual changes will be made"
    
    echo ""
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deployment cancelled by user"
            exit 0
        fi
    fi
    
    # Execute deployment steps
    build_image
    deploy_service
    setup_monitoring
    run_health_check
    
    print_header "Deployment Complete!"
    
    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [[ -n "$service_url" ]]; then
        print_success "Service is live at: $service_url"
        print_status "API Documentation: $service_url/docs"
        print_status "Health Check: $service_url/health"
    fi
    
    print_status "Next steps:"
    print_status "1. Configure DNS records (if using custom domain)"
    print_status "2. Set up monitoring alerts"
    print_status "3. Configure CI/CD pipeline"
    print_status "4. Run load tests"
}

# Run main function with all arguments
main "$@"