// Global variables
const API_URL = "http://localhost:8000/getContext";
const USER_ID = "admin";
const SOURCE = "chatgpt";
let lastErrorTime = 0;
const ERROR_COOLDOWN = 2 * 60 * 1000; // 2 minutes in ms

// Flag to prevent submission loops
let isSubmitting = false;
const SUBMISSION_TIMEOUT = 5000; // 5 seconds safety timeout

// Context enhancement toggle
let isEnhancementEnabled = true;

// API request tracking
const MAX_STORED_REQUESTS = 100; // Maximum number of requests to store

// Debug mode (controlled by storage)
let DEBUG = false;

// Default DOM selectors
const DEFAULT_SELECTORS = {
  form: 'form',
  textarea: 'textarea[data-id="root"]',
  submitButton: 'button[data-testid="send-button"]'
};

// Store current selectors
let currentSelectors = { ...DEFAULT_SELECTORS };

// Enhanced logging function
function debugLog(...args) {
  if (DEBUG) {
    console.log('[ChatGPT Enhancer]', ...args);
  }
}

// Function to show notification
function showNotification(message, isError = false, duration = 3000) {
  debugLog('Showing notification:', message, isError ? '(error)' : '');
  
  // Remove any existing notifications first
  const existingNotifications = document.querySelectorAll('.chatgpt-enhancer-notification');
  existingNotifications.forEach(notification => {
    notification.remove();
  });
  
  const notificationDiv = document.createElement('div');
  notificationDiv.textContent = message;
  notificationDiv.className = 'chatgpt-enhancer-notification';
  notificationDiv.style.position = 'fixed';
  notificationDiv.style.bottom = '20px';
  notificationDiv.style.right = '20px';
  notificationDiv.style.padding = '10px 20px';
  notificationDiv.style.borderRadius = '8px';
  notificationDiv.style.zIndex = '10000';
  notificationDiv.style.backgroundColor = isError ? '#f44336' : '#4CAF50';
  notificationDiv.style.color = 'white';
  notificationDiv.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
  notificationDiv.style.fontWeight = '500';
  notificationDiv.style.fontSize = '14px';
  notificationDiv.style.transition = 'opacity 0.5s ease-in-out';
  document.body.appendChild(notificationDiv);
  
  setTimeout(() => {
    notificationDiv.style.opacity = '0';
    setTimeout(() => {
      if (notificationDiv.parentNode) {
        document.body.removeChild(notificationDiv);
      }
    }, 500);
  }, duration);
}

