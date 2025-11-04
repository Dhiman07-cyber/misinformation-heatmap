# Troubleshooting Guide

Comprehensive troubleshooting guide for the Real-Time Misinformation Heatmap system.

## Quick Diagnosis

### System Health Check

Run the automated health check to quickly identify issues:

```bash
# Check all system components
python scripts/health_check.py --comprehensive

# Check specific component
python scripts/health_check.py --component api
python scripts/health_check.py --component database
python scripts/health_check.py --component nlp
```

### Common Issues Quick Reference

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| API returns 500 errors | Database connection issue | Check database connectivity |
| Frontend shows "Loading..." | API not responding | Verify API service is running |
| No data on heatmap | No events processed | Check ingestion pipeline |
| Slow response times | Performance bottleneck | Check system resources |
| Authentication errors | Invalid credentials | Verify API keys and service accounts |

## Installation and Setup Issues

### Python Environment Problems

**Issue: ModuleNotFoundError**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**
1. Verify Python version (3.8+ required):
   ```bash
   python --version
   ```

2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Check virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   
   # Install dependencies
   pip install -r backend/requirements.txt
   ```

**Issue: Permission denied errors**
```
PermissionError: [Errno 13] Permission denied
```

**Solutions:**
1. Use virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```

2. Install with user flag:
   ```bash
   pip install --user -r backend/requirements.txt
   ```

### Database Setup Issues

**Issue: SQLite database locked**
```
sqlite3.OperationalError: database is locked
```

**Solutions:**
1. Check for running processes:
   ```bash
   # Kill any running API processes
   pkill -f "python.*api.py"
   
   # Remove lock file if exists
   rm -f data/heatmap.db-wal data/heatmap.db-shm
   ```

2. Reinitialize database:
   ```bash
   rm -f data/heatmap.db
   python backend/init_db.py --mode local
   ```

