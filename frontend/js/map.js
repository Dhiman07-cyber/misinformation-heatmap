/**
 * Map functionality for the misinformation heatmap application
 * Handles Leaflet.js map initialization, India boundaries, and heat layer rendering
 * Provides interactive state click handlers and real-time data visualization
 */

class HeatmapMap {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.map = null;
    this.indiaLayer = null;
    this.heatLayer = null;
    this.stateData = new Map();
    this.currentData = null;
    
    // Configuration
    this.config = {
      center: [20.5937, 78.9629], // Center of India
      zoom: 5,
      minZoom: 4,
      maxZoom: 8,
      maxBounds: [[6, 68], [37, 98]], // India boundaries
      ...options
    };
    
    // Event handlers
    this.onStateClick = null;
    this.onMapReady = null;
    
    // Initialize map
    this.init();
  }

  /**
   * Initialize the Leaflet map
   */
  async init() {
    try {
      // Create map instance
      this.map = L.map(this.containerId, {
        center: this.config.center,
        zoom: this.config.zoom,
        minZoom: this.config.minZoom,
        maxZoom: this.config.maxZoom,
        maxBounds: this.config.maxBounds,
        maxBoundsViscosity: 1.0,
        zoomControl: false,
        attributionControl: true
      });

      // Add custom zoom control
      L.control.zoom({
        position: 'bottomright'
      }).addTo(this.map);

      // Add base tile layer
      this.addBaseLayer();

      // Load India boundaries
      await this.loadIndiaBoundaries();

      // Setup map event handlers
      this.setupEventHandlers();

      // Notify that map is ready
      if (this.onMapReady) {
        this.onMapReady(this.map);
      }

      console.log('Map initialized successfully');
    } catch (error) {
      console.error('Failed to initialize map:', error);
      throw error;
    }
  }

  /**
   * Add base tile layer
   */
  addBaseLayer() {
    // Use OpenStreetMap tiles with custom styling
    const baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
      className: 'map-tiles'
    });

    baseLayer.addTo(this.map);
  }

  /**
   * Load India state boundaries from GeoJSON
   */
  async loadIndiaBoundaries() {
    try {
      // First try to load from local file
      let indiaGeoJSON;
      
      try {
        const response = await fetch('data/india-states.geojson');
        if (response.ok) {
          indiaGeoJSON = await response.json();
        } else {
          throw new Error('Local GeoJSON not found');
        }
      } catch (error) {
        console.warn('Local GeoJSON not available, using fallback data');
        indiaGeoJSON = this.getFallbackGeoJSON();
      }

      // Create India layer
      this.indiaLayer = L.geoJSON(indiaGeoJSON, {
        style: this.getDefaultStyle(),
        onEachFeature: (feature, layer) => {
          this.setupStateFeature(feature, layer);
        }
      });

      this.indiaLayer.addTo(this.map);

      // Fit map to India bounds
      this.map.fitBounds(this.indiaLayer.getBounds(), {
        padding: [20, 20]
      });

    } catch (error) {
      console.error('Failed to load India boundaries:', error);
      throw error;
    }
  }

  /**
   * Setup individual state feature
   */
  setupStateFeature(feature, layer) {
    const stateName = this.getStateName(feature);
    
    // Store layer reference
    this.stateData.set(stateName, {
      layer: layer,
      feature: feature,
      data: null
    });

    // Add click handler
    layer.on('click', (e) => {
      this.handleStateClick(stateName, feature, layer, e);
    });

    // Add hover effects
    layer.on('mouseover', (e) => {
      this.handleStateHover(stateName, layer, e, true);
    });

    layer.on('mouseout', (e) => {
      this.handleStateHover(stateName, layer, e, false);
    });

    // Add tooltip
    const tooltip = this.createStateTooltip(stateName, null);
    layer.bindTooltip(tooltip, {
      sticky: true,
      className: 'state-tooltip'
    });
  }

  /**
   * Get state name from feature properties
   */
  getStateName(feature) {
    // Try different possible property names
    const props = feature.properties;
    return props.NAME_1 || props.name || props.NAME || props.state || 'Unknown';
  }

  /**
   * Handle state click events
   */
  handleStateClick(stateName, feature, layer, event) {
    // Highlight clicked state
    this.highlightState(layer);
    
    // Call external click handler if provided
    if (this.onStateClick) {
      this.onStateClick(stateName, feature, layer, event);
    }
  }

  /**
   * Handle state hover events
   */
  handleStateHover(stateName, layer, event, isHover) {
    if (isHover) {
      layer.setStyle({
        weight: 3,
        color: '#2563eb',
        fillOpacity: 0.8
      });
      
      // Update tooltip with current data
      const stateInfo = this.stateData.get(stateName);
      const tooltip = this.createStateTooltip(stateName, stateInfo?.data);
      layer.setTooltipContent(tooltip);
    } else {
      // Reset to original style
      const stateInfo = this.stateData.get(stateName);
      const style = this.getStateStyle(stateInfo?.data);
      layer.setStyle(style);
    }
  }

  /**
   * Highlight a specific state
   */
  highlightState(layer) {
    // Reset all states first
    this.indiaLayer.eachLayer((l) => {
      const stateName = this.getStateName(l.feature);
      const stateInfo = this.stateData.get(stateName);
      const style = this.getStateStyle(stateInfo?.data);
      l.setStyle(style);
    });

    // Highlight selected state
    layer.setStyle({
      weight: 4,
      color: '#1d4ed8',
      fillOpacity: 0.9
    });
  }

  /**
   * Update heatmap data
   */
  updateHeatmapData(data) {
    const previousData = this.currentData;
    this.currentData = data;
    
    if (!this.indiaLayer) {
      console.warn('India layer not loaded yet');
      return;
    }

    // Update each state with animation for significant changes
    this.indiaLayer.eachLayer((layer) => {
      const stateName = this.getStateName(layer.feature);
      const stateData = data.states && data.states[stateName];
      const previousStateData = previousData?.states?.[stateName];
      
      // Store state data
      const stateInfo = this.stateData.get(stateName);
      if (stateInfo) {
        stateInfo.data = stateData;
      }

      // Check for significant changes
      const hasSignificantChange = this.hasSignificantChange(previousStateData, stateData);
      
      // Update layer style with optional animation
      const style = this.getStateStyle(stateData);
      
      if (hasSignificantChange && previousStateData) {
        // Animate the change
        this.animateStateChange(layer, style);
      } else {
        layer.setStyle(style);
      }

      // Update tooltip
      const tooltip = this.createStateTooltip(stateName, stateData);
      layer.setTooltipContent(tooltip);
    });
  }

  /**
   * Check if state data has significant changes
   */
  hasSignificantChange(oldData, newData) {
    if (!oldData || !newData) return false;
    
    const oldRisk = oldData.misinformation_risk || 0;
    const newRisk = newData.misinformation_risk || 0;
    const riskChange = Math.abs(newRisk - oldRisk);
    
    const oldEvents = oldData.event_count || 0;
    const newEvents = newData.event_count || 0;
    const eventChange = newEvents - oldEvents;
    
    return riskChange > 0.1 || eventChange > 5;
  }

  /**
   * Animate state changes
   */
  animateStateChange(layer, targetStyle) {
    // Add a pulse effect for significant changes
    const originalStyle = layer.options;
    
    // First, briefly highlight the change
    layer.setStyle({
      ...targetStyle,
      weight: 4,
      color: '#ffffff',
      fillOpacity: 0.9
    });
    
    // Then transition to the target style
    setTimeout(() => {
      layer.setStyle(targetStyle);
    }, 500);
  }

  /**
   * Get style for a state based on its data
   */
  getStateStyle(stateData) {
    if (!stateData) {
      return this.getDefaultStyle();
    }

    const intensity = stateData.misinformation_risk || 0;
    const color = Utils.color.getHeatmapColor(intensity);

    return {
      fillColor: color,
      weight: 2,
      opacity: 1,
      color: '#ffffff',
      fillOpacity: 0.7
    };
  }

  /**
   * Get default style for states without data
   */
  getDefaultStyle() {
    return {
      fillColor: '#e5e7eb',
      weight: 2,
      opacity: 1,
      color: '#ffffff',
      fillOpacity: 0.7
    };
  }

  /**
   * Create tooltip content for a state
   */
  createStateTooltip(stateName, stateData) {
    if (!stateData) {
      return `<div class="tooltip-content">
        <strong>${stateName}</strong><br>
        <span class="no-data">No data available</span>
      </div>`;
    }

    const risk = Utils.format.percentage(stateData.misinformation_risk || 0);
    const events = stateData.event_count || 0;
    const riskLevel = Utils.color.getRiskLevel(stateData.misinformation_risk || 0);

    return `<div class="tooltip-content">
      <strong>${stateName}</strong><br>
      <span class="risk-level risk-${riskLevel.toLowerCase()}">${riskLevel} Risk</span><br>
      <span class="metric">Risk Score: ${risk}</span><br>
      <span class="metric">Events: ${events}</span>
    </div>`;
  }

  /**
   * Setup map event handlers
   */
  setupEventHandlers() {
    // Handle map clicks (deselect states)
    this.map.on('click', (e) => {
      // Only handle clicks on the map itself, not on states
      if (e.originalEvent.target === this.map.getContainer()) {
        this.clearStateSelection();
      }
    });

    // Handle zoom events
    this.map.on('zoomend', () => {
      this.updateLayerStyles();
    });
  }

  /**
   * Clear state selection
   */
  clearStateSelection() {
    if (!this.indiaLayer) return;

    this.indiaLayer.eachLayer((layer) => {
      const stateName = this.getStateName(layer.feature);
      const stateInfo = this.stateData.get(stateName);
      const style = this.getStateStyle(stateInfo?.data);
      layer.setStyle(style);
    });
  }

  /**
   * Update layer styles based on zoom level
   */
  updateLayerStyles() {
    if (!this.indiaLayer) return;

    const zoom = this.map.getZoom();
    const weight = zoom > 6 ? 3 : 2;

    this.indiaLayer.eachLayer((layer) => {
      const currentStyle = layer.options;
      layer.setStyle({
        ...currentStyle,
        weight: weight
      });
    });
  }

  /**
   * Fit map to specific state
   */
  fitToState(stateName) {
    const stateInfo = this.stateData.get(stateName);
    if (stateInfo && stateInfo.layer) {
      this.map.fitBounds(stateInfo.layer.getBounds(), {
        padding: [50, 50]
      });
      this.highlightState(stateInfo.layer);
    }
  }

  /**
   * Reset map view to show all of India
   */
  resetView() {
    if (this.indiaLayer) {
      this.map.fitBounds(this.indiaLayer.getBounds(), {
        padding: [20, 20]
      });
      this.clearStateSelection();
    }
  }

  /**
   * Get fallback GeoJSON data for India states
   */
  getFallbackGeoJSON() {
    // Simplified GeoJSON with major Indian states
    // In a real application, you would load the complete GeoJSON file
    return {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "properties": { "NAME_1": "Maharashtra" },
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[72.6, 15.6], [80.9, 15.6], [80.9, 22.0], [72.6, 22.0], [72.6, 15.6]]]
          }
        },
        {
          "type": "Feature", 
          "properties": { "NAME_1": "Karnataka" },
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[74.0, 11.5], [78.6, 11.5], [78.6, 18.4], [74.0, 18.4], [74.0, 11.5]]]
          }
        },
        {
          "type": "Feature",
          "properties": { "NAME_1": "Tamil Nadu" },
          "geometry": {
            "type": "Polygon", 
            "coordinates": [[[76.2, 8.1], [80.3, 8.1], [80.3, 13.5], [76.2, 13.5], [76.2, 8.1]]]
          }
        },
        {
          "type": "Feature",
          "properties": { "NAME_1": "Gujarat" },
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[68.2, 20.1], [74.5, 20.1], [74.5, 24.7], [68.2, 24.7], [68.2, 20.1]]]
          }
        },
        {
          "type": "Feature",
          "properties": { "NAME_1": "Rajasthan" },
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[69.5, 23.0], [78.2, 23.0], [78.2, 30.2], [69.5, 30.2], [69.5, 23.0]]]
          }
        }
      ]
    };
  }

  /**
   * Add custom control to map
   */
  addCustomControl(control, position = 'topright') {
    control.addTo(this.map);
    return control;
  }

  /**
   * Remove custom control from map
   */
  removeCustomControl(control) {
    this.map.removeControl(control);
  }

  /**
   * Get map instance
   */
  getMap() {
    return this.map;
  }

  /**
   * Get state data
   */
  getStateData(stateName) {
    return this.stateData.get(stateName);
  }

  /**
   * Get all state names
   */
  getStateNames() {
    return Array.from(this.stateData.keys());
  }

  /**
   * Search for states by name
   */
  searchStates(searchTerm) {
    const term = searchTerm.toLowerCase();
    return this.getStateNames().filter(stateName => 
      stateName.toLowerCase().includes(term)
    );
  }

  /**
   * Highlight specific states
   */
  highlightStates(stateNames) {
    this.clearSearchHighlights();
    
    stateNames.forEach(stateName => {
      const stateInfo = this.stateData.get(stateName);
      if (stateInfo && stateInfo.layer) {
        stateInfo.layer.setStyle({
          weight: 4,
          color: '#FFC107',
          fillOpacity: 0.8,
          className: 'search-highlight'
        });
      }
    });
  }

  /**
   * Clear search highlights
   */
  clearSearchHighlights() {
    this.indiaLayer?.eachLayer((layer) => {
      const stateName = this.getStateName(layer.feature);
      const stateInfo = this.stateData.get(stateName);
      const style = this.getStateStyle(stateInfo?.data);
      layer.setStyle(style);
    });
  }

  /**
   * Destroy map instance
   */
  destroy() {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
    this.stateData.clear();
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HeatmapMap;
} else {
  window.HeatmapMap = HeatmapMap;
}