// Inspect the DOM structure and log it
function analyzeDomStructure(forceFullAnalysis = false) {
  debugLog('Analyzing DOM structure...');
  
  // Try current selectors first
  const elements = getDomElements();
  const allElementsFound = elements.form && elements.textarea && elements.submitButton;
  
  // If all elements are found and we're not forcing a full analysis, return early
  if (allElementsFound && !forceFullAnalysis) {
    debugLog('All required elements found with current selectors');
    return true;
  }
  
  // Only perform full analysis if needed
  if (forceFullAnalysis || !allElementsFound) {
    debugLog('Performing full DOM analysis');
    
    // Log all forms
    const forms = document.querySelectorAll('form');
    debugLog(`Found ${forms.length} forms on the page`);
    forms.forEach((form, index) => {
      debugLog(`Form ${index}:`, form);
      debugLog(`Form ${index} HTML:`, form.outerHTML.substring(0, 300) + '...');
    });
    
    // Log textareas
    const textareas = document.querySelectorAll('textarea');
    debugLog(`Found ${textareas.length} textareas on the page`);
    textareas.forEach((textarea, index) => {
      debugLog(`Textarea ${index}:`, textarea);
      debugLog(`Textarea ${index} attributes:`, 
        Array.from(textarea.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
    });

    // Log contenteditable elements (for ProseMirror)
    const contentEditables = document.querySelectorAll('[contenteditable="true"]');
    debugLog(`Found ${contentEditables.length} contenteditable elements on the page`);
    contentEditables.forEach((el, index) => {
      debugLog(`Contenteditable ${index}:`, el);
      debugLog(`Contenteditable ${index} attributes:`, 
        Array.from(el.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
      if (el.id === 'prompt-textarea') {
        debugLog('Found ProseMirror editor with id="prompt-textarea"');
      }
    });
    
    // Log potential submit buttons
    const buttons = document.querySelectorAll('button');
    debugLog(`Found ${buttons.length} buttons on the page`);
    buttons.forEach((button, index) => {
      if (button.textContent.includes('Send') || 
          button.getAttribute('data-testid')?.includes('send') ||
          button.type === 'submit' ||
          button.getAttribute('aria-label')?.includes('send')) {
        debugLog(`Potential submit button ${index}:`, button);
        debugLog(`Button ${index} attributes:`, 
          Array.from(button.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
      }
    });
  }
  
  // Log the current state
  debugLog('Current selector results:', {
    formFound: !!elements.form,
    textareaFound: !!elements.textarea,
    submitButtonFound: !!elements.submitButton,
    allFound: allElementsFound
  });
  
  return allElementsFound;
}

// Function to get DOM elements using current selectors
function getDomElements() {
  debugLog('Getting DOM elements with selectors:', currentSelectors);
  const elements = {
    form: document.querySelector(currentSelectors.form),
    textarea: document.querySelector(currentSelectors.textarea) || document.getElementById('prompt-textarea'),
    submitButton: document.querySelector(currentSelectors.submitButton)
  };
  
  // Log missing elements
  Object.entries(elements).forEach(([key, element]) => {
    if (!element) {
      console.error(`ChatGPT Context Enhancer: Could not find ${key} element using selector "${currentSelectors[key]}"`);
    }
  });
  
  return elements;
}

// Function to get context from API
async function getEnhancedPrompt(query) {
  debugLog('Getting enhanced prompt for query:', query);
  
  // Record start time for measuring API request duration
  const startTime = Date.now();
  let endTime;
  let responseData;
  
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source: SOURCE,
        user_id: USER_ID,
        query: query
      })
    });
    
    endTime = Date.now();
    const duration = endTime - startTime;
    
    debugLog('API response status:', response.status);
    debugLog(`API response time: ${duration}ms`);
    
    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }
    
    responseData = await response.json();
    debugLog('API response data:', responseData);
    
    if (responseData.status !== "success") {
      throw new Error(`API returned error status: ${responseData.status}`);
    }
    
    // Save API request data
    saveApiRequestData({
      timestamp: new Date().toISOString(),
      query: query,
      response: responseData.prompt,
      duration: duration,
      status: "success"
    });
    
    return responseData.prompt;
  } catch (error) {
    endTime = Date.now();
    console.error("Error getting context:", error);
    lastErrorTime = Date.now();
    showNotification(`Error getting context: ${error.message}. Original prompt will be used for the next 2 minutes.`, true);
    
    // Save failed API request data
    saveApiRequestData({
      timestamp: new Date().toISOString(),
      query: query,
      response: null,
      duration: endTime - startTime,
      status: "error",
      error: error.message
    });
    
    throw error;
  }
}

