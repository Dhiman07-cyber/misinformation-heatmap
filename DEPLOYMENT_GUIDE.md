# 🚀 Deployment Guide - Enhanced Fake News Detection System

## Quick Start Options

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd enhanced-fake-news-detection

# Development environment
docker-compose up --build

# Production environment
docker-compose -f docker-compose.prod.yml up -d
```

### Option 2: Simple Docker

```bash
# Build and run with simple Dockerfile
docker build -f Dockerfile.simple -t fake-news-detector .
docker run -p 8080:8080 fake-news-detector
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
cd backend
python main_application.py
```

## 🌐 Access Points

Once deployed, access the system at:

- **Main Dashboard**: http://localhost:8080
- **Interactive Heatmap**: http://localhost:8080/map/enhanced-india-heatmap.html
- **API Documentation**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Optional API Keys
GOOGLE_MAPS_API_KEY=your_google_maps_key
OPENAI_API_KEY=your_openai_key

# Database (optional - defaults to SQLite)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Performance
CACHE_TYPE=memory
RATE_LIMIT_ENABLED=true

# Logging
LOG_LEVEL=INFO
```

### Docker Environment

For Docker deployments, you can also set environment variables in docker-compose.yml:

```yaml
environment:
  - LOG_LEVEL=INFO
  - API_PORT=8080
  - DATABASE_URL=sqlite:///./data/enhanced_fake_news.db
```

## 📊 System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB
- **Network**: Internet connection for RSS feeds

### Recommended for Production
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Network**: High-speed internet

## 🐳 Docker Details

### Available Docker Targets

1. **Development** (`Dockerfile` target: `development`)
   - Includes development tools
   - Auto-reload enabled
   - Debug logging
   - Port: 8000

2. **Production** (`Dockerfile` target: `production`)
   - Optimized for performance
   - Gunicorn WSGI server
   - Production logging
   - Port: 8080

3. **Simple** (`Dockerfile.simple`)
   - Lightweight build
   - Basic dependencies only
   - Quick startup
   - Port: 8080

### Docker Commands

```bash
# Build development image
docker build --target development -t fake-news-dev .

# Build production image
docker build --target production -t fake-news-prod .

# Run with custom port
docker run -p 3000:8080 fake-news-prod

# Run with environment variables
docker run -e LOG_LEVEL=DEBUG -p 8080:8080 fake-news-prod

# Run with volume mounting (development)
docker run -v $(pwd)/backend:/app/backend -p 8080:8080 fake-news-dev
```

## 🔍 Health Monitoring

### Health Check Endpoints

- `GET /health` - Basic health status
- `GET /api/v1/stats` - System statistics
- `GET /api/v1/processing/status` - Processing status

### Docker Health Checks

The Docker containers include built-in health checks:

```bash
# Check container health
docker ps
# Look for "healthy" status

# View health check logs
docker inspect --format='{{json .State.Health}}' <container-id>
```

## 📈 Performance Optimization

### Production Optimizations

1. **Enable Caching**
   ```bash
   # Add Redis for production
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Database Optimization**
   ```bash
   # Use PostgreSQL for production
   DATABASE_URL=postgresql://user:pass@localhost/fake_news_db
   ```

3. **Load Balancing**
   ```bash
   # Scale with Docker Compose
   docker-compose up --scale app=3
   ```

### Monitoring Setup

```bash
# Start with monitoring stack
docker-compose --profile monitoring up -d

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Change port in docker-compose.yml or use different port
   docker run -p 8081:8080 fake-news-detector
   ```

2. **Memory Issues**
   ```bash
   # Increase Docker memory limit or use simple build
   docker build -f Dockerfile.simple -t fake-news-simple .
   ```

3. **Permission Issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

4. **Database Connection Issues**
   ```bash
   # Check database directory exists
   mkdir -p data
   # Or use in-memory database
   DATABASE_URL=sqlite:///:memory:
   ```

### Debug Mode

```bash
# Run in debug mode
docker run -e LOG_LEVEL=DEBUG -p 8080:8080 fake-news-detector

# View logs
docker logs <container-name>

# Interactive shell
docker exec -it <container-name> /bin/bash
```

## 🌍 Cloud Deployment

### Platform-Agnostic Deployment

The system is designed to work on any cloud platform:

1. **AWS**: ECS, EKS, or EC2
2. **Google Cloud**: Cloud Run, GKE, or Compute Engine
3. **Azure**: Container Instances, AKS, or VMs
4. **DigitalOcean**: App Platform or Droplets
5. **Heroku**: Container deployment

### Example Cloud Run Deployment

```bash
# Build and tag for Google Cloud Run
docker build -t gcr.io/PROJECT_ID/fake-news-detector .
docker push gcr.io/PROJECT_ID/fake-news-detector

# Deploy to Cloud Run
gcloud run deploy fake-news-detector \
  --image gcr.io/PROJECT_ID/fake-news-detector \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 📋 Pre-deployment Checklist

- [ ] Environment variables configured
- [ ] Database directory exists (`data/`)
- [ ] Docker daemon running
- [ ] Ports 8080 (and 3000 for frontend) available
- [ ] Internet connection for RSS feeds
- [ ] Sufficient disk space (10GB+)
- [ ] Memory allocation (4GB+ recommended)

## 🔐 Security Considerations

### Production Security

1. **API Keys**: Store in environment variables, not code
2. **Database**: Use strong passwords and encrypted connections
3. **Network**: Use HTTPS in production (configure reverse proxy)
4. **Updates**: Regularly update dependencies
5. **Monitoring**: Enable logging and monitoring

### Docker Security

```bash
# Run as non-root user (already configured in Dockerfile)
# Scan for vulnerabilities
docker scout quickview fake-news-detector

# Use specific tags, not 'latest'
docker build -t fake-news-detector:v1.0.0 .
```

## 📞 Support

### Getting Help

1. **Documentation**: Check `docs/` folder for detailed guides
2. **Logs**: Always check application and container logs first
3. **Health Checks**: Use `/health` endpoint to verify system status
4. **Issues**: Report issues with logs and system information

### Useful Commands

```bash
# System information
docker system info
docker system df

# Container inspection
docker inspect <container-name>
docker stats <container-name>

# Cleanup
docker system prune -a
docker volume prune
```

---

**🎉 Your Enhanced Fake News Detection System is ready for deployment!**

For detailed technical documentation, see the `docs/` folder.