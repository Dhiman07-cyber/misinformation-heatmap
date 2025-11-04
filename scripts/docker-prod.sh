#!/bin/bash

# Docker Production Environment Management Script
# Provides commands for managing the production Docker environment

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

show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build       Build production Docker images"
    echo "  deploy      Deploy to production environment"
    echo "  update      Update production deployment"
    echo "  rollback    Rollback to previous version"
    echo "  stop        Stop production environment"
    echo "  logs        Show logs from production services"
    echo "  status      Show status of production services"
    echo "  health      Check health of production services"
    echo "  backup      Create backup of production data"
    echo "  restore     Restore from backup"
    echo "  scale       Scale services up/down"
    echo "  clean       Clean up old images and containers"
    echo ""
    echo "Examples:"
    echo "  $0 build                 # Build production images"
    echo "  $0 deploy                # Deploy to production"
    echo "  $0 scale app=3           # Scale app service to 3 replicas"
    echo "  $0 logs app              # Show logs from app service"
}

check_prerequisites() {
    print_status "Checking production prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed."
        exit 1
    fi
    
    # Check if production .env file exists
    if [[ ! -f .env.production ]]; then
        print_error ".env.production file not found."
        print_status "Please create .env.production with production configuration"
        exit 1
    fi
    
    # Check for SSL certificates
    if [[ ! -f "${SSL_CERT_PATH:-./ssl/cert.pem}" ]]; then
        print_warning "SSL certificate not found. HTTPS will not work."
    fi
    
    # Check for Google Cloud credentials
    if [[ ! -f "${GOOGLE_APPLICATION_CREDENTIALS_FILE:-./credentials.json}" ]]; then
        print_warning "Google Cloud credentials not found."
    fi
    
    print_success "Prerequisites check completed"
}

build_production_images() {
    print_header "Building Production Docker Images"
    
    # Set production environment
    export BUILD_TARGET=production
    export VERSION=${VERSION:-$(date +%Y%m%d-%H%M%S)}
    
    # Build with version tag
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Tag with version
    docker tag misinformation-heatmap:latest misinformation-heatmap:$VERSION
    
    print_success "Production images built with version: $VERSION"
}

deploy_production() {
    print_header "Deploying to Production Environment"
    
    # Load production environment
    set -a
    source .env.production
    set +a
    
    export BUILD_TARGET=production
    export COMPOSE_PROFILES=production,monitoring
    
    # Pre-deployment checks
    print_status "Running pre-deployment checks..."
    
    # Check if required environment variables are set
    required_vars=("GOOGLE_CLOUD_PROJECT" "API_KEYS" "GRAFANA_PASSWORD")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            print_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Create necessary directories
    mkdir -p data logs ssl
    
    # Deploy services
    print_status "Starting production services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 30
    
    # Health check
    if check_production_health; then
        print_success "Production deployment completed successfully"
        print_status "Services available at:"
        print_status "  - Application: https://localhost"
        print_status "  - Monitoring: http://localhost:3001"
        print_status "  - Metrics: http://localhost:9090"
    else
        print_error "Production deployment failed health check"
        print_status "Rolling back..."
        rollback_deployment
        exit 1
    fi
}

update_deployment() {
    print_header "Updating Production Deployment"
    
    # Build new images
    build_production_images
    
    # Rolling update
    print_status "Performing rolling update..."
    
    # Update app service
    docker-compose -f docker-compose.prod.yml up -d --no-deps app
    
    # Wait and health check
    sleep 20
    if check_production_health; then
        print_success "Update completed successfully"
    else
        print_error "Update failed, rolling back..."
        rollback_deployment
        exit 1
    fi
}

rollback_deployment() {
    print_header "Rolling Back Deployment"
    
    # Get previous version
    local previous_version=$(docker images misinformation-heatmap --format "table {{.Tag}}" | grep -v latest | head -n 2 | tail -n 1)
    
    if [[ -n "$previous_version" ]]; then
        print_status "Rolling back to version: $previous_version"
        
        # Update with previous version
        export VERSION=$previous_version
        docker-compose -f docker-compose.prod.yml up -d --no-deps app
        
        sleep 20
        if check_production_health; then
            print_success "Rollback completed successfully"
        else
            print_error "Rollback failed"
            exit 1
        fi
    else
        print_error "No previous version found for rollback"
        exit 1
    fi
}

stop_production() {
    print_header "Stopping Production Environment"
    
    print_warning "This will stop the production environment. Are you sure? (y/N)"
    read -r confirmation
    
    if [[ "$confirmation" =~ ^[Yy]$ ]]; then
        docker-compose -f docker-compose.prod.yml down
        print_success "Production environment stopped"
    else
        print_status "Operation cancelled"
    fi
}

show_production_logs() {
    local service=${1:-}
    
    if [[ -n "$service" ]]; then
        print_header "Showing Production Logs for $service"
        docker-compose -f docker-compose.prod.yml logs -f --tail=100 "$service"
    else
        print_header "Showing Production Logs for All Services"
        docker-compose -f docker-compose.prod.yml logs -f --tail=100
    fi
}

show_production_status() {
    print_header "Production Service Status"
    
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    print_status "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    
    echo ""
    print_status "Disk usage:"
    df -h
}

