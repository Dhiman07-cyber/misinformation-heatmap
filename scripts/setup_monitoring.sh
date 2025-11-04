#!/bin/bash

# Monitoring and Alerting Setup Script for Misinformation Heatmap
# Creates comprehensive monitoring, alerting, and observability infrastructure

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
NOTIFICATION_EMAIL=""
SLACK_WEBHOOK=""
SERVICE_NAME="misinformation-heatmap"
REGION="us-central1"
VERBOSE=false
DRY_RUN=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project PROJECT_ID    GCP Project ID"
    echo "  -e, --email EMAIL           Notification email address"
    echo ""
    echo "Optional Options:"
    echo "  -s, --service SERVICE       Service name (default: misinformation-heatmap)"
    echo "  -r, --region REGION         Cloud Run region (default: us-central1)"
    echo "  --slack-webhook URL         Slack webhook URL for notifications"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -p my-project-id -e admin@company.com"
    echo "  $0 -p my-project-id -e admin@company.com --slack-webhook https://hooks.slack.com/..."
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project)
                PROJECT_ID="$2"
                shift 2
                ;;
            -e|--email)
                NOTIFICATION_EMAIL="$2"
                shift 2
                ;;
            -s|--service)
                SERVICE_NAME="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            --slack-webhook)
                SLACK_WEBHOOK="$2"
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
    
    if [[ -z "$NOTIFICATION_EMAIL" ]]; then
        print_error "Notification email is required (--email)"
        exit 1
    fi
    
    # Validate email format
    if [[ ! "$NOTIFICATION_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
        print_error "Invalid email format: $NOTIFICATION_EMAIL"
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

create_notification_channels() {
    print_header "Creating Notification Channels"
    
    # Create email notification channel
    cat > /tmp/email_channel.json << EOF
{
  "type": "email",
  "displayName": "Misinformation Heatmap Email Alerts",
  "description": "Email notifications for misinformation heatmap alerts",
  "labels": {
    "email_address": "$NOTIFICATION_EMAIL"
  },
  "userLabels": {
    "app": "misinformation-heatmap",
    "environment": "production"
  }
}
EOF

    execute_command "gcloud alpha monitoring channels create --channel-content-from-file=/tmp/email_channel.json --project='$PROJECT_ID'" \
        "Creating email notification channel..."
    
    # Get the email channel ID for later use
    local email_channel_id=$(gcloud alpha monitoring channels list --filter="labels.email_address:$NOTIFICATION_EMAIL" --format="value(name)" --project="$PROJECT_ID" | head -1)
    
    # Create Slack notification channel if webhook provided
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        cat > /tmp/slack_channel.json << EOF
{
  "type": "slack",
  "displayName": "Misinformation Heatmap Slack Alerts",
  "description": "Slack notifications for misinformation heatmap alerts",
  "labels": {
    "url": "$SLACK_WEBHOOK"
  },
  "userLabels": {
    "app": "misinformation-heatmap",
    "environment": "production"
  }
}
EOF

        execute_command "gcloud alpha monitoring channels create --channel-content-from-file=/tmp/slack_channel.json --project='$PROJECT_ID'" \
            "Creating Slack notification channel..."
    fi
    
    print_success "Notification channels created"
    
    # Store channel ID for later use
    echo "$email_channel_id" > /tmp/email_channel_id.txt
}

create_alert_policies() {
    print_header "Creating Alert Policies"
    
    # Get notification channel ID
    local email_channel_id=$(cat /tmp/email_channel_id.txt 2>/dev/null || echo "")
    
    if [[ -z "$email_channel_id" ]]; then
        print_error "Email channel ID not found"
        return 1
    fi
    
    # Cloud Run Service Down Alert
    cat > /tmp/service_down_alert.json << EOF
{
  "displayName": "Cloud Run Service Down",
  "documentation": {
    "content": "The misinformation heatmap Cloud Run service is not responding to requests.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Cloud Run request count is zero",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\"",
        "comparison": "COMPARISON_LESS_THAN",
        "thresholdValue": 1,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE",
            "crossSeriesReducer": "REDUCE_SUM"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$email_channel_id"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

    execute_command "gcloud alpha monitoring policies create --policy-from-file=/tmp/service_down_alert.json --project='$PROJECT_ID'" \
        "Creating service down alert..."
    
    # High Error Rate Alert
    cat > /tmp/high_error_rate_alert.json << EOF
{
  "displayName": "High Error Rate",
  "documentation": {
    "content": "The misinformation heatmap service is experiencing a high error rate (>5%).",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Error rate > 5%",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class!=\"2xx\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 0.05,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_RATE",
            "crossSeriesReducer": "REDUCE_SUM"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$email_channel_id"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

    execute_command "gcloud alpha monitoring policies create --policy-from-file=/tmp/high_error_rate_alert.json --project='$PROJECT_ID'" \
        "Creating high error rate alert..."
    
    # High Response Latency Alert
    cat > /tmp/high_latency_alert.json << EOF
{
  "displayName": "High Response Latency",
  "documentation": {
    "content": "The misinformation heatmap service response latency is above 5 seconds.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Response latency > 5s",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_latencies\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 5000,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_PERCENTILE_95",
            "crossSeriesReducer": "REDUCE_MEAN"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$email_channel_id"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

    execute_command "gcloud alpha monitoring policies create --policy-from-file=/tmp/high_latency_alert.json --project='$PROJECT_ID'" \
        "Creating high latency alert..."
    
    # BigQuery Job Failures Alert
    cat > /tmp/bigquery_failures_alert.json << EOF
{
  "displayName": "BigQuery Job Failures",
  "documentation": {
    "content": "BigQuery jobs are failing frequently, which may affect data processing.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "BigQuery job failure rate > 10%",
      "conditionThreshold": {
        "filter": "resource.type=\"bigquery_project\" AND metric.type=\"bigquery.googleapis.com/job/num_failed\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 0.1,
        "duration": "600s",
        "aggregations": [
          {
            "alignmentPeriod": "300s",
            "perSeriesAligner": "ALIGN_RATE",
            "crossSeriesReducer": "REDUCE_SUM"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$email_channel_id"],
  "alertStrategy": {
    "autoClose": "3600s"
  }
}
EOF

    execute_command "gcloud alpha monitoring policies create --policy-from-file=/tmp/bigquery_failures_alert.json --project='$PROJECT_ID'" \
        "Creating BigQuery failures alert..."
    
    # Pub/Sub Subscription Backlog Alert
    cat > /tmp/pubsub_backlog_alert.json << EOF
{
  "displayName": "Pub/Sub Subscription Backlog",
  "documentation": {
    "content": "Pub/Sub subscriptions have a large backlog of unprocessed messages.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Subscription backlog > 1000 messages",
      "conditionThreshold": {
        "filter": "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\"",
        "comparison": "COMPARISON_GREATER_THAN",
        "thresholdValue": 1000,
        "duration": "600s",
        "aggregations": [
          {
            "alignmentPeriod": "60s",
            "perSeriesAligner": "ALIGN_MEAN",
            "crossSeriesReducer": "REDUCE_MAX"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$email_channel_id"],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF

    execute_command "gcloud alpha monitoring policies create --policy-from-file=/tmp/pubsub_backlog_alert.json --project='$PROJECT_ID'" \
        "Creating Pub/Sub backlog alert..."
    
    print_success "Alert policies created"
}

create_dashboards() {
    print_header "Creating Monitoring Dashboards"
    
    # Main Application Dashboard
    cat > /tmp/main_dashboard.json << EOF
{
  "displayName": "Misinformation Heatmap - Main Dashboard",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Cloud Run Request Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM"
                    }
                  }
                },
                "plotType": "LINE",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Requests/sec",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "widget": {
          "title": "Response Latency (95th percentile)",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_latencies\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_PERCENTILE_95",
                      "crossSeriesReducer": "REDUCE_MEAN"
                    }
                  }
                },
                "plotType": "LINE",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Latency (ms)",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "yPos": 4,
        "widget": {
          "title": "Error Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.label.response_code_class!=\"2xx\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM"
                    }
                  }
                },
                "plotType": "LINE",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Errors/sec",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 6,
        "height": 4,
        "xPos": 6,
        "yPos": 4,
        "widget": {
          "title": "Active Instances",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/container/instance_count\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_MEAN",
                      "crossSeriesReducer": "REDUCE_SUM"
                    }
                  }
                },
                "plotType": "LINE",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Instances",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 12,
        "height": 4,
        "yPos": 8,
        "widget": {
          "title": "BigQuery Job Status",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"bigquery_project\" AND metric.type=\"bigquery.googleapis.com/job/num_completed\"",
                    "aggregation": {
                      "alignmentPeriod": "300s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["metric.label.job_type"]
                    }
                  }
                },
                "plotType": "STACKED_AREA",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Jobs/sec",
              "scale": "LINEAR"
            }
          }
        }
      }
    ]
  }
}
EOF

    execute_command "gcloud monitoring dashboards create --config-from-file=/tmp/main_dashboard.json --project='$PROJECT_ID'" \
        "Creating main dashboard..."
    
    # Data Processing Dashboard
    cat > /tmp/data_dashboard.json << EOF
{
  "displayName": "Misinformation Heatmap - Data Processing",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Pub/Sub Message Publish Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"pubsub_topic\" AND metric.type=\"pubsub.googleapis.com/topic/send_message_operation_count\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["resource.label.topic_id"]
                    }
                  }
                },
                "plotType": "STACKED_AREA",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Messages/sec",
              "scale": "LINEAR"
            }
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
                    "filter": "resource.type=\"pubsub_subscription\" AND metric.type=\"pubsub.googleapis.com/subscription/num_undelivered_messages\"",
                    "aggregation": {
                      "alignmentPeriod": "60s",
                      "perSeriesAligner": "ALIGN_MEAN",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["resource.label.subscription_id"]
                    }
                  }
                },
                "plotType": "STACKED_AREA",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Messages",
              "scale": "LINEAR"
            }
          }
        }
      },
      {
        "width": 12,
        "height": 4,
        "yPos": 4,
        "widget": {
          "title": "BigQuery Data Ingestion",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"bigquery_table\" AND metric.type=\"bigquery.googleapis.com/storage/uploaded_bytes\"",
                    "aggregation": {
                      "alignmentPeriod": "300s",
                      "perSeriesAligner": "ALIGN_RATE",
                      "crossSeriesReducer": "REDUCE_SUM"
                    }
                  }
                },
                "plotType": "LINE",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Bytes/sec",
              "scale": "LINEAR"
            }
          }
        }
      }
    ]
  }
}
EOF

    execute_command "gcloud monitoring dashboards create --config-from-file=/tmp/data_dashboard.json --project='$PROJECT_ID'" \
        "Creating data processing dashboard..."
    
    print_success "Dashboards created"
}

