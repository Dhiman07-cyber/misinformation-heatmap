#!/bin/bash

# Pub/Sub Setup Script
# Creates topics, subscriptions, and configurations for the misinformation heatmap application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=""
VERBOSE=false
DRY_RUN=false
DELETE_EXISTING=false

# Pub/Sub configuration
declare -A TOPICS=(
    ["events-raw"]="Raw events from ingestion sources"
    ["events-processed"]="Events after NLP processing"
    ["events-validated"]="Events after satellite validation"
    ["events-failed"]="Failed events for retry processing"
    ["system-alerts"]="System alerts and notifications"
)

declare -A SUBSCRIPTIONS=(
    ["events-raw-processor"]="events-raw"
    ["events-nlp-processor"]="events-processed"
    ["events-satellite-validator"]="events-processed"
    ["events-storage-writer"]="events-validated"
    ["events-retry-handler"]="events-failed"
    ["alerts-notification-handler"]="system-alerts"
)

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
    echo "  -h, --help              Show this help message"
    echo "  -p, --project PROJECT   Google Cloud Project ID (required)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -n, --dry-run           Show what would be created without actually creating"
    echo "  -d, --delete            Delete existing topics and subscriptions first"
    echo "  --list                  List existing topics and subscriptions"
    echo "  --cleanup               Delete all topics and subscriptions"
    echo ""
    echo "Examples:"
    echo "  $0 --project my-project-id"
    echo "  $0 --project my-project --dry-run"
    echo "  $0 --project my-project --delete"
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -p|--project)
                PROJECT_ID="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -d|--delete)
                DELETE_EXISTING=true
                shift
                ;;
            --list)
                list_resources
                exit 0
                ;;
            --cleanup)
                cleanup_resources
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
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check project ID
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required. Use --project flag."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null; then
        print_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    # Enable Pub/Sub API
    print_status "Enabling Pub/Sub API..."
    gcloud services enable pubsub.googleapis.com
    
    print_success "Prerequisites check completed"
}

# Function to create topics
create_topics() {
    print_status "Creating Pub/Sub topics..."
    
    for topic in "${!TOPICS[@]}"; do
        local description="${TOPICS[$topic]}"
        
        if [[ "$DRY_RUN" == true ]]; then
            print_status "[DRY RUN] Would create topic: $topic ($description)"
            continue
        fi
        
        # Check if topic exists
        if gcloud pubsub topics describe "$topic" &> /dev/null; then
            if [[ "$DELETE_EXISTING" == true ]]; then
                print_warning "Deleting existing topic: $topic"
                gcloud pubsub topics delete "$topic" --quiet
            else
                print_warning "Topic already exists: $topic"
                continue
            fi
        fi
        
        # Create topic
        print_status "Creating topic: $topic"
        gcloud pubsub topics create "$topic"
        
        # Add labels
        gcloud pubsub topics update "$topic" \
            --update-labels="app=misinformation-heatmap,component=pubsub,environment=production"
        
        if [[ "$VERBOSE" == true ]]; then
            print_success "Created topic: $topic ($description)"
        fi
    done
    
    print_success "Topics creation completed"
}

# Function to create subscriptions
create_subscriptions() {
    print_status "Creating Pub/Sub subscriptions..."
    
    for subscription in "${!SUBSCRIPTIONS[@]}"; do
        local topic="${SUBSCRIPTIONS[$subscription]}"
        
        if [[ "$DRY_RUN" == true ]]; then
            print_status "[DRY RUN] Would create subscription: $subscription -> $topic"
            continue
        fi
        
        # Check if subscription exists
        if gcloud pubsub subscriptions describe "$subscription" &> /dev/null; then
            if [[ "$DELETE_EXISTING" == true ]]; then
                print_warning "Deleting existing subscription: $subscription"
                gcloud pubsub subscriptions delete "$subscription" --quiet
            else
                print_warning "Subscription already exists: $subscription"
                continue
            fi
        fi
        
        # Create subscription with appropriate settings
        print_status "Creating subscription: $subscription"
        
        case "$subscription" in
            *retry*)
                # Retry subscriptions need longer ack deadline
                gcloud pubsub subscriptions create "$subscription" \
                    --topic="$topic" \
                    --ack-deadline=600 \
                    --max-delivery-attempts=5 \
                    --min-retry-delay=10s \
                    --max-retry-delay=600s
                ;;
            *processor*|*validator*)
                # Processing subscriptions need moderate settings
                gcloud pubsub subscriptions create "$subscription" \
                    --topic="$topic" \
                    --ack-deadline=300 \
                    --max-delivery-attempts=3 \
                    --enable-message-ordering
                ;;
            *notification*|*alert*)
                # Notification subscriptions need fast processing
                gcloud pubsub subscriptions create "$subscription" \
                    --topic="$topic" \
                    --ack-deadline=60 \
                    --max-delivery-attempts=2
                ;;
            *)
                # Default settings
                gcloud pubsub subscriptions create "$subscription" \
                    --topic="$topic" \
                    --ack-deadline=180 \
                    --max-delivery-attempts=3
                ;;
        esac
        
        # Add labels
        gcloud pubsub subscriptions update "$subscription" \
            --update-labels="app=misinformation-heatmap,component=pubsub,environment=production"
        
        if [[ "$VERBOSE" == true ]]; then
            print_success "Created subscription: $subscription -> $topic"
        fi
    done
    
    print_success "Subscriptions creation completed"
}

