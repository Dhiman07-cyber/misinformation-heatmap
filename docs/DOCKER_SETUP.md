# Docker Setup Guide

Complete guide for containerizing and deploying the Real-Time Misinformation Heatmap using Docker.

## Overview

This project includes comprehensive Docker support with:
- **Multi-stage Dockerfile** for optimized production builds
- **Docker Compose** configurations for development and production
- **Management scripts** for easy deployment and maintenance
- **Monitoring stack** with Prometheus and Grafana
- **SSL/TLS support** for production deployments

## Quick Start

### Development Environment

1. **Copy environment template**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start development environment**
   ```bash
   # Unix/Linux/macOS
   ./scripts/docker-dev.sh up
   
   # Windows PowerShell
   docker-compose up -d
   ```

3. **Access services**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Pub/Sub Emulator: http://localhost:8085

### Production Environment

1. **Create production configuration**
   ```bash
   cp .env.example .env.production
   # Edit .env.production with production values
   ```

2. **Deploy to production**
   ```bash
   # Unix/Linux/macOS
   ./scripts/docker-prod.sh deploy
   
   # Windows PowerShell
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Architecture

### Multi-Stage Dockerfile

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Base Stage    │───▶│ Dependencies    │───▶│  Application    │
│                 │    │                 │    │                 │
│ • Python 3.9    │    │ • Pip packages  │    │ • App code      │
│ • System deps   │    │ • ML models     │    │ • Configuration │
│ • Security      │    │ • Cloud SDKs    │    │ • Static files  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                         │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Development   │    │   Production    │
                       │                 │    │                 │
                       │ • Debug tools   │    │ • Gunicorn      │
                       │ • Hot reload    │    │ • Optimized     │
                       │ • Test deps     │    │ • Security      │
                       └─────────────────┘    └─────────────────┘
```

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │    │   Application   │    │     Redis       │
│                 │    │                 │    │                 │
│ • SSL/TLS       │───▶│ • FastAPI       │───▶│ • Caching       │
│ • Load Balance  │    │ • Data Sources  │    │ • Session Store │
│ • Static Files  │    │ • NLP Pipeline  │    │ • Rate Limiting │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │    │  Pub/Sub        │    │   BigQuery      │
│                 │    │                 │    │                 │
│ • Prometheus    │    │ • Event Queue   │    │ • Data Storage  │
│ • Grafana       │    │ • Processing    │    │ • Analytics     │
│ • Alerting      │    │ • Scaling       │    │ • Reporting     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Configuration

### Environment Variables

#### Core Application
```bash
# Application mode
MODE=local|cloud
ENVIRONMENT=development|staging|production
LOG_LEVEL=DEBUG|INFO|WARNING|ERROR

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
CORS_ORIGINS=["http://localhost:3000"]

# Security
API_KEY_ENABLED=true
API_KEYS=["key1","key2"]
```

#### Google Cloud
```bash
# Project Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# BigQuery
BIGQUERY_DATASET=misinformation_heatmap
BIGQUERY_LOCATION=US

# Pub/Sub
PUBSUB_EVENTS_RAW_TOPIC=events-raw
PUBSUB_EVENTS_PROCESSED_TOPIC=events-processed
```

#### Performance & Caching
```bash
# Caching
CACHE_TYPE=redis
REDIS_URL=redis://redis:6379/0

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### Docker Compose Profiles

#### Development Profile
```yaml
# Start development services
COMPOSE_PROFILES=local,development
docker-compose up -d
```

#### Production Profile
```yaml
# Start production services with monitoring
COMPOSE_PROFILES=production,monitoring
docker-compose -f docker-compose.prod.yml up -d
```

#### Testing Profile
```yaml
# Run tests
COMPOSE_PROFILES=testing
docker-compose up test-runner
```

## Management Scripts

### Development Script (`scripts/docker-dev.sh`)

```bash
# Build development images
./scripts/docker-dev.sh build

# Start development environment
./scripts/docker-dev.sh up

# Show logs
./scripts/docker-dev.sh logs [service]

# Open shell in container
./scripts/docker-dev.sh shell

# Run tests
./scripts/docker-dev.sh test

# Clean up resources
./scripts/docker-dev.sh clean
```

### Production Script (`scripts/docker-prod.sh`)

```bash
# Build production images
./scripts/docker-prod.sh build

# Deploy to production
./scripts/docker-prod.sh deploy

# Update deployment
./scripts/docker-prod.sh update

# Rollback deployment
./scripts/docker-prod.sh rollback

# Scale services
./scripts/docker-prod.sh scale app=3

# Create backup
./scripts/docker-prod.sh backup

