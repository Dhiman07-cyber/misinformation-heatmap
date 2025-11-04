#!/bin/bash

# CI/CD Pipeline Setup Script for Misinformation Heatmap
# Sets up Cloud Build triggers and automated deployment pipeline

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
REPO_NAME=""
REPO_OWNER=""
BRANCH_NAME="main"
GITHUB_TOKEN=""
VERBOSE=false
DRY_RUN=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required Options:"
    echo "  -p, --project PROJECT_ID    GCP Project ID"
    echo "  -r, --repo REPO_NAME        GitHub repository name"
    echo "  -o, --owner REPO_OWNER      GitHub repository owner/organization"
    echo ""
    echo "Optional Options:"
    echo "  -b, --branch BRANCH         Branch to trigger builds (default: main)"
    echo "  -t, --token TOKEN           GitHub personal access token"
    echo "  -v, --verbose               Enable verbose output"
    echo "  --dry-run                   Show what would be done without executing"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -p my-project-id -r misinformation-heatmap -o myorg"
    echo "  $0 -p my-project-id -r misinformation-heatmap -o myorg -b develop"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--project)
                PROJECT_ID="$2"
                shift 2
                ;;
            -r|--repo)
                REPO_NAME="$2"
                shift 2
                ;;
            -o|--owner)
                REPO_OWNER="$2"
                shift 2
                ;;
            -b|--branch)
                BRANCH_NAME="$2"
                shift 2
                ;;
            -t|--token)
                GITHUB_TOKEN="$2"
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
    
    if [[ -z "$REPO_NAME" ]]; then
        print_error "Repository name is required (--repo)"
        exit 1
    fi
    
    if [[ -z "$REPO_OWNER" ]]; then
        print_error "Repository owner is required (--owner)"
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
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "You are not authenticated with Google Cloud."
        print_status "Please run: gcloud auth login"
        exit 1
    fi
    
    # Set project
    execute_command "gcloud config set project $PROJECT_ID" "Setting project..."
    
    # Check if Cloud Build API is enabled
    if ! gcloud services list --enabled --filter="name:cloudbuild.googleapis.com" --format="value(name)" | grep -q cloudbuild; then
        print_warning "Cloud Build API is not enabled. Enabling now..."
        execute_command "gcloud services enable cloudbuild.googleapis.com" "Enabling Cloud Build API..."
    fi
    
    # Check if Cloud Source Repositories API is enabled
    if ! gcloud services list --enabled --filter="name:sourcerepo.googleapis.com" --format="value(name)" | grep -q sourcerepo; then
        print_warning "Cloud Source Repositories API is not enabled. Enabling now..."
        execute_command "gcloud services enable sourcerepo.googleapis.com" "Enabling Cloud Source Repositories API..."
    fi
    
    print_success "Prerequisites check completed"
}

setup_cloud_build_permissions() {
    print_header "Setting up Cloud Build Permissions"
    
    # Get Cloud Build service account
    local build_sa_email=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")@cloudbuild.gserviceaccount.com
    
    # Grant necessary roles to Cloud Build service account
    local roles=(
        "roles/run.admin"                    # Deploy to Cloud Run
        "roles/iam.serviceAccountUser"       # Use service accounts
        "roles/storage.admin"                # Access Cloud Storage
        "roles/pubsub.admin"                 # Manage Pub/Sub subscriptions
        "roles/secretmanager.secretAccessor" # Access secrets
        "roles/monitoring.editor"            # Create monitoring resources
    )
    
    for role in "${roles[@]}"; do
        execute_command "gcloud projects add-iam-policy-binding $PROJECT_ID --member='serviceAccount:$build_sa_email' --role='$role'" \
            "Granting $role to Cloud Build service account"
    done
    
    print_success "Cloud Build permissions configured"
}

create_build_buckets() {
    print_header "Creating Build Storage Buckets"
    
    # Create buckets for build artifacts and logs
    local buckets=(
        "$PROJECT_ID-build-artifacts:Build artifacts storage"
        "$PROJECT_ID-build-logs:Build logs storage"
    )
    
    for bucket_info in "${buckets[@]}"; do
        local bucket_name=$(echo "$bucket_info" | cut -d: -f1)
        local bucket_desc=$(echo "$bucket_info" | cut -d: -f2)
        
        # Check if bucket exists
        if gsutil ls -b "gs://$bucket_name" &>/dev/null; then
            print_warning "Bucket $bucket_name already exists"
            continue
        fi
        
        execute_command "gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$bucket_name" \
            "Creating bucket: $bucket_name ($bucket_desc)"
        
        # Set lifecycle policy for logs bucket
        if [[ "$bucket_name" == *"-logs" ]]; then
            cat > /tmp/build_logs_lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 30}
      }
    ]
  }
}
EOF
            execute_command "gsutil lifecycle set /tmp/build_logs_lifecycle.json gs://$bucket_name" \
                "Setting lifecycle policy for build logs bucket"
        fi
    done
    
    print_success "Build buckets created"
}

