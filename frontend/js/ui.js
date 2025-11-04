/**
 * UI controller for the misinformation heatmap application
 * Handles user interface interactions, modal management, and control panel functionality
 * Provides accessibility features and responsive design support
 */

class UIController {
  constructor() {
    this.elements = {};
    this.modals = {};
    this.settings = {};
    this.isInitialized = false;
    
    // Initialize UI
    this.init();
  }

  /**
   * Initialize UI controller
   */
  init() {
    try {
      // Get DOM elements
      this.getElements();
      
      // Setup event listeners
      this.setupEventListeners();
      
      // Load settings
      this.loadSettings();
      
      // Apply initial settings
      this.applySettings();
      
      // Setup accessibility features
      this.setupAccessibility();
      
      this.isInitialized = true;
      console.log('UI Controller initialized successfully');
    } catch (error) {
      console.error('Failed to initialize UI Controller:', error);
    }
  }

  /**
   * Get DOM elements
   */
  getElements() {
    // Header elements
    this.elements.statusDot = Utils.dom.getElementById('status-dot');
    this.elements.statusText = Utils.dom.getElementById('status-text');
    this.elements.infoBtn = Utils.dom.getElementById('info-btn');
    this.elements.settingsBtn = Utils.dom.getElementById('settings-btn');
    
    // Control panel elements
    this.elements.controlPanel = Utils.dom.getElementById('control-panel');
    this.elements.panelToggle = Utils.dom.getElementById('panel-toggle');
    this.elements.panelContent = Utils.dom.getElementById('panel-content');
    
    // Control inputs
    this.elements.timeRange = Utils.dom.getElementById('time-range');
    this.elements.categoryFilter = Utils.dom.getElementById('category-filter');
    this.elements.intensityThreshold = Utils.dom.getElementById('intensity-threshold');
    this.elements.intensityValue = Utils.dom.getElementById('intensity-value');
    this.elements.autoRefresh = Utils.dom.getElementById('auto-refresh');
    this.elements.searchFilter = Utils.dom.getElementById('search-filter');
    this.elements.searchClear = Utils.dom.getElementById('search-clear');
    
    // Quick action buttons
    this.elements.refreshNow = Utils.dom.getElementById('refresh-now');
    this.elements.resetView = Utils.dom.getElementById('reset-view');
    this.elements.exportData = Utils.dom.getElementById('export-data');
    this.elements.fullscreenToggle = Utils.dom.getElementById('fullscreen-toggle');
    
    // Statistics elements
    this.elements.totalEvents = Utils.dom.getElementById('total-events');
    this.elements.activeStates = Utils.dom.getElementById('active-states');
    this.elements.lastUpdated = Utils.dom.getElementById('last-updated');
    this.elements.avgRisk = Utils.dom.getElementById('avg-risk');
    
    // Loading and error overlays
    this.elements.loadingOverlay = Utils.dom.getElementById('loading-overlay');
    this.elements.errorOverlay = Utils.dom.getElementById('error-overlay');
    this.elements.errorMessage = Utils.dom.getElementById('error-message');
    this.elements.errorRetry = Utils.dom.getElementById('error-retry');
    
    // Modals
    this.elements.stateModal = Utils.dom.getElementById('state-modal-overlay');
    this.elements.stateModalContent = Utils.dom.getElementById('modal-content');
    this.elements.stateModalTitle = Utils.dom.getElementById('modal-title');
    this.elements.stateModalClose = Utils.dom.getElementById('modal-close');
    
    this.elements.infoModal = Utils.dom.getElementById('info-modal-overlay');
    this.elements.infoModalClose = Utils.dom.getElementById('info-modal-close');
    
    this.elements.settingsModal = Utils.dom.getElementById('settings-modal-overlay');
    this.elements.settingsModalClose = Utils.dom.getElementById('settings-modal-close');
    
    // Settings elements
    this.elements.darkMode = Utils.dom.getElementById('dark-mode');
    this.elements.highContrast = Utils.dom.getElementById('high-contrast');
    this.elements.reduceMotion = Utils.dom.getElementById('reduce-motion');
    this.elements.refreshInterval = Utils.dom.getElementById('refresh-interval');
    this.elements.showNotifications = Utils.dom.getElementById('show-notifications');
    this.elements.fontSize = Utils.dom.getElementById('font-size');
    this.elements.screenReaderMode = Utils.dom.getElementById('screen-reader-mode');
    this.elements.resetSettings = Utils.dom.getElementById('reset-settings');
    this.elements.saveSettings = Utils.dom.getElementById('save-settings');
    
    // Toast container
    this.elements.toastContainer = Utils.dom.getElementById('toast-container');
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Header buttons
    if (this.elements.infoBtn) {
      Utils.dom.addEventListener(this.elements.infoBtn, 'click', () => {
        this.showModal('info');
      });
    }
    
    if (this.elements.settingsBtn) {
      Utils.dom.addEventListener(this.elements.settingsBtn, 'click', () => {
        this.showModal('settings');
      });
    }
    
    // Control panel toggle
    if (this.elements.panelToggle) {
      Utils.dom.addEventListener(this.elements.panelToggle, 'click', () => {
        this.toggleControlPanel();
      });
    }
    
    // Control inputs
    if (this.elements.timeRange) {
      Utils.dom.addEventListener(this.elements.timeRange, 'change', (e) => {
        this.onTimeRangeChange(parseInt(e.target.value));
      });
    }
    
    if (this.elements.categoryFilter) {
      Utils.dom.addEventListener(this.elements.categoryFilter, 'change', (e) => {
        this.onCategoryFilterChange(e.target.value);
      });
    }
    
    if (this.elements.intensityThreshold) {
      Utils.dom.addEventListener(this.elements.intensityThreshold, 'input', (e) => {
        const value = parseFloat(e.target.value);
        this.elements.intensityValue.textContent = value.toFixed(1);
        this.onIntensityThresholdChange(value);
      });
    }
    
    if (this.elements.autoRefresh) {
      Utils.dom.addEventListener(this.elements.autoRefresh, 'change', (e) => {
        this.onAutoRefreshChange(e.target.checked);
      });
    }
    
    // Search functionality
    if (this.elements.searchFilter) {
      Utils.dom.addEventListener(this.elements.searchFilter, 'input', (e) => {
        this.onSearchChange(e.target.value);
      });
      
      Utils.dom.addEventListener(this.elements.searchFilter, 'keydown', (e) => {
        if (e.key === 'Escape') {
          this.clearSearch();
        }
      });
    }
    
    if (this.elements.searchClear) {
      Utils.dom.addEventListener(this.elements.searchClear, 'click', () => {
        this.clearSearch();
      });
    }
    
    // Modal close buttons
    this.setupModalEventListeners();
    
    // Settings
    this.setupSettingsEventListeners();
    
    // Error retry
    if (this.elements.errorRetry) {
      Utils.dom.addEventListener(this.elements.errorRetry, 'click', () => {
        this.onErrorRetry();
      });
    }
    
    // Quick action buttons
    this.setupQuickActions();
    
    // Keyboard navigation
    this.setupKeyboardNavigation();
    
    // Responsive design
    this.setupResponsiveHandlers();
  }

