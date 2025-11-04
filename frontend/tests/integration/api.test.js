/**
 * Integration tests for API functionality
 * Tests API client, data fetching, error handling, and caching
 */

describe('API Integration Tests', () => {
  let apiClient;
  let mockFetch;

  beforeEach(() => {
    // Mock fetch
    mockFetch = jest.fn();
    global.fetch = mockFetch;

    // Mock Utils
    global.Utils = {
      error: {
        log: jest.fn()
      }
    };

    // Initialize API client
    apiClient = new APIClient('http://localhost:8000');
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('API Client Initialization', () => {
    test('should initialize with correct base URL', () => {
      expect(apiClient.baseURL).toBe('http://localhost:8000');
    });

    test('should auto-detect base URL in development', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'http:',
          hostname: 'localhost',
          port: '3000'
        },
        writable: true
      });

      const client = new APIClient();
      expect(client.baseURL).toBe('http://localhost:8000');
    });

    test('should use same origin in production', () => {
      Object.defineProperty(window, 'location', {
        value: {
          protocol: 'https:',
          hostname: 'example.com',
          port: ''
        },
        writable: true
      });

      const client = new APIClient();
      expect(client.baseURL).toBe('');
    });
  });

  describe('Heatmap Data API', () => {
    const mockHeatmapData = {
      states: {
        'Maharashtra': {
          event_count: 5,
          misinformation_risk: 0.3,
          avg_virality_score: 0.6,
          avg_reality_score: 0.7
        }
      },
      total_events: 5,
      last_updated: '2025-10-26T06:00:00Z'
    };

    test('should fetch heatmap data successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHeatmapData)
      });

      const data = await apiClient.getHeatmapData(24);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/heatmap?hours_back=24',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );

      expect(data).toEqual(mockHeatmapData);
    });

    test('should handle API errors gracefully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ message: 'Server error' })
      });

      await expect(apiClient.getHeatmapData(24)).rejects.toThrow('Server error');
    });

    test('should retry failed requests', async () => {
      // First two calls fail, third succeeds
      mockFetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockHeatmapData)
        });

      const data = await apiClient.getHeatmapData(24);

      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(data).toEqual(mockHeatmapData);
    });

    test('should not retry 4xx errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({ message: 'Not found' })
      });

      await expect(apiClient.getHeatmapData(24)).rejects.toThrow('Not found');
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('State Data API', () => {
    const mockStateData = {
      state_name: 'Maharashtra',
      event_count: 5,
      misinformation_risk: 0.3,
      recent_claims: ['Claim 1', 'Claim 2'],
      timeline: []
    };

    test('should fetch state data with proper encoding', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStateData)
      });

      const data = await apiClient.getStateData('Tamil Nadu', 24, 50);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/region/Tamil%20Nadu?hours_back=24&limit=50',
        expect.any(Object)
      );

      expect(data).toEqual(mockStateData);
    });

    test('should handle special characters in state names', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStateData)
      });

      await apiClient.getStateData('Jammu & Kashmir', 24);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('Jammu%20%26%20Kashmir'),
        expect.any(Object)
      );
    });
  });

  describe('Caching Mechanism', () => {
    const mockData = { test: 'data' };

    test('should cache GET requests', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData)
      });

      // First request
      await apiClient.get('/test');
      // Second request (should use cache)
      await apiClient.get('/test');

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    test('should not cache non-GET requests', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData)
      });

      await apiClient.post('/test', { data: 'test' });
      await apiClient.post('/test', { data: 'test' });

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    test('should expire cache after timeout', async () => {
      // Set short cache timeout for testing
      apiClient.setCacheTimeout(100);

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData)
      });

      await apiClient.get('/test');
      
      // Wait for cache to expire
      await new Promise(resolve => setTimeout(resolve, 150));
      
      await apiClient.get('/test');

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    test('should clear cache manually', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData)
      });

      await apiClient.get('/test');
      apiClient.clearCache();
      await apiClient.get('/test');

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Connection Testing', () => {
    test('should test connection successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' })
      });

      const result = await apiClient.testConnection();

      expect(result.connected).toBe(true);
      expect(result.responseTime).toBeGreaterThan(0);
      expect(result.timestamp).toBeDefined();
    });

    test('should handle connection failures', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await apiClient.testConnection();

      expect(result.connected).toBe(false);
      expect(result.error).toBe('Network error');
      expect(result.timestamp).toBeDefined();
    });
  });

  describe('Test Data Submission', () => {
    test('should submit test data successfully', async () => {
      const testData = {
        text: 'Test misinformation content',
        source: 'manual',
        location: 'Maharashtra'
      };

      const mockResponse = {
        event_id: 'test-123',
        status: 'processed'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      });

      const result = await apiClient.submitTestData(testData);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/ingest/test',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(testData)
        })
      );

      expect(result).toEqual(mockResponse);
    });

    test('should handle validation errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: () => Promise.resolve({
          detail: [{ msg: 'Text too short' }]
        })
      });

      await expect(apiClient.submitTestData({ text: 'short' }))
        .rejects.toThrow();
    });
  });

  describe('Request Interceptors', () => {
    test('should apply request interceptors', async () => {
      const interceptor = jest.fn((config) => ({
        ...config,
        headers: { ...config.headers, 'X-Custom': 'test' }
      }));

      apiClient.addRequestInterceptor(interceptor);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({})
      });

      await apiClient.get('/test');

      expect(interceptor).toHaveBeenCalled();
    });

    test('should apply response interceptors', async () => {
      const interceptor = jest.fn((data) => ({ ...data, processed: true }));

      apiClient.addResponseInterceptor(interceptor);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ original: true })
      });

      const result = await apiClient.get('/test');

      expect(interceptor).toHaveBeenCalled();
      expect(result.processed).toBe(true);
    });
  });

  describe('Error Handling', () => {
    test('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Failed to fetch'));

      await expect(apiClient.get('/test')).rejects.toThrow('Failed to fetch');
      expect(Utils.error.log).toHaveBeenCalled();
    });

    test('should handle JSON parsing errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON'))
      });

      await expect(apiClient.get('/test')).rejects.toThrow('Invalid JSON');
    });

    test('should provide user-friendly error messages', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({})
      });

      await expect(apiClient.getHeatmapData(24))
        .rejects.toThrow('Unable to load heatmap data');
    });
  });

  describe('Performance', () => {
    test('should handle concurrent requests efficiently', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ data: 'test' })
      });

      const requests = Array(10).fill().map((_, i) => 
        apiClient.get(`/test${i}`)
      );

      const results = await Promise.all(requests);

      expect(results).toHaveLength(10);
      expect(mockFetch).toHaveBeenCalledTimes(10);
    });

    test('should provide cache statistics', () => {
      const stats = apiClient.getCacheStats();

      expect(stats).toHaveProperty('totalEntries');
      expect(stats).toHaveProperty('validEntries');
      expect(stats).toHaveProperty('cacheHitRate');
    });
  });
});