/**
 * Integration tests for responsive design
 * Tests layout, interactions, and functionality across different screen sizes
 */

describe('Responsive Design Integration Tests', () => {
  let originalInnerWidth;
  let originalInnerHeight;

  beforeEach(() => {
    // Store original dimensions
    originalInnerWidth = window.innerWidth;
    originalInnerHeight = window.innerHeight;

    // Setup DOM
    document.body.innerHTML = `
      <header class="header">
        <div class="header-container">
          <h1 class="header-title">Test App</h1>
          <div class="header-right">
            <button class="header-btn" id="info-btn">Info</button>
            <button class="header-btn" id="settings-btn">Settings</button>
          </div>
        </div>
      </header>
      
      <main class="main-content">
        <aside class="control-panel" id="control-panel">
          <div class="control-panel-header">
            <h2>Controls</h2>
            <button class="panel-toggle" id="panel-toggle">Toggle</button>
          </div>
          <div class="control-panel-content">
            <div class="control-group">
              <select id="time-range" class="control-select">
                <option value="24">24 hours</option>
              </select>
            </div>
            <div class="quick-actions">
              <button class="quick-action-btn">Action 1</button>
              <button class="quick-action-btn">Action 2</button>
            </div>
          </div>
        </aside>
        
        <div class="map-container">
          <div id="map" class="map"></div>
        </div>
      </main>
      
      <div class="modal-overlay" id="test-modal">
        <div class="modal">
          <div class="modal-content">Test Modal</div>
        </div>
      </div>
      
      <div class="toast-container" id="toast-container"></div>
    `;

    // Mock Utils
    global.Utils = {
      dom: {
        getElementById: jest.fn((id) => document.getElementById(id)),
        addEventListener: jest.fn(),
        show: jest.fn((element) => {
          if (element) element.style.display = 'block';
        }),
        hide: jest.fn((element) => {
          if (element) element.style.display = 'none';
        })
      }
    };
  });

  afterEach(() => {
    // Restore original dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: originalInnerWidth
    });
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: originalInnerHeight
    });

    document.body.innerHTML = '';
    jest.clearAllMocks();
  });

  /**
   * Helper function to simulate window resize
   */
  const resizeWindow = (width, height) => {
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: width
    });
    Object.defineProperty(window, 'innerHeight', {
      writable: true,
      configurable: true,
      value: height
    });

    // Trigger resize event
    window.dispatchEvent(new Event('resize'));
  };

  describe('Mobile Layout (≤ 768px)', () => {
    beforeEach(() => {
      resizeWindow(375, 667); // iPhone dimensions
    });

    test('should apply mobile styles to control panel', () => {
      const ui = new UIController();
      ui.updateResponsiveLayout();

      const controlPanel = document.getElementById('control-panel');
      expect(controlPanel.classList.contains('mobile')).toBe(true);
    });

    test('should stack quick action buttons vertically on mobile', () => {
      const quickActions = document.querySelector('.quick-actions');
      const computedStyle = window.getComputedStyle(quickActions);
      
      // In mobile, grid should be single column
      expect(computedStyle.gridTemplateColumns).toBe('1fr');
    });

    test('should make header buttons touch-friendly', () => {
      const headerBtn = document.getElementById('info-btn');
      const computedStyle = window.getComputedStyle(headerBtn);
      
      // Should have adequate touch target size (44px minimum)
      const minSize = parseInt(computedStyle.minHeight) || parseInt(computedStyle.height);
      expect(minSize).toBeGreaterThanOrEqual(44);
    });

    test('should handle control panel toggle on mobile', () => {
      const ui = new UIController();
      const controlPanel = document.getElementById('control-panel');
      const toggleBtn = document.getElementById('panel-toggle');

      // Simulate toggle click
      ui.toggleControlPanel();

      expect(controlPanel.classList.contains('open')).toBe(true);
    });

    test('should make modals full-width on mobile', () => {
      const modal = document.querySelector('.modal');
      const computedStyle = window.getComputedStyle(modal);
      
      expect(computedStyle.maxWidth).toBe('90vw');
    });

    test('should prevent zoom on form inputs', () => {
      const select = document.getElementById('time-range');
      expect(select.style.fontSize).toBe('16px'); // Prevents iOS zoom
    });
  });

  describe('Tablet Layout (769px - 1024px)', () => {
    beforeEach(() => {
      resizeWindow(768, 1024); // iPad dimensions
    });

    test('should use medium control panel width', () => {
      const ui = new UIController();
      ui.updateResponsiveLayout();

      const controlPanel = document.getElementById('control-panel');
      const computedStyle = window.getComputedStyle(controlPanel);
      
      expect(computedStyle.width).toBe('280px');
    });

    test('should use 2-column grid for quick actions', () => {
      const quickActions = document.querySelector('.quick-actions');
      const computedStyle = window.getComputedStyle(quickActions);
      
      expect(computedStyle.gridTemplateColumns).toBe('repeat(2, 1fr)');
    });

    test('should maintain readable modal width', () => {
      const modal = document.querySelector('.modal');
      const computedStyle = window.getComputedStyle(modal);
      
      expect(computedStyle.maxWidth).toBe('90vw');
    });
  });

  describe('Desktop Layout (≥ 1200px)', () => {
    beforeEach(() => {
      resizeWindow(1920, 1080); // Desktop dimensions
    });

    test('should use full control panel width', () => {
      const ui = new UIController();
      ui.updateResponsiveLayout();

      const controlPanel = document.getElementById('control-panel');
      const computedStyle = window.getComputedStyle(controlPanel);
      
      expect(computedStyle.width).toBe('360px');
    });

    test('should center header content with max width', () => {
      const headerContainer = document.querySelector('.header-container');
      const computedStyle = window.getComputedStyle(headerContainer);
      
      expect(computedStyle.maxWidth).toBe('1400px');
      expect(computedStyle.margin).toBe('0 auto');
    });

    test('should use optimal modal width', () => {
      const modal = document.querySelector('.modal');
      const computedStyle = window.getComputedStyle(modal);
      
      expect(computedStyle.maxWidth).toBe('800px');
    });
  });

  describe('Orientation Changes', () => {
    test('should handle portrait to landscape transition', () => {
      // Start in portrait
      resizeWindow(375, 667);
      
      const ui = new UIController();
      ui.updateResponsiveLayout();
      
      // Switch to landscape
      resizeWindow(667, 375);
      ui.updateResponsiveLayout();

      // Should adapt layout appropriately
      const controlPanel = document.getElementById('control-panel');
      expect(controlPanel.classList.contains('mobile')).toBe(true);
    });

    test('should maintain functionality across orientations', () => {
      const ui = new UIController();
      
      // Test in portrait
      resizeWindow(375, 667);
      ui.toggleControlPanel();
      
      const controlPanel = document.getElementById('control-panel');
      expect(controlPanel.classList.contains('open')).toBe(true);
      
      // Switch to landscape - should still work
      resizeWindow(667, 375);
      ui.toggleControlPanel();
      expect(controlPanel.classList.contains('open')).toBe(false);
    });
  });

  describe('Touch Interactions', () => {
    test('should handle touch events on mobile', () => {
      resizeWindow(375, 667);
      
      const button = document.getElementById('info-btn');
      const touchStartEvent = new TouchEvent('touchstart', {
        touches: [{ clientX: 100, clientY: 100 }]
      });
      
      button.dispatchEvent(touchStartEvent);
      
      // Should not throw errors
      expect(true).toBe(true);
    });

    test('should provide adequate touch targets', () => {
      resizeWindow(375, 667);
      
      const buttons = document.querySelectorAll('.header-btn, .quick-action-btn');
      
      buttons.forEach(button => {
        const rect = button.getBoundingClientRect();
        const size = Math.min(rect.width, rect.height);
        
        // WCAG recommends minimum 44px touch targets
        expect(size).toBeGreaterThanOrEqual(44);
      });
    });
  });

  describe('Accessibility Across Screen Sizes', () => {
    test('should maintain focus visibility on all screen sizes', () => {
      const screenSizes = [
        [375, 667],   // Mobile
        [768, 1024],  // Tablet
        [1920, 1080]  // Desktop
      ];

      screenSizes.forEach(([width, height]) => {
        resizeWindow(width, height);
        
        const button = document.getElementById('info-btn');
        button.focus();
        
        const computedStyle = window.getComputedStyle(button, ':focus-visible');
        expect(computedStyle.outline).toBeTruthy();
      });
    });

    test('should maintain keyboard navigation on mobile', () => {
      resizeWindow(375, 667);
      
      const ui = new UIController();
      const controlPanel = document.getElementById('control-panel');
      
      // Simulate keyboard toggle
      const keyEvent = new KeyboardEvent('keydown', { key: 'Enter' });
      document.getElementById('panel-toggle').dispatchEvent(keyEvent);
      
      // Should still be accessible via keyboard
      expect(controlPanel.getAttribute('aria-hidden')).toBeFalsy();
    });
  });

  describe('Performance Across Devices', () => {
    test('should disable hover effects on touch devices', () => {
      // Mock touch device
      Object.defineProperty(window, 'ontouchstart', {
        value: () => {},
        writable: true
      });
      
      resizeWindow(375, 667);
      
      const button = document.getElementById('info-btn');
      const hoverEvent = new MouseEvent('mouseover');
      
      button.dispatchEvent(hoverEvent);
      
      // Hover effects should be minimal on touch devices
      const computedStyle = window.getComputedStyle(button);
      expect(computedStyle.transform).toBe('none');
    });

    test('should optimize animations for low-end devices', () => {
      // Mock reduced motion preference
      Object.defineProperty(window, 'matchMedia', {
        value: jest.fn(() => ({
          matches: true, // prefers-reduced-motion: reduce
          addEventListener: jest.fn(),
          removeEventListener: jest.fn()
        }))
      });

      resizeWindow(375, 667);
      
      const ui = new UIController();
      
      // Animations should be disabled or simplified
      const modal = document.querySelector('.modal');
      const computedStyle = window.getComputedStyle(modal);
      
      expect(computedStyle.animationDuration).toBe('0.01ms');
    });
  });

  describe('Content Adaptation', () => {
    test('should truncate text appropriately on small screens', () => {
      resizeWindow(320, 568); // Small mobile
      
      const title = document.querySelector('.header-title');
      const computedStyle = window.getComputedStyle(title);
      
      expect(computedStyle.textOverflow).toBe('ellipsis');
      expect(computedStyle.whiteSpace).toBe('nowrap');
    });

    test('should stack elements vertically on narrow screens', () => {
      resizeWindow(320, 568);
      
      const headerRight = document.querySelector('.header-right');
      const computedStyle = window.getComputedStyle(headerRight);
      
      expect(computedStyle.flexDirection).toBe('column');
    });
  });

  describe('Print Styles', () => {
    test('should hide interactive elements when printing', () => {
      // Mock print media query
      Object.defineProperty(window, 'matchMedia', {
        value: jest.fn(() => ({
          matches: true, // print media
          addEventListener: jest.fn(),
          removeEventListener: jest.fn()
        }))
      });

      const controlPanel = document.getElementById('control-panel');
      const modal = document.getElementById('test-modal');
      
      const controlPanelStyle = window.getComputedStyle(controlPanel);
      const modalStyle = window.getComputedStyle(modal);
      
      expect(controlPanelStyle.display).toBe('none');
      expect(modalStyle.display).toBe('none');
    });

    test('should optimize map for printing', () => {
      const mapContainer = document.querySelector('.map-container');
      const computedStyle = window.getComputedStyle(mapContainer);
      
      expect(computedStyle.height).toBe('80vh');
      expect(computedStyle.border).toContain('2px solid');
    });
  });
});