// Create toggle button for context enhancement
function createToggleButton() {
  debugLog('Creating context enhancement toggle button');
  
  // Check if button already exists
  if (document.getElementById('context-enhancer-toggle')) {
    return;
  }
  
  // Check if we have the textarea to position relative to
  const elements = getDomElements();
  if (!elements.textarea || !elements.textarea.parentElement) {
    debugLog('Cannot create toggle button: textarea or its parent not found');
    // Try again in 1 second
    setTimeout(createToggleButton, 1000);
    return;
  }
  
  // Find a better container - try to find the chat input container
  const chatInputContainer = elements.textarea.closest('form') || 
                             elements.textarea.closest('[role="presentation"]') ||
                             elements.textarea.closest('.w-full') || 
                             elements.textarea.closest('[data-testid="chat-input-container"]') ||
                             elements.textarea.parentElement;
  
  // Create a container for our buttons
  const buttonContainer = document.createElement('div');
  buttonContainer.id = 'context-enhancer-buttons';
  buttonContainer.style.position = 'relative';
  buttonContainer.style.display = 'flex';
  buttonContainer.style.justifyContent = 'center'; // Center the button for better visibility
  buttonContainer.style.gap = '10px';
  buttonContainer.style.marginBottom = '10px';
  buttonContainer.style.marginTop = '10px';
  buttonContainer.style.zIndex = '1000';
  
  // Create the button
  const toggleButton = document.createElement('button');
  toggleButton.id = 'context-enhancer-toggle';
  toggleButton.textContent = isEnhancementEnabled ? '✓ Context Enhancement Enabled' : '○ Context Enhancement Disabled';
  toggleButton.title = isEnhancementEnabled ? 'Context enhancement is enabled (click to disable)' : 'Context enhancement is disabled (click to enable)';
  
  // Style the button with more prominent styling
  toggleButton.style.padding = '8px 16px';
  toggleButton.style.backgroundColor = isEnhancementEnabled ? '#4CAF50' : '#808080';
  toggleButton.style.color = 'white';
  toggleButton.style.border = '2px solid ' + (isEnhancementEnabled ? '#2E7D32' : '#606060');
  toggleButton.style.borderRadius = '6px';
  toggleButton.style.fontSize = '14px';
  toggleButton.style.fontWeight = 'bold';
  toggleButton.style.cursor = 'pointer';
  toggleButton.style.display = 'flex';
  toggleButton.style.alignItems = 'center';
  toggleButton.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
  toggleButton.style.transition = 'all 0.3s ease';
  toggleButton.style.width = '250px';
  toggleButton.style.justifyContent = 'center';
  
  // Add hover effect
  toggleButton.addEventListener('mouseover', function() {
    this.style.transform = 'scale(1.05)';
    this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
  });
  
  toggleButton.addEventListener('mouseout', function() {
    this.style.transform = 'scale(1)';
    this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
  });
  
  // Add click event listener
  toggleButton.addEventListener('click', function() {
    isEnhancementEnabled = !isEnhancementEnabled;
    toggleButton.textContent = isEnhancementEnabled ? '✓ Context Enhancement Enabled' : '○ Context Enhancement Disabled';
    toggleButton.title = isEnhancementEnabled ? 'Context enhancement is enabled (click to disable)' : 'Context enhancement is disabled (click to enable)';
    toggleButton.style.backgroundColor = isEnhancementEnabled ? '#4CAF50' : '#808080';
    toggleButton.style.border = '2px solid ' + (isEnhancementEnabled ? '#2E7D32' : '#606060');
    
    // Save preference to storage
    chrome.storage.sync.set({ isEnhancementEnabled: isEnhancementEnabled }, function() {
      debugLog('Saved enhancement preference:', isEnhancementEnabled);
    });
    
    // Show a more prominent notification
    showNotification(`Context enhancement ${isEnhancementEnabled ? 'ENABLED' : 'DISABLED'}`, false, 5000);
    
    // Log debug information about the current toggle state
    console.log('[ChatGPT Enhancer] Toggle state changed:', isEnhancementEnabled);
  });
  
  // Add button to container
  buttonContainer.appendChild(toggleButton);
  
  // Insert the container before the chat input
  if (chatInputContainer && chatInputContainer.parentElement) {
    chatInputContainer.parentElement.insertBefore(buttonContainer, chatInputContainer);
    debugLog('Toggle button created and added to the DOM');
  } else {
    debugLog('Could not find a suitable container for the toggle button');
    // Create a floating button instead
    toggleButton.style.position = 'fixed';
    toggleButton.style.bottom = '100px';
    toggleButton.style.right = '20px';
    toggleButton.style.zIndex = '10000';
    document.body.appendChild(toggleButton);
  }
  
  // Force console log of toggle state for debugging
  console.log('[ChatGPT Enhancer] Toggle button created with state:', isEnhancementEnabled);
}

