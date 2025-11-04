# GCP Production Setup Guide

Complete guide for deploying the Misinformation Heatmap to Google Cloud Platform in a production-ready configuration.

## 🎯 Overview

This guide walks you through setting up a production-grade deployment on GCP with:
- **Scalable infrastructure** with Cloud Run and auto-scaling
- **Comprehensive monitoring** and alerting
- **Secure configuration** with IAM and Secret Manager
- **Automated CI/CD pipeline** with Cloud Build
- **Data processing** with BigQuery and Pub/Sub
- **High availability** and disaster recovery

## 📋 Prerequisites

### Required Tools
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (latest version)
- [Docker](https://docs.docker.com/get-docker/) (for local testing)
- Git (for repository management)
- A Google Cloud account with billing enabled

### Required Information
- **GCP Project ID** (must be globally unique)
- **Billing Account ID** (from GCP Console > Billing)
- **Administrator Email** (for notifications)
- **Domain Name** (optional, for custom domain)
- **GitHub Repository** (for CI/CD setup)

### Getting Your Billing Account ID
1. Go to [GCP Console > Billing](https://console.cloud.google.com/billing)
2. Select your billing account
3. Copy the Billing Account ID from the URL or account details

## 🚀 Quick Start (Automated Setup)

For a complete automated setup, run the master setup script:

```bash
# Clone the repository
git clone <your-repo-url>
cd misinformation-heatmap

# Make scripts executable
chmod +x scripts/*.sh

# Run complete setup (replace with your values)
./scripts/gcp-setup.sh \
  --project-id "your-project-id" \
  --project-name "Misinformation Heatmap Production" \
  --billing-account "012345-678901-ABCDEF" \
  --admin-email "admin@yourcompany.com" \
  --domain "heatmap.yourcompany.com" \
  --verbose

# Follow up with additional services
./scripts/setup_bigquery.sh --project "your-project-id"
./scripts/setup_pubsub.sh --project "your-project-id"
./scripts/setup_monitoring.sh --project "your-project-id" --email "admin@yourcompany.com"
./scripts/deploy_cloudrun.sh --project "your-project-id"
./scripts/setup_cicd.sh --project "your-project-id" --repo "misinformation-heatmap" --owner "your-github-org"
```

## 📖 Step-by-Step Setup

### Step 1: Initial GCP Project Setup

```bash
# Authenticate with Google Cloud
gcloud auth login

# Run the main setup script
./scripts/gcp-setup.sh \
  --project-id "misinformation-heatmap-prod" \
  --project-name "Misinformation Heatmap Production" \
  --billing-account "012345-678901-ABCDEF" \
  --admin-email "admin@company.com" \
  --region "us-central1" \
  --verbose
```

This script will:
- ✅ Create a new GCP project
- ✅ Link billing account
- ✅ Enable required APIs (20+ services)
- ✅ Create IAM service accounts with minimal permissions
- ✅ Set up Cloud Storage buckets
- ✅ Configure Secret Manager
- ✅ Generate production environment configuration

### Step 2: BigQuery Data Warehouse Setup

```bash
# Set up BigQuery datasets, tables, and views
./scripts/setup_bigquery.sh \
  --project "misinformation-heatmap-prod" \
  --dataset "misinformation_heatmap" \
  --location "US" \
  --verbose
```

Creates:
- **Events table** - Main data storage with partitioning
- **Aggregations table** - Pre-computed heatmap data
- **Data sources table** - Source tracking and health
- **Views** - Optimized queries for frontend
- **Scheduled queries** - Automated data processing

### Step 3: Pub/Sub Event Processing

```bash
# Set up Pub/Sub topics and subscriptions
./scripts/setup_pubsub.sh \
  --project "misinformation-heatmap-prod" \
  --verbose
```

Creates:
- **Event processing pipeline** - Raw → Processed → Validated → Published
- **Dead letter queues** - Failed message handling
- **Monitoring topics** - System health and alerts
- **Schemas** - Message validation and structure
- **Push subscriptions** - Integration with Cloud Run

### Step 4: Application Deployment

```bash
# Deploy the application to Cloud Run
./scripts/deploy_cloudrun.sh \
  --project "misinformation-heatmap-prod" \
  --domain "heatmap.yourcompany.com" \
  --max-instances 20 \
  --verbose
```

Deploys:
- **Containerized application** - Production-optimized Docker image
- **Auto-scaling service** - 1-20 instances based on load
- **Health checks** - Automated service monitoring
- **Custom domain** - SSL certificate and DNS configuration
- **Secret integration** - Secure credential management

### Step 5: Monitoring and Alerting

```bash
# Set up comprehensive monitoring
./scripts/setup_monitoring.sh \
  --project "misinformation-heatmap-prod" \
  --email "admin@company.com" \
  --slack-webhook "https://hooks.slack.com/..." \
  --verbose
```

Creates:
- **Alert policies** - Service down, high error rate, latency
- **Dashboards** - Application metrics and data processing
- **Uptime checks** - External monitoring from multiple regions
- **Custom metrics** - Application-specific monitoring
- **Notification channels** - Email and Slack integration

### Step 6: CI/CD Pipeline

```bash
# Set up automated deployment pipeline
./scripts/setup_cicd.sh \
  --project "misinformation-heatmap-prod" \
  --repo "misinformation-heatmap" \
  --owner "your-github-org" \
  --branch "main" \
  --verbose
```

Sets up:
- **Build triggers** - Automatic deployment on code changes
- **Testing pipeline** - Automated tests on pull requests
- **Build monitoring** - Success rates and duration tracking
- **Deployment notifications** - Team alerts on deployments

## 🔧 Configuration

### Environment Variables

The setup creates a `.env.production` file with all necessary configuration:

```bash
# Application Configuration
MODE=cloud
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8080

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
BIGQUERY_DATASET=misinformation_heatmap
BIGQUERY_LOCATION=US

# Security Configuration
API_KEY_ENABLED=true
CORS_ORIGINS=["https://your-domain.com"]
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Performance Configuration
CACHE_TYPE=redis
CACHE_TTL=300
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### Secret Management

Sensitive values are stored in Google Secret Manager:

```bash
# Add API keys
echo "your-api-key-1,your-api-key-2" | gcloud secrets versions add api-keys --data-file=-

# Add HuggingFace token
echo "your-huggingface-token" | gcloud secrets versions add huggingface-token --data-file=-

# Add Watson API key
echo "your-watson-api-key" | gcloud secrets versions add watson-api-key --data-file=-
```

## 📊 Monitoring and Observability

### Key Metrics to Monitor

**Application Health:**
- Request rate and response times
- Error rates and status codes
- Instance count and CPU/memory usage
- Cache hit rates and performance

**Data Processing:**
- Events processed per minute
- NLP processing latency
- Satellite validation success rate
- Data quality scores

**Infrastructure:**
- BigQuery job success rates
- Pub/Sub message backlog
- Storage usage and costs
- Network latency and throughput

### Dashboards

Access your monitoring dashboards:
- **Main Dashboard**: Application performance and health
- **Data Processing**: Event pipeline and data quality
- **CI/CD Pipeline**: Build success rates and deployment history

### Alerts

Configured alerts for:
- 🚨 **Critical**: Service down, high error rate (>5%)
- ⚠️ **Warning**: High latency (>5s), resource usage (>80%)
- 📊 **Info**: Deployment notifications, data quality issues

## 🔒 Security

### IAM and Permissions

The setup follows the principle of least privilege:
- **Application service account**: Minimal permissions for data access
- **Build service account**: Deployment and CI/CD permissions only
- **Monitoring service account**: Read-only access for observability

### Network Security

- **HTTPS only**: All traffic encrypted with managed SSL certificates
- **CORS configuration**: Restricted to allowed origins
- **Rate limiting**: Protection against abuse and DDoS
- **Input validation**: Comprehensive request sanitization

### Data Protection

- **Encryption at rest**: All data encrypted in BigQuery and Cloud Storage
- **Encryption in transit**: TLS 1.2+ for all communications
- **Access logging**: Comprehensive audit trail
- **Data retention**: Automated cleanup of old logs and temporary data

## 🚀 Scaling and Performance

### Auto-scaling Configuration

```yaml
# Cloud Run scaling settings
min_instances: 1          # Always-on for low latency
max_instances: 20         # Scale up to handle traffic spikes
cpu_limit: "2"           # 2 vCPU per instance
memory_limit: "4Gi"      # 4GB RAM per instance
concurrency: 100         # Max concurrent requests per instance
```

### Performance Optimizations

- **Container optimization**: Multi-stage Docker builds
- **Database indexing**: Optimized BigQuery tables with partitioning
- **Caching strategy**: Redis for API responses and computed data
- **CDN integration**: Static asset delivery via Cloud CDN

### Cost Optimization

- **Resource right-sizing**: Appropriate CPU/memory allocation
- **Auto-scaling**: Pay only for resources you use
- **Data lifecycle**: Automated cleanup of old data
- **Reserved capacity**: Committed use discounts for predictable workloads

## 🔄 Backup and Disaster Recovery

### Automated Backups

- **BigQuery**: Automatic table snapshots and point-in-time recovery
- **Cloud Storage**: Cross-region replication for critical data
- **Configuration**: Version-controlled infrastructure as code

### Recovery Procedures

1. **Service Recovery**: Automatic health checks and instance replacement
2. **Data Recovery**: Point-in-time restore from BigQuery snapshots
3. **Full Disaster Recovery**: Multi-region deployment capability

## 🧪 Testing the Deployment

### Health Checks

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe misinformation-heatmap --region=us-central1 --format="value(status.url)")

# Test health endpoints
curl "$SERVICE_URL/health"
curl "$SERVICE_URL/api/v1/health"

# Test API functionality
curl "$SERVICE_URL/api/v1/events?limit=10"
curl "$SERVICE_URL/api/v1/heatmap/states"
```

### Load Testing

```bash
# Install Apache Bench for load testing
sudo apt-get install apache2-utils

# Run load test (100 concurrent requests, 1000 total)
ab -n 1000 -c 100 "$SERVICE_URL/api/v1/health"

# Monitor performance in Cloud Monitoring console
```

### Data Pipeline Testing

```bash
# Test Pub/Sub pipeline
gcloud pubsub topics publish events-raw --message='{"id":"test-001","title":"Test Event","content":"Testing data pipeline"}'

# Check BigQuery for processed data
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM misinformation_heatmap.events WHERE id LIKE 'test-%'"
```

## 🛠️ Troubleshooting

### Common Issues

**Deployment Failures:**
```bash
# Check Cloud Build logs
gcloud builds list --limit=5
gcloud builds log BUILD_ID

# Check Cloud Run service logs
gcloud logs read "resource.type=cloud_run_revision" --limit=50
```

**API Errors:**
```bash
# Check application logs
gcloud logs read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20

# Check service configuration
gcloud run services describe misinformation-heatmap --region=us-central1
```

**Data Processing Issues:**
```bash
# Check Pub/Sub subscription backlog
gcloud pubsub subscriptions list
gcloud pubsub subscriptions describe SUBSCRIPTION_NAME

# Check BigQuery job status
bq ls -j --max_results=10
```

### Performance Issues

**High Latency:**
- Check Cloud Run instance count and scaling
- Review database query performance
- Verify cache hit rates

**High Error Rates:**
- Check application logs for exceptions
- Verify external API connectivity
- Review rate limiting configuration

## 📞 Support and Maintenance

### Regular Maintenance Tasks

**Weekly:**
- Review monitoring dashboards and alerts
- Check cost reports and optimize resources
- Update dependencies and security patches

**Monthly:**
- Review and rotate API keys and secrets
- Analyze performance trends and optimize
- Update documentation and runbooks

**Quarterly:**
- Disaster recovery testing
- Security audit and penetration testing
- Capacity planning and scaling review

### Getting Help

- **GCP Support**: Use your support plan for infrastructure issues
- **Application Issues**: Check logs and monitoring dashboards
- **Performance Problems**: Use Cloud Profiler and APM tools

## 🎉 Success Criteria

Your production deployment is successful when:

✅ **Service Health**: 99.9% uptime with <2s response times  
✅ **Data Processing**: Real-time event processing with <5min latency  
✅ **Monitoring**: Comprehensive dashboards and working alerts  
✅ **Security**: All security scans pass, proper access controls  
✅ **Scalability**: Handles 1000+ concurrent users smoothly  
✅ **CI/CD**: Automated deployments working reliably  

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [Cloud Monitoring Guide](https://cloud.google.com/monitoring/docs)
- [Security Best Practices](https://cloud.google.com/security/best-practices)

---

**Need help?** Check the troubleshooting section or review the monitoring dashboards for insights into any issues.