#!/bin/bash

# IBM Cloud Production Setup Script for Misinformation Heatmap
# Creates and configures a production-ready IBM Cloud environment

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
APP_NAME="misinformation-heatmap"
ORGANIZATION=""
SPACE="production"
ADMIN_EMAIL=""
VERBOSE=false
DRY_RUN=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -o, --org ORGANIZATION      IBM Cloud organization name"
    echo "  -e, --email EMAIL           Administrator email address"
    echo ""
    echo "Optional Options:"
    echo "  -r, --region REGION         IBM Cloud region (default: us-south)"
    echo "  -g, --resource-group GROUP  Resource group name (default: misinformation-heatmap)"
    echo "  -a, --app-name NAME         Application name (default: misinformation-heatmap)"
    echo "  -s, --space SPACE           Cloud Foundry space (default: production)"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -o 'your-email@example.com' -e 'admin@company.com'"
    echo "  $0 -o 'myorg' -e 'admin@company.com' -r 'eu-gb'"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -o|--org)
                ORGANIZATION="$2"
                shift 2
                ;;
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
            -a|--app-name)
                APP_NAME="$2"
                shift 2
                ;;
            -s|--space)
                SPACE="$2"
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
    if [[ -z "$ORGANIZATION" ]]; then
        print_error "Organization is required (--org)"
        exit 1
    fi
    
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
        print_status "Please install it from: https://cloud.ibm.com/docs/cli?topic=cli-getting-started"
        exit 1
    fi
    
    # Check if user is logged in
    if ! ibmcloud target &>/dev/null; then
        print_error "You are not logged in to IBM Cloud."
        print_status "Please run: ibmcloud login"
        exit 1
    fi
    
    # Check IBM Cloud CLI version
    local cli_version=$(ibmcloud version | head -1)
    print_status "Using IBM Cloud CLI: $cli_version"
    
    print_success "Prerequisites check completed"
}

setup_target_environment() {
    print_header "Setting up Target Environment"
    
    # Target the organization and space
    execute_command "ibmcloud target -o '$ORGANIZATION' -s '$SPACE'" \
        "Targeting organization and space..."
    
    # Create resource group if it doesn't exist
    if ! ibmcloud resource group "$RESOURCE_GROUP" &>/dev/null; then
        execute_command "ibmcloud resource group-create '$RESOURCE_GROUP'" \
            "Creating resource group..."
    fi
    
    # Target the resource group
    execute_command "ibmcloud target -g '$RESOURCE_GROUP'" \
        "Targeting resource group..."
    
    print_success "Target environment configured"
}

create_watson_services() {
    print_header "Creating Watson AI Services"
    
    # Create Watson Natural Language Understanding service
    execute_command "ibmcloud resource service-instance-create watson-nlu natural-language-understanding free '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Watson Natural Language Understanding service..."
    
    # Create Watson Language Translator service
    execute_command "ibmcloud resource service-instance-create watson-translator language-translator lite '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Watson Language Translator service..."
    
    # Create Watson Discovery service for content analysis
    execute_command "ibmcloud resource service-instance-create watson-discovery discovery plus '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Watson Discovery service..."
    
    # Create service keys
    execute_command "ibmcloud resource service-key-create watson-nlu-key Manager --instance-name watson-nlu" \
        "Creating Watson NLU service key..."
    
    execute_command "ibmcloud resource service-key-create watson-translator-key Manager --instance-name watson-translator" \
        "Creating Watson Translator service key..."
    
    execute_command "ibmcloud resource service-key-create watson-discovery-key Manager --instance-name watson-discovery" \
        "Creating Watson Discovery service key..."
    
    print_success "Watson AI services created"
}

create_database_services() {
    print_header "Creating Database Services"
    
    # Create Db2 Warehouse service for main data storage
    execute_command "ibmcloud resource service-instance-create misinformation-db2 dashdb-for-transactions free '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Db2 database service..."
    
    # Create Cloudant NoSQL database for document storage
    execute_command "ibmcloud resource service-instance-create misinformation-cloudant cloudantnosqldb lite '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Cloudant NoSQL database..."
    
    # Create Redis cache service
    execute_command "ibmcloud resource service-instance-create misinformation-redis databases-for-redis standard '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Redis cache service..."
    
    # Create service keys
    execute_command "ibmcloud resource service-key-create db2-key Manager --instance-name misinformation-db2" \
        "Creating Db2 service key..."
    
    execute_command "ibmcloud resource service-key-create cloudant-key Manager --instance-name misinformation-cloudant" \
        "Creating Cloudant service key..."
    
    execute_command "ibmcloud resource service-key-create redis-key Manager --instance-name misinformation-redis" \
        "Creating Redis service key..."
    
    print_success "Database services created"
}

create_messaging_services() {
    print_header "Creating Messaging and Event Services"
    
    # Create Event Streams (Kafka) service for event processing
    execute_command "ibmcloud resource service-instance-create misinformation-events messagehub standard '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Event Streams (Kafka) service..."
    
    # Create service key
    execute_command "ibmcloud resource service-key-create events-key Manager --instance-name misinformation-events" \
        "Creating Event Streams service key..."
    
    print_success "Messaging services created"
}

