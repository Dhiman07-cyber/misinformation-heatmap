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

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="misinformation-heatmap"
IMAGE_TAG="latest"
DOMAIN_NAME=""
ENVIRONMENT="production"
MIN_INSTANCES=1
MAX_INSTANCES=10
CPU_LIMIT="2"
MEMORY_LIMIT="4Gi"
TIMEOUT="300"
CONCURRENCY=100
VERBOSE=false
DRY_RUN=false
BUILD_ONLY=false
DEPLOY_ONLY=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project PROJECT_ID    GCP Project ID"
    echo ""
    echo "Optional Options:"
    echo "  -r, --region REGION         Cloud Run region (default: us-central1)"
    echo "  -s, --service SERVICE       Service name (default: misinformation-heatmap)"
    echo "  -t, --tag TAG               Image tag (default: latest)"
    echo "  -d, --domain DOMAIN         Custom domain name"
    echo "  -e, --environment ENV       Environment (default: production)"
    echo "  --min-instances NUM         Minimum instances (default: 1)"
    echo "  --max-instances NUM         Maximum instances (default: 10)"
    echo "  --cpu CPU                   CPU limit (default: 2)"
    echo "  --memory MEMORY             Memory limit (default: 4Gi)"
    echo "  --timeout SECONDS           Request timeout (default: 300)"
    echo "  --concurrency NUM           Max concurrent requests (default: 100)"
    echo "  --build-only                Only build the image, don't deploy"
    echo "  --deploy-only               Only deploy, don't build"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -p my-project-id"
    echo "  $0 -p my-project-id -d heatmap.example.com --max-instances 20"
    echo "  $0 -p my-project-id --build-only"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project)
                PROJECT_ID="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -s|--service)
                SERVICE_NAME="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -d|--domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
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
            --cpu)
                CPU_LIMIT="$2"
                shift 2
                ;;
            --memory)
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
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            --deploy-only)
                DEPLOY_ONLY=true
                shift
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
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required (--project)"
        exit 1
    fi
    
    if [[ "$BUILD_ONLY" == true && "$DEPLOY_ONLY" == true ]]; then
        print_error "Cannot specify both --build-only and --deploy-only"
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
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud SDK is not installed."
        exit 1
    fi
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "You are not authenticated with Google Cloud."
        print_status "Please run: gcloud auth login"
        exit 1
    fi
    
    # Set project
    execute_command "gcloud config set project $PROJECT_ID" "Setting project..."
    
    # Check if required files exist
    if [[ ! -f "Dockerfile" ]]; then
        print_error "Dockerfile not found in current directory"
        exit 1
    fi
    
    if [[ ! -f ".env.production" ]]; then
        print_warning ".env.production not found. Using .env.example as template."
        if [[ -f ".env.example" ]]; then
            cp .env.example .env.production
        fi
    fi
    
    print_success "Prerequisites check completed"
}

build_image() {
    if [[ "$DEPLOY_ONLY" == true ]]; then
        print_status "Skipping build (--deploy-only specified)"
        return 0
    fi
    
    print_header "Building Container Image"
    
    local image_name="gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG"
    
    # Build the Docker image
    execute_command "docker build -t '$image_name' --target production ." \
        "Building production Docker image..."
    
    # Push to Google Container Registry
    execute_command "docker push '$image_name'" \
        "Pushing image to Container Registry..."
    
    print_success "Image built and pushed: $image_name"
}

