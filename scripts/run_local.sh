#!/bin/bash

# Local Development Setup Script
# Starts all services required for the misinformation heatmap application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DATA_DIR="$PROJECT_ROOT/data"
LOGS_DIR="$PROJECT_ROOT/logs"

# Default configuration
MODE="local"
SKIP_DEPS=false
SKIP_DB_INIT=false
SKIP_FRONTEND=false
VERBOSE=false
DETACHED=false

# Function to print colored output
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

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -m, --mode MODE     Set deployment mode (local|cloud) [default: local]"
    echo "  -s, --skip-deps     Skip dependency installation"
    echo "  -d, --skip-db       Skip database initialization"
    echo "  -f, --skip-frontend Skip frontend serving"
    echo "  -v, --verbose       Enable verbose output"
    echo "  -D, --detached      Run services in detached mode"
    echo "  --stop              Stop all running services"
    echo "  --status            Show status of running services"
    echo "  --logs              Show logs from all services"
    echo ""
    echo "Examples:"
    echo "  $0                  Start all services in local mode"
    echo "  $0 --mode cloud     Start with cloud configuration"
    echo "  $0 --skip-deps      Start without installing dependencies"
    echo "  $0 --detached       Start services in background"
    echo "  $0 --stop           Stop all running services"
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -s|--skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            -d|--skip-db)
                SKIP_DB_INIT=true
                shift
                ;;
            -f|--skip-frontend)
                SKIP_FRONTEND=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -D|--detached)
                DETACHED=true
                shift
                ;;
            --stop)
                stop_services
                exit 0
                ;;
            --status)
                show_status
                exit 0
                ;;
            --logs)
                show_logs
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

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    print_status "Python version: $python_version"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3."
        exit 1
    fi
    
    # Check Node.js (for frontend)
    if [[ "$SKIP_FRONTEND" == false ]]; then
        if ! command -v node &> /dev/null; then
            print_warning "Node.js not found. Frontend serving will be disabled."
            SKIP_FRONTEND=true
        else
            local node_version=$(node --version)
            print_status "Node.js version: $node_version"
        fi
    fi
    
    # Check required directories
    for dir in "$BACKEND_DIR" "$FRONTEND_DIR" "$DATA_DIR"; do
        if [[ ! -d "$dir" ]]; then
            print_error "Required directory not found: $dir"
            exit 1
        fi
    done
    
    print_success "Prerequisites check completed"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$LOGS_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$PROJECT_ROOT/.env"
    
    print_success "Directories created"
}

# Function to install dependencies
install_dependencies() {
    if [[ "$SKIP_DEPS" == true ]]; then
        print_warning "Skipping dependency installation"
        return
    fi
    
    print_status "Installing Python dependencies..."
    
    cd "$BACKEND_DIR"
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
    else
        print_error "requirements.txt not found in backend directory"
        exit 1
    fi
    
    print_success "Python dependencies installed"
    
    # Install frontend dependencies if needed
    if [[ "$SKIP_FRONTEND" == false && -f "$FRONTEND_DIR/package.json" ]]; then
        print_status "Installing frontend dependencies..."
        cd "$FRONTEND_DIR"
        npm install
        print_success "Frontend dependencies installed"
    fi
}

# Function to initialize database
initialize_database() {
    if [[ "$SKIP_DB_INIT" == true ]]; then
        print_warning "Skipping database initialization"
        return
    fi
    
    print_status "Initializing database..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Run database initialization script
    if [[ -f "init_db.py" ]]; then
        python init_db.py --mode "$MODE"
        print_success "Database initialized"
    else
        print_warning "Database initialization script not found, skipping..."
    fi
}

# Function to setup environment variables
setup_environment() {
    print_status "Setting up environment variables..."
    
    # Create .env file if it doesn't exist
    local env_file="$PROJECT_ROOT/.env"
    if [[ ! -f "$env_file" ]]; then
        print_status "Creating .env file..."
        cat > "$env_file" << EOF
# Misinformation Heatmap Configuration
MODE=$MODE
DEBUG=true
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=sqlite:///./data/heatmap.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# NLP Configuration
HUGGINGFACE_TOKEN=
MODEL_CACHE_DIR=./models

# Pub/Sub Configuration (Local)
PUBSUB_EMULATOR_HOST=localhost:8085
PUBSUB_PROJECT_ID=misinformation-heatmap-local

# Google Cloud Configuration (for cloud mode)
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=

# IBM Watson Configuration (for cloud mode)
WATSON_DISCOVERY_API_KEY=
WATSON_DISCOVERY_URL=

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090
EOF
        print_success ".env file created"
    else
        print_status ".env file already exists"
    fi
}

