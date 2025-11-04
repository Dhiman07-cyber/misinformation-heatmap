/**
 * API client for the misinformation heatmap application
 * Handles all communication with the backend REST API
 * Provides error handling, retry logic, and response caching
 */

class APIClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL || this.detectBaseURL();
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    this.retryAttempts = 3;
    this.retryDelay = 1000; // 1 second
    
    // Request interceptors
    this.requestInterceptors = [];
    this.responseInterceptors = [];
    
    // Setup default error handling
    this.setupDefaultErrorHandling();
  }

  /**
   * Auto-detect base URL based on current location
   */
  detectBaseURL() {
    const { protocol, hostname, port } = window.location;
    
    // In development, assume backend runs on port 8000
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `${protocol}//${hostname}:8000`;
    }
    
    // In production, assume same origin
    return '';
  }

  /**
   * Setup default error handling
   */
  setupDefaultErrorHandling() {
    this.addResponseInterceptor(
      (response) => response,
      (error) => {
        Utils.error.log(error, 'API Request');
        throw error;
      }
    );
  }

  /**
   * Add request interceptor
   */
  addRequestInterceptor(onFulfilled, onRejected) {
    this.requestInterceptors.push({ onFulfilled, onRejected });
  }

  /**
   * Add response interceptor
   */
  addResponseInterceptor(onFulfilled, onRejected) {
    this.responseInterceptors.push({ onFulfilled, onRejected });
  }

  /**
   * Apply request interceptors
   */
  async applyRequestInterceptors(config) {
    let result = config;
    
    for (const interceptor of this.requestInterceptors) {
      try {
        if (interceptor.onFulfilled) {
          result = await interceptor.onFulfilled(result);
        }
      } catch (error) {
        if (interceptor.onRejected) {
          result = await interceptor.onRejected(error);
        } else {
          throw error;
        }
      }
    }
    
    return result;
  }

  /**
   * Apply response interceptors
   */
  async applyResponseInterceptors(response) {
    let result = response;
    
    for (const interceptor of this.responseInterceptors) {
      try {
        if (interceptor.onFulfilled) {
          result = await interceptor.onFulfilled(result);
        }
      } catch (error) {
        if (interceptor.onRejected) {
          result = await interceptor.onRejected(error);
        } else {
          throw error;
        }
      }
    }
    
    return result;
  }

  /**
   * Generate cache key for request
   */
  getCacheKey(url, options = {}) {
    const method = options.method || 'GET';
    const body = options.body || '';
    return `${method}:${url}:${body}`;
  }

  /**
   * Check if cached response is valid
   */
  isCacheValid(cacheEntry) {
    return Date.now() - cacheEntry.timestamp < this.cacheTimeout;
  }

  /**
   * Get cached response
   */
  getCachedResponse(cacheKey) {
    const cacheEntry = this.cache.get(cacheKey);
    if (cacheEntry && this.isCacheValid(cacheEntry)) {
      return cacheEntry.data;
    }
    return null;
  }

  /**
   * Cache response
   */
  setCachedResponse(cacheKey, data) {
    this.cache.set(cacheKey, {
      data: data,
      timestamp: Date.now()
    });
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Sleep for retry delay
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Make HTTP request with retry logic
   */
  async makeRequest(url, options = {}) {
    const fullURL = url.startsWith('http') ? url : `${this.baseURL}${url}`;
    
    // Apply request interceptors
    const config = await this.applyRequestInterceptors({
      url: fullURL,
      ...options
    });

    // Check cache for GET requests
    const cacheKey = this.getCacheKey(config.url, config);
    if (config.method === 'GET' || !config.method) {
      const cachedResponse = this.getCachedResponse(cacheKey);
      if (cachedResponse) {
        return cachedResponse;
      }
    }

    let lastError;
    
    for (let attempt = 1; attempt <= this.retryAttempts; attempt++) {
      try {
        const response = await fetch(config.url, {
          method: config.method || 'GET',
          headers: {
            'Content-Type': 'application/json',
            ...config.headers
          },
          body: config.body,
          ...config
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const error = new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
          error.status = response.status;
          error.statusText = response.statusText;
          error.data = errorData;
          throw error;
        }

        const data = await response.json();
        
        // Apply response interceptors
        const processedData = await this.applyResponseInterceptors(data);
        
        // Cache successful GET responses
        if (config.method === 'GET' || !config.method) {
          this.setCachedResponse(cacheKey, processedData);
        }
        
        return processedData;
        
      } catch (error) {
        lastError = error;
        
        // Don't retry for certain error types
        if (error.status === 400 || error.status === 401 || error.status === 403 || error.status === 404) {
          break;
        }
        
        // Don't retry on last attempt
        if (attempt === this.retryAttempts) {
          break;
        }
        
        // Wait before retry
        await this.sleep(this.retryDelay * attempt);
      }
    }
    
    throw lastError;
  }

  /**
   * GET request
   */
  async get(url, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const fullURL = queryString ? `${url}?${queryString}` : url;
    
    return this.makeRequest(fullURL, {
      method: 'GET'
    });
  }

  /**
   * POST request
   */
  async post(url, data = {}) {
    return this.makeRequest(url, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  /**
   * PUT request
   */
  async put(url, data = {}) {
    return this.makeRequest(url, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  /**
   * DELETE request
   */
  async delete(url) {
    return this.makeRequest(url, {
      method: 'DELETE'
    });
  }

  /**
   * API Methods for Heatmap Application
   */

  /**
   * Get heatmap data for all Indian states
   */
  async getHeatmapData(hoursBack = 24) {
    try {
      const params = { hours_back: hoursBack };
      return await this.get('/heatmap', params);
    } catch (error) {
      console.error('Failed to fetch heatmap data:', error);
      throw new Error('Unable to load heatmap data. Please try again.');
    }
  }

  /**
   * Get detailed data for a specific state
   */
  async getStateData(stateName, hoursBack = 24, limit = 50) {
    try {
      const params = { hours_back: hoursBack, limit };
      return await this.get(`/region/${encodeURIComponent(stateName)}`, params);
    } catch (error) {
      console.error(`Failed to fetch data for ${stateName}:`, error);
      throw new Error(`Unable to load data for ${stateName}. Please try again.`);
    }
  }

  /**
   * Get state rankings by metric
   */
  async getStateRankings(metric = 'misinformation_risk', hoursBack = 24) {
    try {
      const params = { metric, hours_back: hoursBack };
      return await this.get('/rankings', params);
    } catch (error) {
      console.error('Failed to fetch state rankings:', error);
      throw new Error('Unable to load state rankings. Please try again.');
    }
  }

  /**
   * Get temporal analysis for a state
   */
  async getTemporalAnalysis(stateName, daysBack = 7) {
    try {
      const params = { days_back: daysBack };
      return await this.get(`/temporal/${encodeURIComponent(stateName)}`, params);
    } catch (error) {
      console.error(`Failed to fetch temporal analysis for ${stateName}:`, error);
      throw new Error(`Unable to load temporal analysis for ${stateName}. Please try again.`);
    }
  }

  /**
   * Submit test data (for development/testing)
   */
  async submitTestData(testData) {
    try {
      return await this.post('/ingest/test', testData);
    } catch (error) {
      console.error('Failed to submit test data:', error);
      throw new Error('Unable to submit test data. Please try again.');
    }
  }

  /**
   * Get system health status
   */
  async getHealthStatus() {
    try {
      return await this.get('/health');
    } catch (error) {
      console.error('Failed to fetch health status:', error);
      throw new Error('Unable to check system health. Please try again.');
    }
  }

  /**
   * Get API statistics
   */
  async getStatistics() {
    try {
      return await this.get('/stats');
    } catch (error) {
      console.error('Failed to fetch statistics:', error);
      throw new Error('Unable to load statistics. Please try again.');
    }
  }

  /**
   * Search for events by text
   */
  async searchEvents(query, hoursBack = 24, limit = 50) {
    try {
      const params = { q: query, hours_back: hoursBack, limit };
      return await this.get('/search', params);
    } catch (error) {
      console.error('Failed to search events:', error);
      throw new Error('Unable to search events. Please try again.');
    }
  }

  /**
   * Get events by category
   */
  async getEventsByCategory(category, hoursBack = 24, limit = 50) {
    try {
      const params = { category, hours_back: hoursBack, limit };
      return await this.get('/events/category', params);
    } catch (error) {
      console.error(`Failed to fetch events for category ${category}:`, error);
      throw new Error(`Unable to load events for category ${category}. Please try again.`);
    }
  }

  /**
   * Utility Methods
   */

  /**
   * Test API connectivity
   */
  async testConnection() {
    try {
      const startTime = Date.now();
      await this.getHealthStatus();
      const endTime = Date.now();
      
      return {
        connected: true,
        responseTime: endTime - startTime,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        connected: false,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Get cache statistics
   */
  getCacheStats() {
    const entries = Array.from(this.cache.entries());
    const validEntries = entries.filter(([key, entry]) => this.isCacheValid(entry));
    
    return {
      totalEntries: entries.length,
      validEntries: validEntries.length,
      cacheHitRate: entries.length > 0 ? (validEntries.length / entries.length) * 100 : 0,
      oldestEntry: entries.length > 0 ? Math.min(...entries.map(([key, entry]) => entry.timestamp)) : null,
      newestEntry: entries.length > 0 ? Math.max(...entries.map(([key, entry]) => entry.timestamp)) : null
    };
  }

  /**
   * Set cache timeout
   */
  setCacheTimeout(timeoutMs) {
    this.cacheTimeout = timeoutMs;
  }

  /**
   * Set retry configuration
   */
  setRetryConfig(attempts, delay) {
    this.retryAttempts = attempts;
    this.retryDelay = delay;
  }
}

// Create global API client instance
const api = new APIClient();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { APIClient, api };
} else {
  window.APIClient = APIClient;
  window.api = api;
}