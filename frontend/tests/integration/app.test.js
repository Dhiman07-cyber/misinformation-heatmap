/**
 * Integration tests for main application functionality
 * Tests application initialization, state management, and component coordination
 */

describe('Application Integration Tests', () => {
  let app;
  let mockApiClient;
  let mockUIController;
  let mockHeatmapMap;

  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <div id="map" style="width: 800px; height: 600px;"></div>
      <div id="status-dot"></div>
      <div id="status-text">Connecting...</div>
      <div id="total-events">0</div>
      <div id="active-states">0</div>
      <div id="last-updated">-</div>
      <div id="avg-risk">-</div>
      <div id="data-freshness">Live</div>
      <div id="connection-quality">Excellent</div>
      <div id="refresh-indicator">30s</div>
      <div id="search-filter"></div>
      <div id="time-range"></div>
      <div id="category-filter"></div>
      <div id="intensity-threshold"></div>
      <div id="auto-refresh"></div>
    `;

    // Mock API client
    mockApiClient = {
      getHeatmapData: jest.fn(),
      getStateData: jest.fn(),
      testConnection: jest.fn(),
      addRequestInterceptor: jest.fn(),
      addResponseInterceptor: jest.fn()
    };

    // Mock UI controller
    mockUIController = {
      showLoading: jest.fn(),
      hideLoading: jest.fn(),
      showError: jest.fn(),
      showToast: jest.fn(),
      updateConnectionStatus: jest.fn(),
      updateStatistics: jest.fn(),
      showStateDetails: jest.fn(),
      onControlChange: null,
      onRetry: null,
      onSearch: null,
      onQuickActionClick: null
    };

    // Mock HeatmapMap
    mockHeatmapMap = {
      updateHeatmapData: jest.fn(),
      onStateClick: null,
      onMapReady: null,
      searchStates: jest.fn(),
      highlightStates: jest.fn(),
      clearSearchHighlights: jest.fn(),
      fitToState: jest.fn(),
      resetView: jest.fn(),
      destroy: jest.fn()
    };

    // Mock global objects
    global.APIClient = jest.fn(() => mockApiClient);
    global.UIController = jest.fn(() => mockUIController);
    global.HeatmapMap = jest.fn(() => mockHeatmapMap);

    // Mock Utils
    global.Utils = {
      dom: {
        addEventListener: jest.fn()
      },
      network: {
        setupConnectionListeners: jest.fn(),
        isOnline: jest.fn(() => true)
      },
      accessibility: {
        announce: jest.fn()
      },
      error: {
        getUserMessage: jest.fn(() => 'Test error message')
      }
    };

    // Mock window globals
    global.ui = mockUIController;
    global.api = mockApiClient;
  });

  afterEach(() => {
    if (app) {
      app.cleanup();
    }
    document.body.innerHTML = '';
    jest.clearAllMocks();
  });

  describe('Application Initialization', () => {
    test('should initialize all components successfully', async () => {
      mockApiClient.testConnection.mockResolvedValue({
        connected: true,
        responseTime: 100
      });

      mockApiClient.getHeatmapData.mockResolvedValue({
        states: {},
        total_events: 0,
        last_updated: '2025-10-26T06:00:00Z'
      });

      app = new HeatmapApp();
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(global.HeatmapMap).toHaveBeenCalledWith('map', expect.objectContaining({
        center: [20.5937, 78.9629],
        zoom: 5,
        minZoom: 4,
        maxZoom: 8
      }));

      expect(mockApiClient.testConnection).toHaveBeenCalled();
      expect(mockUIController.updateConnectionStatus).toHaveBeenCalledWith(true, 100);
    });

    test('should handle initialization errors gracefully', async () => {
      mockApiClient.testConnection.mockRejectedValue(new Error('Connection failed'));

      app = new HeatmapApp();
      
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockUIController.showError).toHaveBeenCalled();
    });

    test('should setup event handlers correctly', async () => {
      app = new HeatmapApp();
      
      expect(mockUIController.onControlChange).toBeDefined();
      expect(mockUIController.onRetry).toBeDefined();
      expect(mockUIController.onSearch).toBeDefined();
      expect(mockUIController.onQuickActionClick).toBeDefined();
    });
  });

  describe('Data Loading and Updates', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({
        connected: true,
        responseTime: 100
      });

      mockApiClient.getHeatmapData.mockResolvedValue({
        states: {
          'Maharashtra': {
            event_count: 5,
            misinformation_risk: 0.3,
            avg_virality_score: 0.6
          }
        },
        total_events: 5,
        last_updated: '2025-10-26T06:00:00Z'
      });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should load initial heatmap data', () => {
      expect(mockApiClient.getHeatmapData).toHaveBeenCalledWith(24);
      expect(mockHeatmapMap.updateHeatmapData).toHaveBeenCalled();
      expect(mockUIController.updateStatistics).toHaveBeenCalled();
    });

    test('should handle data refresh', async () => {
      await app.refreshData();

      expect(mockApiClient.getHeatmapData).toHaveBeenCalledTimes(2);
      expect(mockHeatmapMap.updateHeatmapData).toHaveBeenCalledTimes(2);
    });

    test('should detect significant data changes', () => {
      const oldData = {
        states: {
          'Maharashtra': { misinformation_risk: 0.2, event_count: 3 }
        }
      };

      const newData = {
        states: {
          'Maharashtra': { misinformation_risk: 0.4, event_count: 8 }
        }
      };

      const changes = app.detectDataChanges(oldData, newData);

      expect(changes.hasSignificantChanges).toBe(true);
      expect(changes.summary).toContain('5 new events');
    });

    test('should handle refresh failures with exponential backoff', async () => {
      mockApiClient.getHeatmapData.mockRejectedValue(new Error('API Error'));

      await app.refreshData();

      expect(app.state.refreshFailureCount).toBe(1);
      expect(mockUIController.showToast).toHaveBeenCalledWith(
        'Failed to update data',
        'error'
      );
    });
  });

  describe('Auto-refresh Functionality', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({
        states: {},
        total_events: 0
      });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should start auto-refresh by default', () => {
      expect(app.state.autoRefresh).toBe(true);
      expect(app.refreshTimer).toBeDefined();
    });

    test('should pause auto-refresh when tab is hidden', () => {
      const pauseSpy = jest.spyOn(app, 'pauseAutoRefresh');
      
      Object.defineProperty(document, 'hidden', {
        value: true,
        writable: true
      });

      document.dispatchEvent(new Event('visibilitychange'));

      expect(pauseSpy).toHaveBeenCalled();
    });

    test('should resume auto-refresh when tab becomes visible', () => {
      const resumeSpy = jest.spyOn(app, 'resumeAutoRefresh');
      
      Object.defineProperty(document, 'hidden', {
        value: false,
        writable: true
      });

      document.dispatchEvent(new Event('visibilitychange'));

      expect(resumeSpy).toHaveBeenCalled();
    });

    test('should respect network connectivity', () => {
      Utils.network.isOnline.mockReturnValue(false);
      
      // Auto-refresh should not trigger when offline
      app.startAutoRefresh();
      
      // Simulate timer tick
      jest.advanceTimersByTime(30000);
      
      expect(mockApiClient.getHeatmapData).not.toHaveBeenCalled();
    });
  });

  describe('State Interactions', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({ states: {}, total_events: 0 });
      mockApiClient.getStateData.mockResolvedValue({
        state_name: 'Maharashtra',
        event_count: 5,
        recent_claims: ['Test claim']
      });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should handle state click events', async () => {
      const mockFeature = { properties: { NAME_1: 'Maharashtra' } };
      const mockLayer = {};
      const mockEvent = {};

      await app.handleStateClick('Maharashtra', mockFeature, mockLayer, mockEvent);

      expect(mockUIController.showLoading).toHaveBeenCalledWith(
        'Loading details for Maharashtra...'
      );
      expect(mockApiClient.getStateData).toHaveBeenCalledWith('Maharashtra', 24);
      expect(mockUIController.showStateDetails).toHaveBeenCalled();
      expect(mockUIController.hideLoading).toHaveBeenCalled();
    });

    test('should handle state click errors', async () => {
      mockApiClient.getStateData.mockRejectedValue(new Error('API Error'));

      await app.handleStateClick('Maharashtra', {}, {}, {});

      expect(mockUIController.showToast).toHaveBeenCalledWith(
        'Failed to load data for Maharashtra',
        'error'
      );
    });
  });

  describe('Search Functionality', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({ states: {}, total_events: 0 });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should handle search queries', () => {
      mockHeatmapMap.searchStates.mockReturnValue(['Maharashtra', 'Madhya Pradesh']);

      app.handleSearch('maha');

      expect(mockHeatmapMap.searchStates).toHaveBeenCalledWith('maha');
      expect(mockHeatmapMap.highlightStates).toHaveBeenCalledWith(['Maharashtra', 'Madhya Pradesh']);
      expect(mockUIController.showToast).toHaveBeenCalledWith(
        'Found 2 matching states',
        'info',
        2000
      );
    });

    test('should focus on single search result', () => {
      mockHeatmapMap.searchStates.mockReturnValue(['Maharashtra']);
      const focusSpy = jest.spyOn(app, 'focusState');

      app.handleSearch('maharashtra');

      expect(focusSpy).toHaveBeenCalledWith('Maharashtra');
    });

    test('should handle no search results', () => {
      mockHeatmapMap.searchStates.mockReturnValue([]);

      app.handleSearch('nonexistent');

      expect(mockUIController.showToast).toHaveBeenCalledWith(
        'No matching states found',
        'warning',
        2000
      );
    });

    test('should clear search highlights', () => {
      app.handleSearch('');

      expect(mockHeatmapMap.clearSearchHighlights).toHaveBeenCalled();
    });
  });

  describe('Filter Management', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({
        states: {
          'Maharashtra': { misinformation_risk: 0.5, dominant_category: 'politics' },
          'Karnataka': { misinformation_risk: 0.2, dominant_category: 'health' }
        },
        total_events: 10
      });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should apply intensity threshold filter', () => {
      app.state.filters.intensityThreshold = 0.3;
      
      const filteredData = app.filterData(app.state.currentData);
      
      expect(filteredData.states).toHaveProperty('Maharashtra');
      expect(filteredData.states).not.toHaveProperty('Karnataka');
    });

    test('should apply category filter', () => {
      app.state.filters.category = 'politics';
      
      const filteredData = app.filterData(app.state.currentData);
      
      expect(filteredData.states).toHaveProperty('Maharashtra');
      expect(filteredData.states).not.toHaveProperty('Karnataka');
    });

    test('should handle time range changes', () => {
      app.handleControlChange('timeRange', 72);

      expect(app.state.filters.timeRange).toBe(72);
      expect(mockApiClient.getHeatmapData).toHaveBeenCalledWith(72);
    });

    test('should handle auto-refresh toggle', () => {
      const stopSpy = jest.spyOn(app, 'stopAutoRefresh');
      const startSpy = jest.spyOn(app, 'startAutoRefresh');

      app.handleControlChange('autoRefresh', false);
      expect(stopSpy).toHaveBeenCalled();

      app.handleControlChange('autoRefresh', true);
      expect(startSpy).toHaveBeenCalled();
    });
  });

  describe('Quick Actions', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({ states: {}, total_events: 0 });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should handle refresh action', () => {
      const refreshSpy = jest.spyOn(app, 'refreshData');

      app.handleQuickAction('refresh');

      expect(refreshSpy).toHaveBeenCalled();
    });

    test('should handle reset view action', () => {
      const resetSpy = jest.spyOn(app, 'resetMapView');

      app.handleQuickAction('resetView');

      expect(resetSpy).toHaveBeenCalled();
    });

    test('should handle export action', () => {
      const exportSpy = jest.spyOn(app, 'exportData');

      app.handleQuickAction('export');

      expect(exportSpy).toHaveBeenCalled();
    });

    test('should handle fullscreen action', () => {
      app.handleQuickAction('fullscreen');

      expect(mockUIController.toggleFullscreen).toHaveBeenCalled();
    });
  });

  describe('Connection Management', () => {
    beforeEach(async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({ states: {}, total_events: 0 });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    test('should monitor connection status', () => {
      expect(app.connectionCheckTimer).toBeDefined();
    });

    test('should handle connection restored', () => {
      const refreshSpy = jest.spyOn(app, 'refreshData');

      app.handleConnectionRestored();

      expect(mockUIController.showToast).toHaveBeenCalledWith(
        'Connection restored',
        'success'
      );
      expect(refreshSpy).toHaveBeenCalled();
    });

    test('should handle connection lost', () => {
      app.handleConnectionLost();

      expect(mockUIController.showToast).toHaveBeenCalledWith(
        'Connection lost. Retrying...',
        'warning'
      );
      expect(mockUIController.updateConnectionStatus).toHaveBeenCalledWith(false);
    });
  });

  describe('Cleanup and Memory Management', () => {
    test('should cleanup resources properly', async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({ states: {}, total_events: 0 });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));

      app.cleanup();

      expect(app.refreshTimer).toBeNull();
      expect(mockHeatmapMap.destroy).toHaveBeenCalled();
    });

    test('should handle window beforeunload', async () => {
      mockApiClient.testConnection.mockResolvedValue({ connected: true });
      mockApiClient.getHeatmapData.mockResolvedValue({ states: {}, total_events: 0 });

      app = new HeatmapApp();
      await new Promise(resolve => setTimeout(resolve, 100));

      const cleanupSpy = jest.spyOn(app, 'cleanup');

      window.dispatchEvent(new Event('beforeunload'));

      expect(cleanupSpy).toHaveBeenCalled();
    });
  });
});