// Save API request data to local storage
function saveApiRequestData(data) {
  debugLog('Saving API request data to local storage');
  
  chrome.storage.local.get(['apiRequests'], function(result) {
    let requests = result.apiRequests || [];
    
    // Add new request data
    requests.push(data);
    
    // Keep only the most recent requests
    if (requests.length > MAX_STORED_REQUESTS) {
      requests = requests.slice(-MAX_STORED_REQUESTS);
    }
    
    // Save back to storage
    chrome.storage.local.set({ apiRequests: requests }, function() {
      debugLog(`Saved API request data, total requests: ${requests.length}`);
    });
  });
}

// Load user preferences from storage
function loadPreferences() {
  debugLog('Loading user preferences from storage');
  chrome.storage.sync.get(['domSelectors', 'lastErrorTime', 'isEnhancementEnabled', 'debugMode'], function(result) {
    console.log('[ChatGPT Enhancer] Loaded preferences inside loadPreferences:', result);
    
    if (result.domSelectors) {
      currentSelectors = { ...DEFAULT_SELECTORS, ...result.domSelectors };
      debugLog('Loaded custom selectors:', currentSelectors);
    } else {
      debugLog('No custom selectors found, using defaults');
    }
    
    if (result.lastErrorTime) {
      lastErrorTime = result.lastErrorTime;
      debugLog('Loaded last error time:', new Date(lastErrorTime));
    }
    
    if (result.isEnhancementEnabled !== undefined) {
      isEnhancementEnabled = result.isEnhancementEnabled;
      console.log('[ChatGPT Enhancer] Enhancement state inside loadPreferences:', isEnhancementEnabled);
    }
    
    // Update DEBUG setting if present
    if (result.debugMode !== undefined) {
      DEBUG = result.debugMode;
      console.log('[ChatGPT Enhancer] Debug mode:', DEBUG ? 'enabled' : 'disabled');
    }
  });
}

// Toggle debug mode
function toggleDebugMode() {
  DEBUG = !DEBUG;
  console.log('[ChatGPT Enhancer] Debug mode:', DEBUG ? 'enabled' : 'disabled');
  
  // Save to storage
  chrome.storage.sync.set({ debugMode: DEBUG }, function() {
    console.log('[ChatGPT Enhancer] Saved debug mode preference:', DEBUG);
  });
  
  // Show notification
  showNotification(`Debug mode ${DEBUG ? 'enabled' : 'disabled'}`);
}

