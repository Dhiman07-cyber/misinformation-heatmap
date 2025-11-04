# IBM Cloud Production Setup Guide

Complete guide for deploying the Misinformation Heatmap to IBM Cloud using your 1-year free access from cognitive classes.

## 🎯 **Why IBM Cloud is Perfect for This Project**

IBM Cloud offers excellent services for our misinformation heatmap:

### **Key Advantages:**
- **Watson AI Services** - Advanced NLP for misinformation detection
- **Free Tier Access** - Your 1-year cognitive classes access covers everything
- **Enterprise Grade** - Production-ready infrastructure
- **Easy Deployment** - Cloud Foundry makes deployment simple
- **Integrated Services** - Everything works together seamlessly

### **Services We'll Use:**
- **Watson Natural Language Understanding** - Sentiment analysis and entity extraction
- **Watson Language Translator** - Multi-language support for Indian content
- **Watson Discovery** - Advanced content analysis and categorization
- **Db2 Warehouse** - Structured data storage for events and analytics
- **Cloudant** - NoSQL database for flexible document storage
- **Event Streams (Kafka)** - Real-time event processing pipeline
- **Cloud Object Storage** - File and backup storage
- **Log Analysis & Monitoring** - Comprehensive observability

## 📋 **Prerequisites**

### **What You Need:**
1. **IBM Cloud Account** with cognitive classes access ✅ (You have this!)
2. **IBM Cloud CLI** - Command line tool for deployment
3. **Git** - For code management
4. **Python 3.8+** - For local development and testing

### **Getting Your IBM Cloud Information:**

**Organization Name:**
- This is usually your email address or account name
- Check in IBM Cloud Console → Manage → Account → Cloud Foundry Orgs

**Space Name:**
- We'll create a "production" space
- Or use an existing space name

## 🚀 **Quick Setup (10 Minutes)**

### **Step 1: Install IBM Cloud CLI**

**Windows:**
```powershell
# Download and install from: https://cloud.ibm.com/docs/cli?topic=cli-getting-started
# Or use chocolatey:
choco install ibmcloud-cli
```

**Mac:**
```bash
curl -fsSL https://clis.cloud.ibm.com/install/osx | sh
```

**Linux:**
```bash
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh
```

### **Step 2: Login to IBM Cloud**

```bash
# Login to IBM Cloud
ibmcloud login

# If you have SSO (Single Sign-On):
ibmcloud login --sso

# Select your account when prompted
# Note your organization name (usually your email)
```

### **Step 3: Run the Setup Script**

```bash
# Navigate to your project
cd misinformation-heatmap

# Make the script executable (Linux/Mac)
chmod +x scripts/ibm-cloud-setup.sh

# Run the setup (replace with YOUR values)
./scripts/ibm-cloud-setup.sh \
  --org "your-email@example.com" \
  --email "your-email@example.com" \
  --region "us-south" \
  --verbose
```

**Example with real values:**
```bash
./scripts/ibm-cloud-setup.sh \
  --org "student123@university.edu" \
  --email "student123@university.edu" \
  --region "us-south" \
  --app-name "misinformation-heatmap" \
  --verbose
```

## 📖 **What the Setup Creates**

### **Watson AI Services (Free Tier):**
- **Natural Language Understanding** - Analyzes text for sentiment, entities, concepts
- **Language Translator** - Translates content between languages
- **Discovery** - Advanced text analytics and search

### **Data Services:**
- **Db2 Warehouse** - Main database for structured data
- **Cloudant** - NoSQL database for flexible document storage
- **Redis** - High-performance caching layer

### **Event Processing:**
- **Event Streams (Kafka)** - Real-time message processing
- **Topics**: events-raw, events-processed, events-validated

### **Monitoring & Operations:**
- **Log Analysis** - Centralized logging with search and alerts
- **Monitoring** - Application performance monitoring
- **Cloud Object Storage** - File storage and backups

## 🔧 **Configuration Files Created**

### **1. manifest.yml (Cloud Foundry Deployment)**
```yaml
applications:
- name: misinformation-heatmap
  memory: 1G
  instances: 2
  buildpacks:
    - python_buildpack
  services:
    - watson-nlu
    - watson-translator
    - misinformation-db2
    - misinformation-redis
    # ... all other services
```

