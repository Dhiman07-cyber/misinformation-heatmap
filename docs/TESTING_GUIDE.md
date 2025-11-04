# Testing Guide

Comprehensive testing documentation for the Real-Time Misinformation Heatmap system.

## Overview

This guide covers all aspects of testing the misinformation heatmap system, including unit tests, integration tests, end-to-end tests, and performance testing.

## Test Architecture

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_nlp_analyzer.py
│   ├── test_satellite_client.py
│   ├── test_database.py
│   └── test_api.py
├── integration/             # Integration tests for component interactions
│   ├── test_ingestion_pipeline.py
│   ├── test_api_integration.py
│   └── test_deployment.py
├── e2e/                     # End-to-end tests for complete workflows
│   ├── test_end_to_end.py
│   ├── run_e2e_tests.sh
│   └── run_e2e_tests.ps1
├── performance/             # Performance and load tests
│   ├── test_performance.py
│   └── load_test.py
└── fixtures/                # Test data and fixtures
    ├── sample_events.json
    ├── test_states.geojson
    └── mock_responses/
```

## Test Categories

### 1. Unit Tests

Unit tests verify individual components in isolation.

#### Running Unit Tests

```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/test_nlp_analyzer.py -v

# Run with coverage
python -m pytest tests/unit/ --cov=backend --cov-report=html
```

#### Unit Test Coverage

| Component | Test File | Coverage Target | Current Coverage |
|-----------|-----------|-----------------|------------------|
| NLP Analyzer | `test_nlp_analyzer.py` | 90% | 85% |
| Satellite Client | `test_satellite_client.py` | 85% | 80% |
| Database Layer | `test_database.py` | 95% | 90% |
| API Endpoints | `test_api.py` | 90% | 88% |
| Configuration | `test_config.py` | 100% | 95% |

#### Key Unit Test Scenarios

**NLP Analyzer Tests:**
- Text preprocessing and cleaning
- Language detection accuracy
- Entity extraction for Indian locations
- Claim extraction from various text types
- Virality and reality score calculations
- Error handling for malformed input

**Satellite Client Tests:**
- API authentication and connection
- Coordinate validation for India boundaries
- Embedding extraction and similarity calculation
- Stub mode functionality
- Error handling and retry logic

**Database Tests:**
- Connection management (SQLite and BigQuery)
- CRUD operations for events
- Query optimization and indexing
- Data validation and constraints
- Migration and schema updates

**API Tests:**
- Endpoint response formats
- Input validation and sanitization
- Authentication and authorization
- Rate limiting functionality
- Error response handling

### 2. Integration Tests

Integration tests verify component interactions and data flow.

#### Running Integration Tests

```bash
# Run all integration tests
python -m pytest tests/integration/ -v

# Run with specific markers
python -m pytest tests/integration/ -m "database" -v
python -m pytest tests/integration/ -m "api" -v
```

#### Integration Test Scenarios

**Ingestion Pipeline Tests:**
- End-to-end event processing flow
- NLP analysis integration with database storage
- Satellite validation integration
- Error propagation and handling
- Data consistency across components

**API Integration Tests:**
- Database query integration
- Real-time data updates
- Cross-component error handling
- Performance under concurrent requests

**Deployment Tests:**
- Local environment setup validation
- Cloud deployment verification
- Service connectivity and health checks
- Configuration validation across environments

### 3. End-to-End Tests

E2E tests verify complete user workflows from frontend to backend.

#### Running E2E Tests

```bash
# Local mode
cd tests/e2e
./run_e2e_tests.sh --mode local --verbose

# Cloud mode
./run_e2e_tests.sh --mode cloud --output results.json