// Main function to intercept form submission
async function interceptSubmission(event) {
  // Force console log for debugging the interception
  console.log('[ChatGPT Enhancer] Intercepting submission, isEnhancementEnabled:', isEnhancementEnabled);
  
  debugLog('Intercepting submission event:', event);
  
  // Skip if enhancement is disabled
  if (!isEnhancementEnabled) {
    debugLog('Context enhancement is disabled, allowing normal submission');
    return;
  }
  
  // Skip if we're already in the process of submitting
  if (isSubmitting) {
    debugLog('Already submitting, skipping interception to prevent loops');
    return;
  }
  
  // Don't intercept if there was an error in the last 2 minutes
  if (Date.now() - lastErrorTime < ERROR_COOLDOWN) {
    debugLog('Skipping interception due to recent error');
    return;
  }
  
  const elements = getDomElements();
  debugLog('DOM elements found:', {
    form: !!elements.form,
    textarea: !!elements.textarea,
    submitButton: !!elements.submitButton
  });
  
  // If we can't find the necessary elements, show error and abort
  if (!elements.textarea) {
    lastErrorTime = Date.now();
    showNotification("Could not find ChatGPT input field. Please check extension settings.", true);
    return;
  }
  
  let originalQuery = '';
  if (elements.textarea.tagName.toLowerCase() === 'textarea') {
    originalQuery = elements.textarea.value.trim();
  } else if (elements.textarea.getAttribute('contenteditable') === 'true') {
    originalQuery = elements.textarea.textContent.trim();
  }
  debugLog('Original query:', originalQuery);
  
  if (!originalQuery) {
    debugLog('Empty query, skipping');
    return;
  }
  
  // Prevent the default submission
  if (event && event.preventDefault) {
    event.preventDefault();
  }
  if (event && event.stopPropagation) {
    event.stopPropagation();
  }
  debugLog('Prevented default event action');
  
  try {
    // Set flag at the beginning to prevent loops
    isSubmitting = true;
    
    showNotification("Getting context...");
    const enhancedPrompt = await getEnhancedPrompt(originalQuery);
    
    debugLog('Received enhanced prompt, updating textarea');
    
    // Update the input field with the enhanced prompt
    if (elements.textarea.tagName.toLowerCase() === 'textarea') {
      // First clear the field
      elements.textarea.value = '';
      
      // Force browser to recognize the change
      elements.textarea.dispatchEvent(new Event('input', { bubbles: true }));
      
      // Then set the new value
      elements.textarea.value = enhancedPrompt;
      elements.textarea.style.height = 'auto';
      elements.textarea.style.height = elements.textarea.scrollHeight + 'px';
    } else if (elements.textarea.getAttribute('contenteditable') === 'true') {
      // For contenteditable elements like ProseMirror
      elements.textarea.textContent = '';
      elements.textarea.dispatchEvent(new Event('input', { bubbles: true }));
      elements.textarea.textContent = enhancedPrompt;
    }
    
    // Force the input event and other necessary events to make sure ChatGPT recognizes the new content
    debugLog('Dispatching events to ensure content recognition');
    
    // Blur the field first
    elements.textarea.blur();
    
    // Then focus it again
    setTimeout(() => {
      elements.textarea.focus();
      
      // Trigger input event
      elements.textarea.dispatchEvent(new Event('input', { bubbles: true }));
      
      // Trigger change event
      elements.textarea.dispatchEvent(new Event('change', { bubbles: true }));
      
      // For ProseMirror, also dispatch a keydown event (Enter)
      if (elements.textarea.getAttribute('contenteditable') === 'true') {
        elements.textarea.dispatchEvent(new KeyboardEvent('keydown', { 
          key: 'Enter', 
          code: 'Enter',
          keyCode: 13,
          which: 13,
          bubbles: true
        }));
      }
      
      showNotification("Context added successfully");
      
      // Safety timeout to reset flag in case of errors
      const safetyTimeout = setTimeout(() => {
        debugLog('Safety timeout reached, resetting isSubmitting flag');
        isSubmitting = false;
      }, SUBMISSION_TIMEOUT);
      
      // Wait a bit longer before submitting to ensure ChatGPT has processed the new content
      setTimeout(() => {
        debugLog('Triggering original submit action after delay');
        
        // Try different methods to submit the form
        if (elements.submitButton && elements.submitButton.click) {
          debugLog('Clicking submit button directly');
          elements.submitButton.click();
        } else if (elements.form && elements.form.requestSubmit) {
          debugLog('Using form.requestSubmit()');
          elements.form.requestSubmit();
        } else if (elements.form && elements.form.submit) {
          debugLog('Using form.submit()');
          elements.form.submit();
        } else {
          debugLog('Dispatching form submit event');
          const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
          if (elements.form) {
            elements.form.dispatchEvent(submitEvent);
          }
        }
        
        // Reset flag after submission is processed
        setTimeout(() => {
          debugLog('Resetting isSubmitting flag after submission');
          isSubmitting = false;
          clearTimeout(safetyTimeout);
        }, 200);
      }, 800); // Increased delay to 800ms
    }, 200); // Increased focus delay
    
  } catch (error) {
    debugLog('Error in interceptSubmission:', error);
    isSubmitting = false; // Reset flag on error
    // Error already shown by getEnhancedPrompt
    // Don't continue with submission
  }
}

