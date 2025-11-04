/**
 * Main application controller for the misinformation heatmap
 * Coordinates between the map, API, and UI components
 * Handles real-time data updates and user interactions
 */

class HeatmapApp {
  constructor() {
    this.map = null;
    this.ui = null;
    this.api = null;
    
    // Application state
    this.state = {
      currentData: null,
      filters: {
        timeRange: 24,
        category: 'all',
        intensityThreshold: 0.0
      },
      autoRefresh: true,
      refreshInterval: 30000, // 30 seconds
      isLoading: false,
      lastUpdate: null
    };
    
    // Timers
    this.refreshTimer = null;
    this.connectionCheckTimer = null;
    this.countdownTimer = null;
    
    // Initialize application
    this.init();
  }

  /**
   * Initialize the application
   */
  async init() {
    try {
      console.log('Initializing Misinformation Heatmap Application...');
      
      // Wait for DOM to be ready
      if (document.readyState === 'loading') {
        await new Promise(resolve => {
          document.addEventListener('DOMContentLoaded', resolve);
        });
      }
      
      // Initialize components
      await this.initializeComponents();
      
      // Setup event handlers
      this.setupEventHandlers();
      
      // Load initial data
      await this.loadInitialData();
      
      // Start auto-refresh if enabled
      this.startAutoRefresh();
      
      // Start connection monitoring
      this.startConnectionMonitoring();
      
      console.log('Application initialized successfully');
      
    } catch (error) {
      console.error('Failed to initialize application:', error);
      this.handleInitializationError(error);
    }
  }

  /**
   * Initialize application components
   */
  async initializeComponents() {
    // Initialize UI controller (already created globally)
    this.ui = window.ui;
    
    // Initialize API client (already created globally)
    this.api = window.api;
    
    // Initialize map
    this.map = new HeatmapMap('map', {
      center: [20.5937, 78.9629],
      zoom: 5,
      minZoom: 4,
      maxZoom: 8
    });
    
    // Wait for map to be ready
    await new Promise((resolve) => {
      this.map.onMapReady = resolve;
    });
    
    console.log('All components initialized');
  }

  /**
   * Setup event handlers
   */
  setupEventHandlers() {
    // Map event handlers
    this.map.onStateClick = (stateName, feature, layer, event) => {
      this.handleStateClick(stateName, feature, layer, event);
    };
    
    // UI event handlers
    this.ui.onControlChange = (controlName, value) => {
      this.handleControlChange(controlName, value);
    };
    
    this.ui.onRetry = () => {
      this.handleRetry();
    };
    
    this.ui.onSearch = (searchTerm) => {
      this.handleSearch(searchTerm);
    };
    
    this.ui.onQuickActionClick = (action) => {
      this.handleQuickAction(action);
    };
    
    // Network event handlers
    Utils.network.setupConnectionListeners(
      () => this.handleConnectionRestored(),
      () => this.handleConnectionLost()
    );
    
    // Window event handlers
    Utils.dom.addEventListener(window, 'beforeunload', () => {
      this.cleanup();
    });
    
    // Visibility change handler (pause updates when tab is hidden)
    Utils.dom.addEventListener(document, 'visibilitychange', () => {
      if (document.hidden) {
        this.pauseAutoRefresh();
      } else {
        this.resumeAutoRefresh();
      }
    });
  }

  /**
   * Load initial data
   */
  async loadInitialData() {
    try {
      this.ui.showLoading('Loading heatmap data...');
      
      // Test API connection first
      const connectionTest = await this.api.testConnection();
      this.ui.updateConnectionStatus(connectionTest.connected, connectionTest.responseTime);
      
      if (!connectionTest.connected) {
        throw new Error('Unable to connect to the API server');
      }
      
      // Load heatmap data
      await this.loadHeatmapData();
      
      this.ui.hideLoading();
      this.ui.showToast('Heatmap data loaded successfully', 'success');
      
    } catch (error) {
      console.error('Failed to load initial data:', error);
      this.ui.hideLoading();
      this.ui.showError(Utils.error.getUserMessage(error));
      throw error;
    }
  }

  /**
   * Load heatmap data from API
   */
  async loadHeatmapData() {
    try {
      this.state.isLoading = true;
      
      // Get heatmap data
      const data = await this.api.getHeatmapData(this.state.filters.timeRange);
      
      // Update application state
      this.state.currentData = data;
      this.state.lastUpdate = new Date();
      
      // Reset failure count on successful load
      this.state.refreshFailureCount = 0;
      
      // Update map
      this.map.updateHeatmapData(data);
      
      // Update statistics
      this.updateStatistics(data);
      
      // Apply current filters
      this.applyFilters();
      
      this.state.isLoading = false;
      
    } catch (error) {
      this.state.isLoading = false;
      throw error;
    }
  }