# Windows PowerShell
.\run_e2e_tests.ps1 -Mode local -Verbose
```

#### E2E Test Scenarios

**Complete User Workflows:**
1. **Data Ingestion to Visualization**
   - Submit test events via API
   - Verify NLP processing and satellite validation
   - Check heatmap data updates
   - Validate frontend display

2. **Interactive Map Usage**
   - Load frontend application
   - Verify map initialization and state boundaries
   - Test state click interactions
   - Validate modal displays and data accuracy

3. **Real-time Updates**
   - Inject new events during testing
   - Verify real-time data refresh
   - Check status indicators and notifications

4. **Error Handling and Recovery**
   - Test invalid input handling
   - Verify graceful degradation
   - Check error message display

#### E2E Test Results Interpretation

**Success Criteria:**
- All API endpoints respond correctly (< 2s response time)
- Frontend loads and displays map within 10 seconds
- Data ingestion processes events within 30 seconds
- Real-time updates reflect within 60 seconds
- Error scenarios handled gracefully

**Common Issues and Solutions:**

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Service startup timeout | Tests fail with connection errors | Increase startup wait time, check service logs |
| WebDriver failures | Browser tests skip or fail | Install Chrome/Chromium, check headless mode |
| Data inconsistency | Heatmap shows incorrect data | Verify database state, check processing pipeline |
| Performance degradation | Slow response times | Check system resources, optimize queries |

### 4. Performance Tests

Performance tests verify system behavior under load and measure response times.

#### Running Performance Tests

```bash
# Basic performance test
python tests/performance/test_performance.py

# Load testing
python tests/performance/load_test.py --users 50 --duration 300

# Benchmark specific components
python scripts/performance_benchmark.py --component nlp
```

#### Performance Benchmarks

**API Response Times (95th percentile):**
- `/health`: < 100ms
- `/heatmap`: < 1000ms
- `/region/{state}`: < 800ms
- `/ingest/test`: < 2000ms

**Processing Times:**
- NLP Analysis: < 500ms per event
- Satellite Validation: < 1000ms per event
- Database Query (heatmap): < 200ms
- Frontend Load Time: < 5 seconds

**Throughput Targets:**
- API Requests: 100 requests/second
- Event Processing: 50 events/second
- Concurrent Users: 100 users

#### Load Testing Scenarios

1. **Steady Load Test**
   - 50 concurrent users
   - 5-minute duration
   - Mixed API endpoints

2. **Spike Test**
   - Ramp up to 200 users in 30 seconds
   - Hold for 2 minutes
   - Ramp down to 10 users

3. **Stress Test**
   - Gradually increase load until failure
   - Identify breaking point
   - Measure recovery time

## Test Data Management

### Test Fixtures

**Sample Events (`fixtures/sample_events.json`):**
```json
[
  {
    "text": "Breaking news about infrastructure development in Maharashtra",
    "source": "test_news",
    "location": "Maharashtra",
    "category": "infrastructure",
    "expected_virality": 0.6,
    "expected_reality": 0.8
  },
  {
    "text": "False claims about Karnataka government policies",
    "source": "test_social",
    "location": "Karnataka", 
    "category": "politics",
    "expected_virality": 0.8,
    "expected_reality": 0.2
  }
]
```

**Mock Responses:**
- Satellite API responses with various similarity scores
- NLP model outputs for different text types
- Database query results for different scenarios

### Test Database Setup

**Local Testing:**
```bash
# Initialize test database
python backend/init_db.py --mode local --test-data

# Reset test database
rm data/test_heatmap.db
python backend/init_db.py --mode local --test-data
```

**Cloud Testing:**
```bash
# Setup test dataset in BigQuery
./scripts/setup_bigquery.sh --project test-project --test-data
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
      - name: Run unit tests
        run: python -m pytest tests/unit/ --cov=backend

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v3
      - name: Setup services
        run: ./scripts/run_local.sh &
      - name: Run integration tests
        run: python -m pytest tests/integration/

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - uses: actions/checkout@v3
      - name: Setup Chrome
        uses: browser-actions/setup-chrome@latest
      - name: Run E2E tests
        run: cd tests/e2e && ./run_e2e_tests.sh --mode local
