# Design Document

## Overview

The Real-Time Misinformation Heatmap system is designed as a hybrid architecture that seamlessly operates in both local development and cloud production environments. The system ingests content from Indian news sources and social media, applies NLP-based claim detection, validates claims against satellite imagery using Google Earth Engine embeddings, and visualizes misinformation patterns on an interactive map of India.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Processing     │    │   Visualization │
│                 │    │   Pipeline       │    │                 │
│ • News APIs     │───▶│ • NLP Analysis   │───▶│ • Leaflet Map   │
│ • Social Media  │    │ • Satellite Val  │    │ • Heatmap Layer │
│ • Manual Input  │    │ • Scoring        │    │ • State Details │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Local Mode:     │    │ Local Mode:      │    │ Local Mode:     │
│ • File scrapers │    │ • SQLite DB      │    │ • Static files  │
│ • Pub/Sub emu   │    │ • Stub responses │    │ • FastAPI serve │
│                 │    │                  │    │                 │
│ Cloud Mode:     │    │ Cloud Mode:      │    │ Cloud Mode:     │
│ • GCP Pub/Sub   │    │ • BigQuery       │    │ • CDN deploy    │
│ • Watson API    │    │ • Real GEE API   │    │ • Load balancer │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Component Architecture

```
Backend Services:
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                      │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Ingestion     │   Processing    │        API Layer           │
│                 │                 │                             │
│ • ingest_local  │ • processor.py  │ • /heatmap                  │
│ • pubsub_emu    │ • nlp_analyzer  │ • /region/{state}           │
│ • watson_client │ • satellite_val │ • /ingest/test              │
└─────────────────┴─────────────────┴─────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                           │
├─────────────────────────────┬───────────────────────────────────┤
│        Local Mode           │          Cloud Mode               │
│                             │                                   │
│ • SQLite database           │ • BigQuery tables                 │
│ • Local file storage        │ • Cloud Storage buckets           │
│ • In-memory cache           │ • Redis/Memorystore               │
└─────────────────────────────┴───────────────────────────────────┘
```

## Components and Interfaces

### 1. Configuration Management (`config.py`)

**Purpose**: Centralized configuration handling for hybrid mode switching

**Key Components**:
- Environment variable parsing for MODE selection
- Database connection string generation
- API endpoint configuration
- Credential management (cloud vs stub)

**Interface**:
```python
class Config:
    def __init__(self, mode: str = "local")
    def get_database_url(self) -> str
    def get_pubsub_config(self) -> dict
    def get_satellite_config(self) -> dict
    def is_cloud_mode(self) -> bool
```

### 2. Data Ingestion Layer

#### Local Ingestion (`ingest_local.py`)
**Purpose**: Simulates real-time data feeds using local scrapers and file-based sources

**Key Components**:
- RSS feed parsers for Indian news sources
- Social media API simulators
- Manual test data injection
- Pub/Sub emulator integration

#### Cloud Ingestion (`watson_client.py`)
**Purpose**: Integrates with IBM Watson Discovery and GCP Pub/Sub for production data

**Key Components**:
- Watson Discovery API client
- GCP Pub/Sub publisher/subscriber
- Rate limiting and error handling
- Data validation and sanitization

**Interface**:
```python
class IngestionClient:
    def __init__(self, config: Config)
    def ingest_news_sources(self) -> List[RawEvent]
    def ingest_social_media(self) -> List[RawEvent]
    def publish_to_queue(self, events: List[RawEvent]) -> bool
```

### 3. Processing Pipeline (`processor.py`)

**Purpose**: Core NLP analysis, claim extraction, and satellite validation orchestration

**Key Components**:
- IndicBERT-based text analysis for Indian languages
- Named Entity Recognition for geographic locations
- Claim extraction and categorization
- Virality score calculation
- Satellite validation coordination

**Interface**:
```python
class EventProcessor:
    def __init__(self, config: Config)
    def process_event(self, raw_event: RawEvent) -> ProcessedEvent
    def extract_claims(self, text: str, lang: str) -> List[Claim]
    def calculate_virality_score(self, event: RawEvent) -> float
    def validate_with_satellite(self, claim: Claim) -> SatelliteResult
```

### 4. Satellite Validation (`satellite_client.py`)

**Purpose**: Validates claims against Google Earth Engine satellite imagery embeddings

**Key Components**:
- Google Earth Engine API integration (cloud mode)
- Embedding similarity calculation
- Historical baseline comparison
- Stub response generation (local mode)
- Anomaly detection algorithms

**Interface**:
```python
class SatelliteValidator:
    def __init__(self, config: Config)
    def get_embeddings(self, lat: float, lon: float, date: str) -> np.ndarray
    def compare_with_baseline(self, current: np.ndarray, baseline: np.ndarray) -> float
    def detect_anomaly(self, similarity: float) -> bool
    def calculate_reality_score(self, satellite_data: dict) -> float
```

### 5. API Layer (`api.py`)

**Purpose**: RESTful API endpoints for frontend integration and external access

**Key Components**:
- FastAPI application with CORS support
- Heatmap data aggregation
- Regional detail queries
- Test data injection endpoints
- Static file serving for frontend

**Interface**:
```python
@app.get("/heatmap")
async def get_heatmap_data() -> HeatmapResponse

@app.get("/region/{state}")
async def get_region_details(state: str) -> RegionResponse

@app.post("/ingest/test")
async def ingest_test_data(payload: TestPayload) -> IngestResponse
```

