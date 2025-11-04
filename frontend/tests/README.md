# Frontend Integration Tests

Comprehensive integration tests for the India Misinformation Heatmap frontend application.

## Overview

This test suite validates the functionality, performance, and user experience of the frontend application across different scenarios and device types. The tests ensure that all components work together correctly and provide a reliable user experience.

## Test Structure

```
frontend/tests/
├── integration/           # Integration test files
│   ├── app.test.js       # Main application tests
│   ├── api.test.js       # API client tests
│   ├── map.test.js       # Map functionality tests
│   └── responsive.test.js # Responsive design tests
├── __mocks__/            # Mock files
│   └── fileMock.js       # Static file mocks
├── coverage/             # Coverage reports (generated)
├── jest.config.js        # Jest configuration
├── package.json          # Test dependencies
├── setup.js              # Test setup and mocks
├── run-tests.sh          # Test runner (Unix/Linux)
├── run-tests.ps1         # Test runner (Windows)
└── README.md             # This file
```

## Test Categories

### 1. Map Integration Tests (`map.test.js`)

Tests the Leaflet.js map functionality including:

- **Map Initialization**
  - Correct center and zoom for India
  - India boundary constraints
  - GeoJSON data loading
  - Error handling for failed data loading

- **State Interactions**
  - State click event handling
  - Heatmap data updates
  - State search functionality
  - Search result highlighting

- **Data Visualization**
  - Color coding based on intensity
  - Tooltip generation
  - Handling states with no data

- **Performance & Memory**
  - Resource cleanup
  - Rapid data update handling

- **Accessibility**
  - ARIA labels and roles
  - Screen reader announcements

### 2. API Integration Tests (`api.test.js`)

Tests the API client functionality including:

- **Client Initialization**
  - Base URL configuration
  - Environment detection (dev/prod)

- **Data Fetching**
  - Heatmap data retrieval
  - State-specific data fetching
  - Error handling and retry logic
  - Request/response interceptors

- **Caching Mechanism**
  - GET request caching
  - Cache expiration
  - Manual cache clearing

- **Connection Testing**
  - Connection status monitoring
  - Failure detection and reporting

- **Test Data Submission**
  - Manual data injection
  - Validation error handling

### 3. Responsive Design Tests (`responsive.test.js`)

Tests the application across different screen sizes:

- **Mobile Layout (≤ 768px)**
  - Touch-friendly controls
  - Vertical button stacking
  - Full-width modals
  - iOS zoom prevention

- **Tablet Layout (769px - 1024px)**
  - Medium control panel width
  - 2-column grid layouts
  - Readable modal widths

- **Desktop Layout (≥ 1200px)**
  - Full control panel width
  - Centered content with max-width
  - Optimal modal sizing

- **Orientation Changes**
  - Portrait to landscape transitions
  - Maintained functionality

- **Touch Interactions**
  - Touch event handling
  - Adequate touch target sizes

- **Accessibility**
  - Focus visibility across sizes
  - Keyboard navigation on mobile

### 4. Application Integration Tests (`app.test.js`)

Tests the main application coordination:

- **Application Initialization**
  - Component initialization
  - Error handling
  - Event handler setup

- **Data Management**
  - Initial data loading
  - Data refresh functionality
  - Change detection
  - Failure handling with backoff

- **Auto-refresh**
  - Timer management
  - Tab visibility handling
  - Network connectivity awareness

- **User Interactions**
  - State click handling
  - Search functionality
  - Filter management
  - Quick actions

- **Connection Management**
  - Status monitoring
  - Connection restoration
  - Disconnection handling

## Running Tests

### Prerequisites

- Node.js (v14 or higher)
- npm (v6 or higher)

### Installation

```bash
cd frontend/tests
npm install
```

### Running All Tests

**Unix/Linux/macOS:**
```bash
./run-tests.sh
```

**Windows:**
```powershell
.\run-tests.ps1
```

### Running Specific Test Suites

**Map tests only:**
```bash
./run-tests.sh map
# or
.\run-tests.ps1 map
```

**API tests only:**
```bash
./run-tests.sh api
```

**Responsive design tests:**
```bash
./run-tests.sh responsive
```

**Application tests:**
```bash
./run-tests.sh app
```