setup_uptime_checks() {
    print_header "Setting up Uptime Checks"
    
    # Get service URL
    local service_url=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)" 2>/dev/null || echo "")
    
    if [[ -z "$service_url" ]]; then
        print_warning "Service URL not found, skipping uptime checks"
        return 0
    fi
    
    # Remove https:// prefix for uptime check configuration
    local host=$(echo "$service_url" | sed 's|https://||')
    
    # Main service uptime check
    cat > /tmp/uptime_check.json << EOF
{
  "displayName": "Misinformation Heatmap Service",
  "monitoredResource": {
    "type": "uptime_url",
    "labels": {
      "project_id": "$PROJECT_ID",
      "host": "$host"
    }
  },
  "httpCheck": {
    "path": "/health",
    "port": 443,
    "useSsl": true,
    "validateSsl": true
  },
  "period": "60s",
  "timeout": "10s",
  "selectedRegions": [
    "USA",
    "EUROPE",
    "ASIA_PACIFIC"
  ]
}
EOF

    execute_command "gcloud monitoring uptime create --config-from-file=/tmp/uptime_check.json --project='$PROJECT_ID'" \
        "Creating uptime check..."
    
    # API uptime check
    cat > /tmp/api_uptime_check.json << EOF
{
  "displayName": "Misinformation Heatmap API",
  "monitoredResource": {
    "type": "uptime_url",
    "labels": {
      "project_id": "$PROJECT_ID",
      "host": "$host"
    }
  },
  "httpCheck": {
    "path": "/api/v1/health",
    "port": 443,
    "useSsl": true,
    "validateSsl": true
  },
  "period": "300s",
  "timeout": "10s",
  "selectedRegions": [
    "USA",
    "EUROPE"
  ]
}
EOF

    execute_command "gcloud monitoring uptime create --config-from-file=/tmp/api_uptime_check.json --project='$PROJECT_ID'" \
        "Creating API uptime check..."
    
    print_success "Uptime checks created"
}