  /**
   * Update statistics display
   */
  updateStatistics(data) {
    const stats = {
      total_events: data.total_events || 0,
      active_states: Object.keys(data.states || {}).length,
      last_updated: data.last_updated,
      avg_risk: this.calculateAverageRisk(data.states || {})
    };
    
    this.ui.updateStatistics(stats);
  }

  /**
   * Calculate average risk across all states
   */
  calculateAverageRisk(states) {
    const stateValues = Object.values(states);
    if (stateValues.length === 0) return 0;
    
    const totalRisk = stateValues.reduce((sum, state) => {
      return sum + (state.misinformation_risk || 0);
    }, 0);
    
    return totalRisk / stateValues.length;
  }

  /**
   * Handle state click events
   */
  async handleStateClick(stateName, feature, layer, event) {
    try {
      // Show loading state
      this.ui.showLoading(`Loading details for ${stateName}...`);
      
      // Get detailed state data
      const stateData = await this.api.getStateData(stateName, this.state.filters.timeRange);
      
      this.ui.hideLoading();
      
      // Show state details modal
      this.ui.showStateDetails(stateName, stateData);
      
      // Announce to screen readers
      Utils.accessibility.announce(`Showing details for ${stateName}`);
      
    } catch (error) {
      console.error(`Failed to load state data for ${stateName}:`, error);
      this.ui.hideLoading();
      this.ui.showToast(`Failed to load data for ${stateName}`, 'error');
    }
  }

  /**
   * Handle control changes
   */
  handleControlChange(controlName, value) {
    switch (controlName) {
      case 'timeRange':
        this.state.filters.timeRange = value;
        this.refreshData();
        break;
        
      case 'categoryFilter':
        this.state.filters.category = value;
        this.applyFilters();
        break;
        
      case 'intensityThreshold':
        this.state.filters.intensityThreshold = value;
        this.applyFilters();
        break;
        
      case 'autoRefresh':
        this.state.autoRefresh = value;
        if (value) {
          this.startAutoRefresh();
        } else {
          this.stopAutoRefresh();
        }
        break;
    }
  }

  /**
   * Apply current filters to the map
   */
  applyFilters() {
    if (!this.state.currentData || !this.map) return;
    
    // Filter data based on current filters
    const filteredData = this.filterData(this.state.currentData);
    
    // Update map with filtered data
    this.map.updateHeatmapData(filteredData);
  }

  /**
   * Filter data based on current filter settings
   */
  filterData(data) {
    if (!data || !data.states) return data;
    
    const filteredStates = {};
    
    Object.entries(data.states).forEach(([stateName, stateData]) => {
      // Apply intensity threshold filter
      if ((stateData.misinformation_risk || 0) >= this.state.filters.intensityThreshold) {
        // Apply category filter
        if (this.state.filters.category === 'all' || 
            stateData.dominant_category === this.state.filters.category) {
          filteredStates[stateName] = stateData;
        }
      }
    });
    
    return {
      ...data,
      states: filteredStates
    };
  }

  /**
   * Refresh data from API
   */
  async refreshData() {
    if (this.state.isLoading) return;
    
    try {
      const previousData = this.state.currentData;
      await this.loadHeatmapData();
      
      // Check for significant changes and notify user
      if (this.state.autoRefresh && previousData) {
        const changes = this.detectDataChanges(previousData, this.state.currentData);
        if (changes.hasSignificantChanges) {
          this.ui.showToast(`Data updated - ${changes.summary}`, 'info', 3000);
          
          // Add visual feedback for data update
          this.showDataUpdateFeedback();
        }
      }
      
      // Update last refresh indicator
      this.updateLastRefreshIndicator();
      
    } catch (error) {
      console.error('Failed to refresh data:', error);
      this.ui.showToast('Failed to update data', 'error');
      
      // Implement exponential backoff for failed requests
      this.handleRefreshFailure();
    }
  }

