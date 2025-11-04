#!/bin/bash

# Cloud Environment Configuration Template
# Sets up environment variables and configuration for cloud deployment

# This script should be sourced, not executed directly
# Usage: source cloud_env_template.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    print_error "This script should be sourced, not executed directly"
    print_status "Usage: source cloud_env_template.sh"
    exit 1
fi

print_status "Setting up cloud environment variables..."

# =============================================================================
# REQUIRED CONFIGURATION - MUST BE SET
# =============================================================================

# Google Cloud Project Configuration
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
export GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS:-/path/to/service-account.json}"

# Application Configuration
export MODE="cloud"
export ENVIRONMENT="${ENVIRONMENT:-production}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# =============================================================================
# GOOGLE CLOUD SERVICES CONFIGURATION
# =============================================================================

# Cloud Run Configuration
export CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-misinformation-heatmap}"
export CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
export CLOUD_RUN_MEMORY="${CLOUD_RUN_MEMORY:-2Gi}"
export CLOUD_RUN_CPU="${CLOUD_RUN_CPU:-1}"
export CLOUD_RUN_MIN_INSTANCES="${CLOUD_RUN_MIN_INSTANCES:-0}"
export CLOUD_RUN_MAX_INSTANCES="${CLOUD_RUN_MAX_INSTANCES:-10}"
export CLOUD_RUN_TIMEOUT="${CLOUD_RUN_TIMEOUT:-300}"
export CLOUD_RUN_CONCURRENCY="${CLOUD_RUN_CONCURRENCY:-80}"

# BigQuery Configuration
export BIGQUERY_DATASET="${BIGQUERY_DATASET:-misinformation_heatmap}"
export BIGQUERY_RAW_DATASET="${BIGQUERY_RAW_DATASET:-misinformation_raw}"
export BIGQUERY_ANALYTICS_DATASET="${BIGQUERY_ANALYTICS_DATASET:-misinformation_analytics}"
export BIGQUERY_LOCATION="${BIGQUERY_LOCATION:-US}"

# Pub/Sub Configuration
export PUBSUB_EVENTS_RAW_TOPIC="${PUBSUB_EVENTS_RAW_TOPIC:-events-raw}"
export PUBSUB_EVENTS_PROCESSED_TOPIC="${PUBSUB_EVENTS_PROCESSED_TOPIC:-events-processed}"
export PUBSUB_EVENTS_VALIDATED_TOPIC="${PUBSUB_EVENTS_VALIDATED_TOPIC:-events-validated}"
export PUBSUB_EVENTS_FAILED_TOPIC="${PUBSUB_EVENTS_FAILED_TOPIC:-events-failed}"
export PUBSUB_SYSTEM_ALERTS_TOPIC="${PUBSUB_SYSTEM_ALERTS_TOPIC:-system-alerts}"

# Pub/Sub Subscriptions
export PUBSUB_RAW_PROCESSOR_SUB="${PUBSUB_RAW_PROCESSOR_SUB:-events-raw-processor}"
export PUBSUB_NLP_PROCESSOR_SUB="${PUBSUB_NLP_PROCESSOR_SUB:-events-nlp-processor}"
export PUBSUB_SATELLITE_VALIDATOR_SUB="${PUBSUB_SATELLITE_VALIDATOR_SUB:-events-satellite-validator}"
export PUBSUB_STORAGE_WRITER_SUB="${PUBSUB_STORAGE_WRITER_SUB:-events-storage-writer}"

# Cloud Storage Configuration
export CLOUD_STORAGE_BUCKET="${CLOUD_STORAGE_BUCKET:-${GOOGLE_CLOUD_PROJECT}-misinformation-heatmap}"
export CLOUD_STORAGE_FRONTEND_BUCKET="${CLOUD_STORAGE_FRONTEND_BUCKET:-${GOOGLE_CLOUD_PROJECT}-misinformation-heatmap-frontend}"

# =============================================================================
# EXTERNAL SERVICES CONFIGURATION
# =============================================================================

# IBM Watson Discovery Configuration
export WATSON_DISCOVERY_API_KEY="${WATSON_DISCOVERY_API_KEY:-your-watson-api-key}"
export WATSON_DISCOVERY_URL="${WATSON_DISCOVERY_URL:-https://api.us-south.discovery.watson.cloud.ibm.com}"
export WATSON_DISCOVERY_VERSION="${WATSON_DISCOVERY_VERSION:-2019-04-30}"
export WATSON_DISCOVERY_ENVIRONMENT_ID="${WATSON_DISCOVERY_ENVIRONMENT_ID:-your-environment-id}"
export WATSON_DISCOVERY_COLLECTION_ID="${WATSON_DISCOVERY_COLLECTION_ID:-your-collection-id}"

# Hugging Face Configuration
export HUGGINGFACE_TOKEN="${HUGGINGFACE_TOKEN:-your-huggingface-token}"
export HUGGINGFACE_CACHE_DIR="${HUGGINGFACE_CACHE_DIR:-/tmp/huggingface_cache}"