create_custom_metrics() {
    print_header "Creating Custom Metrics"
    
    # Create custom metric descriptors for application-specific metrics
    cat > /tmp/misinformation_events_metric.json << EOF
{
  "type": "custom.googleapis.com/misinformation_heatmap/events_processed",
  "labels": [
    {
      "key": "source_type",
      "valueType": "STRING",
      "description": "Type of data source (rss, crawler, api)"
    },
    {
      "key": "processing_stage",
      "valueType": "STRING",
      "description": "Processing stage (raw, processed, validated, published)"
    }
  ],
  "metricKind": "CUMULATIVE",
  "valueType": "INT64",
  "unit": "1",
  "description": "Number of misinformation events processed",
  "displayName": "Misinformation Events Processed"
}
EOF

    execute_command "gcloud logging metrics create misinformation_events_processed --config-from-file=/tmp/misinformation_events_metric.json --project='$PROJECT_ID'" \
        "Creating custom events metric..."
    
    # Create metric for data quality
    cat > /tmp/data_quality_metric.json << EOF
{
  "type": "custom.googleapis.com/misinformation_heatmap/data_quality_score",
  "labels": [
    {
      "key": "source",
      "valueType": "STRING",
      "description": "Data source identifier"
    }
  ],
  "metricKind": "GAUGE",
  "valueType": "DOUBLE",
  "unit": "1",
  "description": "Data quality score (0-1)",
  "displayName": "Data Quality Score"
}
EOF

    execute_command "gcloud logging metrics create data_quality_score --config-from-file=/tmp/data_quality_metric.json --project='$PROJECT_ID'" \
        "Creating data quality metric..."
    
    print_success "Custom metrics created"
}