### **2. .env.ibmcloud (Environment Variables)**
```bash
MODE=cloud
ENVIRONMENT=production
WATSON_NLU_ENABLED=true
DB_TYPE=db2
CACHE_TYPE=redis
# ... all configuration
```

### **3. Database Schema (Db2)**
- Events table with optimized indexes
- Aggregations table for heatmap data
- Data sources tracking
- Performance-optimized views

## 🚀 **Deployment Process**

### **Step 1: Deploy the Application**

```bash
# Deploy to IBM Cloud
./scripts/deploy-ibmcloud.sh
```

This will:
1. ✅ Install dependencies
2. ✅ Run tests
3. ✅ Deploy to Cloud Foundry
4. ✅ Bind all services automatically
5. ✅ Run health checks
6. ✅ Provide your application URL

### **Step 2: Set Up Database Schema**

```bash
# The setup creates a SQL file for you
# Connect to your Db2 instance and run:
# scripts/setup_db2_schema.sql

# Or use the IBM Cloud console:
# 1. Go to IBM Cloud Dashboard
# 2. Find your Db2 service
# 3. Open the console
# 4. Run the SQL script
```

### **Step 3: Configure Watson Services**

The services are automatically bound, but you can customize:

```bash
# Get service credentials
ibmcloud resource service-key watson-nlu-key

# The app automatically reads these via VCAP_SERVICES
# No manual configuration needed!
```

## 📊 **Monitoring Your Application**

### **Application URL:**
After deployment, you'll get a URL like:
`https://misinformation-heatmap.mybluemix.net`

### **Key Endpoints:**
- **Health Check**: `/health`
- **API Documentation**: `/docs`
- **Heatmap Data**: `/api/v1/heatmap/states`
- **Recent Events**: `/api/v1/events`

### **Monitoring Dashboards:**
1. Go to IBM Cloud Dashboard
2. Find your "misinformation-monitoring" service
3. Open the monitoring console
4. View application metrics, logs, and performance

### **Log Analysis:**
1. Find your "misinformation-logs" service
2. Open LogDNA console
3. Search and filter application logs
4. Set up alerts for errors

## 💰 **Cost Management (Free Tier)**

### **What's Included in Your Free Access:**
- **Watson Services**: Generous free tiers for NLU, Translator, Discovery
- **Db2**: Free tier with 200MB storage
- **Cloudant**: 1GB storage, 20 lookups/sec
- **Event Streams**: 1 partition, 100MB/month
- **Cloud Foundry**: 256MB memory free
- **Monitoring & Logging**: Basic tier included

### **Staying Within Free Limits:**
```bash
# Monitor usage in IBM Cloud console
# Set up billing alerts
ibmcloud billing org-usage ORG_NAME

# Scale down if needed
ibmcloud cf scale misinformation-heatmap -i 1 -m 512M
```

## 🔒 **Security Configuration**

### **Automatic Security Features:**
- **HTTPS by default** - All traffic encrypted
- **Service binding security** - Credentials managed automatically
- **Network isolation** - Services communicate securely
- **Access control** - IBM Cloud IAM integration

### **Additional Security Setup:**
```bash
# Set up API keys for external access
# Add to your application environment:
export API_KEYS="your-secure-api-key-1,your-secure-api-key-2"

# Configure CORS for your domain
export CORS_ORIGINS='["https://your-frontend-domain.com"]'
```

## 🧪 **Testing Your Deployment**

### **Health Checks:**
```bash
# Get your app URL
APP_URL=$(ibmcloud cf app misinformation-heatmap --show-app-url | tail -1)

# Test health endpoint
curl "$APP_URL/health"

# Test API
curl "$APP_URL/api/v1/health"

# Test with sample data
curl -X POST "$APP_URL/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Event","content":"Testing the API"}'
```

### **Load Testing:**
```bash
# Install Apache Bench
# Windows: Download from Apache website
# Mac: brew install httpie
# Linux: sudo apt-get install apache2-utils

# Run load test
ab -n 100 -c 10 "$APP_URL/api/v1/health"
```