# Function to setup dead letter topics
setup_dead_letter_topics() {
    print_status "Setting up dead letter topics..."
    
    local dead_letter_topics=(
        "events-dead-letter"
        "alerts-dead-letter"
    )
    
    for topic in "${dead_letter_topics[@]}"; do
        if [[ "$DRY_RUN" == true ]]; then
            print_status "[DRY RUN] Would create dead letter topic: $topic"
            continue
        fi
        
        # Create dead letter topic if it doesn't exist
        if ! gcloud pubsub topics describe "$topic" &> /dev/null; then
            print_status "Creating dead letter topic: $topic"
            gcloud pubsub topics create "$topic"
            
            # Add labels
            gcloud pubsub topics update "$topic" \
                --update-labels="app=misinformation-heatmap,component=pubsub,type=dead-letter,environment=production"
        fi
    done
    
    # Update subscriptions to use dead letter topics
    local subscriptions_with_dlq=(
        "events-raw-processor:events-dead-letter"
        "events-nlp-processor:events-dead-letter"
        "events-satellite-validator:events-dead-letter"
        "alerts-notification-handler:alerts-dead-letter"
    )
    
    for sub_dlq in "${subscriptions_with_dlq[@]}"; do
        IFS=':' read -r subscription dlq_topic <<< "$sub_dlq"
        
        if [[ "$DRY_RUN" == true ]]; then
            print_status "[DRY RUN] Would configure dead letter queue for: $subscription"
            continue
        fi
        
        print_status "Configuring dead letter queue for: $subscription"
        gcloud pubsub subscriptions update "$subscription" \
            --dead-letter-topic="projects/$PROJECT_ID/topics/$dlq_topic" \
            --max-delivery-attempts=5
    done
    
    print_success "Dead letter topics setup completed"
}

# Function to create IAM bindings
setup_iam_bindings() {
    print_status "Setting up IAM bindings..."
    
    # Service account for Cloud Run
    local service_account="${PROJECT_ID}-compute@developer.gserviceaccount.com"
    
    if [[ "$DRY_RUN" == true ]]; then
        print_status "[DRY RUN] Would setup IAM bindings for: $service_account"
        return
    fi
    
    # Grant Pub/Sub permissions to service account
    local roles=(
        "roles/pubsub.publisher"
        "roles/pubsub.subscriber"
        "roles/pubsub.viewer"
    )
    
    for role in "${roles[@]}"; do
        print_status "Granting $role to $service_account"
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$service_account" \
            --role="$role" \
            --quiet
    done
    
    # Grant specific topic/subscription permissions
    for topic in "${!TOPICS[@]}"; do
        gcloud pubsub topics add-iam-policy-binding "$topic" \
            --member="serviceAccount:$service_account" \
            --role="roles/pubsub.publisher" \
            --quiet
    done
    
    for subscription in "${!SUBSCRIPTIONS[@]}"; do
        gcloud pubsub subscriptions add-iam-policy-binding "$subscription" \
            --member="serviceAccount:$service_account" \
            --role="roles/pubsub.subscriber" \
            --quiet
    done
    
    print_success "IAM bindings setup completed"
}