**Issue: BigQuery authentication errors**
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**Solutions:**
1. Set service account key:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
   ```

2. Authenticate with gcloud:
   ```bash
   gcloud auth application-default login
   ```

3. Verify project ID:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

### Network and Connectivity Issues

**Issue: Port already in use**
```
OSError: [Errno 48] Address already in use
```

**Solutions:**
1. Find and kill process using the port:
   ```bash
   # Find process using port 8000
   lsof -i :8000
   kill -9 <PID>
   ```

2. Use different port:
   ```bash
   export API_PORT=8001
   python backend/api.py
   ```

**Issue: CORS errors in browser**
```
Access to fetch at 'http://localhost:8000/heatmap' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**Solutions:**
1. Check CORS configuration in `backend/api.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. Verify frontend URL matches CORS origins

## Runtime Issues

### API Service Problems

**Issue: API service won't start**

**Diagnostic Steps:**
1. Check logs:
   ```bash
   python backend/api.py 2>&1 | tee api.log
   ```

2. Verify configuration:
   ```bash
   python -c "from backend.config import Config; print(Config().dict())"
   ```

3. Test database connection:
   ```bash
   python -c "from backend.database import Database; db = Database(); print('DB OK')"
   ```

**Issue: API returns empty responses**

**Diagnostic Steps:**
1. Check database content:
   ```bash
   sqlite3 data/heatmap.db "SELECT COUNT(*) FROM events;"
   ```

2. Verify data ingestion:
   ```bash
   curl -X POST http://localhost:8000/ingest/test \
     -H "Content-Type: application/json" \
     -d '{"text":"Test event","source":"test","location":"Maharashtra"}'
   ```

3. Check API logs for errors

### Data Processing Issues

**Issue: NLP processing fails**
```
RuntimeError: Model not found or failed to load
```

**Solutions:**
1. Check internet connection for model download
2. Clear model cache:
   ```bash
   rm -rf ~/.cache/huggingface/
   ```

3. Manually download model:
   ```python
   from transformers import AutoTokenizer, AutoModel
   tokenizer = AutoTokenizer.from_pretrained("ai4bharat/indic-bert")
   model = AutoModel.from_pretrained("ai4bharat/indic-bert")
   ```

**Issue: Satellite validation always fails**

**Diagnostic Steps:**
1. Check satellite client configuration:
   ```python
   from backend.satellite_client import SatelliteClient
   client = SatelliteClient()
   print(client.config)
   ```

2. Verify coordinates are within India:
   ```python
   # Valid India coordinates
   lat, lon = 19.0760, 72.8777  # Mumbai
   ```

3. Check stub mode is working:
   ```bash
   export MODE=local
   python -c "from backend.satellite_client import SatelliteClient; print(SatelliteClient().validate_location(19.0760, 72.8777))"
   ```

### Frontend Issues

**Issue: Frontend shows blank page**

**Diagnostic Steps:**
1. Check browser console for JavaScript errors
2. Verify API connectivity:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check frontend server:
   ```bash
   cd frontend
   python -m http.server 3000
   ```

**Issue: Map doesn't load**

**Solutions:**
1. Check Leaflet.js library loading:
   ```html
   <!-- Verify these are loaded in index.html -->
   <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
   <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
   ```

2. Verify GeoJSON data:
   ```bash
   curl http://localhost:3000/data/india_states.geojson
   ```

3. Check browser network tab for failed requests

**Issue: Real-time updates not working**

**Diagnostic Steps:**
1. Check polling interval in JavaScript:
   ```javascript
   // In frontend/js/app.js
   setInterval(updateHeatmapData, 30000); // 30 seconds
   ```

2. Verify API returns updated data:
   ```bash
   # Add test event
   curl -X POST http://localhost:8000/ingest/test -H "Content-Type: application/json" -d '{"text":"New test event","source":"test","location":"Gujarat"}'
   
   # Check heatmap data
   curl http://localhost:8000/heatmap
   ```

## Performance Issues

### Slow Response Times

**Diagnostic Steps:**
1. Check system resources:
   ```bash
   # CPU and memory usage
   top
   
   # Disk I/O
   iostat -x 1
   
   # Network connections
   netstat -an | grep :8000
   ```

2. Profile API performance:
   ```bash
   python scripts/performance_benchmark.py --endpoint /heatmap
   ```

3. Check database query performance:
   ```bash
   sqlite3 data/heatmap.db ".timer on" "SELECT COUNT(*) FROM events;"
   ```

**Solutions:**
1. Enable caching:
   ```python
   # In backend/api.py
   from backend.performance_optimizer import cache_result
   
   @cache_result(ttl=300)
   def get_heatmap_data():
       # Implementation
   ```

2. Optimize database queries:
   ```sql
   -- Add indexes for common queries
   CREATE INDEX idx_events_timestamp ON events(timestamp);
   CREATE INDEX idx_events_region ON events(region_hint);
   ```

3. Increase system resources or optimize code

### Memory Issues

**Issue: High memory usage**

**Diagnostic Steps:**
1. Monitor memory usage:
   ```bash
   # Python memory profiler
   pip install memory-profiler
   python -m memory_profiler backend/api.py
   ```

2. Check for memory leaks:
   ```python
   import gc
   import psutil
   
   process = psutil.Process()
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
   print(f"Objects in memory: {len(gc.get_objects())}")
   ```

**Solutions:**
1. Enable garbage collection:
   ```python
   import gc
   gc.collect()  # Force garbage collection
   ```

2. Reduce cache size:
   ```python
   # In performance_optimizer.py
   cache = MemoryCache(max_size=500)  # Reduce from 1000
   ```

3. Process data in batches instead of loading all at once

## Cloud Deployment Issues

### Google Cloud Platform Problems

**Issue: Cloud Run deployment fails**
```
ERROR: (gcloud.run.deploy) Cloud Run error: Container failed to start
```

**Diagnostic Steps:**
1. Check Cloud Run logs:
   ```bash
   gcloud logs read --service=misinformation-heatmap --limit=50
   ```

2. Test container locally:
   ```bash
   docker build -t misinformation-heatmap .
   docker run -p 8080:8080 misinformation-heatmap
   ```

3. Verify environment variables:
   ```bash
   gcloud run services describe misinformation-heatmap --region=us-central1
   ```

**Issue: BigQuery permission errors**
```
403 Forbidden: Access Denied: Project your-project: User does not have permission to query table
```

**Solutions:**
1. Check service account permissions:
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
     --role="roles/bigquery.dataEditor"
   ```

2. Verify dataset exists:
   ```bash
   bq ls --project_id=PROJECT_ID
   ```

**Issue: Pub/Sub message processing fails**

**Diagnostic Steps:**
1. Check subscription status:
   ```bash
   gcloud pubsub subscriptions describe events-raw-sub
   ```

2. View undelivered messages:
   ```bash
   gcloud pubsub subscriptions pull events-raw-sub --limit=5
   ```

3. Check dead letter queue:
   ```bash
   gcloud pubsub topics list | grep dead-letter
   ```

### Container and Docker Issues