prepare_secrets() {
    print_header "Preparing Secrets"
    
    # Check if service account key exists
    local key_file="$PROJECT_ID-service-account.json"
    if [[ ! -f "$key_file" ]]; then
        print_warning "Service account key not found: $key_file"
        print_status "Creating new service account key..."
        
        local sa_email="misinformation-heatmap@$PROJECT_ID.iam.gserviceaccount.com"
        execute_command "gcloud iam service-accounts keys create '$key_file' --iam-account='$sa_email'" \
            "Creating service account key..."
    fi
    
    # Create secret for service account key
    if ! gcloud secrets describe "service-account-key" --project="$PROJECT_ID" &>/dev/null; then
        execute_command "gcloud secrets create service-account-key --replication-policy='automatic' --project='$PROJECT_ID'" \
            "Creating service account key secret..."
        
        execute_command "gcloud secrets versions add service-account-key --data-file='$key_file' --project='$PROJECT_ID'" \
            "Adding service account key to secret..."
    fi
    
    # Create secret for environment variables
    if [[ -f ".env.production" ]]; then
        if ! gcloud secrets describe "env-production" --project="$PROJECT_ID" &>/dev/null; then
            execute_command "gcloud secrets create env-production --replication-policy='automatic' --project='$PROJECT_ID'" \
                "Creating production environment secret..."
            
            execute_command "gcloud secrets versions add env-production --data-file='.env.production' --project='$PROJECT_ID'" \
                "Adding production environment to secret..."
        fi
    fi
    
    print_success "Secrets prepared"
}

deploy_service() {
    if [[ "$BUILD_ONLY" == true ]]; then
        print_status "Skipping deployment (--build-only specified)"
        return 0
    fi
    
    print_header "Deploying to Cloud Run"
    
    local image_name="gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG"
    local sa_email="misinformation-heatmap@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Prepare deployment command
    local deploy_cmd="gcloud run deploy '$SERVICE_NAME' \
        --image='$image_name' \
        --platform=managed \
        --region='$REGION' \
        --project='$PROJECT_ID' \
        --service-account='$sa_email' \
        --allow-unauthenticated \
        --port=8080 \
        --cpu='$CPU_LIMIT' \
        --memory='$MEMORY_LIMIT' \
        --timeout='$TIMEOUT' \
        --concurrency='$CONCURRENCY' \
        --min-instances='$MIN_INSTANCES' \
        --max-instances='$MAX_INSTANCES' \
        --set-env-vars='MODE=cloud,ENVIRONMENT=$ENVIRONMENT,GOOGLE_CLOUD_PROJECT=$PROJECT_ID' \
        --set-secrets='/app/credentials.json=service-account-key:latest' \
        --labels='app=misinformation-heatmap,environment=$ENVIRONMENT,version=$IMAGE_TAG'"
    
    execute_command "$deploy_cmd" "Deploying service to Cloud Run..."
    
    # Get service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")
    
    print_success "Service deployed successfully!"
    print_status "Service URL: $service_url"
    
    # Update Pub/Sub push subscriptions with actual URL
    update_push_subscriptions "$service_url"
    
    return 0
}

update_push_subscriptions() {
    local service_url="$1"
    
    print_header "Updating Pub/Sub Push Subscriptions"
    
    # Update push subscriptions with actual service URL
    local push_subscriptions=(
        "events-raw-push:/webhooks/events/raw"
        "events-processed-push:/webhooks/events/processed"
        "events-validated-push:/webhooks/events/validated"
        "monitoring-alerts-push:/webhooks/monitoring/alerts"
    )
    
    for sub_info in "${push_subscriptions[@]}"; do
        local sub_name=$(echo "$sub_info" | cut -d: -f1)
        local endpoint_path=$(echo "$sub_info" | cut -d: -f2)
        local push_endpoint="$service_url$endpoint_path"
        
        # Check if subscription exists
        if gcloud pubsub subscriptions describe "$sub_name" --project="$PROJECT_ID" &>/dev/null; then
            execute_command "gcloud pubsub subscriptions modify-push-config '$sub_name' \
                --push-endpoint='$push_endpoint' \
                --project='$PROJECT_ID'" \
                "Updating push subscription: $sub_name"
        else
            print_warning "Subscription $sub_name not found, skipping"
        fi
    done
    
    print_success "Push subscriptions updated"
}

