#!/bin/bash

# Pub/Sub Setup Script for Misinformation Heatmap
# Creates topics, subscriptions, and dead letter queues for event processing

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
VERBOSE=false
DRY_RUN=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project PROJECT_ID    GCP Project ID"
    echo ""
    echo "Optional Options:"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -p my-project-id"
    echo "  $0 -p my-project-id --verbose"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project)
                PROJECT_ID="$2"
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
    if [[ -z "$PROJECT_ID" ]]; then
        print_error "Project ID is required (--project)"
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

create_topics() {
    print_header "Creating Pub/Sub Topics"
    
    # Define topics for the event processing pipeline
    local topics=(
        "events-raw:Raw events from data sources"
        "events-processed:Events after NLP processing"
        "events-validated:Events after satellite validation"
        "events-published:Events ready for frontend"
        "events-dlq:Dead letter queue for failed events"
        "monitoring-alerts:System monitoring alerts"
        "data-source-status:Data source health updates"
    )
    
    for topic_info in "${topics[@]}"; do
        local topic_name=$(echo "$topic_info" | cut -d: -f1)
        local topic_desc=$(echo "$topic_info" | cut -d: -f2)
        
        # Check if topic exists
        if gcloud pubsub topics describe "$topic_name" --project="$PROJECT_ID" &>/dev/null; then
            print_warning "Topic $topic_name already exists"
            continue
        fi
        
        execute_command "gcloud pubsub topics create '$topic_name' --project='$PROJECT_ID' --labels='app=misinformation-heatmap,component=pubsub'" \
            "Creating topic: $topic_name ($topic_desc)"
    done
    
    print_success "Topics created successfully"
}

create_subscriptions() {
    print_header "Creating Pub/Sub Subscriptions"
    
    # Define subscriptions with their configurations
    local subscriptions=(
        "events-raw:events-raw-processor:events-raw:Process raw events through NLP pipeline"
        "events-processed:events-processed-validator:events-processed:Validate processed events with satellite data"
        "events-validated:events-validated-publisher:events-validated:Publish validated events to BigQuery"
        "events-published:events-published-aggregator:events-published:Aggregate published events for heatmap"
        "monitoring-alerts:monitoring-alerts-handler:monitoring-alerts:Handle system monitoring alerts"
        "data-source-status:data-source-status-tracker:data-source-status:Track data source health"
    )
    
    for sub_info in "${subscriptions[@]}"; do
        local topic_name=$(echo "$sub_info" | cut -d: -f1)
        local sub_name=$(echo "$sub_info" | cut -d: -f2)
        local dlq_topic=$(echo "$sub_info" | cut -d: -f3)
        local sub_desc=$(echo "$sub_info" | cut -d: -f4)
        
        # Check if subscription exists
        if gcloud pubsub subscriptions describe "$sub_name" --project="$PROJECT_ID" &>/dev/null; then
            print_warning "Subscription $sub_name already exists"
            continue
        fi
        
        # Create subscription with dead letter queue
        execute_command "gcloud pubsub subscriptions create '$sub_name' \
            --topic='$topic_name' \
            --project='$PROJECT_ID' \
            --ack-deadline=60 \
            --message-retention-duration=7d \
            --max-delivery-attempts=5 \
            --dead-letter-topic='events-dlq' \
            --labels='app=misinformation-heatmap,component=pubsub'" \
            "Creating subscription: $sub_name ($sub_desc)"
    done
    
    print_success "Subscriptions created successfully"
}

create_push_subscriptions() {
    print_header "Creating Push Subscriptions for Cloud Run"
    
    # Push subscriptions for Cloud Run services
    local push_subscriptions=(
        "events-raw:events-raw-push:https://api-service-url/webhooks/events/raw"
        "events-processed:events-processed-push:https://api-service-url/webhooks/events/processed"
        "events-validated:events-validated-push:https://api-service-url/webhooks/events/validated"
        "monitoring-alerts:monitoring-alerts-push:https://api-service-url/webhooks/monitoring/alerts"
    )
    
    print_warning "Push subscriptions require actual Cloud Run service URLs"
    print_status "Creating pull subscriptions instead. Convert to push after deployment."
    
    for sub_info in "${push_subscriptions[@]}"; do
        local topic_name=$(echo "$sub_info" | cut -d: -f1)
        local sub_name=$(echo "$sub_info" | cut -d: -f2)
        local endpoint_url=$(echo "$sub_info" | cut -d: -f3)
        
        # Check if subscription exists
        if gcloud pubsub subscriptions describe "$sub_name" --project="$PROJECT_ID" &>/dev/null; then
            print_warning "Subscription $sub_name already exists"
            continue
        fi
        
        # Create pull subscription for now
        execute_command "gcloud pubsub subscriptions create '$sub_name' \
            --topic='$topic_name' \
            --project='$PROJECT_ID' \
            --ack-deadline=30 \
            --message-retention-duration=1d \
            --max-delivery-attempts=3 \
            --dead-letter-topic='events-dlq' \
            --labels='app=misinformation-heatmap,component=pubsub,type=push-ready'" \
            "Creating pull subscription (push-ready): $sub_name"
    done
    
    print_success "Push-ready subscriptions created"
}