create_monitoring_services() {
    print_header "Creating Monitoring and Logging Services"
    
    # Create Log Analysis service
    execute_command "ibmcloud resource service-instance-create misinformation-logs logdna 7-day '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Log Analysis service..."
    
    # Create Monitoring service
    execute_command "ibmcloud resource service-instance-create misinformation-monitoring sysdig-monitor graduated-tier '$REGION' -g '$RESOURCE_GROUP'" \
        "Creating Monitoring service..."
    
    # Create service keys
    execute_command "ibmcloud resource service-key-create logs-key Manager --instance-name misinformation-logs" \
        "Creating Log Analysis service key..."
    
    execute_command "ibmcloud resource service-key-create monitoring-key Manager --instance-name misinformation-monitoring" \
        "Creating Monitoring service key..."
    
    print_success "Monitoring services created"
}

create_storage_services() {
    print_header "Creating Storage Services"
    
    # Create Cloud Object Storage for file storage
    execute_command "ibmcloud resource service-instance-create misinformation-storage cloud-object-storage lite global -g '$RESOURCE_GROUP'" \
        "Creating Cloud Object Storage service..."
    
    # Create service key
    execute_command "ibmcloud resource service-key-create storage-key Manager --instance-name misinformation-storage" \
        "Creating Cloud Object Storage service key..."
    
    print_success "Storage services created"
}

generate_manifest() {
    print_header "Generating Application Manifest"
    
    # Create Cloud Foundry manifest for deployment
    cat > manifest.yml << EOF
---
applications:
- name: $APP_NAME
  memory: 1G
  instances: 2
  buildpacks:
    - python_buildpack
  command: gunicorn --bind 0.0.0.0:\$PORT --workers 4 backend.main:app
  env:
    MODE: cloud
    ENVIRONMENT: production
    LOG_LEVEL: INFO
  services:
    - watson-nlu
    - watson-translator
    - watson-discovery
    - misinformation-db2
    - misinformation-cloudant
    - misinformation-redis
    - misinformation-events
    - misinformation-logs
    - misinformation-monitoring
    - misinformation-storage
  routes:
    - route: $APP_NAME.mybluemix.net
EOF
    
    print_success "Application manifest created: manifest.yml"
}

generate_environment_config() {
    print_header "Generating Environment Configuration"
    
    # Create IBM Cloud specific environment file
    cat > .env.ibmcloud << EOF
# IBM Cloud Production Environment Configuration
# Generated by IBM Cloud setup script on $(date)

# Application Configuration
MODE=cloud
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=\${PORT:-8080}

# IBM Cloud Configuration
VCAP_SERVICES_ENABLED=true
IBM_CLOUD_REGION=$REGION

# Watson AI Configuration
WATSON_NLU_ENABLED=true
WATSON_TRANSLATOR_ENABLED=true
WATSON_DISCOVERY_ENABLED=true

# Database Configuration
DB_TYPE=db2
CACHE_TYPE=redis
DOCUMENT_STORE=cloudant

# Event Processing Configuration
EVENT_STREAMING_TYPE=kafka
KAFKA_ENABLED=true

# Monitoring Configuration
ENABLE_METRICS=true
ENABLE_TRACING=true
ENABLE_LOGGING=true

# Security Configuration
API_KEY_ENABLED=true
CORS_ORIGINS=["https://$APP_NAME.mybluemix.net"]
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Performance Configuration
CACHE_TTL=300
TRACING_SAMPLE_RATE=0.1

# Version
VERSION=latest
EOF
    
    print_success "IBM Cloud environment configuration created: .env.ibmcloud"
}

create_deployment_script() {
    print_header "Creating Deployment Script"
    
    # Create IBM Cloud deployment script
    cat > scripts/deploy-ibmcloud.sh << 'EOF'
#!/bin/bash

# IBM Cloud Deployment Script for Misinformation Heatmap

set -e

print_status() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# Check if logged in
if ! ibmcloud target &>/dev/null; then
    print_error "Not logged in to IBM Cloud. Please run: ibmcloud login"
    exit 1
fi

print_status "Starting deployment to IBM Cloud..."

# Install dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Run tests
print_status "Running tests..."
python -m pytest tests/ -v || {
    print_error "Tests failed. Deployment aborted."
    exit 1
}

# Deploy to Cloud Foundry
print_status "Deploying to Cloud Foundry..."
ibmcloud cf push

# Check deployment status
print_status "Checking deployment status..."
APP_URL=$(ibmcloud cf app misinformation-heatmap --show-app-url | tail -1)

# Test health endpoint
print_status "Testing health endpoint..."
sleep 30  # Wait for app to start
curl -f "$APP_URL/health" || {
    print_error "Health check failed"
    exit 1
}

print_success "Deployment completed successfully!"
print_status "Application URL: $APP_URL"
print_status "API Documentation: $APP_URL/docs"
EOF

    chmod +x scripts/deploy-ibmcloud.sh
    
    print_success "Deployment script created: scripts/deploy-ibmcloud.sh"
}