# Google Earth Engine Configuration (if using)
export GOOGLE_EARTH_ENGINE_SERVICE_ACCOUNT="${GOOGLE_EARTH_ENGINE_SERVICE_ACCOUNT:-your-gee-service-account@project.iam.gserviceaccount.com}"
export GOOGLE_EARTH_ENGINE_PRIVATE_KEY_PATH="${GOOGLE_EARTH_ENGINE_PRIVATE_KEY_PATH:-/path/to/gee-private-key.json}"

# =============================================================================
# APPLICATION SPECIFIC CONFIGURATION
# =============================================================================

# API Configuration
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8080}"
export API_WORKERS="${API_WORKERS:-1}"
export API_TIMEOUT="${API_TIMEOUT:-300}"

# CORS Configuration
export CORS_ORIGINS="${CORS_ORIGINS:-[\"https://${CLOUD_STORAGE_FRONTEND_BUCKET}.storage.googleapis.com\",\"https://storage.googleapis.com\"]}"
export CORS_ALLOW_CREDENTIALS="${CORS_ALLOW_CREDENTIALS:-false}"
export CORS_ALLOW_METHODS="${CORS_ALLOW_METHODS:-[\"GET\",\"POST\",\"PUT\",\"DELETE\",\"OPTIONS\"]}"
export CORS_ALLOW_HEADERS="${CORS_ALLOW_HEADERS:-[\"*\"]}"

# Database Configuration (BigQuery)
export DATABASE_TYPE="bigquery"
export DATABASE_URL="bigquery://${GOOGLE_CLOUD_PROJECT}/${BIGQUERY_DATASET}"

# NLP Configuration
export NLP_MODEL_NAME="${NLP_MODEL_NAME:-ai4bharat/indic-bert}"
export NLP_MAX_LENGTH="${NLP_MAX_LENGTH:-512}"
export NLP_BATCH_SIZE="${NLP_BATCH_SIZE:-8}"
export NLP_DEVICE="${NLP_DEVICE:-cpu}"

# Satellite Validation Configuration
export SATELLITE_VALIDATION_ENABLED="${SATELLITE_VALIDATION_ENABLED:-true}"
export SATELLITE_SIMILARITY_THRESHOLD="${SATELLITE_SIMILARITY_THRESHOLD:-0.3}"
export SATELLITE_CONFIDENCE_THRESHOLD="${SATELLITE_CONFIDENCE_THRESHOLD:-0.7}"

# Caching Configuration
export CACHE_TYPE="${CACHE_TYPE:-memory}"
export CACHE_TTL="${CACHE_TTL:-300}"
export CACHE_MAX_SIZE="${CACHE_MAX_SIZE:-1000}"

# Rate Limiting Configuration
export RATE_LIMIT_ENABLED="${RATE_LIMIT_ENABLED:-true}"
export RATE_LIMIT_REQUESTS_PER_MINUTE="${RATE_LIMIT_REQUESTS_PER_MINUTE:-100}"
export RATE_LIMIT_BURST="${RATE_LIMIT_BURST:-20}"

# Monitoring Configuration
export ENABLE_METRICS="${ENABLE_METRICS:-true}"
export METRICS_PORT="${METRICS_PORT:-9090}"
export ENABLE_TRACING="${ENABLE_TRACING:-true}"
export TRACING_SAMPLE_RATE="${TRACING_SAMPLE_RATE:-0.1}"

# Health Check Configuration
export HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-30}"
export HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-10}"
export HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-3}"

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Authentication Configuration
export AUTH_ENABLED="${AUTH_ENABLED:-false}"
export AUTH_SECRET_KEY="${AUTH_SECRET_KEY:-your-secret-key}"
export AUTH_ALGORITHM="${AUTH_ALGORITHM:-HS256}"
export AUTH_ACCESS_TOKEN_EXPIRE_MINUTES="${AUTH_ACCESS_TOKEN_EXPIRE_MINUTES:-30}"

# API Key Configuration (for external access)
export API_KEY_ENABLED="${API_KEY_ENABLED:-false}"
export API_KEY_HEADER="${API_KEY_HEADER:-X-API-Key}"
export API_KEYS="${API_KEYS:-[]}"  # JSON array of valid API keys

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

# Container Registry Configuration
export CONTAINER_REGISTRY="${CONTAINER_REGISTRY:-gcr.io}"
export IMAGE_NAME="${IMAGE_NAME:-${CONTAINER_REGISTRY}/${GOOGLE_CLOUD_PROJECT}/${CLOUD_RUN_SERVICE}}"
export IMAGE_TAG="${IMAGE_TAG:-latest}"

# Build Configuration
export BUILD_TIMEOUT="${BUILD_TIMEOUT:-1200}"
export BUILD_MACHINE_TYPE="${BUILD_MACHINE_TYPE:-E2_HIGHCPU_8}"

# =============================================================================
# VALIDATION AND HELPER FUNCTIONS
# =============================================================================

