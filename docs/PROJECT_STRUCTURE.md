# 🏗️ Project Structure Overview

## 📁 Directory Organization

```
enhanced-fake-news-detection/
├── 📂 backend/                     # Core backend services
│   ├── 📄 main_application.py      # FastAPI main application
│   ├── 📄 enhanced_fake_news_detector.py  # Core detection engine
│   ├── 📄 advanced_ml_classifier.py       # ML classification pipeline
│   ├── 📄 realtime_processor.py           # Live data processing
│   ├── 📄 data_ingestion_service.py       # RSS feed management
│   ├── 📄 enhanced_realtime_system.py     # Real-time system coordinator
│   ├── 📄 heatmap_aggregator.py           # Geographic data aggregation
│   ├── 📄 nlp_analyzer.py                 # Natural language processing
│   ├── 📄 satellite_analysis.py           # Satellite verification
│   ├── 📄 satellite_client.py             # Satellite API client
│   ├── 📄 satellite_stub.py               # Satellite service stub
│   ├── 📄 performance_optimizer.py        # System optimization
│   ├── 📄 processor.py                    # Data processing utilities
│   ├── 📄 ingestion_manager.py            # Ingestion coordination
│   ├── 📄 ingest_local.py                 # Local data ingestion
│   ├── 📄 massive_data_ingestion.py       # High-volume processing
│   ├── 📄 enhanced_heatmap.py             # Enhanced visualization
│   ├── 📄 api.py                          # API route definitions
│   ├── 📄 api_utils.py                    # API utility functions
│   ├── 📄 config.py                       # Configuration management
│   ├── 📄 database.py                     # Database operations
│   ├── 📄 models.py                       # Data models
│   ├── 📄 init_db.py                      # Database initialization
│   ├── 📄 requirements.txt                # Python dependencies
│   ├── 📄 __init__.py                     # Package initialization
│   ├── 📂 data_sources/                   # Data source connectors
│   │   ├── 📄 base/                       # Base classes
│   │   ├── 📄 rss/                        # RSS feed connectors
│   │   ├── 📄 crawlers/                   # Web crawlers
│   │   ├── 📄 registry.py                 # Source registration
│   │   └── 📄 coordinator.py              # Ingestion orchestration
│   └── 📂 test_*.py                       # Backend test files
├── 📂 frontend/                    # Web interface
│   ├── 📄 index.html              # Main dashboard
│   ├── 📄 dashboard.html          # Analytics dashboard
│   ├── 📄 styles.css              # Styling
│   └── 📄 scripts.js              # Frontend JavaScript
├── 📂 map/                        # Interactive India map
│   ├── 📄 interactive-india-map.html      # Basic map interface
│   ├── 📄 enhanced-india-heatmap.html     # Enhanced heatmap
│   ├── 📄 mapdata.js                      # Map data and utilities
│   └── 📄 in.svg                          # India SVG map
├── 📂 docs/                       # Complete documentation
│   ├── 📄 README.md               # Documentation index
│   ├── 📄 PROJECT_STRUCTURE.md    # This file
│   ├── 📄 SYSTEM_OVERVIEW.md      # System capabilities
│   ├── 📄 BACKEND_ARCHITECTURE.md # Backend design
│   ├── 📄 ML_MODEL_DOCUMENTATION.md # AI model specs
│   ├── 📄 DOCKER_SETUP.md         # Containerization guide
│   ├── 📄 TESTING_GUIDE.md        # Testing procedures
│   ├── 📄 TROUBLESHOOTING.md      # Issue resolution
│   ├── 📄 DATA_INGESTION_ARCHITECTURE.md # Data processing
│   ├── 📄 CLOUD_PLATFORM_COMPARISON.md  # Platform analysis
│   ├── 📄 IMPROVEMENTS_SUMMARY.md        # Recent enhancements
│   ├── 📄 IMPROVEMENT_ROADMAP.md         # Future plans
│   └── 📄 PRODUCTION_ROADMAP.md          # Deployment timeline
├── 📂 data/                       # Database and datasets
│   ├── 📄 enhanced_fake_news.db   # SQLite database
│   └── 📄 training_data/          # ML training datasets
├── 📂 tests/                      # Test suites
│   ├── 📄 test_*.py               # Unit tests
│   └── 📄 integration/            # Integration tests
├── 📂 scripts/                    # Utility scripts
│   ├── 📄 docker-dev.sh           # Development Docker script
│   ├── 📄 docker-prod.sh          # Production Docker script
│   └── 📄 setup.sh                # Environment setup
├── 📄 README.md                   # Main project documentation
├── 📄 requirements.txt            # Python dependencies
├── 📄 Dockerfile                  # Docker container definition
├── 📄 docker-compose.yml          # Development environment
├── 📄 docker-compose.prod.yml     # Production environment
├── 📄 .env.example                # Environment variables template
├── 📄 .env.sample                 # Sample configuration
├── 📄 .gitignore                  # Git ignore rules
└── 📄 LICENSE                     # Project license
```

## 🔧 Core Components

### Backend Services (`/backend/`)

#### Main Application Layer
- **`main_application.py`** - FastAPI application entry point with CORS, routing, and middleware
- **`api.py`** - RESTful API endpoint definitions and request handling
- **`api_utils.py`** - Utility functions for API operations and response formatting

#### AI & Detection Engine
- **`enhanced_fake_news_detector.py`** - Core detection engine orchestrating all analysis components
- **`advanced_ml_classifier.py`** - Machine learning pipeline with ensemble algorithms
- **`nlp_analyzer.py`** - Natural language processing and sentiment analysis