# Function to start Pub/Sub emulator
start_pubsub_emulator() {
    if [[ "$MODE" != "local" ]]; then
        return
    fi
    
    print_status "Starting Pub/Sub emulator..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_warning "gcloud CLI not found. Installing Pub/Sub emulator..."
        # Install using pip as fallback
        pip install google-cloud-pubsub
    fi
    
    # Start emulator in background
    local pubsub_log="$LOGS_DIR/pubsub-emulator.log"
    
    if [[ "$DETACHED" == true ]]; then
        nohup gcloud beta emulators pubsub start --host-port=localhost:8085 > "$pubsub_log" 2>&1 &
        local pubsub_pid=$!
        echo $pubsub_pid > "$LOGS_DIR/pubsub.pid"
        print_success "Pub/Sub emulator started (PID: $pubsub_pid)"
    else
        print_status "Starting Pub/Sub emulator (press Ctrl+C to stop all services)"
        gcloud beta emulators pubsub start --host-port=localhost:8085 &
        local pubsub_pid=$!
        echo $pubsub_pid > "$LOGS_DIR/pubsub.pid"
    fi
    
    # Wait for emulator to start
    sleep 3
    
    # Create topics and subscriptions
    export PUBSUB_EMULATOR_HOST=localhost:8085
    python3 -c "
import os
from google.cloud import pubsub_v1

os.environ['PUBSUB_EMULATOR_HOST'] = 'localhost:8085'
project_id = 'misinformation-heatmap-local'

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# Create topics
topics = ['events-raw', 'events-processed', 'events-validated']
for topic_name in topics:
    topic_path = publisher.topic_path(project_id, topic_name)
    try:
        publisher.create_topic(request={'name': topic_path})
        print(f'Created topic: {topic_name}')
    except Exception as e:
        print(f'Topic {topic_name} may already exist: {e}')

# Create subscriptions
subscriptions = [
    ('events-raw', 'events-raw-sub'),
    ('events-processed', 'events-processed-sub'),
    ('events-validated', 'events-validated-sub')
]

for topic_name, sub_name in subscriptions:
    topic_path = publisher.topic_path(project_id, topic_name)
    subscription_path = subscriber.subscription_path(project_id, sub_name)
    try:
        subscriber.create_subscription(
            request={'name': subscription_path, 'topic': topic_path}
        )
        print(f'Created subscription: {sub_name}')
    except Exception as e:
        print(f'Subscription {sub_name} may already exist: {e}')
"
}

# Function to start backend API
start_backend() {
    print_status "Starting backend API server..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    local api_log="$LOGS_DIR/api.log"
    
    if [[ "$DETACHED" == true ]]; then
        nohup python api.py > "$api_log" 2>&1 &
        local api_pid=$!
        echo $api_pid > "$LOGS_DIR/api.pid"
        print_success "Backend API started (PID: $api_pid)"
    else
        print_status "Starting backend API (press Ctrl+C to stop all services)"
        python api.py &
        local api_pid=$!
        echo $api_pid > "$LOGS_DIR/api.pid"
    fi
}

# Function to start frontend server
start_frontend() {
    if [[ "$SKIP_FRONTEND" == true ]]; then
        print_warning "Skipping frontend server"
        return
    fi
    
    print_status "Starting frontend server..."
    
    cd "$FRONTEND_DIR"
    
    local frontend_log="$LOGS_DIR/frontend.log"
    
    # Use Python's built-in HTTP server for simplicity
    if [[ "$DETACHED" == true ]]; then
        nohup python3 -m http.server 3000 > "$frontend_log" 2>&1 &
        local frontend_pid=$!
        echo $frontend_pid > "$LOGS_DIR/frontend.pid"
        print_success "Frontend server started (PID: $frontend_pid)"
    else
        print_status "Starting frontend server (press Ctrl+C to stop all services)"
        python3 -m http.server 3000 &
        local frontend_pid=$!
        echo $frontend_pid > "$LOGS_DIR/frontend.pid"
    fi
}

# Function to perform health checks
perform_health_checks() {
    print_status "Performing health checks..."
    
    # Wait a moment for services to start
    sleep 5
    
    # Check backend API
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Backend API is healthy"
    else
        print_warning "Backend API health check failed"
    fi
    
    # Check frontend
    if [[ "$SKIP_FRONTEND" == false ]]; then
        if curl -s http://localhost:3000 > /dev/null; then
            print_success "Frontend server is healthy"
        else
            print_warning "Frontend server health check failed"
        fi
    fi
    
    # Check Pub/Sub emulator (local mode only)
    if [[ "$MODE" == "local" ]]; then
        if curl -s http://localhost:8085 > /dev/null; then
            print_success "Pub/Sub emulator is healthy"
        else
            print_warning "Pub/Sub emulator health check failed"
        fi
    fi
}