// Setup event listeners
function setupEventListeners() {
  debugLog('Setting up event listeners');
  console.log('[ChatGPT Enhancer] Setting up event listeners, isEnhancementEnabled:', isEnhancementEnabled);
  
  // Listen for form submissions
  document.addEventListener('submit', function(event) {
    debugLog('Form submit event detected:', event.target);
    console.log('[ChatGPT Enhancer] Form submit detected, isSubmitting:', isSubmitting, 'isEnhancementEnabled:', isEnhancementEnabled);
    
    // Skip if we're already in the submission process
    if (isSubmitting) {
      debugLog('Already submitting, allowing native form submission');
      return;
    }
    
    // Skip if enhancement is disabled
    if (!isEnhancementEnabled) {
      debugLog('Enhancement disabled, allowing native form submission');
      return;
    }
    
    const elements = getDomElements();
    if (elements.form && elements.form.contains(event.target)) {
      debugLog('Submit event matches our form');
      interceptSubmission(event);
    }
  }, true);
  
  // Listen for Enter key in textarea
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      debugLog('Enter keypress detected');
      console.log('[ChatGPT Enhancer] Enter keypress detected, isSubmitting:', isSubmitting, 'isEnhancementEnabled:', isEnhancementEnabled);
      
      // Skip if we're already in the submission process
      if (isSubmitting) {
        debugLog('Already submitting, allowing native keydown');
        return;
      }
      
      // Skip if enhancement is disabled
      if (!isEnhancementEnabled) {
        debugLog('Enhancement disabled, allowing native keydown');
        return;
      }
      
      const elements = getDomElements();
      const activeElement = document.activeElement;
      
      debugLog('Active element:', activeElement);
      
      if (elements.textarea && activeElement === elements.textarea) {
        debugLog('Enter pressed in our textarea');
        interceptSubmission({ 
          target: elements.form, 
          preventDefault: () => {
            debugLog('Preventing default for keydown event');
            event.preventDefault();
          }, 
          stopPropagation: () => {
            debugLog('Stopping propagation for keydown event');
            event.stopPropagation();
          } 
        });
      }
    }
  }, true);
  
  // Listen for click on submit button
  document.addEventListener('click', function(event) {
    debugLog('Click event detected:', event.target);
    
    // Skip if we're already in the submission process
    if (isSubmitting) {
      debugLog('Already submitting, allowing native click');
      return;
    }
    
    // Skip if enhancement is disabled
    if (!isEnhancementEnabled) {
      debugLog('Enhancement disabled, allowing native click');
      return;
    }
    
    const elements = getDomElements();
    if (elements.submitButton && (event.target === elements.submitButton || elements.submitButton.contains(event.target))) {
      console.log('[ChatGPT Enhancer] Submit button click detected, isEnhancementEnabled:', isEnhancementEnabled);
      debugLog('Click on submit button detected');
      interceptSubmission({
        target: elements.form,
        preventDefault: () => {
          debugLog('Preventing default for click event');
          event.preventDefault();
        },
        stopPropagation: () => {
          debugLog('Stopping propagation for click event');
          event.stopPropagation();
        }
      });
    }
  }, true);
  
  // Listen for storage changes (selector updates from popup)
  chrome.storage.onChanged.addListener(function(changes, namespace) {
    if (namespace === 'sync') {
      // Update selectors if changed
      if (changes.domSelectors) {
        currentSelectors = { ...DEFAULT_SELECTORS, ...changes.domSelectors.newValue };
        debugLog('Updated selectors from storage:', currentSelectors);
      }
      
      // Update enhancement state if changed
      if (changes.isEnhancementEnabled !== undefined) {
        isEnhancementEnabled = changes.isEnhancementEnabled.newValue;
        console.log('[ChatGPT Enhancer] Enhancement state updated from storage:', isEnhancementEnabled);
        
        // Update toggle button if it exists
        const toggleButton = document.getElementById('context-enhancer-toggle');
        if (toggleButton) {
          toggleButton.textContent = isEnhancementEnabled ? '✓ Context Enhancement Enabled' : '○ Context Enhancement Disabled';
          toggleButton.style.backgroundColor = isEnhancementEnabled ? '#4CAF50' : '#808080';
          toggleButton.style.border = '2px solid ' + (isEnhancementEnabled ? '#2E7D32' : '#606060');
        }
        
        // Show notification
        showNotification(`Context enhancement ${isEnhancementEnabled ? 'ENABLED' : 'DISABLED'}`, false, 3000);
      }
      
      // Update debug mode if changed
      if (changes.debugMode !== undefined) {
        DEBUG = changes.debugMode.newValue;
        console.log('[ChatGPT Enhancer] Debug mode updated:', DEBUG);
      }
    }
  });
  
  // Listen for messages from popup
  chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
    console.log('[ChatGPT Enhancer] Received message:', message);
    
    if (message.action === 'updateEnhancementState') {
      isEnhancementEnabled = message.isEnabled;
      console.log('[ChatGPT Enhancer] Enhancement state updated from message:', isEnhancementEnabled);
      
      // Update toggle button if it exists
      const toggleButton = document.getElementById('context-enhancer-toggle');
      if (toggleButton) {
        toggleButton.textContent = isEnhancementEnabled ? '✓ Context Enhancement Enabled' : '○ Context Enhancement Disabled';
        toggleButton.style.backgroundColor = isEnhancementEnabled ? '#4CAF50' : '#808080';
        toggleButton.style.border = '2px solid ' + (isEnhancementEnabled ? '#2E7D32' : '#606060');
      }
      
      // Show notification
      showNotification(`Context enhancement ${isEnhancementEnabled ? 'ENABLED' : 'DISABLED'}`, false, 3000);
      
      // Send response
      sendResponse({ success: true });
    }
    
    // Always return true to indicate async response
    return true;
  });
  
  // Listen for messages from background script
  window.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'CHATGPT_ENHANCER_CHECK') {
      debugLog('Received check message from background script');
      analyzeDomStructure(true); // Force full analysis
      showNotification('ChatGPT Context Enhancer is active');
    }
  });
  
  // Watch for DOM changes that might affect our UI elements
  const observer = new MutationObserver((mutations) => {
    // Check if buttons are missing (throttled)
    if (!document.getElementById('context-enhancer-toggle')) {
      // Only recreate at most once per second
      if (!window.buttonRecreationTimeout) {
        window.buttonRecreationTimeout = setTimeout(() => {
          debugLog('Buttons missing after DOM changes, recreating');
          createToggleButton();
          window.buttonRecreationTimeout = null;
        }, 1000);
      }
    }
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  debugLog('Event listeners setup complete');
}

// Initialize the extension
function initializeExtension() {
  console.log('[ChatGPT Enhancer] Initializing extension');
  
  // Load preferences right away to get the correct toggle state
  chrome.storage.sync.get(['domSelectors', 'lastErrorTime', 'isEnhancementEnabled', 'debugMode'], function(result) {
    console.log('[ChatGPT Enhancer] Loaded preferences:', result);
    
    if (result.domSelectors) {
      currentSelectors = { ...DEFAULT_SELECTORS, ...result.domSelectors };
      debugLog('Loaded custom selectors:', currentSelectors);
    }
    
    if (result.lastErrorTime) {
      lastErrorTime = result.lastErrorTime;
      debugLog('Loaded last error time:', new Date(lastErrorTime));
    }
    
    if (result.isEnhancementEnabled !== undefined) {
      isEnhancementEnabled = result.isEnhancementEnabled;
      console.log('[ChatGPT Enhancer] Initial enhancement state:', isEnhancementEnabled);
    }
    
    // Update DEBUG setting if present
    if (result.debugMode !== undefined) {
      DEBUG = result.debugMode;
      console.log('[ChatGPT Enhancer] Debug mode:', DEBUG ? 'enabled' : 'disabled');
    }
    
    // Continue initialization after loading preferences
    continueInitialization();
  });
}

// Continue initialization after preferences are loaded
function continueInitialization() {
  // Periodically check for UI elements and ensure buttons exist (backup for observer)
  const periodicUICheck = setInterval(() => {
    const elements = getDomElements();
    if (elements.form && elements.textarea && elements.submitButton) {
      // Check if the buttons exist
      if (!document.getElementById('context-enhancer-toggle')) {
        console.log('[ChatGPT Enhancer] Toggle button not found, creating it');
        createToggleButton();
      }
      
      // If all is well, clear the interval after a while (still keeping observer)
      if (document.getElementById('context-enhancer-toggle')) {
        debugLog('UI is fully set up, clearing periodic check');
        clearInterval(periodicUICheck);
      }
    }
  }, 3000);  // Check every 3 seconds as a backup
  
  // Also clear the check after 60 seconds no matter what
  setTimeout(() => {
    if (periodicUICheck) {
      clearInterval(periodicUICheck);
      debugLog('Cleared periodic UI check after timeout');
    }
  }, 60000);
  
  // Set up a mutation observer to watch for the ChatGPT UI to be ready
  const observer = new MutationObserver((mutations, obs) => {
    const elements = getDomElements();
    if (elements.form && elements.textarea && elements.submitButton) {
      debugLog('All required elements found, initializing UI');
      
      // Check if we've already created the buttons
      const hasToggleButton = !!document.getElementById('context-enhancer-toggle');
                        
      if (!hasToggleButton) {
        setupEventListeners();
        createToggleButton();
      }
      
      // Create a debug indicator element
      if (!document.querySelector('[data-chatgpt-enhancer="debug-indicator"]')) {
        const debugIndicator = document.createElement('div');
        debugIndicator.setAttribute('data-chatgpt-enhancer', 'debug-indicator');
        debugIndicator.style.display = 'none';
        document.body.appendChild(debugIndicator);
      }
      
      // Only disconnect if we've found everything AND created the buttons
      if (hasToggleButton) {
        debugLog('Everything is set up, disconnecting observer');
        obs.disconnect();
        debugLog('Initialization complete');
      }
    }
  });
  
  // Start observing with a more aggressive configuration
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    characterData: false,
    attributeFilter: ['class', 'id', 'data-testid']
  });
  
  // Safety timeout after 30 seconds
  setTimeout(() => {
    if (observer) {
      debugLog('Safety timeout reached, stopping observer');
      observer.disconnect();
      
      // Force attempt to set up UI even if not all elements were found
      setupEventListeners();
      createToggleButton();
    }
  }, 30000);
}