# Function to list existing resources
list_resources() {
    print_header "Existing Pub/Sub Resources"
    
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required. Use --project flag."
        exit 1
    fi
    
    gcloud config set project "$PROJECT_ID"
    
    echo -e "${BLUE}Topics:${NC}"
    gcloud pubsub topics list --format="table(name.basename():label=NAME,labels.app:label=APP)"
    
    echo ""
    echo -e "${BLUE}Subscriptions:${NC}"
    gcloud pubsub subscriptions list --format="table(name.basename():label=NAME,topic.basename():label=TOPIC,ackDeadlineSeconds:label=ACK_DEADLINE,messageRetentionDuration:label=RETENTION)"
}

# Function to cleanup all resources
cleanup_resources() {
    print_header "Cleaning Up Pub/Sub Resources"
    
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required. Use --project flag."
        exit 1
    fi
    
    gcloud config set project "$PROJECT_ID"
    
    print_warning "This will delete ALL Pub/Sub topics and subscriptions in the project!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleanup cancelled"
        exit 0
    fi
    
    # Delete all subscriptions first
    print_status "Deleting subscriptions..."
    local subscriptions=$(gcloud pubsub subscriptions list --format="value(name.basename())")
    
    for subscription in $subscriptions; do
        print_status "Deleting subscription: $subscription"
        gcloud pubsub subscriptions delete "$subscription" --quiet
    done
    
    # Delete all topics
    print_status "Deleting topics..."
    local topics=$(gcloud pubsub topics list --format="value(name.basename())")
    
    for topic in $topics; do
        print_status "Deleting topic: $topic"
        gcloud pubsub topics delete "$topic" --quiet
    done
    
    print_success "Cleanup completed"
}

# Function to validate setup
validate_setup() {
    print_status "Validating Pub/Sub setup..."
    
    local errors=0
    
    # Check topics
    for topic in "${!TOPICS[@]}"; do
        if ! gcloud pubsub topics describe "$topic" &> /dev/null; then
            print_error "Topic not found: $topic"
            ((errors++))
        elif [[ "$VERBOSE" == true ]]; then
            print_success "Topic exists: $topic"
        fi
    done
    
    # Check subscriptions
    for subscription in "${!SUBSCRIPTIONS[@]}"; do
        if ! gcloud pubsub subscriptions describe "$subscription" &> /dev/null; then
            print_error "Subscription not found: $subscription"
            ((errors++))
        elif [[ "$VERBOSE" == true ]]; then
            print_success "Subscription exists: $subscription"
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        print_success "Validation completed successfully"
        return 0
    else
        print_error "Validation failed with $errors errors"
        return 1
    fi
}

# Function to show setup summary
show_summary() {
    print_header "Pub/Sub Setup Summary"
    
    echo -e "${GREEN}Project:${NC} $PROJECT_ID"
    echo -e "${GREEN}Topics Created:${NC} ${#TOPICS[@]}"
    echo -e "${GREEN}Subscriptions Created:${NC} ${#SUBSCRIPTIONS[@]}"
    
    echo ""
    echo -e "${BLUE}Topics:${NC}"
    for topic in "${!TOPICS[@]}"; do
        echo "  - $topic: ${TOPICS[$topic]}"
    done
    
    echo ""
    echo -e "${BLUE}Subscriptions:${NC}"
    for subscription in "${!SUBSCRIPTIONS[@]}"; do
        echo "  - $subscription -> ${SUBSCRIPTIONS[$subscription]}"
    done
    
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Update your application configuration to use these topics"
    echo "2. Deploy your Cloud Run service with Pub/Sub permissions"
    echo "3. Test message publishing and consumption"
    echo "4. Monitor subscription metrics in Cloud Console"
}

# Main execution function
main() {
    print_header "Pub/Sub Setup - Misinformation Heatmap"
    
    parse_args "$@"
    check_prerequisites
    
    if [[ "$DRY_RUN" == true ]]; then
        print_warning "DRY RUN MODE - No resources will be created"
    fi
    
    create_topics
    create_subscriptions
    setup_dead_letter_topics
    setup_iam_bindings
    
    if [[ "$DRY_RUN" == false ]]; then
        validate_setup
        show_summary
        print_success "Pub/Sub setup completed successfully!"
    else
        print_success "Dry run completed - review the planned changes above"
    fi
}

# Run main function
main "$@"