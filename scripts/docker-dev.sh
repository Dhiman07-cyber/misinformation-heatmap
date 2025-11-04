#!/bin/bash

# Docker Development Environment Management Script
# Provides easy commands for managing the development Docker environment

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
    echo "  build       Build development Docker images"
    echo "  up          Start development environment"
    echo "  down        Stop development environment"
    echo "  restart     Restart development environment"
    echo "  logs        Show logs from all services"
    echo "  shell       Open shell in main application container"
    echo "  test        Run tests in Docker environment"
    echo "  clean       Clean up Docker resources"
    echo "  status      Show status of all services"
    echo "  health      Check health of all services"
    echo ""
    echo "Examples:"
    echo "  $0 up                    # Start development environment"
    echo "  $0 logs app              # Show logs from app service"
    echo "  $0 shell                 # Open shell in app container"
    echo "  $0 test                  # Run all tests"
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed."
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f .env ]]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_status "Please edit .env file with your configuration"
    fi
    
    print_success "Prerequisites check completed"
}

build_images() {
    print_header "Building Development Docker Images"
    
    export BUILD_TARGET=development
    export VOLUME_MODE=rw
    
    docker-compose build --no-cache
    
    print_success "Docker images built successfully"
}

start_environment() {
    print_header "Starting Development Environment"
    
    export BUILD_TARGET=development
    export VOLUME_MODE=rw
    export COMPOSE_PROFILES=local,development
    
    # Start core services
    docker-compose up -d app frontend pubsub-emulator
    
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are healthy
    if docker-compose ps | grep -q "Up"; then
        print_success "Development environment started successfully"
        print_status "Services available at:"
        print_status "  - Frontend: http://localhost:3000"
        print_status "  - API: http://localhost:8000"
        print_status "  - API Docs: http://localhost:8000/docs"
        print_status "  - Pub/Sub Emulator: http://localhost:8085"
    else
        print_error "Some services failed to start"
        docker-compose logs
        exit 1
    fi
}

stop_environment() {
    print_header "Stopping Development Environment"
    
    docker-compose down
    
    print_success "Development environment stopped"
}

restart_environment() {
    print_header "Restarting Development Environment"
    
    stop_environment
    sleep 2
    start_environment
}

show_logs() {
    local service=${1:-}
    
    if [[ -n "$service" ]]; then
        print_header "Showing Logs for $service"
        docker-compose logs -f "$service"
    else
        print_header "Showing Logs for All Services"
        docker-compose logs -f
    fi
}

open_shell() {
    print_header "Opening Shell in Application Container"
    
    if docker-compose ps app | grep -q "Up"; then
        docker-compose exec app /bin/bash
    else
        print_error "Application container is not running"
        print_status "Starting container first..."
        docker-compose up -d app
        sleep 5
        docker-compose exec app /bin/bash
    fi
}

run_tests() {
    print_header "Running Tests in Docker Environment"
    
    export COMPOSE_PROFILES=testing
    
    # Start test environment
    docker-compose up -d test-runner
    
    # Wait for tests to complete
    docker-compose logs -f test-runner
    
    # Get exit code
    exit_code=$(docker-compose ps -q test-runner | xargs docker inspect -f '{{.State.ExitCode}}')
    
    if [[ "$exit_code" == "0" ]]; then
        print_success "All tests passed"
    else
        print_error "Some tests failed"
        exit 1
    fi
}

clean_resources() {
    print_header "Cleaning Docker Resources"
    
    print_status "Stopping all containers..."
    docker-compose down -v
    
    print_status "Removing unused images..."
    docker image prune -f
    
    print_status "Removing unused volumes..."
    docker volume prune -f
    
    print_status "Removing unused networks..."
    docker network prune -f
    
    print_success "Docker resources cleaned"
}

show_status() {
    print_header "Service Status"
    
    docker-compose ps
    
    echo ""
    print_status "Docker resource usage:"
    docker system df
}

check_health() {
    print_header "Health Check"
    
    print_status "Checking service health..."
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Services are running"
        
        # Check API health
        if curl -s http://localhost:8000/health > /dev/null; then
            print_success "API is healthy"
        else
            print_warning "API health check failed"
        fi
        
        # Check frontend
        if curl -s http://localhost:3000 > /dev/null; then
            print_success "Frontend is accessible"
        else
            print_warning "Frontend is not accessible"
        fi
        
    else
        print_warning "Some services are not running"
    fi
    
    # Show resource usage
    echo ""
    print_status "Resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

main() {
    case "${1:-}" in
        build)
            check_prerequisites
            build_images
            ;;
        up|start)
            check_prerequisites
            start_environment
            ;;
        down|stop)
            stop_environment
            ;;
        restart)
            restart_environment
            ;;
        logs)
            show_logs "${2:-}"
            ;;
        shell|bash)
            open_shell
            ;;
        test)
            check_prerequisites
            run_tests
            ;;
        clean)
            clean_resources
            ;;
        status)
            show_status
            ;;
        health)
            check_health
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