  /**
   * Setup modal event listeners
   */
  setupModalEventListeners() {
    // State modal
    if (this.elements.stateModalClose) {
      Utils.dom.addEventListener(this.elements.stateModalClose, 'click', () => {
        this.hideModal('state');
      });
    }
    
    if (this.elements.stateModal) {
      Utils.dom.addEventListener(this.elements.stateModal, 'click', (e) => {
        if (e.target === this.elements.stateModal) {
          this.hideModal('state');
        }
      });
    }
    
    // Info modal
    if (this.elements.infoModalClose) {
      Utils.dom.addEventListener(this.elements.infoModalClose, 'click', () => {
        this.hideModal('info');
      });
    }
    
    if (this.elements.infoModal) {
      Utils.dom.addEventListener(this.elements.infoModal, 'click', (e) => {
        if (e.target === this.elements.infoModal) {
          this.hideModal('info');
        }
      });
    }
    
    // Settings modal
    if (this.elements.settingsModalClose) {
      Utils.dom.addEventListener(this.elements.settingsModalClose, 'click', () => {
        this.hideModal('settings');
      });
    }
    
    if (this.elements.settingsModal) {
      Utils.dom.addEventListener(this.elements.settingsModal, 'click', (e) => {
        if (e.target === this.elements.settingsModal) {
          this.hideModal('settings');
        }
      });
    }
  }

