/**
 * API Service for Sidetrip DeepContext
 * Handles all API communication with robust error handling
 */

class ApiService {
  constructor() {
    this.apiUrl = "http://localhost:8000/getContext";
    this.maxRetries = 3;
    this.timeout = 15000; // 15 seconds
    this.retryBackoffFactor = 1.5;
    this.lastErrorTime = 0;
    this.errorCooldown = 2 * 60 * 1000; // 2 minutes
    this.errors = {
      count: 0,
      lastType: null,
      timestamp: 0
    };
    
    // Initialize configuration
    this.loadConfig();
  }
  
  /**
   * Load configuration from Chrome storage
   */
  async loadConfig() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(['apiUrl', 'maxRetries', 'timeout'], (result) => {
        if (chrome.runtime.lastError) {
          console.error('Error loading API config:', chrome.runtime.lastError);
        } else {
          if (result.apiUrl) this.apiUrl = result.apiUrl;
          if (result.maxRetries) this.maxRetries = result.maxRetries;
          if (result.timeout) this.timeout = result.timeout;
          console.log('[Sidetrip DeepContext] API service configured with URL:', this.apiUrl);
        }
        resolve();
      });
    });
  }
  
  /**
   * Get enhanced prompt from API with comprehensive error handling
   * @param {string} query - The original prompt
   * @param {string} userId - User identifier
   * @param {string} source - Source of the prompt
   * @returns {Promise<Object>} - Result with success status and data
   */
  async getEnhancedPrompt(query, userId = 'admin', source = 'chatgpt') {
    // Check error cooldown only for same type of errors
    const now = Date.now();
    if (this.errors.count > 3 && 
        now - this.errors.timestamp < this.errorCooldown) {
      console.log('[Sidetrip DeepContext] Too many recent errors, skipping API call');
      return {
        success: false, 
        data: query,
        error: 'Service temporarily unavailable due to recent errors'
      };
    }
    
    // Prepare request data
    const data = {
      query,
      user_id: userId,
      source
    };
    
    // Try API request with retries
    let retryCount = 0;
    let lastError = null;
    
    while (retryCount <= this.maxRetries) {
      try {
        // Create timeout controller
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        const startTime = Date.now();
        const response = await fetch(this.apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
          signal: controller.signal
        });
        
        // Clear timeout
        clearTimeout(timeoutId);
        
        // Handle HTTP errors
        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
        }
        
        // Parse and validate response
        const result = await response.json();
        
        // Validate response schema
        if (!result || !result.status) {
          throw new Error('Invalid API response schema');
        }
        
        // Handle API-level errors
        if (result.status !== 'success') {
          throw new Error(`API error: ${result.message || 'Unknown error'}`);
        }
        
        // Reset error counters on success
        this.errors.count = 0;
        
        // Log successful response time
        const responseTime = Date.now() - startTime;
        
        // Save request stats
        this.saveApiStats({
          timestamp: Date.now(),
          originalQuery: query,
          responseTime,
          success: true
        });
        
        return {
          success: true,
          data: result.prompt,
          responseTime
        };
        
      } catch (error) {
        lastError = error;
        
        // Categorize error
        const errorType = this.categorizeError(error);
        
        // Log detailed error information
        console.error(`[Sidetrip DeepContext] API error (attempt ${retryCount + 1}/${this.maxRetries + 1}):`, {
          type: errorType,
          message: error.message,
          url: this.apiUrl
        });
        
        // Update error tracking
        this.errors.count++;
        this.errors.lastType = errorType;
        this.errors.timestamp = Date.now();
        
        // Don't retry certain errors
        if (errorType === 'auth' || errorType === 'validation') {
          break;
        }
        
        // Add exponential backoff delay before retry
        if (retryCount < this.maxRetries) {
          const delay = Math.pow(this.retryBackoffFactor, retryCount) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
        }
        
        retryCount++;
      }
    }
    
    // All retries failed
    this.saveApiStats({
      timestamp: Date.now(),
      originalQuery: query,
      error: lastError.message,
      errorType: this.errors.lastType,
      success: false
    });
    
    // Notify user of failure if appropriate
    if (this.errors.count <= 3) {
      this.notifyUser(`API error: ${lastError.message}. Using original prompt.`);
    }
    
    return {
      success: false,
      data: query,
      error: lastError.message
    };
  }
  
  /**
   * Categorize the type of error
   * @param {Error} error - The error object
   * @returns {string} - Error category
   */
  categorizeError(error) {
    const message = error.message.toLowerCase();
    
    if (error.name === 'AbortError') return 'timeout';
    if (message.includes('networkerror')) return 'network';
    if (message.includes('401') || message.includes('403')) return 'auth';
    if (message.includes('404')) return 'not_found';
    if (message.includes('400') || message.includes('validation')) return 'validation';
    if (message.includes('500')) return 'server';
    
    return 'unknown';
  }
  
  /**
   * Save API request statistics for monitoring
   * @param {Object} data - Request statistics data
   */
  saveApiStats(data) {
    chrome.storage.local.get(['apiRequests'], function(result) {
      try {
        let requests = result.apiRequests || [];
        requests.unshift(data);
        
        // Keep only the most recent requests
        const MAX_STORED_REQUESTS = 100;
        if (requests.length > MAX_STORED_REQUESTS) {
          requests = requests.slice(0, MAX_STORED_REQUESTS);
        }
        
        chrome.storage.local.set({ 'apiRequests': requests }, function() {
          if (chrome.runtime.lastError) {
            console.error('[Sidetrip DeepContext] Error saving API stats:', chrome.runtime.lastError);
          }
        });
      } catch (error) {
        console.error('[Sidetrip DeepContext] Error processing API stats:', error);
      }
    });
  }
  
  /**
   * Send notification about API issues to the user
   * @param {string} message - The notification message
   */
  notifyUser(message) {
    chrome.runtime.sendMessage({
      action: 'showNotification',
      message,
      isError: true
    });
  }
  
  /**
   * Check if the API is accessible
   * @returns {Promise<Object>} - Status of the API
   */
  async checkApiHealth() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(this.apiUrl, {
        method: 'OPTIONS',
        signal: controller.signal
      }).catch(error => {
        throw error;
      });
      
      clearTimeout(timeoutId);
      
      return {
        available: response.ok,
        status: response.status,
        message: response.ok ? 'API available' : `API error: ${response.status} ${response.statusText}`
      };
    } catch (error) {
      return {
        available: false,
        status: 0,
        message: `API unavailable: ${error.message}`
      };
    }
  }
}

// Initialize and expose the API service
window.ApiService = new ApiService(); 