setup_database_schema() {
    print_header "Setting up Database Schema"
    
    # Create SQL script for Db2 setup
    cat > scripts/setup_db2_schema.sql << 'EOF'
-- Db2 Schema Setup for Misinformation Heatmap

-- Create events table
CREATE TABLE events (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    title CLOB,
    content CLOB,
    url VARCHAR(2048),
    state VARCHAR(100),
    district VARCHAR(100),
    city VARCHAR(100),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    misinformation_score DECIMAL(5,4),
    confidence DECIMAL(5,4),
    categories VARCHAR(1000),
    sentiment VARCHAR(50),
    language VARCHAR(10),
    satellite_validated BOOLEAN,
    infrastructure_detected BOOLEAN,
    processing_status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_location ON events(state, district);
CREATE INDEX idx_events_score ON events(misinformation_score);
CREATE INDEX idx_events_status ON events(processing_status);

-- Create aggregations table
CREATE TABLE aggregations (
    id VARCHAR(255) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    time_window VARCHAR(20) NOT NULL,
    state VARCHAR(100) NOT NULL,
    district VARCHAR(100),
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    total_events INTEGER NOT NULL,
    misinformation_events INTEGER NOT NULL,
    avg_misinformation_score DECIMAL(5,4),
    validated_events INTEGER NOT NULL,
    heat_intensity DECIMAL(5,4) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for aggregations
CREATE INDEX idx_agg_timestamp ON aggregations(timestamp);
CREATE INDEX idx_agg_location ON aggregations(state, district);
CREATE INDEX idx_agg_intensity ON aggregations(heat_intensity);

-- Create data sources tracking table
CREATE TABLE data_sources (
    source_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    category VARCHAR(100),
    language VARCHAR(10),
    region VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    last_fetch TIMESTAMP,
    fetch_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create view for heatmap data
CREATE VIEW heatmap_view AS
SELECT 
    state,
    district,
    latitude,
    longitude,
    COUNT(*) as total_events,
    SUM(CASE WHEN misinformation_score > 0.5 THEN 1 ELSE 0 END) as misinformation_events,
    AVG(misinformation_score) as avg_misinformation_score,
    SUM(CASE WHEN satellite_validated = TRUE THEN 1 ELSE 0 END) as validated_events,
    CASE 
        WHEN COUNT(*) = 0 THEN 0
        ELSE (SUM(CASE WHEN misinformation_score > 0.5 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)) * 
             (1 + SUM(CASE WHEN satellite_validated = TRUE THEN 1 ELSE 0 END) * 0.2)
    END as heat_intensity,
    MAX(timestamp) as last_event_time
FROM events
WHERE 
    latitude IS NOT NULL 
    AND longitude IS NOT NULL
    AND timestamp >= CURRENT_TIMESTAMP - 24 HOURS
    AND processing_status = 'published'
GROUP BY state, district, latitude, longitude
HAVING COUNT(*) >= 1
ORDER BY heat_intensity DESC;
EOF
    
    print_success "Database schema script created: scripts/setup_db2_schema.sql"
}

main() {
    print_header "IBM Cloud Production Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Starting IBM Cloud setup with the following configuration:"
    print_status "  Organization: $ORGANIZATION"
    print_status "  Space: $SPACE"
    print_status "  Resource Group: $RESOURCE_GROUP"
    print_status "  Region: $REGION"
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
    setup_target_environment
    create_watson_services
    create_database_services
    create_messaging_services
    create_monitoring_services
    create_storage_services
    generate_manifest
    generate_environment_config
    create_deployment_script
    setup_database_schema
    
    print_header "IBM Cloud Setup Complete!"
    print_success "IBM Cloud infrastructure is ready for deployment"
    print_status ""
    print_status "Created resources:"
    print_status "  - Watson AI services (NLU, Translator, Discovery)"
    print_status "  - Db2 database and Cloudant NoSQL storage"
    print_status "  - Redis cache and Event Streams (Kafka)"
    print_status "  - Monitoring and logging services"
    print_status "  - Cloud Object Storage"
    print_status ""
    print_status "Created files:"
    print_status "  - manifest.yml (Cloud Foundry deployment config)"
    print_status "  - .env.ibmcloud (IBM Cloud environment variables)"
    print_status "  - scripts/deploy-ibmcloud.sh (deployment script)"
    print_status "  - scripts/setup_db2_schema.sql (database schema)"
    print_status ""
    print_status "Next steps:"
    print_status "1. Run database setup: Connect to Db2 and run setup_db2_schema.sql"
    print_status "2. Deploy application: ./scripts/deploy-ibmcloud.sh"
    print_status "3. Test the deployment: Check the application URL"
    print_status "4. Set up monitoring dashboards in IBM Cloud console"
}

# Run main function with all arguments
main "$@"