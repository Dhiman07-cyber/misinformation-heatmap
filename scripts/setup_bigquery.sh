#!/bin/bash

# BigQuery Setup Script for Misinformation Heatmap
# Creates datasets, tables, and views for production data storage

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
DATASET_NAME="misinformation_heatmap"
LOCATION="US"
VERBOSE=false
DRY_RUN=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project PROJECT_ID    GCP Project ID"
    echo ""
    echo "Optional Options:"
    echo "  -d, --dataset DATASET       Dataset name (default: misinformation_heatmap)"
    echo "  -l, --location LOCATION     BigQuery location (default: US)"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -p my-project-id"
    echo "  $0 -p my-project-id -d custom_dataset -l EU"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project)
                PROJECT_ID="$2"
                shift 2
                ;;
            -d|--dataset)
                DATASET_NAME="$2"
                shift 2
                ;;
            -l|--location)
                LOCATION="$2"
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

execute_bq_command() {
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

create_dataset() {
    print_header "Creating BigQuery Dataset"
    
    # Check if dataset exists
    if bq show --project_id="$PROJECT_ID" "$DATASET_NAME" &>/dev/null; then
        print_warning "Dataset $DATASET_NAME already exists"
        return 0
    fi
    
    execute_bq_command "bq mk --project_id='$PROJECT_ID' --location='$LOCATION' --description='Misinformation heatmap data storage' '$DATASET_NAME'" \
        "Creating dataset $DATASET_NAME..."
    
    print_success "Dataset created successfully"
}

create_events_table() {
    print_header "Creating Events Table"
    
    local table_name="$DATASET_NAME.events"
    
    # Create events table with schema
    cat > /tmp/events_schema.json << 'EOF'
[
  {
    "name": "id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique event identifier"
  },
  {
    "name": "timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Event timestamp"
  },
  {
    "name": "source",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Data source identifier"
  },
  {
    "name": "source_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Type of data source (rss, crawler, api)"
  },
  {
    "name": "title",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Event title or headline"
  },
  {
    "name": "content",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Full event content"
  },
  {
    "name": "url",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Source URL"
  },
  {
    "name": "location",
    "type": "RECORD",
    "mode": "NULLABLE",
    "description": "Geographic location information",
    "fields": [
      {
        "name": "state",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "Indian state"
      },
      {
        "name": "district",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "District within state"
      },
      {
        "name": "city",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "City name"
      },
      {
        "name": "latitude",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Latitude coordinate"
      },
      {
        "name": "longitude",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Longitude coordinate"
      }
    ]
  },
  {
    "name": "nlp_analysis",
    "type": "RECORD",
    "mode": "NULLABLE",
    "description": "NLP analysis results",
    "fields": [
      {
        "name": "misinformation_score",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Misinformation probability (0-1)"
      },
      {
        "name": "confidence",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Analysis confidence (0-1)"
      },
      {
        "name": "categories",
        "type": "STRING",
        "mode": "REPEATED",
        "description": "Content categories"
      },
      {
        "name": "sentiment",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "Sentiment analysis result"
      },
      {
        "name": "language",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "Detected language"
      }
    ]
  },
  {
    "name": "satellite_validation",
    "type": "RECORD",
    "mode": "NULLABLE",
    "description": "Satellite validation results",
    "fields": [
      {
        "name": "validated",
        "type": "BOOLEAN",
        "mode": "NULLABLE",
        "description": "Whether satellite validation was performed"
      },
      {
        "name": "infrastructure_detected",
        "type": "BOOLEAN",
        "mode": "NULLABLE",
        "description": "Infrastructure detected in satellite imagery"
      },
      {
        "name": "confidence",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Validation confidence (0-1)"
      },
      {
        "name": "image_url",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "Satellite image URL"
      }
    ]
  },
  {
    "name": "processing_status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Processing status (raw, processed, validated, published)"
  },
  {
    "name": "created_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Record creation timestamp"
  },
  {
    "name": "updated_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Record last update timestamp"
  },
  {
    "name": "metadata",
    "type": "JSON",
    "mode": "NULLABLE",
    "description": "Additional metadata as JSON"
  }
]
EOF

    execute_bq_command "bq mk --project_id='$PROJECT_ID' --table '$table_name' /tmp/events_schema.json" \
        "Creating events table..."
    
    print_success "Events table created successfully"
}

create_aggregations_table() {
    print_header "Creating Aggregations Table"
    
    local table_name="$DATASET_NAME.aggregations"
    
    # Create aggregations table for heatmap data
    cat > /tmp/aggregations_schema.json << 'EOF'
[
  {
    "name": "id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique aggregation identifier"
  },
  {
    "name": "timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Aggregation timestamp"
  },
  {
    "name": "time_window",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Time window (hourly, daily, weekly)"
  },
  {
    "name": "location",
    "type": "RECORD",
    "mode": "REQUIRED",
    "description": "Geographic location",
    "fields": [
      {
        "name": "state",
        "type": "STRING",
        "mode": "REQUIRED",
        "description": "Indian state"
      },
      {
        "name": "district",
        "type": "STRING",
        "mode": "NULLABLE",
        "description": "District within state"
      },
      {
        "name": "latitude",
        "type": "FLOAT",
        "mode": "REQUIRED",
        "description": "Latitude coordinate"
      },
      {
        "name": "longitude",
        "type": "FLOAT",
        "mode": "REQUIRED",
        "description": "Longitude coordinate"
      }
    ]
  },
  {
    "name": "metrics",
    "type": "RECORD",
    "mode": "REQUIRED",
    "description": "Aggregated metrics",
    "fields": [
      {
        "name": "total_events",
        "type": "INTEGER",
        "mode": "REQUIRED",
        "description": "Total number of events"
      },
      {
        "name": "misinformation_events",
        "type": "INTEGER",
        "mode": "REQUIRED",
        "description": "Number of misinformation events"
      },
      {
        "name": "avg_misinformation_score",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Average misinformation score"
      },
      {
        "name": "validated_events",
        "type": "INTEGER",
        "mode": "REQUIRED",
        "description": "Number of satellite-validated events"
      },
      {
        "name": "heat_intensity",
        "type": "FLOAT",
        "mode": "REQUIRED",
        "description": "Calculated heat intensity (0-1)"
      }
    ]
  },
  {
    "name": "categories",
    "type": "RECORD",
    "mode": "REPEATED",
    "description": "Category breakdown",
    "fields": [
      {
        "name": "category",
        "type": "STRING",
        "mode": "REQUIRED",
        "description": "Content category"
      },
      {
        "name": "count",
        "type": "INTEGER",
        "mode": "REQUIRED",
        "description": "Number of events in category"
      }
    ]
  },
  {
    "name": "created_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Record creation timestamp"
  }
]
EOF

    execute_bq_command "bq mk --project_id='$PROJECT_ID' --table '$table_name' /tmp/aggregations_schema.json" \
        "Creating aggregations table..."
    
    print_success "Aggregations table created successfully"
}

create_data_sources_table() {
    print_header "Creating Data Sources Table"
    
    local table_name="$DATASET_NAME.data_sources"
    
    # Create data sources tracking table
    cat > /tmp/data_sources_schema.json << 'EOF'
[
  {
    "name": "source_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique source identifier"
  },
  {
    "name": "name",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Human-readable source name"
  },
  {
    "name": "type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Source type (rss, crawler, api)"
  },
  {
    "name": "url",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Source URL"
  },
  {
    "name": "category",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Source category"
  },
  {
    "name": "language",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Primary language"
  },
  {
    "name": "region",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Geographic region"
  },
  {
    "name": "status",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Source status (active, inactive, error)"
  },
  {
    "name": "last_fetch",
    "type": "TIMESTAMP",
    "mode": "NULLABLE",
    "description": "Last successful fetch timestamp"
  },
  {
    "name": "fetch_count",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "Total number of fetches"
  },
  {
    "name": "error_count",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "Number of fetch errors"
  },
  {
    "name": "created_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Source registration timestamp"
  },
  {
    "name": "updated_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Last update timestamp"
  }
]
EOF

    execute_bq_command "bq mk --project_id='$PROJECT_ID' --table '$table_name' /tmp/data_sources_schema.json" \
        "Creating data sources table..."
    
    print_success "Data sources table created successfully"
}

create_views() {
    print_header "Creating BigQuery Views"
    
    # Create heatmap view for frontend
    local heatmap_view="$DATASET_NAME.heatmap_view"
    
    cat > /tmp/heatmap_view.sql << EOF
CREATE OR REPLACE VIEW \`$PROJECT_ID.$heatmap_view\` AS
SELECT
  location.state,
  location.district,
  location.latitude,
  location.longitude,
  COUNT(*) as total_events,
  COUNTIF(nlp_analysis.misinformation_score > 0.5) as misinformation_events,
  AVG(nlp_analysis.misinformation_score) as avg_misinformation_score,
  COUNTIF(satellite_validation.validated = true) as validated_events,
  -- Calculate heat intensity based on misinformation events and validation
  CASE 
    WHEN COUNT(*) = 0 THEN 0
    ELSE (COUNTIF(nlp_analysis.misinformation_score > 0.5) * 1.0 / COUNT(*)) * 
         (1 + COUNTIF(satellite_validation.validated = true) * 0.2)
  END as heat_intensity,
  MAX(timestamp) as last_event_time
FROM \`$PROJECT_ID.$DATASET_NAME.events\`
WHERE 
  location.latitude IS NOT NULL 
  AND location.longitude IS NOT NULL
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  AND processing_status = 'published'
GROUP BY 
  location.state, 
  location.district, 
  location.latitude, 
  location.longitude
HAVING COUNT(*) >= 1
ORDER BY heat_intensity DESC
EOF

    execute_bq_command "bq query --project_id='$PROJECT_ID' --use_legacy_sql=false < /tmp/heatmap_view.sql" \
        "Creating heatmap view..."
    
    # Create recent events view
    local recent_events_view="$DATASET_NAME.recent_events_view"
    
    cat > /tmp/recent_events_view.sql << EOF
CREATE OR REPLACE VIEW \`$PROJECT_ID.$recent_events_view\` AS
SELECT
  id,
  timestamp,
  source,
  title,
  content,
  url,
  location.state,
  location.district,
  location.city,
  location.latitude,
  location.longitude,
  nlp_analysis.misinformation_score,
  nlp_analysis.confidence,
  nlp_analysis.categories,
  satellite_validation.validated as satellite_validated,
  satellite_validation.infrastructure_detected
FROM \`$PROJECT_ID.$DATASET_NAME.events\`
WHERE 
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND processing_status = 'published'
  AND nlp_analysis.misinformation_score IS NOT NULL
ORDER BY timestamp DESC
LIMIT 1000
EOF

    execute_bq_command "bq query --project_id='$PROJECT_ID' --use_legacy_sql=false < /tmp/recent_events_view.sql" \
        "Creating recent events view..."
    
    # Create source statistics view
    local source_stats_view="$DATASET_NAME.source_statistics_view"
    
    cat > /tmp/source_stats_view.sql << EOF
CREATE OR REPLACE VIEW \`$PROJECT_ID.$source_stats_view\` AS
SELECT
  source,
  COUNT(*) as total_events,
  COUNTIF(nlp_analysis.misinformation_score > 0.5) as misinformation_events,
  AVG(nlp_analysis.misinformation_score) as avg_misinformation_score,
  COUNTIF(satellite_validation.validated = true) as validated_events,
  MIN(timestamp) as first_event,
  MAX(timestamp) as last_event,
  COUNT(DISTINCT location.state) as states_covered
FROM \`$PROJECT_ID.$DATASET_NAME.events\`
WHERE 
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND processing_status = 'published'
GROUP BY source
ORDER BY total_events DESC
EOF

    execute_bq_command "bq query --project_id='$PROJECT_ID' --use_legacy_sql=false < /tmp/source_stats_view.sql" \
        "Creating source statistics view..."
    
    print_success "Views created successfully"
}

setup_partitioning() {
    print_header "Setting up Table Partitioning"
    
    # Create partitioned events table for better performance
    local partitioned_table="$DATASET_NAME.events_partitioned"
    
    cat > /tmp/partitioned_events_schema.json << 'EOF'
[
  {
    "name": "id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "event_date",
    "type": "DATE",
    "mode": "REQUIRED",
    "description": "Partition key - event date"
  },
  {
    "name": "timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "source",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "data",
    "type": "JSON",
    "mode": "REQUIRED",
    "description": "Complete event data as JSON"
  }
]
EOF

    execute_bq_command "bq mk --project_id='$PROJECT_ID' --table '$partitioned_table' --time_partitioning_field=event_date --time_partitioning_type=DAY --clustering_fields=source /tmp/partitioned_events_schema.json" \
        "Creating partitioned events table..."
    
    print_success "Partitioned table created successfully"
}

create_scheduled_queries() {
    print_header "Creating Scheduled Queries"
    
    # Create scheduled query for aggregations
    cat > /tmp/aggregation_query.sql << EOF
INSERT INTO \`$PROJECT_ID.$DATASET_NAME.aggregations\`
SELECT
  GENERATE_UUID() as id,
  CURRENT_TIMESTAMP() as timestamp,
  'hourly' as time_window,
  STRUCT(
    location.state,
    location.district,
    location.latitude,
    location.longitude
  ) as location,
  STRUCT(
    COUNT(*) as total_events,
    COUNTIF(nlp_analysis.misinformation_score > 0.5) as misinformation_events,
    AVG(nlp_analysis.misinformation_score) as avg_misinformation_score,
    COUNTIF(satellite_validation.validated = true) as validated_events,
    CASE 
      WHEN COUNT(*) = 0 THEN 0
      ELSE (COUNTIF(nlp_analysis.misinformation_score > 0.5) * 1.0 / COUNT(*)) * 
           (1 + COUNTIF(satellite_validation.validated = true) * 0.2)
    END as heat_intensity
  ) as metrics,
  ARRAY_AGG(
    STRUCT(
      category,
      COUNT(*) as count
    )
  ) as categories,
  CURRENT_TIMESTAMP() as created_at
FROM \`$PROJECT_ID.$DATASET_NAME.events\`
CROSS JOIN UNNEST(nlp_analysis.categories) as category
WHERE 
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
  AND location.latitude IS NOT NULL 
  AND location.longitude IS NOT NULL
  AND processing_status = 'published'
GROUP BY 
  location.state, 
  location.district, 
  location.latitude, 
  location.longitude
HAVING COUNT(*) >= 1
EOF

    print_status "Scheduled query SQL created. Manual setup required in BigQuery console."
    print_warning "Please create scheduled query manually in BigQuery console using /tmp/aggregation_query.sql"
    
    print_success "Scheduled queries prepared"
}

main() {
    print_header "BigQuery Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Setting up BigQuery with the following configuration:"
    print_status "  Project ID: $PROJECT_ID"
    print_status "  Dataset: $DATASET_NAME"
    print_status "  Location: $LOCATION"
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with BigQuery setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Execute setup steps
    create_dataset
    create_events_table
    create_aggregations_table
    create_data_sources_table
    create_views
    setup_partitioning
    create_scheduled_queries
    
    print_header "BigQuery Setup Complete!"
    print_success "Dataset $DATASET_NAME is ready for production use"
    print_status ""
    print_status "Created resources:"
    print_status "  - Dataset: $DATASET_NAME"
    print_status "  - Tables: events, aggregations, data_sources, events_partitioned"
    print_status "  - Views: heatmap_view, recent_events_view, source_statistics_view"
    print_status ""
    print_status "Next steps:"
    print_status "1. Set up scheduled queries in BigQuery console"
    print_status "2. Configure data retention policies"
    print_status "3. Set up monitoring and alerting"
    
    # Cleanup temp files
    rm -f /tmp/*_schema.json /tmp/*_view.sql /tmp/aggregation_query.sql /tmp/lifecycle.json
}

# Run main function with all arguments
main "$@"