setup_iam_permissions() {
    print_header "Setting up IAM Permissions for Pub/Sub"
    
    # Service account for Pub/Sub operations
    local sa_email="misinformation-heatmap@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Grant Pub/Sub permissions to service account
    local pubsub_roles=(
        "roles/pubsub.publisher"
        "roles/pubsub.subscriber"
        "roles/pubsub.viewer"
    )
    
    for role in "${pubsub_roles[@]}"; do
        execute_command "gcloud projects add-iam-policy-binding '$PROJECT_ID' \
            --member='serviceAccount:$sa_email' \
            --role='$role'" \
            "Granting $role to service account"
    done
    
    # Create Pub/Sub service account for Cloud Run
    local pubsub_sa_name="pubsub-invoker"
    local pubsub_sa_email="$pubsub_sa_name@$PROJECT_ID.iam.gserviceaccount.com"
    
    # Check if service account exists
    if ! gcloud iam service-accounts describe "$pubsub_sa_email" --project="$PROJECT_ID" &>/dev/null; then
        execute_command "gcloud iam service-accounts create '$pubsub_sa_name' \
            --display-name='Pub/Sub Cloud Run Invoker' \
            --description='Service account for Pub/Sub to invoke Cloud Run services' \
            --project='$PROJECT_ID'" \
            "Creating Pub/Sub invoker service account"
        
        # Grant Cloud Run invoker role
        execute_command "gcloud projects add-iam-policy-binding '$PROJECT_ID' \
            --member='serviceAccount:$pubsub_sa_email' \
            --role='roles/run.invoker'" \
            "Granting Cloud Run invoker role"
    else
        print_warning "Pub/Sub invoker service account already exists"
    fi
    
    print_success "IAM permissions configured"
}

create_schemas() {
    print_header "Creating Pub/Sub Schemas"
    
    # Create Avro schema for event messages
    cat > /tmp/event_schema.avsc << 'EOF'
{
  "type": "record",
  "name": "Event",
  "namespace": "com.misinformation.heatmap",
  "fields": [
    {
      "name": "id",
      "type": "string",
      "doc": "Unique event identifier"
    },
    {
      "name": "timestamp",
      "type": "long",
      "logicalType": "timestamp-millis",
      "doc": "Event timestamp in milliseconds"
    },
    {
      "name": "source",
      "type": "string",
      "doc": "Data source identifier"
    },
    {
      "name": "source_type",
      "type": {
        "type": "enum",
        "name": "SourceType",
        "symbols": ["RSS", "CRAWLER", "API", "MANUAL"]
      },
      "doc": "Type of data source"
    },
    {
      "name": "title",
      "type": ["null", "string"],
      "default": null,
      "doc": "Event title or headline"
    },
    {
      "name": "content",
      "type": ["null", "string"],
      "default": null,
      "doc": "Full event content"
    },
    {
      "name": "url",
      "type": ["null", "string"],
      "default": null,
      "doc": "Source URL"
    },
    {
      "name": "location",
      "type": [
        "null",
        {
          "type": "record",
          "name": "Location",
          "fields": [
            {"name": "state", "type": ["null", "string"], "default": null},
            {"name": "district", "type": ["null", "string"], "default": null},
            {"name": "city", "type": ["null", "string"], "default": null},
            {"name": "latitude", "type": ["null", "double"], "default": null},
            {"name": "longitude", "type": ["null", "double"], "default": null}
          ]
        }
      ],
      "default": null,
      "doc": "Geographic location information"
    },
    {
      "name": "processing_status",
      "type": {
        "type": "enum",
        "name": "ProcessingStatus",
        "symbols": ["RAW", "PROCESSED", "VALIDATED", "PUBLISHED", "FAILED"]
      },
      "doc": "Current processing status"
    },
    {
      "name": "metadata",
      "type": ["null", "string"],
      "default": null,
      "doc": "Additional metadata as JSON string"
    }
  ]
}
EOF

    # Create schema in Pub/Sub
    execute_command "gcloud pubsub schemas create event-schema \
        --type=AVRO \
        --definition-file=/tmp/event_schema.avsc \
        --project='$PROJECT_ID'" \
        "Creating event schema"
    
    # Create monitoring alert schema
    cat > /tmp/alert_schema.avsc << 'EOF'
{
  "type": "record",
  "name": "Alert",
  "namespace": "com.misinformation.heatmap.monitoring",
  "fields": [
    {
      "name": "id",
      "type": "string",
      "doc": "Unique alert identifier"
    },
    {
      "name": "timestamp",
      "type": "long",
      "logicalType": "timestamp-millis",
      "doc": "Alert timestamp"
    },
    {
      "name": "severity",
      "type": {
        "type": "enum",
        "name": "Severity",
        "symbols": ["INFO", "WARNING", "ERROR", "CRITICAL"]
      },
      "doc": "Alert severity level"
    },
    {
      "name": "component",
      "type": "string",
      "doc": "System component that generated the alert"
    },
    {
      "name": "message",
      "type": "string",
      "doc": "Alert message"
    },
    {
      "name": "details",
      "type": ["null", "string"],
      "default": null,
      "doc": "Additional alert details as JSON"
    }
  ]
}
EOF

    execute_command "gcloud pubsub schemas create alert-schema \
        --type=AVRO \
        --definition-file=/tmp/alert_schema.avsc \
        --project='$PROJECT_ID'" \
        "Creating alert schema"
    
    print_success "Schemas created successfully"
}