  /**
   * Detect significant changes between data updates
   */
  detectDataChanges(oldData, newData) {
    if (!oldData || !newData) {
      return { hasSignificantChanges: false, summary: '' };
    }

    const changes = {
      newStates: 0,
      increasedRisk: 0,
      decreasedRisk: 0,
      newEvents: 0
    };

    // Compare state data
    Object.keys(newData.states || {}).forEach(stateName => {
      const oldState = oldData.states?.[stateName];
      const newState = newData.states[stateName];

      if (!oldState) {
        changes.newStates++;
      } else {
        const oldRisk = oldState.misinformation_risk || 0;
        const newRisk = newState.misinformation_risk || 0;
        const riskDiff = newRisk - oldRisk;

        if (riskDiff > 0.1) changes.increasedRisk++;
        if (riskDiff < -0.1) changes.decreasedRisk++;

        const eventDiff = (newState.event_count || 0) - (oldState.event_count || 0);
        if (eventDiff > 0) changes.newEvents += eventDiff;
      }
    });

    const hasSignificantChanges = changes.newStates > 0 || 
                                 changes.increasedRisk > 0 || 
                                 changes.newEvents > 5;

    let summary = '';
    if (changes.newEvents > 0) summary += `${changes.newEvents} new events`;
    if (changes.increasedRisk > 0) {
      if (summary) summary += ', ';
      summary += `${changes.increasedRisk} states with increased risk`;
    }
    if (changes.newStates > 0) {
      if (summary) summary += ', ';
      summary += `${changes.newStates} new active states`;
    }

    return { hasSignificantChanges, summary: summary || 'minor updates' };
  }

  /**
   * Update last refresh indicator
   */
  updateLastRefreshIndicator() {
    const now = new Date();
    this.state.lastRefreshTime = now;
    
    // Update UI indicator if it exists
    const refreshIndicator = document.getElementById('last-refresh-time');
    if (refreshIndicator) {
      refreshIndicator.textContent = Utils.format.relativeTime(now.toISOString());
    }
  }

  /**
   * Handle refresh failures with exponential backoff
   */
  handleRefreshFailure() {
    if (!this.state.refreshFailureCount) {
      this.state.refreshFailureCount = 0;
    }
    
    this.state.refreshFailureCount++;
    
    // Implement exponential backoff (max 5 minutes)
    const backoffDelay = Math.min(
      this.state.refreshInterval * Math.pow(2, this.state.refreshFailureCount - 1),
      5 * 60 * 1000 // 5 minutes max
    );
    
    console.log(`Refresh failed ${this.state.refreshFailureCount} times. Next attempt in ${backoffDelay/1000}s`);
    
    // Stop current auto-refresh and restart with backoff delay
    this.stopAutoRefresh();
    
    setTimeout(() => {
      if (this.state.autoRefresh) {
        this.startAutoRefresh();
      }
    }, backoffDelay);
  }

  /**
   * Handle retry button click
   */
  async handleRetry() {
    try {
      await this.loadInitialData();
    } catch (error) {
      // Error is already handled in loadInitialData
    }
  }

  /**
   * Start auto-refresh timer
   */
  startAutoRefresh() {
    if (!this.state.autoRefresh) return;
    
    this.stopAutoRefresh(); // Clear existing timer
    
    // Use the current refresh interval (may be adjusted for backoff)
    const interval = this.state.refreshFailureCount > 0 ? 
      Math.min(this.state.refreshInterval * Math.pow(2, this.state.refreshFailureCount - 1), 5 * 60 * 1000) :
      this.state.refreshInterval;
    
    this.refreshTimer = setInterval(() => {
      if (!document.hidden && this.state.autoRefresh && Utils.network.isOnline()) {
        this.refreshData();
      }
    }, interval);
    
    // Update refresh indicator
    this.updateRefreshIndicator();
  }

  /**
   * Update refresh indicator in UI
   */
  updateRefreshIndicator() {
    const indicator = document.getElementById('refresh-indicator');
    if (!indicator) return;
    
    // Start countdown timer
    this.startRefreshCountdown();
  }

  /**
   * Start countdown timer for next refresh
   */
  startRefreshCountdown() {
    const indicator = document.getElementById('refresh-indicator');
    if (!indicator) return;
    
    // Clear existing countdown
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
    
    let secondsLeft = Math.floor(this.state.refreshInterval / 1000);
    
    const updateCountdown = () => {
      if (secondsLeft <= 0) {
        indicator.textContent = 'Updating...';
        indicator.innerHTML = 'Updating... <span class="realtime-loading"></span>';
        return;
      }
      
      const minutes = Math.floor(secondsLeft / 60);
      const seconds = secondsLeft % 60;
      
      if (minutes > 0) {
        indicator.textContent = `${minutes}m ${seconds}s`;
      } else {
        indicator.textContent = `${seconds}s`;
      }
      
      secondsLeft--;
    };
    
    // Update immediately
    updateCountdown();
    
    // Update every second
    this.countdownTimer = setInterval(updateCountdown, 1000);
  }

  /**
   * Stop auto-refresh timer
   */
  stopAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  /**
   * Pause auto-refresh (when tab is hidden)
   */
  pauseAutoRefresh() {
    this.stopAutoRefresh();
  }

  /**
   * Resume auto-refresh (when tab becomes visible)
   */
  resumeAutoRefresh() {
    if (this.state.autoRefresh) {
      this.startAutoRefresh();
      // Refresh data immediately when tab becomes visible
      this.refreshData();
    }
  }