setup_custom_domain() {
    if [[ -z "$DOMAIN_NAME" ]]; then
        print_status "No custom domain specified, skipping domain setup"
        return 0
    fi
    
    print_header "Setting up Custom Domain"
    
    # Create domain mapping
    execute_command "gcloud run domain-mappings create \
        --service='$SERVICE_NAME' \
        --domain='$DOMAIN_NAME' \
        --region='$REGION' \
        --project='$PROJECT_ID'" \
        "Creating domain mapping..."
    
    # Get DNS records to configure
    local dns_records=$(gcloud run domain-mappings describe "$DOMAIN_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.resourceRecords[].name,status.resourceRecords[].rrdata)")
    
    print_success "Domain mapping created"
    print_status "Configure the following DNS records:"
    echo "$dns_records"
    
    print_warning "DNS propagation may take up to 24 hours"
}

setup_monitoring() {
    print_header "Setting up Cloud Run Monitoring"
    
    # Create monitoring dashboard
    cat > /tmp/cloudrun_dashboard.json << EOF
{
  "displayName": "Misinformation Heatmap - Cloud Run Monitoring",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ]
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "widget": {
          "title": "Response Latency",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_MEAN",
                      "crossSeriesReducer": "REDUCE_MEAN"
                    }
                  }
                },
                "plotType": "LINE"
              }
            ]
          }
        }
      }
    ]
  }
}
EOF

    print_status "Monitoring dashboard configuration created at /tmp/cloudrun_dashboard.json"
    print_warning "Please create the dashboard manually in Cloud Monitoring console"
    
    print_success "Monitoring setup prepared"
}

run_health_check() {
    print_header "Running Health Check"
    
    # Get service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)" 2>/dev/null)
    
    if [[ -z "$service_url" ]]; then
        print_warning "Could not get service URL, skipping health check"
        return 0
    fi
    
    print_status "Service URL: $service_url"
    
    # Test health endpoint
    print_status "Testing health endpoint..."
    if curl -f -s "$service_url/health" > /dev/null; then
        print_success "Health check passed"
    else
        print_warning "Health check failed or endpoint not available"
    fi
    
    # Test API endpoints
    print_status "Testing API endpoints..."
    if curl -f -s "$service_url/api/v1/health" > /dev/null; then
        print_success "API health check passed"
    else
        print_warning "API health check failed or endpoint not available"
    fi
    
    print_success "Health check completed"
}

main() {
    print_header "Cloud Run Deployment for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Deployment configuration:"
    print_status "  Project ID: $PROJECT_ID"
    print_status "  Region: $REGION"
    print_status "  Service Name: $SERVICE_NAME"
    print_status "  Image Tag: $IMAGE_TAG"
    print_status "  Environment: $ENVIRONMENT"
    print_status "  Min Instances: $MIN_INSTANCES"
    print_status "  Max Instances: $MAX_INSTANCES"
    print_status "  CPU: $CPU_LIMIT"
    print_status "  Memory: $MEMORY_LIMIT"
    if [[ -n "$DOMAIN_NAME" ]]; then
        print_status "  Domain: $DOMAIN_NAME"
    fi
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deployment cancelled by user"
            exit 0
        fi
    fi
    
    # Execute deployment steps
    check_prerequisites
    build_image
    prepare_secrets
    deploy_service
    setup_custom_domain
    setup_monitoring
    run_health_check
    
    print_header "Deployment Complete!"
    
    # Get final service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)" 2>/dev/null)
    
    print_success "Misinformation Heatmap deployed successfully!"
    print_status ""
    print_status "Service Details:"
    print_status "  Service URL: $service_url"
    print_status "  API Documentation: $service_url/docs"
    print_status "  Health Check: $service_url/health"
    if [[ -n "$DOMAIN_NAME" ]]; then
        print_status "  Custom Domain: https://$DOMAIN_NAME (after DNS propagation)"
    fi
    print_status ""
    print_status "Next steps:"
    print_status "1. Test the deployed service"
    print_status "2. Configure monitoring alerts"
    print_status "3. Set up CI/CD pipeline"
    print_status "4. Configure custom domain DNS (if applicable)"
    
    # Cleanup temp files
    rm -f /tmp/cloudrun_dashboard.json
}

# Run main function with all arguments
main "$@"