**Issue: Docker build fails**
```
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**Solutions:**
1. Check Dockerfile syntax and dependencies
2. Use specific Python version:
   ```dockerfile
   FROM python:3.8-slim
   ```

3. Clear Docker cache:
   ```bash
   docker system prune -a
   ```

**Issue: Container runs locally but fails in cloud**

**Diagnostic Steps:**
1. Check environment differences:
   ```bash
   # Local
   docker run --env-file .env misinformation-heatmap env
   
   # Cloud
   gcloud run services describe misinformation-heatmap --format="export"
   ```

2. Verify port configuration:
   ```python
   # In api.py
   port = int(os.environ.get("PORT", 8080))  # Cloud Run uses PORT env var
   ```

## Monitoring and Alerting Issues

### Health Check Failures

**Issue: Health endpoint returns unhealthy status**

**Diagnostic Steps:**
1. Check individual component health:
   ```bash
   curl http://localhost:8000/health | jq '.dependencies'
   ```

2. Test database connectivity:
   ```python
   from backend.database import Database
   db = Database()
   try:
       db.get_recent_events(limit=1)
       print("Database: OK")
   except Exception as e:
       print(f"Database: ERROR - {e}")
   ```

3. Test NLP service:
   ```python
   from backend.nlp_analyzer import NLPAnalyzer
   analyzer = NLPAnalyzer()
   try:
       result = analyzer.analyze("Test text")
       print("NLP: OK")
   except Exception as e:
       print(f"NLP: ERROR - {e}")
   ```

### Performance Monitoring Issues

**Issue: Performance metrics not collecting**

**Solutions:**
1. Start performance monitoring:
   ```python
   from backend.performance_optimizer import get_performance_optimizer
   optimizer = get_performance_optimizer()
   optimizer.start_monitoring(interval=30)
   ```

2. Check monitoring thread:
   ```python
   import threading
   print([t.name for t in threading.enumerate()])
   ```

## Data Quality Issues

### Inconsistent Results

**Issue: Heatmap shows unexpected data**

**Diagnostic Steps:**
1. Check raw event data:
   ```sql
   SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;
   ```

2. Verify processing pipeline:
   ```bash
   # Test with known input
   curl -X POST http://localhost:8000/ingest/test \
     -H "Content-Type: application/json" \
     -d '{"text":"Test misinformation in Maharashtra","source":"test","location":"Maharashtra"}'
   
   # Check processed result
   sqlite3 data/heatmap.db "SELECT * FROM events WHERE source='test' ORDER BY timestamp DESC LIMIT 1;"
   ```

3. Validate aggregation logic:
   ```python
   from backend.database import Database
   db = Database()
   heatmap_data = db.get_heatmap_data(hours_back=24)
   print(json.dumps(heatmap_data, indent=2))
   ```

### Missing or Incorrect Location Data

**Issue: Events not assigned to correct states**

**Solutions:**
1. Check entity extraction:
   ```python
   from backend.nlp_analyzer import NLPAnalyzer
   analyzer = NLPAnalyzer()
   result = analyzer.analyze("News from Mumbai, Maharashtra")
   print(result.entities)  # Should include 'Maharashtra'
   ```

2. Verify state name mapping:
   ```python
   # Check if state names are standardized
   valid_states = [
       "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
       "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
       "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
       # ... etc
   ]
   ```

## Getting Help

### Log Analysis

**Enable Debug Logging:**
```bash
export LOG_LEVEL=DEBUG
python backend/api.py
```

**Collect System Information:**
```bash
# Create diagnostic report
python scripts/health_check.py --diagnostic-report > diagnostic_report.txt
```

### Support Channels

1. **GitHub Issues**: Report bugs and feature requests
2. **Documentation**: Check README.md and docs/ directory
3. **Performance Reports**: Use performance_benchmark.py for detailed analysis

### Emergency Procedures

**System Recovery Steps:**
1. Stop all services
2. Backup current data
3. Reset to known good state
4. Restart services
5. Verify functionality

**Data Recovery:**
```bash
# Backup current database
cp data/heatmap.db data/heatmap.db.backup.$(date +%Y%m%d_%H%M%S)

# Restore from backup
cp data/heatmap.db.backup.YYYYMMDD_HHMMSS data/heatmap.db

# Reinitialize if needed
python backend/init_db.py --mode local --sample-data
```

This troubleshooting guide covers the most common issues encountered with the misinformation heatmap system. For issues not covered here, please check the system logs and create a detailed issue report with steps to reproduce the problem.