  /**
   * Start connection monitoring
   */
  startConnectionMonitoring() {
    this.connectionCheckTimer = setInterval(async () => {
      const connectionTest = await this.api.testConnection();
      this.ui.updateConnectionStatus(connectionTest.connected, connectionTest.responseTime);
    }, 60000); // Check every minute
  }

  /**
   * Handle connection restored
   */
  handleConnectionRestored() {
    console.log('Connection restored');
    this.ui.showToast('Connection restored', 'success');
    this.ui.updateConnectionStatus(true);
    
    // Refresh data if auto-refresh is enabled
    if (this.state.autoRefresh) {
      this.refreshData();
    }
  }

  /**
   * Handle connection lost
   */
  handleConnectionLost() {
    console.log('Connection lost');
    this.ui.showToast('Connection lost. Retrying...', 'warning');
    this.ui.updateConnectionStatus(false);
  }

  /**
   * Handle initialization error
   */
  handleInitializationError(error) {
    const errorMessage = Utils.error.getUserMessage(error);
    
    // Show error in UI if available
    if (this.ui) {
      this.ui.showError(errorMessage);
    } else {
      // Fallback error display
      const errorDiv = document.createElement('div');
      errorDiv.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #dc2626;
        color: white;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        z-index: 10000;
      `;
      errorDiv.innerHTML = `
        <h3>Application Error</h3>
        <p>${errorMessage}</p>
        <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px;">
          Reload Page
        </button>
      `;
      document.body.appendChild(errorDiv);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this.stopAutoRefresh();
    
    if (this.connectionCheckTimer) {
      clearInterval(this.connectionCheckTimer);
    }
    
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
    
    if (this.map) {
      this.map.destroy();
    }
  }

  /**
   * Public API methods
   */

  /**
   * Get current application state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Update filter settings
   */
  updateFilters(newFilters) {
    this.state.filters = { ...this.state.filters, ...newFilters };
    this.applyFilters();
  }

  /**
   * Focus on specific state
   */
  focusState(stateName) {
    if (this.map) {
      this.map.fitToState(stateName);
    }
  }

  /**
   * Reset map view
   */
  resetMapView() {
    if (this.map) {
      this.map.resetView();
    }
  }

  /**
   * Handle search functionality
   */
  handleSearch(searchTerm) {
    if (!this.map) return;
    
    if (searchTerm.length === 0) {
      // Clear search highlights
      this.map.clearSearchHighlights();
      return;
    }
    
    // Search for matching states
    const matchingStates = this.map.searchStates(searchTerm);
    
    if (matchingStates.length > 0) {
      // Highlight matching states
      this.map.highlightStates(matchingStates);
      
      // If only one match, focus on it
      if (matchingStates.length === 1) {
        this.focusState(matchingStates[0]);
      }
      
      this.ui.showToast(`Found ${matchingStates.length} matching state${matchingStates.length > 1 ? 's' : ''}`, 'info', 2000);
    } else {
      this.ui.showToast('No matching states found', 'warning', 2000);
    }
  }

  /**
   * Handle quick action buttons
   */
  handleQuickAction(action) {
    switch (action) {
      case 'refresh':
        this.refreshData();
        break;
        
      case 'resetView':
        this.resetMapView();
        break;
        
      case 'export':
        this.exportData();
        break;
        
      case 'fullscreen':
        this.ui.toggleFullscreen();
        break;
    }
  }

  /**
   * Show visual feedback for data updates
   */
  showDataUpdateFeedback() {
    // Add a subtle flash to the map container
    const mapContainer = document.querySelector('.map-container');
    if (mapContainer) {
      mapContainer.classList.add('data-updated');
      setTimeout(() => {
        mapContainer.classList.remove('data-updated');
      }, 1000);
    }
    
    // Update the status indicator
    const statusDot = document.getElementById('status-dot');
    if (statusDot) {
      statusDot.classList.add('data-pulse');
      setTimeout(() => {
        statusDot.classList.remove('data-pulse');
      }, 2000);
    }
  }

  /**
   * Export current data
   */
  exportData(format = 'json') {
    if (!this.state.currentData) {
      this.ui.showToast('No data available to export', 'warning');
      return;
    }
    
    const dataStr = JSON.stringify(this.state.currentData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `heatmap-data-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    this.ui.showToast('Data exported successfully', 'success');
  }
}

// Initialize application when DOM is ready
let app;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    app = new HeatmapApp();
  });
} else {
  app = new HeatmapApp();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HeatmapApp;
} else {
  window.HeatmapApp = HeatmapApp;
  window.app = app;
}