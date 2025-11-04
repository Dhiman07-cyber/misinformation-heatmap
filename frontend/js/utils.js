/**
 * Utility functions for the misinformation heatmap application
 * Provides common functionality for DOM manipulation, data formatting,
 * accessibility features, and performance optimization.
 */

// Utility object to hold all utility functions
const Utils = {
  
  /**
   * DOM Utilities
   */
  dom: {
    /**
     * Get element by ID with error handling
     */
    getElementById(id) {
      const element = document.getElementById(id);
      if (!element) {
        console.warn(`Element with ID '${id}' not found`);
      }
      return element;
    },

    /**
     * Get elements by class name
     */
    getElementsByClassName(className) {
      return Array.from(document.getElementsByClassName(className));
    },

    /**
     * Create element with attributes and content
     */
    createElement(tag, attributes = {}, content = '') {
      const element = document.createElement(tag);
      
      Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
          element.className = value;
        } else if (key === 'innerHTML') {
          element.innerHTML = value;
        } else if (key === 'textContent') {
          element.textContent = value;
        } else {
          element.setAttribute(key, value);
        }
      });
      
      if (content) {
        element.textContent = content;
      }
      
      return element;
    },

    /**
     * Add event listener with error handling
     */
    addEventListener(element, event, handler, options = {}) {
      if (!element) {
        console.warn('Cannot add event listener to null element');
        return;
      }
      
      const wrappedHandler = (e) => {
        try {
          handler(e);
        } catch (error) {
          console.error(`Error in ${event} handler:`, error);
        }
      };
      
      element.addEventListener(event, wrappedHandler, options);
      return wrappedHandler;
    },

    /**
     * Show/hide element with accessibility
     */
    show(element, focusElement = null) {
      if (!element) return;
      
      element.style.display = '';
      element.setAttribute('aria-hidden', 'false');
      
      if (focusElement) {
        setTimeout(() => focusElement.focus(), 100);
      }
    },

    hide(element) {
      if (!element) return;
      
      element.style.display = 'none';
      element.setAttribute('aria-hidden', 'true');
    },

    /**
     * Toggle element visibility
     */
    toggle(element, show = null) {
      if (!element) return;
      
      const isVisible = element.style.display !== 'none';
      const shouldShow = show !== null ? show : !isVisible;
      
      if (shouldShow) {
        this.show(element);
      } else {
        this.hide(element);
      }
      
      return shouldShow;
    }
  },

  /**
   * Data Formatting Utilities
   */
  format: {
    /**
     * Format number with appropriate precision
     */
    number(value, decimals = 2) {
      if (typeof value !== 'number' || isNaN(value)) {
        return '-';
      }
      return value.toFixed(decimals);
    },

    /**
     * Format percentage
     */
    percentage(value, decimals = 1) {
      if (typeof value !== 'number' || isNaN(value)) {
        return '-';
      }
      return `${(value * 100).toFixed(decimals)}%`;
    },

    /**
     * Format date/time
     */
    dateTime(dateString, options = {}) {
      try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) {
          return 'Invalid date';
        }
        
        const defaultOptions = {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        };
        
        return date.toLocaleDateString('en-IN', { ...defaultOptions, ...options });
      } catch (error) {
        console.error('Date formatting error:', error);
        return 'Invalid date';
      }
    },

    /**
     * Format relative time (e.g., "2 hours ago")
     */
    relativeTime(dateString) {
      try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        
        return this.dateTime(dateString, { month: 'short', day: 'numeric' });
      } catch (error) {
        console.error('Relative time formatting error:', error);
        return 'Unknown';
      }
    },

    /**
     * Format large numbers with K/M suffixes
     */
    compactNumber(value) {
      if (typeof value !== 'number' || isNaN(value)) {
        return '-';
      }
      
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
      }
      if (value >= 1000) {
        return `${(value / 1000).toFixed(1)}K`;
      }
      return value.toString();
    },

    /**
     * Capitalize first letter of each word
     */
    titleCase(str) {
      if (typeof str !== 'string') return '';
      return str.replace(/\w\S*/g, (txt) => 
        txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
      );
    }
  },

  /**
   * Color Utilities
   */
  color: {
    /**
     * Get heatmap color based on intensity
     */
    getHeatmapColor(intensity) {
      if (typeof intensity !== 'number' || isNaN(intensity)) {
        return '#cccccc'; // Gray for invalid data
      }
      
      // Clamp intensity between 0 and 1
      const clampedIntensity = Math.max(0, Math.min(1, intensity));
      
      if (clampedIntensity < 0.3) {
        return '#2E8B57'; // Green - Low
      } else if (clampedIntensity < 0.6) {
        return '#FFD700'; // Yellow - Medium
      } else if (clampedIntensity < 0.8) {
        return '#FF6347'; // Orange - High
      } else {
        return '#DC143C'; // Red - Critical
      }
    },

    /**
     * Get risk level text based on intensity
     */
    getRiskLevel(intensity) {
      if (typeof intensity !== 'number' || isNaN(intensity)) {
        return 'Unknown';
      }
      
      const clampedIntensity = Math.max(0, Math.min(1, intensity));
      
      if (clampedIntensity < 0.3) return 'Low';
      if (clampedIntensity < 0.6) return 'Medium';
      if (clampedIntensity < 0.8) return 'High';
      return 'Critical';
    },

    /**
     * Convert hex color to rgba
     */
    hexToRgba(hex, alpha = 1) {
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      if (!result) return null;
      
      return `rgba(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}, ${alpha})`;
    }
  },

  /**
   * Validation Utilities
   */
  validate: {
    /**
     * Validate Indian state name
     */
    indianState(stateName) {
      const indianStates = [
        'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
        'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
        'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya',
        'mizoram', 'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim',
        'tamil nadu', 'telangana', 'tripura', 'uttar pradesh', 'uttarakhand',
        'west bengal', 'andaman and nicobar islands', 'chandigarh',
        'dadra and nagar haveli and daman and diu', 'delhi', 'jammu and kashmir',
        'ladakh', 'lakshadweep', 'puducherry'
      ];
      
      return indianStates.includes(stateName.toLowerCase());
    },

    /**
     * Validate time range
     */
    timeRange(hours) {
      return typeof hours === 'number' && hours > 0 && hours <= 168; // Max 7 days
    },

    /**
     * Validate intensity value
     */
    intensity(value) {
      return typeof value === 'number' && value >= 0 && value <= 1;
    }
  },

  /**
   * Performance Utilities
   */
  performance: {
    /**
     * Debounce function calls
     */
    debounce(func, wait, immediate = false) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          timeout = null;
          if (!immediate) func(...args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func(...args);
      };
    },

    /**
     * Throttle function calls
     */
    throttle(func, limit) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    /**
     * Measure execution time
     */
    measureTime(name, func) {
      const start = performance.now();
      const result = func();
      const end = performance.now();
      console.log(`${name} took ${(end - start).toFixed(2)} milliseconds`);
      return result;
    }
  },

  /**
   * Accessibility Utilities
   */
  accessibility: {
    /**
     * Announce to screen readers
     */
    announce(message, priority = 'polite') {
      const announcer = document.createElement('div');
      announcer.setAttribute('aria-live', priority);
      announcer.setAttribute('aria-atomic', 'true');
      announcer.className = 'sr-only';
      announcer.style.cssText = 'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;';
      
      document.body.appendChild(announcer);
      announcer.textContent = message;
      
      setTimeout(() => {
        document.body.removeChild(announcer);
      }, 1000);
    },

    /**
     * Manage focus trap for modals
     */
    trapFocus(element) {
      const focusableElements = element.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      
      const handleTabKey = (e) => {
        if (e.key !== 'Tab') return;
        
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      };
      
      element.addEventListener('keydown', handleTabKey);
      
      // Return cleanup function
      return () => {
        element.removeEventListener('keydown', handleTabKey);
      };
    },

    /**
     * Set up keyboard navigation
     */
    setupKeyboardNav(element, onEscape = null, onEnter = null) {
      const handleKeyDown = (e) => {
        switch (e.key) {
          case 'Escape':
            if (onEscape) onEscape(e);
            break;
          case 'Enter':
            if (onEnter) onEnter(e);
            break;
        }
      };
      
      element.addEventListener('keydown', handleKeyDown);
      
      return () => {
        element.removeEventListener('keydown', handleKeyDown);
      };
    }
  },

  /**
   * Storage Utilities
   */
  storage: {
    /**
     * Get item from localStorage with error handling
     */
    get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        console.error(`Error reading from localStorage (${key}):`, error);
        return defaultValue;
      }
    },

    /**
     * Set item in localStorage with error handling
     */
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        console.error(`Error writing to localStorage (${key}):`, error);
        return false;
      }
    },

    /**
     * Remove item from localStorage
     */
    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (error) {
        console.error(`Error removing from localStorage (${key}):`, error);
        return false;
      }
    },

    /**
     * Clear all localStorage
     */
    clear() {
      try {
        localStorage.clear();
        return true;
      } catch (error) {
        console.error('Error clearing localStorage:', error);
        return false;
      }
    }
  },

  /**
   * Network Utilities
   */
  network: {
    /**
     * Check if online
     */
    isOnline() {
      return navigator.onLine;
    },

    /**
     * Setup online/offline listeners
     */
    setupConnectionListeners(onOnline, onOffline) {
      const handleOnline = () => {
        console.log('Connection restored');
        if (onOnline) onOnline();
      };
      
      const handleOffline = () => {
        console.log('Connection lost');
        if (onOffline) onOffline();
      };
      
      window.addEventListener('online', handleOnline);
      window.addEventListener('offline', handleOffline);
      
      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
      };
    }
  },

  /**
   * Error Handling Utilities
   */
  error: {
    /**
     * Log error with context
     */
    log(error, context = '') {
      const errorInfo = {
        message: error.message || 'Unknown error',
        stack: error.stack,
        context,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      };
      
      console.error('Application Error:', errorInfo);
      
      // In production, you might want to send this to an error tracking service
      // this.sendToErrorService(errorInfo);
    },

    /**
     * Create user-friendly error message
     */
    getUserMessage(error) {
      if (error.name === 'NetworkError' || error.message.includes('fetch')) {
        return 'Network connection error. Please check your internet connection and try again.';
      }
      
      if (error.name === 'TypeError') {
        return 'A technical error occurred. Please refresh the page and try again.';
      }
      
      if (error.status === 404) {
        return 'The requested data could not be found.';
      }
      
      if (error.status === 500) {
        return 'Server error. Please try again later.';
      }
      
      return 'An unexpected error occurred. Please try again.';
    }
  }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = Utils;
} else {
  window.Utils = Utils;
}