setup_log_based_metrics() {
    print_header "Setting up Log-based Metrics"
    
    # Error rate metric from logs
    execute_command "gcloud logging metrics create error_rate_from_logs \
        --description='Error rate calculated from application logs' \
        --log-filter='resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND severity>=ERROR' \
        --project='$PROJECT_ID'" \
        "Creating error rate log metric..."
    
    # NLP processing time metric
    execute_command "gcloud logging metrics create nlp_processing_time \
        --description='NLP processing time from application logs' \
        --log-filter='resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND jsonPayload.component=\"nlp_analyzer\"' \
        --value-extractor='EXTRACT(jsonPayload.processing_time_ms)' \
        --project='$PROJECT_ID'" \
        "Creating NLP processing time metric..."
    
    # Data source health metric
    execute_command "gcloud logging metrics create data_source_health \
        --description='Data source health status from logs' \
        --log-filter='resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND jsonPayload.component=\"data_source\" AND jsonPayload.status=\"error\"' \
        --project='$PROJECT_ID'" \
        "Creating data source health metric..."
    
    print_success "Log-based metrics created"
}

main() {
    print_header "Monitoring Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Setting up monitoring with the following configuration:"
    print_status "  Project ID: $PROJECT_ID"
    print_status "  Service Name: $SERVICE_NAME"
    print_status "  Region: $REGION"
    print_status "  Notification Email: $NOTIFICATION_EMAIL"
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        print_status "  Slack Webhook: Configured"
    fi
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with monitoring setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Execute setup steps
    create_notification_channels
    create_alert_policies
    create_dashboards
    setup_uptime_checks
    create_custom_metrics
    setup_log_based_metrics
    
    print_header "Monitoring Setup Complete!"
    print_success "Comprehensive monitoring and alerting is now configured"
    print_status ""
    print_status "Created resources:"
    print_status "  - Notification channels (email, slack if configured)"
    print_status "  - Alert policies for service health, errors, latency, and data processing"
    print_status "  - Monitoring dashboards for application and data processing metrics"
    print_status "  - Uptime checks for service and API endpoints"
    print_status "  - Custom metrics for application-specific monitoring"
    print_status "  - Log-based metrics for detailed observability"
    print_status ""
    print_status "Next steps:"
    print_status "1. Review dashboards in Cloud Monitoring console"
    print_status "2. Test alert notifications"
    print_status "3. Customize alert thresholds based on baseline performance"
    print_status "4. Set up additional custom metrics as needed"
    
    # Cleanup temp files
    rm -f /tmp/*_channel.json /tmp/*_alert.json /tmp/*_dashboard.json /tmp/*_check.json /tmp/*_metric.json /tmp/email_channel_id.txt
}

# Run main function with all arguments
main "$@"