# Function to validate required environment variables
validate_environment() {
    local required_vars=(
        "GOOGLE_CLOUD_PROJECT"
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" || "${!var}" == "your-"* ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            print_error "  - $var"
        done
        return 1
    fi
    
    return 0
}

# Function to show current configuration
show_configuration() {
    print_status "Current Cloud Configuration:"
    echo ""
    echo "Google Cloud:"
    echo "  Project: $GOOGLE_CLOUD_PROJECT"
    echo "  Region: $CLOUD_RUN_REGION"
    echo "  Service: $CLOUD_RUN_SERVICE"
    echo ""
    echo "BigQuery:"
    echo "  Dataset: $BIGQUERY_DATASET"
    echo "  Location: $BIGQUERY_LOCATION"
    echo ""
    echo "Pub/Sub Topics:"
    echo "  Raw Events: $PUBSUB_EVENTS_RAW_TOPIC"
    echo "  Processed Events: $PUBSUB_EVENTS_PROCESSED_TOPIC"
    echo "  Validated Events: $PUBSUB_EVENTS_VALIDATED_TOPIC"
    echo ""
    echo "Cloud Storage:"
    echo "  Main Bucket: $CLOUD_STORAGE_BUCKET"
    echo "  Frontend Bucket: $CLOUD_STORAGE_FRONTEND_BUCKET"
    echo ""
    echo "Application:"
    echo "  Mode: $MODE"
    echo "  Environment: $ENVIRONMENT"
    echo "  Log Level: $LOG_LEVEL"
}

# Function to create .env file for cloud deployment
create_cloud_env_file() {
    local env_file="${1:-.env.cloud}"
    
    print_status "Creating cloud environment file: $env_file"
    
    cat > "$env_file" << EOF
# Cloud Environment Configuration
# Generated on $(date)

# Application Configuration
MODE=$MODE
ENVIRONMENT=$ENVIRONMENT
LOG_LEVEL=$LOG_LEVEL

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS

# BigQuery Configuration
BIGQUERY_DATASET=$BIGQUERY_DATASET
BIGQUERY_RAW_DATASET=$BIGQUERY_RAW_DATASET
BIGQUERY_ANALYTICS_DATASET=$BIGQUERY_ANALYTICS_DATASET
BIGQUERY_LOCATION=$BIGQUERY_LOCATION
DATABASE_TYPE=$DATABASE_TYPE
DATABASE_URL=$DATABASE_URL

# Pub/Sub Configuration
PUBSUB_EVENTS_RAW_TOPIC=$PUBSUB_EVENTS_RAW_TOPIC
PUBSUB_EVENTS_PROCESSED_TOPIC=$PUBSUB_EVENTS_PROCESSED_TOPIC
PUBSUB_EVENTS_VALIDATED_TOPIC=$PUBSUB_EVENTS_VALIDATED_TOPIC
PUBSUB_RAW_PROCESSOR_SUB=$PUBSUB_RAW_PROCESSOR_SUB
PUBSUB_NLP_PROCESSOR_SUB=$PUBSUB_NLP_PROCESSOR_SUB
PUBSUB_SATELLITE_VALIDATOR_SUB=$PUBSUB_SATELLITE_VALIDATOR_SUB

# Cloud Storage Configuration
CLOUD_STORAGE_BUCKET=$CLOUD_STORAGE_BUCKET
CLOUD_STORAGE_FRONTEND_BUCKET=$CLOUD_STORAGE_FRONTEND_BUCKET

# External Services
WATSON_DISCOVERY_API_KEY=$WATSON_DISCOVERY_API_KEY
WATSON_DISCOVERY_URL=$WATSON_DISCOVERY_URL
HUGGINGFACE_TOKEN=$HUGGINGFACE_TOKEN

# API Configuration
API_HOST=$API_HOST
API_PORT=$API_PORT
CORS_ORIGINS=$CORS_ORIGINS

# NLP Configuration
NLP_MODEL_NAME=$NLP_MODEL_NAME
NLP_MAX_LENGTH=$NLP_MAX_LENGTH
NLP_BATCH_SIZE=$NLP_BATCH_SIZE

# Monitoring Configuration
ENABLE_METRICS=$ENABLE_METRICS
METRICS_PORT=$METRICS_PORT
ENABLE_TRACING=$ENABLE_TRACING

# Security Configuration
AUTH_ENABLED=$AUTH_ENABLED
API_KEY_ENABLED=$API_KEY_ENABLED
EOF

    print_success "Cloud environment file created: $env_file"
}

# =============================================================================
# INITIALIZATION
# =============================================================================

# Show configuration on source
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    print_success "Cloud environment variables loaded"
    
    # Validate configuration
    if validate_environment; then
        print_success "Environment validation passed"
    else
        print_warning "Environment validation failed - please update required variables"
    fi
fi

# Export functions for use in other scripts
export -f validate_environment
export -f show_configuration
export -f create_cloud_env_file