  /**
   * Setup settings event listeners
   */
  setupSettingsEventListeners() {
    const settingsInputs = [
      'darkMode', 'highContrast', 'reduceMotion', 'refreshInterval',
      'showNotifications', 'fontSize', 'screenReaderMode'
    ];
    
    settingsInputs.forEach(inputName => {
      const element = this.elements[inputName];
      if (element) {
        const eventType = element.type === 'checkbox' ? 'change' : 'change';
        Utils.dom.addEventListener(element, eventType, () => {
          this.onSettingChange(inputName, this.getSettingValue(inputName));
        });
      }
    });
    
    if (this.elements.resetSettings) {
      Utils.dom.addEventListener(this.elements.resetSettings, 'click', () => {
        this.resetSettings();
      });
    }
    
    if (this.elements.saveSettings) {
      Utils.dom.addEventListener(this.elements.saveSettings, 'click', () => {
        this.saveSettings();
      });
    }
  }

  /**
   * Setup keyboard navigation
   */
  setupKeyboardNavigation() {
    // Global keyboard shortcuts
    Utils.dom.addEventListener(document, 'keydown', (e) => {
      // Escape key closes modals
      if (e.key === 'Escape') {
        this.hideAllModals();
      }
      
      // Ctrl/Cmd + I opens info modal
      if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
        e.preventDefault();
        this.showModal('info');
      }
      
      // Ctrl/Cmd + , opens settings
      if ((e.ctrlKey || e.metaKey) && e.key === ',') {
        e.preventDefault();
        this.showModal('settings');
      }
    });
  }

  /**
   * Setup responsive design handlers
   */
  setupResponsiveHandlers() {
    // Handle window resize
    const handleResize = Utils.performance.debounce(() => {
      this.updateResponsiveLayout();
    }, 250);
    
    Utils.dom.addEventListener(window, 'resize', handleResize);
    
    // Initial layout update
    this.updateResponsiveLayout();
  }

  /**
   * Update responsive layout
   */
  updateResponsiveLayout() {
    const isMobile = window.innerWidth <= 768;
    
    if (isMobile && this.elements.controlPanel) {
      this.elements.controlPanel.classList.add('mobile');
    } else if (this.elements.controlPanel) {
      this.elements.controlPanel.classList.remove('mobile');
    }
  }

  /**
   * Toggle control panel visibility
   */
  toggleControlPanel() {
    if (this.elements.controlPanel) {
      const isOpen = this.elements.controlPanel.classList.contains('open');
      
      if (isOpen) {
        this.elements.controlPanel.classList.remove('open');
        Utils.accessibility.announce('Control panel closed');
      } else {
        this.elements.controlPanel.classList.add('open');
        Utils.accessibility.announce('Control panel opened');
      }
    }
  }

  /**
   * Show modal
   */
  showModal(modalType) {
    const modalElement = this.elements[`${modalType}Modal`];
    if (!modalElement) return;
    
    // Hide other modals first
    this.hideAllModals();
    
    // Show modal
    Utils.dom.show(modalElement);
    
    // Setup focus trap
    const focusTrap = Utils.accessibility.trapFocus(modalElement);
    this.modals[modalType] = { element: modalElement, focusTrap };
    
    // Focus first focusable element
    const focusableElements = modalElement.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }
    
    Utils.accessibility.announce(`${modalType} modal opened`);
  }

  /**
   * Hide modal
   */
  hideModal(modalType) {
    const modal = this.modals[modalType];
    if (!modal) return;
    
    // Hide modal
    Utils.dom.hide(modal.element);
    
    // Cleanup focus trap
    if (modal.focusTrap) {
      modal.focusTrap();
    }
    
    delete this.modals[modalType];
    
    Utils.accessibility.announce(`${modalType} modal closed`);
  }

  /**
   * Hide all modals
   */
  hideAllModals() {
    Object.keys(this.modals).forEach(modalType => {
      this.hideModal(modalType);
    });
  }

  /**
   * Show state details modal
   */
  showStateDetails(stateName, stateData) {
    if (!this.elements.stateModalTitle || !this.elements.stateModalContent) return;
    
    // Set modal title
    this.elements.stateModalTitle.textContent = `${stateName} - Misinformation Analysis`;
    
    // Generate content
    const content = this.generateStateDetailsContent(stateName, stateData);
    this.elements.stateModalContent.innerHTML = content;
    
    // Show modal
    this.showModal('state');
  }

  /**
   * Generate state details content
   */
  generateStateDetailsContent(stateName, stateData) {
    if (!stateData) {
      return `
        <div class="state-details">
          <div class="no-data-message">
            <h3>No Data Available</h3>
            <p>There is currently no misinformation data available for ${stateName}.</p>
          </div>
        </div>
      `;
    }

    const riskLevel = Utils.color.getRiskLevel(stateData.misinformation_risk || 0);
    const riskColor = Utils.color.getHeatmapColor(stateData.misinformation_risk || 0);

    return `
      <div class="state-details">
        <div class="state-overview">
          <div class="risk-indicator" style="background-color: ${riskColor}">
            <span class="risk-level">${riskLevel} Risk</span>
            <span class="risk-score">${Utils.format.percentage(stateData.misinformation_risk || 0)}</span>
          </div>
          
          <div class="metrics-grid">
            <div class="metric">
              <span class="metric-label">Total Events</span>
              <span class="metric-value">${stateData.event_count || 0}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Avg Virality</span>
              <span class="metric-value">${Utils.format.percentage(stateData.avg_virality_score || 0)}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Avg Reality</span>
              <span class="metric-value">${Utils.format.percentage(stateData.avg_reality_score || 0)}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Satellite Validated</span>
              <span class="metric-value">${stateData.satellite_validated_count || 0}</span>
            </div>
          </div>
        </div>

        ${stateData.recent_claims && stateData.recent_claims.length > 0 ? `
          <div class="recent-claims">
            <h4>Recent Claims</h4>
            <ul class="claims-list">
              ${stateData.recent_claims.slice(0, 5).map(claim => `
                <li class="claim-item">${claim}</li>
              `).join('')}
            </ul>
          </div>
        ` : ''}

        <div class="state-actions">
          <button class="btn btn-primary" onclick="ui.viewStateTimeline('${stateName}')">
            View Timeline
          </button>
          <button class="btn btn-secondary" onclick="ui.exportStateData('${stateName}')">
            Export Data
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Update connection status
   */
  updateConnectionStatus(isConnected, responseTime = null) {
    if (!this.elements.statusDot || !this.elements.statusText) return;
    
    if (isConnected) {
      // Determine connection quality based on response time
      let quality = 'excellent';
      let className = 'status-dot connected';
      
      if (responseTime) {
        if (responseTime > 2000) {
          quality = 'poor';
          className = 'status-dot connected slow';
        } else if (responseTime > 1000) {
          quality = 'fair';
          className = 'status-dot connected moderate';
        } else if (responseTime > 500) {
          quality = 'good';
          className = 'status-dot connected';
        }
      }
      
      this.elements.statusDot.className = className;
      this.elements.statusText.textContent = responseTime ? 
        `Connected (${responseTime}ms - ${quality})` : 'Connected';
        
      // Update connection quality indicator
      this.updateConnectionQuality(quality, responseTime);
    } else {
      this.elements.statusDot.className = 'status-dot error';
      this.elements.statusText.textContent = 'Disconnected';
      this.updateConnectionQuality('disconnected', null);
    }
  }

  /**
   * Update connection quality indicator
   */
  updateConnectionQuality(quality, responseTime) {
    const qualityIndicator = document.getElementById('connection-quality');
    if (qualityIndicator) {
      qualityIndicator.className = `connection-quality ${quality}`;
      qualityIndicator.textContent = quality === 'disconnected' ? 
        'Offline' : `${quality.charAt(0).toUpperCase() + quality.slice(1)} (${responseTime}ms)`;
    }
  }

  /**
   * Update statistics display
   */
  updateStatistics(stats) {
    if (this.elements.totalEvents) {
      this.elements.totalEvents.textContent = Utils.format.compactNumber(stats.total_events || 0);
    }
    
    if (this.elements.activeStates) {
      this.elements.activeStates.textContent = stats.active_states || 0;
    }
    
    if (this.elements.lastUpdated) {
      const lastUpdated = stats.last_updated ? 
        Utils.format.relativeTime(stats.last_updated) : '-';
      this.elements.lastUpdated.textContent = lastUpdated;
      
      // Add data freshness indicator
      this.updateDataFreshness(stats.last_updated);
    }
    
    if (this.elements.avgRisk) {
      this.elements.avgRisk.textContent = stats.avg_risk ? 
        Utils.format.percentage(stats.avg_risk) : '-';
    }
  }

  /**
   * Update data freshness indicator
   */
  updateDataFreshness(lastUpdated) {
    const freshnessIndicator = document.getElementById('data-freshness');
    if (!freshnessIndicator || !lastUpdated) return;
    
    const now = new Date();
    const updateTime = new Date(lastUpdated);
    const ageMinutes = (now - updateTime) / (1000 * 60);
    
    let freshnessClass = 'fresh';
    let freshnessText = 'Live';
    
    if (ageMinutes > 60) {
      freshnessClass = 'stale';
      freshnessText = 'Stale';
    } else if (ageMinutes > 30) {
      freshnessClass = 'aging';
      freshnessText = 'Aging';
    } else if (ageMinutes > 10) {
      freshnessClass = 'recent';
      freshnessText = 'Recent';
    }
    
    freshnessIndicator.className = `data-freshness ${freshnessClass}`;
    freshnessIndicator.textContent = freshnessText;
    freshnessIndicator.title = `Data is ${Utils.format.relativeTime(lastUpdated)}`;
  }

  /**
   * Show loading state
   */
  showLoading(message = 'Loading data...') {
    if (this.elements.loadingOverlay) {
      const loadingText = this.elements.loadingOverlay.querySelector('.loading-text');
      if (loadingText) {
        loadingText.textContent = message;
      }
      Utils.dom.show(this.elements.loadingOverlay);
    }
  }

  /**
   * Hide loading state
   */
  hideLoading() {
    if (this.elements.loadingOverlay) {
      Utils.dom.hide(this.elements.loadingOverlay);
    }
  }

  /**
   * Show error state
   */
  showError(message = 'An error occurred. Please try again.') {
    if (this.elements.errorOverlay && this.elements.errorMessage) {
      this.elements.errorMessage.textContent = message;
      Utils.dom.show(this.elements.errorOverlay);
    }
    this.hideLoading();
  }

  /**
   * Hide error state
   */
  hideError() {
    if (this.elements.errorOverlay) {
      Utils.dom.hide(this.elements.errorOverlay);
    }
  }

  /**
   * Show toast notification
   */
  showToast(message, type = 'info', duration = 5000) {
    if (!this.elements.toastContainer) return;
    
    const toast = Utils.dom.createElement('div', {
      className: `toast ${type}`,
      'aria-live': 'polite'
    });
    
    toast.innerHTML = `
      <div class="toast-content">
        <div class="toast-title">${this.getToastTitle(type)}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close notification">×</button>
    `;
    
    // Add close handler
    const closeBtn = toast.querySelector('.toast-close');
    Utils.dom.addEventListener(closeBtn, 'click', () => {
      this.removeToast(toast);
    });
    
    // Add to container
    this.elements.toastContainer.appendChild(toast);
    
    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        this.removeToast(toast);
      }, duration);
    }
  }

  /**
   * Remove toast notification
   */
  removeToast(toast) {
    if (toast && toast.parentNode) {
      toast.style.animation = 'slideOut 0.3s ease-in';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }
  }

  /**
   * Get toast title based on type
   */
  getToastTitle(type) {
    const titles = {
      success: 'Success',
      warning: 'Warning',
      error: 'Error',
      info: 'Information'
    };
    return titles[type] || 'Notification';
  }

  /**
   * Event handlers
   */
  onTimeRangeChange(hours) {
    if (this.onControlChange) {
      this.onControlChange('timeRange', hours);
    }
  }

  onCategoryFilterChange(category) {
    if (this.onControlChange) {
      this.onControlChange('categoryFilter', category);
    }
  }

  onIntensityThresholdChange(threshold) {
    if (this.onControlChange) {
      this.onControlChange('intensityThreshold', threshold);
    }
  }

  onAutoRefreshChange(enabled) {
    if (this.onControlChange) {
      this.onControlChange('autoRefresh', enabled);
    }
  }

  onErrorRetry() {
    this.hideError();
    if (this.onRetry) {
      this.onRetry();
    }
  }

  /**
   * Settings management
   */
  loadSettings() {
    const defaultSettings = {
      darkMode: false,
      highContrast: false,
      reduceMotion: false,
      refreshInterval: 30,
      showNotifications: true,
      fontSize: 'medium',
      screenReaderMode: false
    };
    
    this.settings = { ...defaultSettings, ...Utils.storage.get('heatmap-settings', {}) };
  }

  saveSettings() {
    Utils.storage.set('heatmap-settings', this.settings);
    this.showToast('Settings saved successfully', 'success');
  }

  resetSettings() {
    this.loadSettings();
    this.applySettings();
    this.showToast('Settings reset to defaults', 'info');
  }

  applySettings() {
    // Apply theme settings
    document.documentElement.setAttribute('data-theme', this.settings.darkMode ? 'dark' : 'light');
    document.documentElement.setAttribute('data-contrast', this.settings.highContrast ? 'high' : 'normal');
    document.documentElement.setAttribute('data-font-size', this.settings.fontSize);
    
    // Apply motion settings
    if (this.settings.reduceMotion) {
      document.documentElement.style.setProperty('--transition-fast', '0ms');
      document.documentElement.style.setProperty('--transition-normal', '0ms');
      document.documentElement.style.setProperty('--transition-slow', '0ms');
    }
    
    // Update form elements
    Object.keys(this.settings).forEach(key => {
      this.setSettingValue(key, this.settings[key]);
    });
  }

  getSettingValue(settingName) {
    const element = this.elements[settingName];
    if (!element) return null;
    
    if (element.type === 'checkbox') {
      return element.checked;
    } else {
      return element.value;
    }
  }

  setSettingValue(settingName, value) {
    const element = this.elements[settingName];
    if (!element) return;
    
    if (element.type === 'checkbox') {
      element.checked = value;
    } else {
      element.value = value;
    }
  }

  onSettingChange(settingName, value) {
    this.settings[settingName] = value;
    this.applySettings();
  }

  /**
   * Setup accessibility features
   */
  setupAccessibility() {
    // Add skip links
    const skipLink = Utils.dom.createElement('a', {
      href: '#main-content',
      className: 'skip-link'
    }, 'Skip to main content');
    
    document.body.insertBefore(skipLink, document.body.firstChild);
    
    // Setup ARIA live regions
    Utils.accessibility.announce('Misinformation heatmap application loaded');
  }

  /**
   * Setup quick action buttons
   */
  setupQuickActions() {
    if (this.elements.refreshNow) {
      Utils.dom.addEventListener(this.elements.refreshNow, 'click', () => {
        this.onQuickAction('refresh');
      });
    }
    
    if (this.elements.resetView) {
      Utils.dom.addEventListener(this.elements.resetView, 'click', () => {
        this.onQuickAction('resetView');
      });
    }
    
    if (this.elements.exportData) {
      Utils.dom.addEventListener(this.elements.exportData, 'click', () => {
        this.onQuickAction('export');
      });
    }
    
    if (this.elements.fullscreenToggle) {
      Utils.dom.addEventListener(this.elements.fullscreenToggle, 'click', () => {
        this.onQuickAction('fullscreen');
      });
    }
  }

  /**
   * Handle search input changes
   */
  onSearchChange(searchTerm) {
    const trimmedTerm = searchTerm.trim();
    
    // Show/hide clear button
    if (this.elements.searchClear) {
      this.elements.searchClear.style.display = trimmedTerm ? 'flex' : 'none';
    }
    
    // Trigger search callback
    if (this.onSearch) {
      this.onSearch(trimmedTerm);
    }
  }

  /**
   * Clear search input
   */
  clearSearch() {
    if (this.elements.searchFilter) {
      this.elements.searchFilter.value = '';
      this.onSearchChange('');
      this.elements.searchFilter.focus();
    }
  }

  /**
   * Handle quick action button clicks
   */
  onQuickAction(action) {
    const button = this.elements[action === 'refresh' ? 'refreshNow' : 
                                  action === 'resetView' ? 'resetView' :
                                  action === 'export' ? 'exportData' : 'fullscreenToggle'];
    
    if (button) {
      // Add loading state
      button.classList.add('loading');
      
      // Remove loading state after animation
      setTimeout(() => {
        button.classList.remove('loading');
        button.classList.add('success');
        
        setTimeout(() => {
          button.classList.remove('success');
        }, 1000);
      }, 500);
    }
    
    // Trigger callback
    if (this.onQuickActionClick) {
      this.onQuickActionClick(action);
    }
  }

  /**
   * Toggle fullscreen mode
   */
  toggleFullscreen() {
    const mapContainer = document.querySelector('.map-container');
    if (!mapContainer) return;
    
    if (document.fullscreenElement) {
      document.exitFullscreen();
      mapContainer.classList.remove('fullscreen-active');
    } else {
      mapContainer.requestFullscreen();
      mapContainer.classList.add('fullscreen-active');
    }
  }

  /**
   * Highlight search results on map
   */
  highlightSearchResults(stateName) {
    // This would be called by the map component
    const stateElements = document.querySelectorAll(`[data-state="${stateName}"]`);
    stateElements.forEach(element => {
      element.classList.add('search-highlight');
      setTimeout(() => {
        element.classList.remove('search-highlight');
      }, 3000);
    });
  }

  /**
   * Utility methods
   */
  viewStateTimeline(stateName) {
    // Placeholder for timeline functionality
    this.showToast(`Timeline view for ${stateName} - Coming soon`, 'info');
  }

  exportStateData(stateName) {
    // Placeholder for export functionality
    this.showToast(`Exporting data for ${stateName} - Coming soon`, 'info');
  }
}

// Create global UI controller instance
const ui = new UIController();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = UIController;
} else {
  window.UIController = UIController;
  window.ui = ui;
}