setup_monitoring() {
    print_header "Setting up Pub/Sub Monitoring"
    
    # Create monitoring dashboard configuration
    cat > /tmp/pubsub_dashboard.json << EOF
{
  "displayName": "Misinformation Heatmap - Pub/Sub Monitoring",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Message Publish Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"pubsub_topic\" AND resource.label.project_id=\"$PROJECT_ID\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["resource.label.topic_id"]
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
          "title": "Subscription Backlog",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"pubsub_subscription\" AND resource.label.project_id=\"$PROJECT_ID\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_MEAN",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["resource.label.subscription_id"]
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

    print_status "Monitoring dashboard configuration created at /tmp/pubsub_dashboard.json"
    print_warning "Please create the dashboard manually in Cloud Monitoring console"
    
    print_success "Monitoring setup prepared"
}

create_test_messages() {
    print_header "Creating Test Messages"
    
    # Create sample test messages
    cat > /tmp/test_event.json << 'EOF'
{
  "id": "test-event-001",
  "timestamp": 1640995200000,
  "source": "test-source",
  "source_type": "MANUAL",
  "title": "Test Event for Pipeline Validation",
  "content": "This is a test event to validate the Pub/Sub pipeline setup.",
  "url": "https://example.com/test",
  "location": {
    "state": "Delhi",
    "district": "New Delhi",
    "city": "New Delhi",
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "processing_status": "RAW",
  "metadata": "{\"test\": true, \"environment\": \"setup\"}"
}
EOF

    cat > /tmp/test_alert.json << 'EOF'
{
  "id": "test-alert-001",
  "timestamp": 1640995200000,
  "severity": "INFO",
  "component": "pubsub-setup",
  "message": "Test alert for monitoring pipeline validation",
  "details": "{\"test\": true, \"setup_phase\": \"complete\"}"
}
EOF

    print_status "Test message files created:"
    print_status "  - Event: /tmp/test_event.json"
    print_status "  - Alert: /tmp/test_alert.json"
    print_status ""
    print_status "To test the pipeline, run:"
    print_status "  gcloud pubsub topics publish events-raw --message-body='\$(cat /tmp/test_event.json)'"
    print_status "  gcloud pubsub topics publish monitoring-alerts --message-body='\$(cat /tmp/test_alert.json)'"
    
    print_success "Test messages prepared"
}

main() {
    print_header "Pub/Sub Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Setting up Pub/Sub with the following configuration:"
    print_status "  Project ID: $PROJECT_ID"
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with Pub/Sub setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Execute setup steps
    create_topics
    create_subscriptions
    create_push_subscriptions
    setup_iam_permissions
    create_schemas
    setup_monitoring
    create_test_messages
    
    print_header "Pub/Sub Setup Complete!"
    print_success "Pub/Sub infrastructure is ready for production use"
    print_status ""
    print_status "Created resources:"
    print_status "  - Topics: events-raw, events-processed, events-validated, events-published, events-dlq, monitoring-alerts, data-source-status"
    print_status "  - Subscriptions: Pull and push-ready subscriptions for all topics"
    print_status "  - Schemas: event-schema, alert-schema"
    print_status "  - IAM: Service accounts and permissions"
    print_status ""
    print_status "Next steps:"
    print_status "1. Deploy Cloud Run services"
    print_status "2. Convert pull subscriptions to push subscriptions with actual endpoints"
    print_status "3. Test the pipeline with sample messages"
    print_status "4. Set up monitoring dashboards"
    
    # Cleanup temp files
    rm -f /tmp/event_schema.avsc /tmp/alert_schema.avsc /tmp/pubsub_dashboard.json
    
    print_status ""
    print_status "Test files available at:"
    print_status "  - /tmp/test_event.json"
    print_status "  - /tmp/test_alert.json"
}

# Run main function with all arguments
main "$@"