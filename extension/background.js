/**
 * Network Monitor - Browser Extension Background Script
 * Tracks active tab domain and reports to local API
 */

const API_ENDPOINT = 'http://localhost:7500/api/browser/active-tab';
const REPORT_INTERVAL = 5000; // 5 seconds
const BROWSER_NAME = 'zen'; // Or detect dynamically

let currentTabId = null;
let currentDomain = null;
let reportTimer = null;

/**
 * Extract domain from URL
 */
function extractDomain(url) {
  if (!url) return null;

  try {
    const urlObj = new URL(url);

    // Skip internal browser pages
    if (urlObj.protocol === 'about:' ||
        urlObj.protocol === 'moz-extension:' ||
        urlObj.protocol === 'chrome:') {
      return null;
    }

    // Return hostname (e.g., "www.netflix.com")
    return urlObj.hostname;
  } catch (e) {
    console.error('Error extracting domain:', e);
    return null;
  }
}

/**
 * Extract parent domain from full domain
 * Example: www.netflix.com -> netflix.com
 */
function extractParentDomain(domain) {
  if (!domain) return null;

  const parts = domain.split('.');

  // Handle special cases
  if (parts.length <= 2) {
    return domain; // Already a parent domain
  }

  // Remove subdomain (keep last 2 parts)
  return parts.slice(-2).join('.');
}

/**
 * Report current domain to API
 */
async function reportDomain(domain) {
  if (!domain) return;

  const payload = {
    domain: extractParentDomain(domain), // Send parent domain for rollup
    timestamp: Math.floor(Date.now() / 1000), // Unix timestamp
    browser: BROWSER_NAME
  };

  try {
    const response = await fetch(API_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      console.warn('API responded with status:', response.status);
    }
  } catch (error) {
    // API might be offline - fail silently
    console.debug('Could not reach API (this is normal if daemon is not running)');
  }
}

/**
 * Start periodic reporting
 */
function startReporting(domain) {
  // Clear existing timer
  if (reportTimer) {
    clearInterval(reportTimer);
  }

  currentDomain = domain;

  // Report immediately
  reportDomain(domain);

  // Report every REPORT_INTERVAL
  reportTimer = setInterval(() => {
    reportDomain(currentDomain);
  }, REPORT_INTERVAL);
}

/**
 * Stop periodic reporting
 */
function stopReporting() {
  if (reportTimer) {
    clearInterval(reportTimer);
    reportTimer = null;
  }
  currentDomain = null;
}

/**
 * Handle tab activation (user switches tabs)
 */
async function handleTabActivated(activeInfo) {
  currentTabId = activeInfo.tabId;

  try {
    const tab = await browser.tabs.get(currentTabId);
    const domain = extractDomain(tab.url);

    if (domain) {
      startReporting(domain);
    } else {
      stopReporting();
    }
  } catch (error) {
    console.error('Error getting tab info:', error);
    stopReporting();
  }
}

/**
 * Handle tab URL update (user navigates within same tab)
 */
function handleTabUpdated(tabId, changeInfo, tab) {
  // Only process the active tab
  if (tabId !== currentTabId) return;

  // Only when URL changes
  if (!changeInfo.url) return;

  const domain = extractDomain(changeInfo.url);

  if (domain && domain !== currentDomain) {
    startReporting(domain);
  } else if (!domain) {
    stopReporting();
  }
}

/**
 * Initialize extension on startup
 */
async function initialize() {
  console.log('Network Monitor extension initialized');

  // Get currently active tab
  try {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      const tab = tabs[0];
      currentTabId = tab.id;
      const domain = extractDomain(tab.url);
      if (domain) {
        startReporting(domain);
      }
    }
  } catch (error) {
    console.error('Error during initialization:', error);
  }

  // Set up event listeners
  browser.tabs.onActivated.addListener(handleTabActivated);
  browser.tabs.onUpdated.addListener(handleTabUpdated);
}

// Start extension
initialize();
