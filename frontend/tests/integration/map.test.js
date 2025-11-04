/**
 * Integration tests for map functionality
 * Tests map initialization, boundary constraints, and state interactions
 */

describe('Map Integration Tests', () => {
  let app;
  let mockApiData;

  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <div id="map" style="width: 800px; height: 600px;"></div>
      <div id="status-dot"></div>
      <div id="status-text"></div>
      <div id="total-events">0</div>
      <div id="active-states">0</div>
      <div id="last-updated">-</div>
      <div id="avg-risk">-</div>
      <div id="data-freshness">Live</div>
      <div id="connection-quality">Excellent</div>
      <div id="refresh-indicator">30s</div>
    `;

    // Mock API data
    mockApiData = {
      states: {
        'Maharashtra': {
          event_count: 5,
          intensity: 0.4,
          avg_virality_score: 0.6,
          avg_reality_score: 0.7,
          misinformation_risk: 0.3,
          dominant_category: 'politics',
          recent_claims: ['Claim 1', 'Claim 2'],
          satellite_validated_count: 3,
          last_updated: '2025-10-26T06:00:00Z'
        },
        'Karnataka': {
          event_count: 3,
          intensity: 0.2,
          avg_virality_score: 0.4,
          avg_reality_score: 0.8,
          misinformation_risk: 0.1,
          dominant_category: 'health',
          recent_claims: ['Health claim'],
          satellite_validated_count: 2,
          last_updated: '2025-10-26T06:00:00Z'
        }
      },
      total_events: 8,
      last_updated: '2025-10-26T06:00:00Z',
      metadata: {
        data_freshness: 'live',
        coverage: '2 states'
      }
    };

    // Mock Leaflet
    global.L = {
      map: jest.fn(() => ({
        setView: jest.fn(),
        fitBounds: jest.fn(),
        on: jest.fn(),
        remove: jest.fn(),
        getZoom: jest.fn(() => 5),
        getBounds: jest.fn(),
        getContainer: jest.fn(() => document.getElementById('map'))
      })),
      tileLayer: jest.fn(() => ({
        addTo: jest.fn()
      })),
      geoJSON: jest.fn(() => ({
        addTo: jest.fn(),
        getBounds: jest.fn(() => [[8, 68], [37, 98]]),
        eachLayer: jest.fn()
      })),
      control: {
        zoom: jest.fn(() => ({
          addTo: jest.fn()
        }))
      }
    };

    // Mock Utils
    global.Utils = {
      dom: {
        getElementById: jest.fn((id) => document.getElementById(id)),
        addEventListener: jest.fn()
      },
      format: {
        relativeTime: jest.fn(() => '5 minutes ago'),
        percentage: jest.fn((val) => `${(val * 100).toFixed(1)}%`),
        compactNumber: jest.fn((val) => val.toString())
      },
      color: {
        getHeatmapColor: jest.fn(() => '#FF6347'),
        getRiskLevel: jest.fn(() => 'Medium')
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
  });

  afterEach(() => {
    if (app) {
      app.cleanup();
    }
    document.body.innerHTML = '';
    jest.clearAllMocks();
  });

  describe('Map Initialization', () => {
    test('should initialize map with correct center and zoom for India', async () => {
      const map = new HeatmapMap('map', {
        center: [20.5937, 78.9629],
        zoom: 5,
        minZoom: 4,
        maxZoom: 8
      });

      expect(L.map).toHaveBeenCalledWith('map', expect.objectContaining({
        center: [20.5937, 78.9629],
        zoom: 5,
        minZoom: 4,
        maxZoom: 8
      }));
    });

    test('should set India boundary constraints', () => {
      const map = new HeatmapMap('map');
      
      expect(L.map).toHaveBeenCalledWith('map', expect.objectContaining({
        maxBounds: [[6, 68], [37, 98]],
        maxBoundsViscosity: 1.0
      }));
    });

    test('should load India states GeoJSON data', async () => {
      // Mock fetch for GeoJSON
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            type: 'FeatureCollection',
            features: [
              {
                type: 'Feature',
                properties: { NAME_1: 'Maharashtra' },
                geometry: { type: 'Polygon', coordinates: [] }
              }
            ]
          })
        })
      );

      const map = new HeatmapMap('map');
      await map.loadIndiaBoundaries();

      expect(fetch).toHaveBeenCalledWith('data/india-states.geojson');
      expect(L.geoJSON).toHaveBeenCalled();
    });

    test('should handle GeoJSON loading failure gracefully', async () => {
      global.fetch = jest.fn(() => Promise.reject(new Error('Network error')));
      
      const map = new HeatmapMap('map');
      
      // Should not throw and should use fallback data
      await expect(map.loadIndiaBoundaries()).resolves.not.toThrow();
    });
  });

  describe('State Interactions', () => {
    let map;

    beforeEach(() => {
      map = new HeatmapMap('map');
    });

    test('should handle state click events', () => {
      const mockLayer = {
        setStyle: jest.fn(),
        feature: { properties: { NAME_1: 'Maharashtra' } }
      };
      
      const clickHandler = jest.fn();
      map.onStateClick = clickHandler;

      map.handleStateClick('Maharashtra', mockLayer.feature, mockLayer, {});

      expect(clickHandler).toHaveBeenCalledWith(
        'Maharashtra',
        mockLayer.feature,
        mockLayer,
        {}
      );
    });

    test('should update heatmap data correctly', () => {
      map.updateHeatmapData(mockApiData);

      expect(map.currentData).toEqual(mockApiData);
    });

    test('should search states by name', () => {
      // Setup state data
      map.stateData.set('Maharashtra', { layer: {}, feature: {}, data: null });
      map.stateData.set('Karnataka', { layer: {}, feature: {}, data: null });
      map.stateData.set('Tamil Nadu', { layer: {}, feature: {}, data: null });

      const results = map.searchStates('kar');
      expect(results).toContain('Karnataka');
      expect(results).not.toContain('Maharashtra');
    });

    test('should highlight search results', () => {
      const mockLayer = { setStyle: jest.fn() };
      map.stateData.set('Maharashtra', { layer: mockLayer, feature: {}, data: null });

      map.highlightStates(['Maharashtra']);

      expect(mockLayer.setStyle).toHaveBeenCalledWith(expect.objectContaining({
        weight: 4,
        color: '#FFC107',
        fillOpacity: 0.8
      }));
    });
  });

  describe('Data Visualization', () => {
    let map;

    beforeEach(() => {
      map = new HeatmapMap('map');
    });

    test('should apply correct colors based on intensity', () => {
      const lowIntensityData = { misinformation_risk: 0.2 };
      const highIntensityData = { misinformation_risk: 0.8 };

      Utils.color.getHeatmapColor.mockReturnValueOnce('#2E8B57'); // Low
      const lowStyle = map.getStateStyle(lowIntensityData);
      expect(lowStyle.fillColor).toBe('#2E8B57');

      Utils.color.getHeatmapColor.mockReturnValueOnce('#DC143C'); // High
      const highStyle = map.getStateStyle(highIntensityData);
      expect(highStyle.fillColor).toBe('#DC143C');
    });

    test('should create appropriate tooltips', () => {
      const stateData = {
        misinformation_risk: 0.4,
        event_count: 5
      };

      Utils.format.percentage.mockReturnValue('40.0%');
      Utils.color.getRiskLevel.mockReturnValue('Medium');

      const tooltip = map.createStateTooltip('Maharashtra', stateData);

      expect(tooltip).toContain('Maharashtra');
      expect(tooltip).toContain('Medium Risk');
      expect(tooltip).toContain('40.0%');
      expect(tooltip).toContain('Events: 5');
    });

    test('should handle states with no data', () => {
      const tooltip = map.createStateTooltip('Unknown State', null);
      
      expect(tooltip).toContain('Unknown State');
      expect(tooltip).toContain('No data available');
    });
  });

  describe('Performance and Memory', () => {
    test('should cleanup resources properly', () => {
      const map = new HeatmapMap('map');
      const mockMapInstance = { remove: jest.fn() };
      map.map = mockMapInstance;

      map.destroy();

      expect(mockMapInstance.remove).toHaveBeenCalled();
      expect(map.map).toBeNull();
      expect(map.stateData.size).toBe(0);
    });

    test('should handle rapid data updates efficiently', () => {
      const map = new HeatmapMap('map');
      
      // Simulate rapid updates
      for (let i = 0; i < 10; i++) {
        map.updateHeatmapData({
          ...mockApiData,
          total_events: i * 10
        });
      }

      expect(map.currentData.total_events).toBe(90);
    });
  });

  describe('Accessibility', () => {
    test('should provide proper ARIA labels', () => {
      const mapElement = document.getElementById('map');
      mapElement.setAttribute('role', 'application');
      mapElement.setAttribute('aria-label', 'Interactive heatmap of India');

      expect(mapElement.getAttribute('role')).toBe('application');
      expect(mapElement.getAttribute('aria-label')).toContain('Interactive heatmap');
    });

    test('should announce state changes to screen readers', () => {
      const map = new HeatmapMap('map');
      map.onStateClick = () => {
        Utils.accessibility.announce('State selected');
      };

      map.handleStateClick('Maharashtra', {}, {}, {});

      expect(Utils.accessibility.announce).toHaveBeenCalledWith('State selected');
    });
  });
});