// Initialize when DOM is fully loaded
if (document.readyState === 'loading') {
  debugLog('Document still loading, adding DOMContentLoaded listener');
  document.addEventListener('DOMContentLoaded', initializeExtension);
} else {
  debugLog('Document already loaded, initializing immediately');
  initializeExtension();
}

// Log that extension is active
console.log('ChatGPT Context Enhancer is active');
debugLog('Extension initialized with debug mode ON');

// Add a visible debug element
if (DEBUG) {
  setTimeout(() => {
    const debugElement = document.createElement('div');
    debugElement.setAttribute('data-chatgpt-enhancer', 'debug-indicator');
    debugElement.style.position = 'fixed';
    debugElement.style.top = '10px';
    debugElement.style.right = '10px';
    debugElement.style.padding = '5px 10px';
    debugElement.style.background = 'rgba(0, 0, 0, 0.7)';
    debugElement.style.color = 'white';
    debugElement.style.borderRadius = '4px';
    debugElement.style.fontSize = '12px';
    debugElement.style.zIndex = '10000';
    debugElement.textContent = 'ChatGPT Enhancer Active (Debug Mode)';
    debugElement.addEventListener('click', analyzeDomStructure);
    document.body.appendChild(debugElement);
    
    // Create a test button to manually trigger the interception
    const testButton = document.createElement('button');
    testButton.textContent = 'Test Intercept';
    testButton.style.position = 'fixed';
    testButton.style.top = '40px';
    testButton.style.right = '10px';
    testButton.style.padding = '5px 10px';
    testButton.style.background = '#4285f4';
    testButton.style.color = 'white';
    testButton.style.border = 'none';
    testButton.style.borderRadius = '4px';
    testButton.style.fontSize = '12px';
    testButton.style.zIndex = '10000';
    testButton.addEventListener('click', () => {
      debugLog('Test button clicked');
      const elements = getDomElements();
      if (elements.textarea && elements.textarea.value.trim()) {
        interceptSubmission({
          target: elements.form || document.body,
          preventDefault: () => {},
          stopPropagation: () => {}
        });
      } else {
        showNotification('Please enter text in the ChatGPT input field first', true);
      }
    });
    document.body.appendChild(testButton);
  }, 2000);
} 