connect_github_repo() {
    print_header "Connecting GitHub Repository"
    
    if [[ -n "$GITHUB_TOKEN" ]]; then
        # Connect GitHub repository using token
        execute_command "gcloud source repos create $REPO_NAME --project=$PROJECT_ID" \
            "Creating Cloud Source Repository..."
        
        # Set up mirroring from GitHub
        print_status "Setting up GitHub repository connection..."
        print_warning "Manual step required: Connect GitHub repository in Cloud Build console"
        print_status "1. Go to https://console.cloud.google.com/cloud-build/triggers"
        print_status "2. Click 'Connect Repository'"
        print_status "3. Select GitHub and authenticate"
        print_status "4. Select repository: $REPO_OWNER/$REPO_NAME"
    else
        print_warning "No GitHub token provided. Manual repository connection required."
        print_status "Please connect your GitHub repository manually:"
        print_status "1. Go to https://console.cloud.google.com/cloud-build/triggers"
        print_status "2. Click 'Connect Repository'"
        print_status "3. Select GitHub and authenticate"
        print_status "4. Select repository: $REPO_OWNER/$REPO_NAME"
    fi
    
    print_success "GitHub repository connection initiated"
}

create_build_triggers() {
    print_header "Creating Cloud Build Triggers"
    
    # Production deployment trigger (main branch)
    cat > /tmp/production_trigger.json << EOF
{
  "name": "misinformation-heatmap-production",
  "description": "Deploy to production on push to main branch",
  "github": {
    "owner": "$REPO_OWNER",
    "name": "$REPO_NAME",
    "push": {
      "branch": "^$BRANCH_NAME$"
    }
  },
  "filename": "cloudbuild.yaml",
  "substitutions": {
    "_REGION": "us-central1",
    "_SERVICE_NAME": "misinformation-heatmap",
    "_MIN_INSTANCES": "1",
    "_MAX_INSTANCES": "10"
  },
  "includedFiles": [
    "backend/**",
    "frontend/**",
    "config/**",
    "scripts/**",
    "Dockerfile",
    "cloudbuild.yaml",
    "requirements.txt",
    "package.json"
  ],
  "ignoredFiles": [
    "docs/**",
    "*.md",
    ".gitignore",
    "tests/**"
  ]
}
EOF

    execute_command "gcloud builds triggers create github --trigger-config=/tmp/production_trigger.json --project=$PROJECT_ID" \
        "Creating production deployment trigger..."
    
    # Pull request trigger (for testing)
    cat > /tmp/pr_trigger.json << EOF
{
  "name": "misinformation-heatmap-pr-test",
  "description": "Run tests on pull requests",
  "github": {
    "owner": "$REPO_OWNER",
    "name": "$REPO_NAME",
    "pullRequest": {
      "branch": ".*"
    }
  },
  "build": {
    "steps": [
      {
        "name": "gcr.io/cloud-builders/docker",
        "args": [
          "build",
          "--target", "test",
          "-t", "misinformation-heatmap-test",
          "."
        ]
      },
      {
        "name": "gcr.io/cloud-builders/docker",
        "args": [
          "run",
          "--rm",
          "misinformation-heatmap-test"
        ]
      }
    ],
    "timeout": "600s"
  },
  "includedFiles": [
    "backend/**",
    "frontend/**",
    "tests/**",
    "Dockerfile",
    "requirements.txt",
    "package.json"
  ]
}
EOF

    execute_command "gcloud builds triggers create github --trigger-config=/tmp/pr_trigger.json --project=$PROJECT_ID" \
        "Creating pull request test trigger..."
    
    # Manual deployment trigger
    cat > /tmp/manual_trigger.json << EOF
{
  "name": "misinformation-heatmap-manual",
  "description": "Manual deployment trigger",
  "github": {
    "owner": "$REPO_OWNER",
    "name": "$REPO_NAME",
    "push": {
      "tag": "deploy-.*"
    }
  },
  "filename": "cloudbuild.yaml",
  "substitutions": {
    "_REGION": "us-central1",
    "_SERVICE_NAME": "misinformation-heatmap",
    "_MIN_INSTANCES": "2",
    "_MAX_INSTANCES": "20"
  }
}
EOF

    execute_command "gcloud builds triggers create github --trigger-config=/tmp/manual_trigger.json --project=$PROJECT_ID" \
        "Creating manual deployment trigger..."
    
    print_success "Build triggers created"
}

