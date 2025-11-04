/**
 * Jest setup file for frontend integration tests
 * Configures global mocks, polyfills, and test utilities
 */

// Import required polyfills
import 'whatwg-fetch';
import { TextEncoder, TextDecoder } from 'util';

// Global polyfills
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock requestAnimationFrame
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0));
global.cancelAnimationFrame = jest.fn(id => clearTimeout(id));

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.sessionStorage = sessionStorageMock;

// Mock console methods for cleaner test output
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = jest.fn();
  console.warn = jest.fn();
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Mock Leaflet
global.L = {
  map: jest.fn(() => ({
    setView: jest.fn(),
    fitBounds: jest.fn(),
    on: jest.fn(),
    remove: jest.fn(),
    getZoom: jest.fn(() => 5),
    getBounds: jest.fn(),
    getContainer: jest.fn(() => document.createElement('div')),
    addControl: jest.fn(),
    removeControl: jest.fn()
  })),
  
  tileLayer: jest.fn(() => ({
    addTo: jest.fn()
  })),
  
  geoJSON: jest.fn(() => ({
    addTo: jest.fn(),
    getBounds: jest.fn(() => [[8, 68], [37, 98]]),
    eachLayer: jest.fn(),
    setStyle: jest.fn()
  })),
  
  control: {
    zoom: jest.fn(() => ({
      addTo: jest.fn()
    }))
  }
};

// Mock fetch globally
global.fetch = jest.fn();

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock Blob
global.Blob = jest.fn((content, options) => ({
  content,
  options,
  size: content ? content.length : 0,
  type: options ? options.type : ''
}));

// Mock File
global.File = jest.fn((bits, name, options) => ({
  bits,
  name,
  options,
  size: bits ? bits.length : 0,
  type: options ? options.type : ''
}));

// Mock geolocation
const mockGeolocation = {
  getCurrentPosition: jest.fn(),
  watchPosition: jest.fn(),
  clearWatch: jest.fn()
};
global.navigator.geolocation = mockGeolocation;

// Mock fullscreen API
Object.defineProperty(document, 'fullscreenElement', {
  writable: true,
  value: null
});

Object.defineProperty(document, 'exitFullscreen', {
  writable: true,
  value: jest.fn(() => Promise.resolve())
});

Object.defineProperty(Element.prototype, 'requestFullscreen', {
  writable: true,
  value: jest.fn(() => Promise.resolve())
});

// Mock CSS.supports
global.CSS = {
  supports: jest.fn(() => true)
};

// Mock performance API
global.performance = {
  ...global.performance,
  now: jest.fn(() => Date.now()),
  mark: jest.fn(),
  measure: jest.fn(),
  getEntriesByName: jest.fn(() => []),
  getEntriesByType: jest.fn(() => [])
};

// Mock MutationObserver
global.MutationObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
  takeRecords: jest.fn(() => [])
}));

// Mock touch events
global.TouchEvent = class TouchEvent extends Event {
  constructor(type, options = {}) {
    super(type, options);
    this.touches = options.touches || [];
    this.targetTouches = options.targetTouches || [];
    this.changedTouches = options.changedTouches || [];
  }
};

// Mock custom events
global.CustomEvent = class CustomEvent extends Event {
  constructor(type, options = {}) {
    super(type, options);
    this.detail = options.detail;
  }
};

// Test utilities
global.testUtils = {
  /**
   * Wait for next tick
   */
  nextTick: () => new Promise(resolve => setTimeout(resolve, 0)),
  
  /**
   * Wait for specified time
   */
  wait: (ms) => new Promise(resolve => setTimeout(resolve, ms)),
  
  /**
   * Simulate user interaction
   */
  simulateEvent: (element, eventType, options = {}) => {
    const event = new Event(eventType, { bubbles: true, ...options });
    Object.assign(event, options);
    element.dispatchEvent(event);
    return event;
  },
  
  /**
   * Create mock DOM element
   */
  createElement: (tag, attributes = {}) => {
    const element = document.createElement(tag);
    Object.entries(attributes).forEach(([key, value]) => {
      if (key === 'className') {
        element.className = value;
      } else if (key === 'innerHTML') {
        element.innerHTML = value;
      } else {
        element.setAttribute(key, value);
      }
    });
    return element;
  },
  
  /**
   * Mock API response
   */
  mockApiResponse: (data, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data))
  }),
  
  /**
   * Mock API error
   */
  mockApiError: (message, status = 500) => ({
    ok: false,
    status,
    statusText: message,
    json: () => Promise.resolve({ message })
  })
};

// Setup default mocks for application classes
beforeEach(() => {
  // Reset all mocks
  jest.clearAllMocks();
  
  // Reset DOM
  document.body.innerHTML = '';
  document.head.innerHTML = '';
  
  // Reset window properties
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: 1024
  });
  
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: 768
  });
  
  // Reset localStorage
  localStorageMock.getItem.mockReturnValue(null);
  localStorageMock.setItem.mockImplementation(() => {});
  localStorageMock.removeItem.mockImplementation(() => {});
  localStorageMock.clear.mockImplementation(() => {});
  
  // Reset fetch
  global.fetch.mockReset();
});

// Cleanup after each test
afterEach(() => {
  // Clear any remaining timers
  jest.clearAllTimers();
  
  // Clear any remaining intervals
  jest.useRealTimers();
});

// Global error handler for unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Suppress specific console warnings during tests
const originalConsoleWarn = console.warn;
console.warn = (...args) => {
  const message = args[0];
  
  // Suppress known warnings that are expected in test environment
  if (
    typeof message === 'string' && (
      message.includes('Warning: ReactDOM.render is deprecated') ||
      message.includes('Warning: componentWillMount has been renamed') ||
      message.includes('Leaflet') ||
      message.includes('ResizeObserver')
    )
  ) {
    return;
  }
  
  originalConsoleWarn.apply(console, args);
};