# Function to show running services status
show_status() {
    print_header "Service Status"
    
    # Check API
    if [[ -f "$LOGS_DIR/api.pid" ]]; then
        local api_pid=$(cat "$LOGS_DIR/api.pid")
        if ps -p $api_pid > /dev/null; then
            print_success "Backend API running (PID: $api_pid)"
        else
            print_warning "Backend API not running (stale PID file)"
        fi
    else
        print_warning "Backend API not started"
    fi
    
    # Check frontend
    if [[ -f "$LOGS_DIR/frontend.pid" ]]; then
        local frontend_pid=$(cat "$LOGS_DIR/frontend.pid")
        if ps -p $frontend_pid > /dev/null; then
            print_success "Frontend server running (PID: $frontend_pid)"
        else
            print_warning "Frontend server not running (stale PID file)"
        fi
    else
        print_warning "Frontend server not started"
    fi
    
    # Check Pub/Sub emulator
    if [[ -f "$LOGS_DIR/pubsub.pid" ]]; then
        local pubsub_pid=$(cat "$LOGS_DIR/pubsub.pid")
        if ps -p $pubsub_pid > /dev/null; then
            print_success "Pub/Sub emulator running (PID: $pubsub_pid)"
        else
            print_warning "Pub/Sub emulator not running (stale PID file)"
        fi
    else
        print_warning "Pub/Sub emulator not started"
    fi
}

# Function to show logs
show_logs() {
    print_header "Service Logs"
    
    if [[ -f "$LOGS_DIR/api.log" ]]; then
        echo -e "${BLUE}=== Backend API Logs ===${NC}"
        tail -n 20 "$LOGS_DIR/api.log"
        echo ""
    fi
    
    if [[ -f "$LOGS_DIR/frontend.log" ]]; then
        echo -e "${BLUE}=== Frontend Server Logs ===${NC}"
        tail -n 20 "$LOGS_DIR/frontend.log"
        echo ""
    fi
    
    if [[ -f "$LOGS_DIR/pubsub-emulator.log" ]]; then
        echo -e "${BLUE}=== Pub/Sub Emulator Logs ===${NC}"
        tail -n 20 "$LOGS_DIR/pubsub-emulator.log"
        echo ""
    fi
}

# Function to stop all services
stop_services() {
    print_header "Stopping Services"
    
    # Stop API
    if [[ -f "$LOGS_DIR/api.pid" ]]; then
        local api_pid=$(cat "$LOGS_DIR/api.pid")
        if ps -p $api_pid > /dev/null; then
            kill $api_pid
            print_success "Backend API stopped"
        fi
        rm -f "$LOGS_DIR/api.pid"
    fi
    
    # Stop frontend
    if [[ -f "$LOGS_DIR/frontend.pid" ]]; then
        local frontend_pid=$(cat "$LOGS_DIR/frontend.pid")
        if ps -p $frontend_pid > /dev/null; then
            kill $frontend_pid
            print_success "Frontend server stopped"
        fi
        rm -f "$LOGS_DIR/frontend.pid"
    fi
    
    # Stop Pub/Sub emulator
    if [[ -f "$LOGS_DIR/pubsub.pid" ]]; then
        local pubsub_pid=$(cat "$LOGS_DIR/pubsub.pid")
        if ps -p $pubsub_pid > /dev/null; then
            kill $pubsub_pid
            print_success "Pub/Sub emulator stopped"
        fi
        rm -f "$LOGS_DIR/pubsub.pid"
    fi
    
    print_success "All services stopped"
}

# Function to handle cleanup on exit
cleanup() {
    if [[ "$DETACHED" == false ]]; then
        print_status "Cleaning up..."
        stop_services
    fi
}

# Function to display service URLs
show_service_urls() {
    print_header "Service URLs"
    echo -e "${GREEN}Backend API:${NC}      http://localhost:8000"
    echo -e "${GREEN}API Documentation:${NC} http://localhost:8000/docs"
    echo -e "${GREEN}Health Check:${NC}     http://localhost:8000/health"
    
    if [[ "$SKIP_FRONTEND" == false ]]; then
        echo -e "${GREEN}Frontend:${NC}         http://localhost:3000"
    fi
    
    if [[ "$MODE" == "local" ]]; then
        echo -e "${GREEN}Pub/Sub Emulator:${NC}  http://localhost:8085"
    fi
    
    echo ""
    echo -e "${YELLOW}Logs Directory:${NC}   $LOGS_DIR"
    echo -e "${YELLOW}Data Directory:${NC}   $DATA_DIR"
}

# Main execution function
main() {
    print_header "Misinformation Heatmap - Local Development Setup"
    
    parse_args "$@"
    
    # Set up signal handlers for cleanup
    trap cleanup EXIT INT TERM
    
    check_prerequisites
    create_directories
    setup_environment
    install_dependencies
    initialize_database
    
    # Start services
    if [[ "$MODE" == "local" ]]; then
        start_pubsub_emulator
    fi
    
    start_backend
    start_frontend
    
    # Perform health checks
    perform_health_checks
    
    # Show service information
    show_service_urls
    
    if [[ "$DETACHED" == true ]]; then
        print_success "All services started in detached mode"
        print_status "Use '$0 --status' to check service status"
        print_status "Use '$0 --logs' to view service logs"
        print_status "Use '$0 --stop' to stop all services"
    else
        print_success "All services started successfully!"
        print_status "Press Ctrl+C to stop all services"
        
        # Wait for user interrupt
        while true; do
            sleep 1
        done
    fi
}

# Run main function
main "$@"