```

### Test Quality Gates

**Pull Request Requirements:**
- All unit tests pass (100%)
- Integration tests pass (100%)
- Code coverage > 80%
- No critical security vulnerabilities
- Performance benchmarks within acceptable range

**Release Requirements:**
- All test suites pass (100%)
- E2E tests pass in both local and cloud modes
- Performance tests meet SLA requirements
- Load tests demonstrate system stability

## Test Environment Setup

### Local Development Testing

1. **Prerequisites:**
   ```bash
   # Install Python dependencies
   pip install -r backend/requirements.txt
   pip install -r tests/e2e/requirements.txt
   
   # Install Chrome for Selenium tests
   # Ubuntu/Debian: sudo apt-get install google-chrome-stable
   # macOS: brew install --cask google-chrome
   ```

2. **Environment Variables:**
   ```bash
   export MODE=local
   export PYTHONPATH=backend:$PYTHONPATH
   export LOG_LEVEL=DEBUG
   ```

3. **Start Services:**
   ```bash
   ./scripts/run_local.sh
   ```

### Cloud Testing Environment

1. **Setup GCP Project:**
   ```bash
   gcloud projects create test-misinformation-heatmap
   gcloud config set project test-misinformation-heatmap
   ```

2. **Deploy Test Infrastructure:**
   ```bash
   ./scripts/setup_bigquery.sh --project test-misinformation-heatmap
   ./scripts/pubsub_setup.sh --project test-misinformation-heatmap
   ```

3. **Deploy Application:**
   ```bash
   ./scripts/deploy_cloudrun.sh --project test-misinformation-heatmap
   ```

## Troubleshooting Test Issues

### Common Test Failures

**1. Database Connection Errors**
```
Error: sqlite3.OperationalError: database is locked
```
**Solution:** Ensure no other processes are using the test database, or use a unique database file for each test run.

**2. Selenium WebDriver Issues**
```
Error: selenium.common.exceptions.WebDriverException: chrome not reachable
```
**Solution:** Install Chrome/Chromium, update ChromeDriver, or run tests in headless mode.

**3. API Timeout Errors**
```
Error: requests.exceptions.ConnectTimeout: HTTPSConnectionPool
```
**Solution:** Increase timeout values, check service startup, verify network connectivity.

**4. Memory Issues During Testing**
```
Error: MemoryError: Unable to allocate array
```
**Solution:** Reduce test data size, increase system memory, or run tests in smaller batches.

### Debug Mode Testing

**Enable Debug Logging:**
```bash
export LOG_LEVEL=DEBUG
python -m pytest tests/ -v -s --log-cli-level=DEBUG
```

**Run Single Test with Debugging:**
```bash
python -m pytest tests/unit/test_nlp_analyzer.py::test_claim_extraction -v -s --pdb
```

**Profile Test Performance:**
```bash
python -m pytest tests/ --profile --profile-svg
```

## Test Metrics and Reporting

### Coverage Reports

**Generate HTML Coverage Report:**
```bash
python -m pytest tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

**Coverage Targets:**
- Overall: > 80%
- Critical components (NLP, Database): > 90%
- API endpoints: > 85%
- Configuration and utilities: > 75%

### Test Execution Reports

**JUnit XML Report:**
```bash
python -m pytest tests/ --junitxml=test-results.xml
```

**HTML Test Report:**
```bash
python -m pytest tests/ --html=test-report.html --self-contained-html
```

### Performance Metrics

**Response Time Percentiles:**
- P50 (median): Target response time for typical usage
- P95: Maximum acceptable response time
- P99: Response time for worst-case scenarios

**Resource Usage:**
- CPU utilization during tests
- Memory consumption patterns
- Database query performance
- Network I/O metrics

## Best Practices

### Writing Effective Tests

1. **Test Naming Convention:**
   ```python
   def test_should_extract_claims_when_given_valid_text():
       # Test implementation
   ```

2. **Arrange-Act-Assert Pattern:**
   ```python
   def test_nlp_analysis():
       # Arrange
       analyzer = NLPAnalyzer()
       text = "Sample misinformation text"
       
       # Act
       result = analyzer.analyze(text)
       
       # Assert
       assert result.claims is not None
       assert len(result.claims) > 0
   ```

3. **Use Fixtures for Common Setup:**
   ```python
   @pytest.fixture
   def sample_event():
       return {
           "text": "Test event text",
           "source": "test",
           "location": "Maharashtra"
       }
   ```

4. **Mock External Dependencies:**
   ```python
   @patch('backend.satellite_client.requests.get')
   def test_satellite_validation(mock_get):
       mock_get.return_value.json.return_value = {"similarity": 0.8}
       # Test implementation
   ```

### Test Maintenance

1. **Regular Test Review:**
   - Remove obsolete tests
   - Update test data to reflect current requirements
   - Refactor duplicated test code

2. **Test Data Management:**
   - Keep test data minimal and focused
   - Use factories for generating test objects
   - Clean up test data after execution

3. **Performance Monitoring:**
   - Track test execution times
   - Identify and optimize slow tests
   - Parallelize independent tests

## Conclusion

This testing guide provides comprehensive coverage of all testing aspects for the misinformation heatmap system. Regular execution of these tests ensures system reliability, performance, and maintainability.

For questions or issues with testing, please refer to the troubleshooting section or contact the development team.