### 6. Frontend Application

#### HTML Structure (`index.html`)
- Responsive layout with map container
- Control panels for filtering and time range selection
- Modal dialogs for detailed claim information

#### JavaScript Application (`app.js`)
- Leaflet.js map initialization with India boundaries
- Heat layer rendering based on API data
- Interactive state click handlers
- Real-time data polling and updates
- Responsive design for mobile devices

#### Styling (`style.css`)
- Modern, clean interface design
- Color schemes for heatmap intensity
- Mobile-responsive breakpoints
- Accessibility compliance (WCAG 2.1)

## Data Models

### Core Event Model
```python
@dataclass
class ProcessedEvent:
    event_id: str
    source: str  # "news" | "twitter" | "manual"
    original_text: str
    timestamp: datetime
    lang: str  # "hi" | "en" | "bn" | etc.
    region_hint: str  # Indian state name
    lat: float
    lon: float
    entities: List[str]
    virality_score: float  # 0.0 - 1.0
    satellite: SatelliteResult
    claims: List[Claim]
```

### Satellite Validation Model
```python
@dataclass
class SatelliteResult:
    similarity: float  # 0.0 - 1.0
    anomaly: bool
    reality_score: float  # 0.0 - 1.0
    confidence: float
    baseline_date: str
    analysis_metadata: dict
```

### Database Schema

#### SQLite Schema (Local Mode)
```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    original_text TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    lang TEXT,
    region_hint TEXT,
    lat REAL,
    lon REAL,
    entities JSON,
    virality_score REAL,
    satellite_data JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_region ON events(region_hint);
```

#### BigQuery Schema (Cloud Mode)
```sql
CREATE TABLE `project.dataset.events` (
    event_id STRING NOT NULL,
    source STRING NOT NULL,
    original_text STRING NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    lang STRING,
    region_hint STRING,
    lat FLOAT64,
    lon FLOAT64,
    entities ARRAY<STRING>,
    virality_score FLOAT64,
    satellite_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(timestamp)
CLUSTER BY region_hint;
```

## Error Handling

### Graceful Degradation Strategy
1. **Satellite API Failures**: Fall back to cached baseline data or skip satellite validation
2. **NLP Service Errors**: Use simpler keyword-based analysis as backup
3. **Database Connectivity**: Implement local caching and retry mechanisms
4. **External API Rate Limits**: Queue requests and implement exponential backoff

### Error Response Format
```python
@dataclass
class ErrorResponse:
    error_code: str
    message: str
    details: dict
    timestamp: datetime
    request_id: str
```

### Logging Strategy
- Structured JSON logging for cloud environments
- Local file-based logging for development
- Different log levels for components (DEBUG, INFO, WARN, ERROR)
- Performance metrics and timing information

## Testing Strategy

### Unit Testing
- Individual component testing with mocked dependencies
- NLP pipeline accuracy validation
- Satellite validation algorithm testing
- API endpoint response validation

### Integration Testing
- End-to-end pipeline testing from ingestion to visualization
- Database integration testing for both SQLite and BigQuery
- External API integration testing with mock services
- Frontend-backend integration validation

### Performance Testing
- Load testing for high-volume event processing
- API response time benchmarking
- Database query performance optimization
- Memory usage profiling for long-running processes

### Test Data Management
- Synthetic misinformation examples for testing
- Historical satellite data samples
- Geographic test cases covering all Indian states
- Multi-language test content in Hindi, English, and Bengali

### Automated Testing Pipeline
```bash
# Test execution flow
./scripts/run_tests.sh
├── Unit tests (pytest)
├── Integration tests (local mode)
├── Integration tests (cloud mode with emulators)
├── Frontend tests (Jest/Cypress)
└── Performance benchmarks
```

## Security Considerations

### Data Privacy
- No storage of personally identifiable information
- Text content anonymization for social media sources
- Secure credential management for cloud services
- GDPR compliance for any EU user data

### API Security
- Rate limiting on all endpoints
- Input validation and sanitization
- CORS configuration for frontend access
- Authentication for administrative endpoints

### Infrastructure Security
- Encrypted data transmission (HTTPS/TLS)
- Secure cloud service authentication
- Network security groups and firewall rules
- Regular security dependency updates

## Deployment Architecture

### Local Development
```
Developer Machine:
├── Python virtual environment
├── SQLite database file
├── Pub/Sub emulator process
├── FastAPI development server
└── Static file serving
```

### Cloud Production
```
Google Cloud Platform:
├── Cloud Run (FastAPI application)
├── Pub/Sub (message queuing)
├── BigQuery (data warehouse)
├── Cloud Storage (static assets)
├── Load Balancer (traffic distribution)
└── Cloud Monitoring (observability)
```

## Performance Requirements

### Latency Targets
- API response time: < 200ms for heatmap data
- Event processing: < 5 seconds from ingestion to storage
- Satellite validation: < 10 seconds per claim
- Frontend map rendering: < 2 seconds initial load

### Throughput Targets
- Event ingestion: 1000 events/minute (local), 10000 events/minute (cloud)
- Concurrent API requests: 100 (local), 1000 (cloud)
- Database queries: < 100ms average response time
- Real-time updates: 30-second refresh intervals

### Scalability Design
- Horizontal scaling for processing components
- Database partitioning by date and region
- CDN integration for static asset delivery
- Auto-scaling based on queue depth and CPU utilization