### **Watson AI Testing:**
```bash
# Test NLP processing
curl -X POST "$APP_URL/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a test message for sentiment analysis"}'

# Check the response for Watson NLU results
```

## 🔄 **Scaling and Performance**

### **Horizontal Scaling:**
```bash
# Scale up instances
ibmcloud cf scale misinformation-heatmap -i 3

# Scale up memory
ibmcloud cf scale misinformation-heatmap -m 1G
```

### **Performance Optimization:**
- **Redis Caching**: Automatically configured for API responses
- **Database Indexing**: Optimized queries for fast heatmap generation
- **Watson AI**: Efficient batch processing for multiple texts
- **CDN**: Static assets served via IBM Cloud CDN

### **Monitoring Performance:**
- **Response Times**: Monitor via IBM Cloud Monitoring
- **Database Performance**: Db2 performance insights
- **Watson API Usage**: Track API calls and response times
- **Memory/CPU Usage**: Cloud Foundry metrics

## 🛠️ **Troubleshooting**

### **Common Issues:**

**1. Deployment Fails:**
```bash
# Check logs
ibmcloud cf logs misinformation-heatmap --recent

# Check app status
ibmcloud cf app misinformation-heatmap
```

**2. Service Binding Issues:**
```bash
# List services
ibmcloud cf services

# Bind service manually if needed
ibmcloud cf bind-service misinformation-heatmap watson-nlu
```

**3. Database Connection Issues:**
```bash
# Check Db2 service status
ibmcloud resource service-instance misinformation-db2

# Get connection details
ibmcloud resource service-key db2-key
```

**4. Watson API Errors:**
```bash
# Check Watson service status
ibmcloud resource service-instance watson-nlu

# Verify API key
ibmcloud resource service-key watson-nlu-key
```

### **Performance Issues:**
- **High Response Times**: Scale up instances or memory
- **Database Slow**: Check query performance in Db2 console
- **Watson API Limits**: Monitor usage in service dashboard

## 🔄 **CI/CD with IBM Cloud**

### **Automatic Deployment:**
```bash
# Set up toolchain in IBM Cloud
# 1. Go to IBM Cloud Dashboard
# 2. Create Toolchain
# 3. Connect GitHub repository
# 4. Configure automatic deployment

# Or use CLI for simple deployment
ibmcloud cf push
```

### **Environment Management:**
```bash
# Create staging environment
ibmcloud cf create-space staging
ibmcloud target -s staging

# Deploy to staging
ibmcloud cf push misinformation-heatmap-staging
```

## 📞 **Getting Help**

### **IBM Cloud Support:**
- **Documentation**: https://cloud.ibm.com/docs
- **Community**: https://developer.ibm.com/community/
- **Stack Overflow**: Tag questions with `ibm-cloud`

### **Watson AI Support:**
- **Watson Documentation**: https://cloud.ibm.com/docs/watson
- **API Reference**: https://cloud.ibm.com/apidocs/natural-language-understanding

### **Cognitive Classes Support:**
- **Course Forums**: Access through your cognitive classes portal
- **IBM Developer Community**: Free support for students

## 🎉 **Success Checklist**

Your IBM Cloud deployment is successful when:

✅ **Application Running**: App accessible at your IBM Cloud URL  
✅ **Watson AI Working**: NLP analysis returning results  
✅ **Database Connected**: Events being stored in Db2  
✅ **Caching Active**: Redis improving response times  
✅ **Monitoring Setup**: Logs and metrics visible in dashboards  
✅ **Health Checks Passing**: All endpoints responding correctly  

## 🚀 **Next Steps After Deployment**

1. **Add Real Data Sources**: Configure RSS feeds and web scrapers
2. **Customize Watson Models**: Train with domain-specific data
3. **Set Up Alerts**: Configure monitoring alerts for production
4. **Performance Tuning**: Optimize based on usage patterns
5. **Security Hardening**: Add additional security measures
6. **User Interface**: Deploy frontend to IBM Cloud Static Web Apps

---

**Your IBM Cloud setup is now complete!** 🎉

You have a production-ready misinformation heatmap running on enterprise-grade infrastructure with advanced AI capabilities, all within your free cognitive classes access.

Need help? Check the troubleshooting section or reach out through the IBM Developer Community!