### Coverage Reports

**Generate coverage report:**
```bash
./run-tests.sh coverage
```

Coverage reports are generated in the `coverage/` directory and include:
- HTML report: `coverage/lcov-report/index.html`
- LCOV format: `coverage/lcov.info`
- Text summary in console

### Watch Mode

**Run tests in watch mode (auto-rerun on changes):**
```bash
./run-tests.sh watch
```

### CI Mode

**Run tests in continuous integration mode:**
```bash
./run-tests.sh ci
```

## Test Configuration

### Coverage Thresholds

The tests maintain minimum coverage requirements:
- **Branches:** 70%
- **Functions:** 70%
- **Lines:** 70%
- **Statements:** 70%

### Timeout Settings

- **Default test timeout:** 10 seconds
- **Async operation timeout:** 5 seconds
- **Network request timeout:** 3 seconds

## Mocking Strategy

### Global Mocks

- **Leaflet.js:** Complete mock of map functionality
- **Fetch API:** Configurable response mocking
- **LocalStorage/SessionStorage:** In-memory implementations
- **DOM APIs:** ResizeObserver, IntersectionObserver, etc.
- **Browser APIs:** Geolocation, Fullscreen, etc.

### Test Utilities

The test suite includes utilities for:
- **Event simulation:** User interactions and browser events
- **DOM manipulation:** Element creation and modification
- **API mocking:** Response and error simulation
- **Timing control:** Async operation testing

## Best Practices

### Writing Tests

1. **Descriptive test names:** Use clear, specific descriptions
2. **Arrange-Act-Assert:** Structure tests clearly
3. **Mock external dependencies:** Isolate units under test
4. **Test error conditions:** Include failure scenarios
5. **Clean up resources:** Prevent test interference

### Performance Considerations

1. **Minimize DOM operations:** Use efficient selectors
2. **Mock heavy operations:** Avoid actual network calls
3. **Parallel execution:** Tests run independently
4. **Resource cleanup:** Prevent memory leaks

### Accessibility Testing

1. **ARIA attributes:** Verify proper labeling
2. **Keyboard navigation:** Test tab order and shortcuts
3. **Screen reader support:** Validate announcements
4. **Focus management:** Ensure visible focus indicators

## Debugging Tests

### Common Issues

1. **Timing issues:** Use proper async/await patterns
2. **Mock conflicts:** Ensure mocks are reset between tests
3. **DOM state:** Clean up DOM after each test
4. **Event handlers:** Remove listeners to prevent leaks

### Debug Mode

**Run tests with debugger:**
```bash
npm run test:debug
```

This starts tests with Node.js inspector for step-through debugging.

### Verbose Output

**Enable detailed test output:**
```bash
npm test -- --verbose
```

## Continuous Integration

### GitHub Actions

Example workflow configuration:

```yaml
name: Frontend Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '16'
      - run: cd frontend/tests && npm install
      - run: cd frontend/tests && npm run test:ci
      - uses: codecov/codecov-action@v1
        with:
          file: ./frontend/tests/coverage/lcov.info
```

## Maintenance

### Updating Tests

When adding new features:
1. Add corresponding test cases
2. Update mocks if needed
3. Maintain coverage thresholds
4. Update documentation

### Dependencies

Keep test dependencies updated:
```bash
npm audit
npm update
```

## Troubleshooting

### Common Errors

**"Cannot find module" errors:**
- Check file paths in test imports
- Verify mock configurations

**"ReferenceError: X is not defined":**
- Add missing global mocks in setup.js
- Check for browser API usage

**Timeout errors:**
- Increase timeout for slow operations
- Check for unresolved promises

**Coverage threshold failures:**
- Add tests for uncovered code paths
- Review and adjust thresholds if needed

### Getting Help

1. Check test output for specific error messages
2. Review Jest documentation for configuration issues
3. Verify mock implementations match actual APIs
4. Use debug mode for step-through investigation

## Performance Benchmarks

The test suite includes performance validation:

- **Map rendering:** < 2 seconds initial load
- **API responses:** < 200ms for cached requests
- **State interactions:** < 100ms response time
- **Search functionality:** < 50ms for local filtering

These benchmarks ensure the application meets performance requirements across different scenarios and device capabilities.