check_production_health() {
    print_status "Checking production health..."
    
    local health_ok=true
    
    # Check main application
    if curl -k -s https://localhost/health > /dev/null; then
        print_success "Application is healthy"
    else
        print_error "Application health check failed"
        health_ok=false
    fi
    
    # Check Redis
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping | grep -q PONG; then
        print_success "Redis is healthy"
    else
        print_error "Redis health check failed"
        health_ok=false
    fi
    
    # Check Prometheus
    if curl -s http://localhost:9090/-/healthy > /dev/null; then
        print_success "Prometheus is healthy"
    else
        print_warning "Prometheus health check failed"
    fi
    
    # Check Grafana
    if curl -s http://localhost:3001/api/health > /dev/null; then
        print_success "Grafana is healthy"
    else
        print_warning "Grafana health check failed"
    fi
    
    $health_ok
}

backup_production_data() {
    print_header "Creating Production Data Backup"
    
    local backup_date=$(date +%Y%m%d_%H%M%S)
    local backup_dir="backups/backup_$backup_date"
    
    mkdir -p "$backup_dir"
    
    # Backup application data
    print_status "Backing up application data..."
    docker run --rm -v misinformation-heatmap_app-data:/data -v $(pwd)/$backup_dir:/backup alpine tar czf /backup/app-data.tar.gz -C /data .
    
    # Backup Redis data
    print_status "Backing up Redis data..."
    docker-compose -f docker-compose.prod.yml exec -T redis redis-cli BGSAVE
    sleep 5
    docker run --rm -v misinformation-heatmap_redis-prod-data:/data -v $(pwd)/$backup_dir:/backup alpine tar czf /backup/redis-data.tar.gz -C /data .
    
    # Backup Grafana data
    print_status "Backing up Grafana data..."
    docker run --rm -v misinformation-heatmap_grafana-prod-data:/data -v $(pwd)/$backup_dir:/backup alpine tar czf /backup/grafana-data.tar.gz -C /data .
    
    # Create backup manifest
    cat > "$backup_dir/manifest.txt" << EOF
Backup created: $(date)
Version: ${VERSION:-unknown}
Services backed up:
- Application data
- Redis data
- Grafana data
EOF
    
    print_success "Backup created: $backup_dir"
}

restore_production_data() {
    local backup_dir=${1:-}
    
    if [[ -z "$backup_dir" ]]; then
        print_error "Please specify backup directory"
        print_status "Available backups:"
        ls -la backups/ 2>/dev/null || print_status "No backups found"
        exit 1
    fi
    
    if [[ ! -d "$backup_dir" ]]; then
        print_error "Backup directory not found: $backup_dir"
        exit 1
    fi
    
    print_header "Restoring Production Data from $backup_dir"
    
    print_warning "This will overwrite current production data. Are you sure? (y/N)"
    read -r confirmation
    
    if [[ "$confirmation" =~ ^[Yy]$ ]]; then
        # Stop services
        print_status "Stopping services..."
        docker-compose -f docker-compose.prod.yml stop app redis grafana
        
        # Restore data
        print_status "Restoring application data..."
        docker run --rm -v misinformation-heatmap_app-data:/data -v $(pwd)/$backup_dir:/backup alpine tar xzf /backup/app-data.tar.gz -C /data
        
        print_status "Restoring Redis data..."
        docker run --rm -v misinformation-heatmap_redis-prod-data:/data -v $(pwd)/$backup_dir:/backup alpine tar xzf /backup/redis-data.tar.gz -C /data
        
        print_status "Restoring Grafana data..."
        docker run --rm -v misinformation-heatmap_grafana-prod-data:/data -v $(pwd)/$backup_dir:/backup alpine tar xzf /backup/grafana-data.tar.gz -C /data
        
        # Restart services
        print_status "Restarting services..."
        docker-compose -f docker-compose.prod.yml start app redis grafana
        
        print_success "Data restoration completed"
    else
        print_status "Operation cancelled"
    fi
}

scale_services() {
    local scale_config=${1:-}
    
    if [[ -z "$scale_config" ]]; then
        print_error "Please specify scaling configuration (e.g., app=3)"
        exit 1
    fi
    
    print_header "Scaling Production Services"
    
    print_status "Scaling: $scale_config"
    docker-compose -f docker-compose.prod.yml up -d --scale "$scale_config"
    
    print_success "Scaling completed"
    show_production_status
}

clean_production_resources() {
    print_header "Cleaning Production Resources"
    
    print_warning "This will remove unused images and containers. Continue? (y/N)"
    read -r confirmation
    
    if [[ "$confirmation" =~ ^[Yy]$ ]]; then
        print_status "Removing unused images..."
        docker image prune -f
        
        print_status "Removing old versions (keeping last 3)..."
        docker images misinformation-heatmap --format "table {{.Tag}}" | grep -v latest | tail -n +4 | xargs -r docker rmi misinformation-heatmap: 2>/dev/null || true
        
        print_status "Removing unused volumes..."
        docker volume prune -f
        
        print_success "Cleanup completed"
    else
        print_status "Operation cancelled"
    fi
}

main() {
    case "${1:-}" in
        build)
            check_prerequisites
            build_production_images
            ;;
        deploy)
            check_prerequisites
            deploy_production
            ;;
        update)
            check_prerequisites
            update_deployment
            ;;
        rollback)
            rollback_deployment
            ;;
        stop)
            stop_production
            ;;
        logs)
            show_production_logs "${2:-}"
            ;;
        status)
            show_production_status
            ;;
        health)
            check_production_health
            ;;
        backup)
            backup_production_data
            ;;
        restore)
            restore_production_data "${2:-}"
            ;;
        scale)
            scale_services "${2:-}"
            ;;
        clean)
            clean_production_resources
            ;;
        -h|--help|help)
            show_usage
            ;;
        "")
            print_error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"