#### Data Processing Pipeline
- **`data_ingestion_service.py`** - RSS feed management and content extraction
- **`realtime_processor.py`** - Live data processing and classification
- **`enhanced_realtime_system.py`** - Real-time system coordination and monitoring
- **`massive_data_ingestion.py`** - High-volume data processing capabilities

#### Verification & Analysis
- **`satellite_analysis.py`** - Satellite imagery verification for location claims
- **`satellite_client.py`** - Google Earth Engine API integration
- **`heatmap_aggregator.py`** - Geographic data aggregation and state mapping

#### System Management
- **`config.py`** - Configuration management and environment variables
- **`database.py`** - Database operations and connection management
- **`models.py`** - Data models and schema definitions
- **`performance_optimizer.py`** - System optimization and caching

### Frontend Interface (`/frontend/`)

#### Web Interface
- **`index.html`** - Main dashboard with system overview and navigation
- **`dashboard.html`** - Analytics dashboard with comprehensive statistics
- **`styles.css`** - Modern CSS styling with responsive design
- **`scripts.js`** - Frontend JavaScript for API integration and interactivity

### Interactive Visualization (`/map/`)

#### Map Components
- **`enhanced-india-heatmap.html`** - Advanced heatmap with real-time updates
- **`interactive-india-map.html`** - Basic interactive map interface
- **`mapdata.js`** - Map utilities, state data, and interaction handlers
- **`in.svg`** - Scalable vector graphics map of India

### Documentation (`/docs/`)

#### Technical Documentation
- **`BACKEND_ARCHITECTURE.md`** - Detailed backend system design
- **`ML_MODEL_DOCUMENTATION.md`** - AI model specifications and performance
- **`DATA_INGESTION_ARCHITECTURE.md`** - Data processing pipeline design

#### Setup & Operations
- **`DOCKER_SETUP.md`** - Containerization and deployment guide
- **`TESTING_GUIDE.md`** - Comprehensive testing procedures
- **`TROUBLESHOOTING.md`** - Common issues and resolution steps

#### Project Management
- **`IMPROVEMENTS_SUMMARY.md`** - Recent enhancements and bug fixes
- **`IMPROVEMENT_ROADMAP.md`** - Future development plans
- **`PRODUCTION_ROADMAP.md`** - Production deployment timeline

### Data & Storage (`/data/`)

#### Database
- **`enhanced_fake_news.db`** - SQLite database for development
- **`training_data/`** - Machine learning datasets and model training files

### Testing (`/tests/`)

#### Test Suites
- **Unit Tests** - Individual component testing
- **Integration Tests** - End-to-end system testing
- **Performance Tests** - Load and stress testing

### Infrastructure

#### Containerization
- **`Dockerfile`** - Multi-stage Docker build for production optimization
- **`docker-compose.yml`** - Development environment with all services
- **`docker-compose.prod.yml`** - Production environment with monitoring

#### Configuration
- **`.env.example`** - Environment variables template
- **`requirements.txt`** - Python package dependencies
- **`.gitignore`** - Version control exclusions

## 🚀 Key Features by Component

### Real-time Processing
- **RSS Feed Monitoring**: 30+ Indian news sources
- **Live Classification**: Sub-second response times
- **Geographic Mapping**: State-wise aggregation
- **WebSocket Updates**: Real-time frontend synchronization

### AI Analysis Pipeline
- **IndicBERT Integration**: Indian language and cultural context
- **Ensemble ML**: Multiple algorithms for robust classification
- **Linguistic Analysis**: Sensational language and manipulation detection
- **Fact-Checking**: Integration with Indian fact-checkers

### Verification Systems
- **Source Credibility**: News outlet reliability assessment
- **Satellite Verification**: Google Earth Engine integration
- **Cross-Reference**: Multi-source claim validation
- **Attribution Analysis**: Proper sourcing verification

### Visualization & Interface
- **Interactive Heatmap**: Real-time India map with state-wise data
- **Analytics Dashboard**: Comprehensive statistics and trends
- **RESTful API**: Complete programmatic access
- **Mobile Responsive**: Optimized for all device types

## 📊 Data Flow Architecture

```
RSS Sources → Data Ingestion → Content Processing → AI Analysis → 
Classification → Verification → Database Storage → API Endpoints → 
Frontend Visualization → Real-time Updates
```

### Processing Pipeline
1. **Ingestion**: RSS feeds monitored every 30 seconds
2. **Preprocessing**: Content cleaning and metadata extraction
3. **Analysis**: Multi-component AI analysis (IndicBERT, ML, linguistic)
4. **Verification**: Satellite, fact-checking, source credibility
5. **Classification**: Final score calculation and verdict assignment
6. **Storage**: Database persistence with geographic mapping
7. **Visualization**: Real-time map updates and dashboard statistics

## 🔧 Development Workflow

### Local Development
```bash
# Setup environment
pip install -r requirements.txt

# Run backend
cd backend && python main_application.py

# Access interfaces
# Main: http://localhost:8080
# Map: http://localhost:8080/map/enhanced-india-heatmap.html
# API: http://localhost:8080/docs
```

### Docker Development
```bash
# Development environment
docker-compose up --build

# Production testing
docker-compose -f docker-compose.prod.yml up -d
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=backend tests/

# Integration tests
pytest tests/integration/ -v
```

This project structure provides a comprehensive, scalable foundation for real-time fake news detection with advanced AI analysis and interactive visualization capabilities.