# Restore from backup
./scripts/docker-prod.sh restore backups/backup_20241126_143022
```

## Production Deployment

### Prerequisites

1. **SSL Certificates**
   ```bash
   mkdir -p ssl
   # Place your SSL certificate files:
   # ssl/cert.pem
   # ssl/key.pem
   ```

2. **Google Cloud Credentials**
   ```bash
   # Place service account key file:
   # credentials.json
   ```

3. **Production Configuration**
   ```bash
   # Create .env.production with production values
   cp .env.example .env.production
   ```

### Deployment Steps

1. **Build Production Images**
   ```bash
   ./scripts/docker-prod.sh build
   ```

2. **Deploy Services**
   ```bash
   ./scripts/docker-prod.sh deploy
   ```

3. **Verify Deployment**
   ```bash
   ./scripts/docker-prod.sh health
   ```

4. **Monitor Services**
   ```bash
   ./scripts/docker-prod.sh status
   ```

### Production Services

#### Main Application
- **Container**: `misinformation-heatmap-prod`
- **Port**: 8080 (internal)
- **Health Check**: `/health` endpoint
- **Resources**: 2 CPU, 4GB RAM

#### Nginx Reverse Proxy
- **Container**: `misinformation-heatmap-nginx`
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **Features**: SSL termination, static file serving, load balancing
- **Resources**: 0.5 CPU, 512MB RAM

#### Redis Cache
- **Container**: `misinformation-heatmap-redis-prod`
- **Port**: 6379 (internal)
- **Persistence**: Enabled with snapshots
- **Resources**: 1 CPU, 1.5GB RAM

#### Monitoring Stack
- **Prometheus**: Port 9090, metrics collection
- **Grafana**: Port 3001, dashboards and visualization
- **Resources**: 1.5 CPU, 3GB RAM total

## Monitoring & Observability

### Metrics Collection

The application exposes metrics at `/metrics` endpoint:
- **Request metrics**: Rate, latency, errors
- **Business metrics**: Events processed, sources active
- **System metrics**: CPU, memory, disk usage
- **Custom metrics**: Data quality, processing pipeline health

### Dashboards

#### System Overview Dashboard
- Service health and uptime
- Request rate and error rate
- Response time percentiles
- Resource utilization

#### Business Metrics Dashboard
- Events processed per hour
- Data source health
- Misinformation detection rates
- Geographic distribution

#### Performance Dashboard
- API endpoint performance
- Database query performance
- Cache hit rates
- Processing pipeline throughput

### Alerting Rules

#### Critical Alerts
- Service down for >1 minute
- Error rate >5% for >5 minutes
- Response time >2 seconds for >5 minutes

#### Warning Alerts
- High memory usage >80% for >10 minutes
- High CPU usage >80% for >10 minutes
- Cache hit rate <50% for >15 minutes

## Backup & Recovery

### Automated Backups

```bash
# Create daily backup (add to cron)
0 2 * * * /path/to/scripts/docker-prod.sh backup
```

### Backup Contents
- **Application Data**: Event data, configurations
- **Redis Data**: Cache and session data
- **Grafana Data**: Dashboards and settings
- **Logs**: Application and access logs

### Recovery Procedures

1. **List Available Backups**
   ```bash
   ls -la backups/
   ```

2. **Restore from Backup**
   ```bash
   ./scripts/docker-prod.sh restore backups/backup_20241126_143022
   ```

3. **Verify Recovery**
   ```bash
   ./scripts/docker-prod.sh health
   ```

## Security

### Container Security
- **Non-root user**: Application runs as `appuser`
- **Minimal base image**: Python slim image
- **Security updates**: Regular base image updates
- **Secrets management**: Environment variables and mounted files

### Network Security
- **Internal networks**: Services communicate on private networks
- **SSL/TLS**: HTTPS enforced in production
- **Rate limiting**: API and nginx level protection
- **Security headers**: Comprehensive HTTP security headers

### Access Control
- **API authentication**: Key-based authentication
- **Service isolation**: Each service runs in isolated container
- **Resource limits**: CPU and memory limits enforced
- **Health checks**: Automated health monitoring

## Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker-compose logs service-name

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

#### High Memory Usage
```bash
# Check memory usage by container
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Scale down if needed
./scripts/docker-prod.sh scale app=1
```

#### SSL Certificate Issues
```bash
# Verify certificate files
ls -la ssl/
openssl x509 -in ssl/cert.pem -text -noout

# Check nginx configuration
docker-compose exec nginx nginx -t
```

#### Database Connection Issues
```bash
# Check BigQuery connectivity
docker-compose exec app python -c "from backend.database import Database; db = Database(); print('Connected')"

# Check Redis connectivity
docker-compose exec redis redis-cli ping
```

### Performance Tuning

#### Application Performance
- **Worker processes**: Adjust Gunicorn workers based on CPU cores
- **Connection pooling**: Optimize database connections
- **Caching**: Tune Redis cache settings
- **Resource limits**: Adjust container resource limits

#### Database Performance
- **Query optimization**: Monitor slow queries
- **Indexing**: Ensure proper BigQuery table partitioning
- **Connection limits**: Optimize connection pool sizes

#### Network Performance
- **Nginx tuning**: Optimize worker connections and buffers
- **Compression**: Enable gzip for static assets
- **CDN**: Consider CloudFlare or similar for static assets

## Best Practices

### Development
- Use volume mounts for hot reloading
- Run tests in isolated containers
- Use development-specific environment variables
- Enable debug logging and profiling

### Production
- Use multi-stage builds for smaller images
- Implement health checks for all services
- Use resource limits and requests
- Enable monitoring and alerting
- Implement proper backup strategies
- Use secrets management for sensitive data

### Security
- Regularly update base images
- Scan images for vulnerabilities
- Use non-root users in containers
- Implement network segmentation
- Enable audit logging
- Use strong authentication and authorization

This Docker setup provides a robust, scalable, and production-ready deployment solution for the Real-Time Misinformation Heatmap system.