setup_deployment_notifications() {
    print_header "Setting up Deployment Notifications"
    
    # Create Pub/Sub topic for deployment notifications
    if ! gcloud pubsub topics describe deployment-notifications --project="$PROJECT_ID" &>/dev/null; then
        execute_command "gcloud pubsub topics create deployment-notifications --project='$PROJECT_ID'" \
            "Creating deployment notifications topic..."
    fi
    
    # Create subscription for deployment notifications
    if ! gcloud pubsub subscriptions describe deployment-notifications-handler --project="$PROJECT_ID" &>/dev/null; then
        execute_command "gcloud pubsub subscriptions create deployment-notifications-handler \
            --topic=deployment-notifications \
            --project='$PROJECT_ID' \
            --ack-deadline=60 \
            --message-retention-duration=7d" \
            "Creating deployment notifications subscription..."
    fi
    
    print_success "Deployment notifications configured"
}

create_build_dashboard() {
    print_header "Creating Build Monitoring Dashboard"
    
    # Create Cloud Build monitoring dashboard
    cat > /tmp/build_dashboard.json << EOF
{
  "displayName": "Misinformation Heatmap - CI/CD Pipeline",
  "mosaicLayout": {
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Build Success Rate",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"build\" AND metric.type=\"cloudbuild.googleapis.com/build/count\"",
                    "aggregation": {
                      "alignmentPeriod": "3600s",
                      "perSeriesAligner": "ALIGN_SUM",
                      "crossSeriesReducer": "REDUCE_SUM",
                      "groupByFields": ["metric.label.status"]
                    }
                  }
                },
                "plotType": "STACKED_BAR",
                "targetAxis": "Y1"
              }
            ],
            "timeshiftDuration": "0s",
            "yAxis": {
              "label": "Builds",
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
          "title": "Build Duration",
          "xyChart": {
            "dataSets": [
              {
                "timeSeriesQuery": {
                  "timeSeriesFilter": {
                    "filter": "resource.type=\"build\" AND metric.type=\"cloudbuild.googleapis.com/build/duration\"",
                    "aggregation": {
                      "alignmentPeriod": "3600s",
                      "perSeriesAligner": "ALIGN_MEAN",
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
              "label": "Duration (seconds)",
              "scale": "LINEAR"
            }
          }
        }
      }
    ]
  }
}
EOF

    execute_command "gcloud monitoring dashboards create --config-from-file=/tmp/build_dashboard.json --project='$PROJECT_ID'" \
        "Creating build monitoring dashboard..."
    
    print_success "Build dashboard created"
}

test_build_trigger() {
    print_header "Testing Build Trigger"
    
    print_status "To test the CI/CD pipeline:"
    print_status "1. Push a commit to the $BRANCH_NAME branch"
    print_status "2. Check build status: gcloud builds list --project=$PROJECT_ID"
    print_status "3. View build logs: gcloud builds log BUILD_ID --project=$PROJECT_ID"
    print_status "4. Monitor in console: https://console.cloud.google.com/cloud-build/builds"
    
    # Optionally trigger a manual build
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Trigger a test build now? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            execute_command "gcloud builds triggers run misinformation-heatmap-production --branch=$BRANCH_NAME --project=$PROJECT_ID" \
                "Triggering test build..."
        fi
    fi
    
    print_success "Build trigger test completed"
}

main() {
    print_header "CI/CD Pipeline Setup for Misinformation Heatmap"
    
    parse_args "$@"
    validate_args
    
    print_status "Setting up CI/CD pipeline with the following configuration:"
    print_status "  Project ID: $PROJECT_ID"
    print_status "  Repository: $REPO_OWNER/$REPO_NAME"
    print_status "  Branch: $BRANCH_NAME"
    echo ""
    
    if [[ "$DRY_RUN" != true ]]; then
        read -p "Continue with CI/CD setup? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Setup cancelled by user"
            exit 0
        fi
    fi
    
    # Execute setup steps
    check_prerequisites
    setup_cloud_build_permissions
    create_build_buckets
    connect_github_repo
    create_build_triggers
    setup_deployment_notifications
    create_build_dashboard
    test_build_trigger
    
    print_header "CI/CD Pipeline Setup Complete!"
    print_success "Automated deployment pipeline is now configured"
    print_status ""
    print_status "Created resources:"
    print_status "  - Cloud Build triggers for production, PR testing, and manual deployment"
    print_status "  - Build storage buckets with lifecycle policies"
    print_status "  - Deployment notification system"
    print_status "  - Build monitoring dashboard"
    print_status ""
    print_status "Pipeline features:"
    print_status "  - Automatic deployment on push to $BRANCH_NAME branch"
    print_status "  - Automated testing on pull requests"
    print_status "  - Manual deployment via git tags (deploy-*)"
    print_status "  - Health checks and rollback capabilities"
    print_status "  - Build monitoring and notifications"
    print_status ""
    print_status "Next steps:"
    print_status "1. Push code to trigger first automated build"
    print_status "2. Monitor builds in Cloud Build console"
    print_status "3. Set up additional notification channels if needed"
    print_status "4. Configure branch protection rules in GitHub"
    
    # Cleanup temp files
    rm -f /tmp/*_trigger.json /tmp/build_dashboard.json /tmp/build_logs_lifecycle.json
}

# Run main function with all arguments
main "$@"