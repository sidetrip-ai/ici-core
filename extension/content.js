// Global variables
const API_URL = "http://localhost:8000/getContext";
const USER_ID = "admin";
const SOURCE = "chatgpt";
let lastErrorTime = 0;
const ERROR_COOLDOWN = 2 * 60 * 1000; // 2 minutes in ms

// Constants
const MAX_STORED_REQUESTS = 100;  // Keep the 100 most recent requests in storage

// same:
{/* <button id="composer-submit-button" aria-label="Stop streaming" data-testid="stop-button" class="dark:disabled:bg-token-text-quaternary dark:disabled:text-token-main-surface-secondary flex items-center justify-center rounded-full transition-colors hover:opacity-70 disabled:text-[#f4f4f4] disabled:hover:opacity-100 dark:focus-visible:outline-white bg-black text-white disabled:bg-[#D7D7D7] dark:bg-white dark:text-black h-9 w-9"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="icon-lg"><rect x="7" y="7" width="10" height="10" rx="1.25" fill="currentColor"></rect></svg></button> */}

// Flag to prevent submission loops
let isSubmitting = false;
const SUBMISSION_TIMEOUT = 5000; // 5 seconds safety timeout

// Context enhancement toggle
let isEnhancementEnabled = true;

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

// Button style classes
const BUTTON_ENABLED_CLASSES = [
  'radix-state-open:bg-black/10', 'inline-flex', 'h-9', 'rounded-full', 'border',
  'text-[13px]', 'font-medium', 'duration-75', 'motion-safe:transition-all',
  'text-token-interactive-label-accent-default',
  'can-hover:hover:bg-[#BDDCF4]', 
  'dark:can-hover:hover:bg-[#1A416A]',
  'bg-token-composer-blue-bg', 
  'border-transparent', 
  'dark:bg-[#2A4A6D]', 
  'dark:text-[#48AAFF]'
];

const BUTTON_DISABLED_CLASSES = [
  'radix-state-open:bg-black/10', 'inline-flex', 'h-9', 'rounded-full', 'border',
  'text-[13px]', 'font-medium', 'duration-75', 'motion-safe:transition-all',
  'text-token-text-secondary', 
  'can-hover:hover:bg-token-main-surface-secondary',
  'bg-token-main-surface-secondary', 
  'border-token-border-light',
  'opacity-70'
];

// Enhanced logging function
function debugLog(...args) {
  if (DEBUG) {
    console.log('[Sidetrip DeepContext]', ...args);
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
  const allElementsFound = allElementsExist(elements);
  
  // If all elements are found and we're not forcing a full analysis, return early
  if (allElementsFound && !forceFullAnalysis) {
    debugLog('All required elements found with current selectors');
    return true;
  }
  
  // Only perform full analysis if needed
  if (forceFullAnalysis || !allElementsFound) {
    debugLog('Performing full DOM analysis');
    
    // Log current content state
    debugLog('Textarea content status:', elements.hasContent ? 'Has content' : 'Empty');
    debugLog('Button existence status:', elements.buttonExists ? 'Exists' : 'Not found');
    if (elements.buttonExists) {
      debugLog('Button disabled status:', elements.isButtonDisabled ? 'Disabled' : 'Enabled');
    }
    
    // Log all forms
    const forms = document.querySelectorAll('form');
    debugLog(`Found ${forms.length} forms on the page`);
    forms.forEach((form, index) => {
      debugLog(`Form ${index}:`, form);
      debugLog(`Form ${index} HTML:`, form.outerHTML.substring(0, 300) + '...');
    });
    
    // Log all textareas and contenteditable elements
    const textareas = document.querySelectorAll('textarea');
    debugLog(`Found ${textareas.length} textareas on the page`);
    textareas.forEach((textarea, index) => {
      debugLog(`Textarea ${index}:`, textarea);
      debugLog(`Textarea ${index} attributes:`, 
        Array.from(textarea.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
      
      // Log if it has content
      const hasContent = !!textarea.value.trim();
      debugLog(`Textarea ${index} has content:`, hasContent);
    });

    // Log contenteditable elements (for ProseMirror)
    const contentEditables = document.querySelectorAll('[contenteditable="true"]');
    debugLog(`Found ${contentEditables.length} contenteditable elements on the page`);
    contentEditables.forEach((el, index) => {
      debugLog(`Contenteditable ${index}:`, el);
      debugLog(`Contenteditable ${index} attributes:`, 
        Array.from(el.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
      
      // Log if it has content
      const hasContent = !!el.textContent.trim();
      debugLog(`Contenteditable ${index} has content:`, hasContent);
      
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
        
        // Log disabled state
        debugLog(`Button ${index} disabled:`, button.disabled);
        
        // Log visibility state
        const style = window.getComputedStyle(button);
        const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
        debugLog(`Button ${index} visible:`, isVisible);
      }
    });
  }
  
  // Log the current state
  debugLog('Current selector results:', {
    formFound: !!elements.form,
    textareaFound: !!elements.textarea,
    submitButtonFound: !!elements.submitButton,
    hasContent: elements.hasContent,
    buttonExists: elements.buttonExists,
    isButtonDisabled: elements.isButtonDisabled,
    allFound: allElementsFound
  });
  
  return allElementsFound;
}

function allElementsExist(elements) {
  debugLog('Checking if all elements exist:', elements);
  
  // Basic checks for form and textarea
  if (!elements.form || !elements.textarea) {
    return false;
  }
  
  // For submit button, we consider it optional if textarea is empty
  // This handles the case where the button doesn't appear until text is entered
  if (!elements.submitButton) {
    // If textarea has content, the button should exist
    if (elements.hasContent) {
      debugLog('Submit button missing but textarea has content - this is unexpected');
      return false;
    }
    
    // If textarea is empty, it's normal for button to be missing
    debugLog('Submit button missing but textarea is empty - this is normal');
    return true;
  }
  
  // If we get here, all required elements exist
  return true;
}

// Function to get DOM elements using current selectors
function getDomElements() {
  debugLog('Getting DOM elements with selectors:', currentSelectors);
  
  // First try with configured selectors
  let formElement = document.querySelector(currentSelectors.form);
  let textareaElement = document.querySelector(currentSelectors.textarea);
  let submitButtonElement = document.querySelector(currentSelectors.submitButton);
  
  // If textarea not found, try getting the contenteditable element with id="prompt-textarea"
  if (!textareaElement) {
    textareaElement = document.getElementById('prompt-textarea');
    debugLog('Falling back to prompt-textarea element:', textareaElement);
  }
  
  // If submit button not found, try common alternative selectors
  if (!submitButtonElement) {
    submitButtonElement = document.querySelector('button[data-testid="send-button"]') ||
                          document.querySelector('button[aria-label="Send prompt"]');
    debugLog('Falling back to alternative submit button selector:', submitButtonElement);
  }
  
  // Check if textarea has content
  let hasContent = false;
  if (textareaElement) {
    if (textareaElement.tagName.toLowerCase() === 'textarea') {
      hasContent = !!textareaElement.value.trim();
    } else if (textareaElement.getAttribute('contenteditable') === 'true') {
      hasContent = !!textareaElement.textContent.trim();
    }
  }
  debugLog('Textarea has content:', hasContent);
  
  // Button state flags
  const buttonExists = !!submitButtonElement;
  const buttonDisabled = buttonExists ? submitButtonElement.disabled : true;
  
  debugLog('Submit button exists:', buttonExists);
  if (buttonExists) {
    debugLog('Submit button disabled state:', buttonDisabled);
  } else {
    debugLog('Submit button not found in DOM (normal if textarea is empty)');
  }
  
  const elements = {
    form: formElement,
    textarea: textareaElement,
    submitButton: submitButtonElement,
    hasContent: hasContent,
    buttonExists: buttonExists,
    isButtonDisabled: buttonDisabled,
    // For convenience, true if button doesn't exist or is disabled
    isButtonClickable: buttonExists && !buttonDisabled
  };
  
  // Log missing elements but don't consider missing submit button as error when no content
  Object.entries(elements).forEach(([key, element]) => {
    if (!element && 
        key !== 'isButtonDisabled' && 
        key !== 'isButtonClickable' && 
        key !== 'buttonExists' && 
        key !== 'hasContent' && 
        !(key === 'submitButton' && !hasContent)) {
      console.error(`ChatGPT Context Enhancer: Could not find ${key} element using selector "${currentSelectors[key]}"`);
    }
  });
  
  return elements;
}

// Main function to intercept form submission
async function interceptSubmission(event) {
  // Force console log for debugging the interception
  console.log('[Sidetrip DeepContext] Intercepting submission, isEnhancementEnabled:', isEnhancementEnabled);
  
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
    submitButton: !!elements.submitButton,
    buttonExists: elements.buttonExists,
    isButtonDisabled: elements.isButtonDisabled,
    hasContent: elements.hasContent
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
  
  // Check if there's any input text before proceeding
  if (!originalQuery) {
    debugLog('Empty query, skipping');
    return;
  }
  
  // Set flag early to prevent multiple submissions
  isSubmitting = true;
  
  // Prevent the default submission
  if (event && event.preventDefault) {
    event.preventDefault();
  }
  if (event && event.stopPropagation) {
    event.stopPropagation();
  }
  debugLog('Prevented default event action');
  
  try {
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
    
    // Then focus it again and dispatch events
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
      
      // Wait for the submit button to appear with a polling mechanism
      (async () => {
        debugLog('Starting to wait for submit button to appear...');
        
        // Initial delay to allow ChatGPT to process the input
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Wait for the button with multiple attempts
        const result = await waitForSubmitButton(12, 300);
        
        if (result.success) {
          debugLog('Submit button is ready, proceeding with submission');
          
          try {
            // Click the button
            result.elements.submitButton.click();
            debugLog('Successfully clicked submit button');
            
            // Cancel any additional submissions
            clearTimeout(safetyTimeout);
            
            // Reset the flag after a small delay to allow click event to propagate
            setTimeout(() => {
              isSubmitting = false;
              debugLog('isSubmitting reset to false after button click initiated.');
            }, 50);
          } catch (clickError) {
            debugLog('Error clicking submit button:', clickError);
            isSubmitting = false;
            showNotification("Failed to click the submit button.", true);
          }
        } else {
          debugLog(`Failed to get clickable submit button: ${result.reason}`);
          
          if (result.reason === 'timeout') {
            showNotification("ChatGPT didn't enable the submit button. Try clicking it manually.", true);
          } else if (result.reason === 'no_content') {
            showNotification("Your message appears to be empty. Please add some text.", true);
          }
          
          isSubmitting = false;
          clearTimeout(safetyTimeout);
        }
      })();
    }, 200);
    
  } catch (error) {
    debugLog('Error in interceptSubmission:', error);
    isSubmitting = false; // Reset flag on error
    // Error already shown by getEnhancedPrompt
    // Don't continue with submission
  }
}

// Function to get context from API
async function getEnhancedPrompt(query) {
  debugLog('Getting enhanced prompt for query:', query);
  
  // Record start time for measuring API request duration
  const startTime = Date.now();
  let endNetworkTime; // Time when network response is received
  let endTotalTime;  // Time when processing is complete
  let responseData;
  
  try {
    debugLog('Sending API request at:', new Date(startTime).toISOString());
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
    
    // Record the exact time when response is received (network time)
    endNetworkTime = Date.now();
    const networkDuration = endNetworkTime - startTime;
    
    debugLog('API response received at:', new Date(endNetworkTime).toISOString());
    debugLog('API response status:', response.status);
    debugLog(`API network response time: ${networkDuration}ms`);
    
    if (!response.ok) {
      throw new Error(`API responded with status: ${response.status}`);
    }
    
    // Parse the response - this also takes time but isn't part of the network time
    const parseStartTime = Date.now();
    responseData = await response.json();
    endTotalTime = Date.now();
    
    const parseTime = endTotalTime - parseStartTime;
    const totalDuration = endTotalTime - startTime;
    
    debugLog('API response parsing time:', parseTime, 'ms');
    debugLog('API total time (network + parsing):', totalDuration, 'ms');
    debugLog('API response data:', responseData);
    
    if (responseData.status !== "success") {
      throw new Error(`API returned error status: ${responseData.status}`);
    }
    
    // Save API request data with precise timing
    saveApiRequestData({
      timestamp: new Date(startTime).toISOString(),
      responseTimestamp: new Date(endNetworkTime).toISOString(),
      query: query,
      response: responseData.prompt,
      networkDuration: networkDuration,     // Network time only
      totalDuration: totalDuration,         // Total time including parsing
      parsingDuration: parseTime,           // Just the parsing time
      status: "success"
    });
    
    return responseData.prompt;
  } catch (error) {
    endTotalTime = Date.now();
    console.error("Error getting context:", error);
    lastErrorTime = Date.now();
    showNotification(`Error getting context: ${error.message}. Original prompt will be used for the next 2 minutes.`, true);
    
    // Save failed API request data
    saveApiRequestData({
      timestamp: new Date(startTime).toISOString(),
      responseTimestamp: endNetworkTime ? new Date(endNetworkTime).toISOString() : null,
      endTime: new Date(endTotalTime).toISOString(),
      query: query,
      response: null,
      networkDuration: endNetworkTime ? endNetworkTime - startTime : null,
      totalDuration: endTotalTime - startTime,
      status: "error",
      error: error.message
    });
    
    throw error;
  }
}

// Create toggle button for context enhancement
function createToggleButton() {
  debugLog('Creating Sidetrip toggle button (New Design)');

  // Check if button already exists by a unique identifier
  if (document.querySelector('[data-sidetrip-button="true"]')) {
    debugLog('Sidetrip button already exists.');
    return;
  }

  // --- Find the container for action buttons ---
  // This selector targets the div containing Attach, Search, etc.
  const actionButtonContainer = document.querySelector(
    'form div.flex.items-center.gap-2.overflow-x-auto, ' + 
    'form div.max-xs\\:gap-1.flex.items-center.gap-2.overflow-x-auto, ' +
    // Alternative selectors for robustness
    'form div[class*="flex"][class*="items-center"][class*="gap-2"][class*="overflow-x-auto"]'
  );

  if (!actionButtonContainer) {
    debugLog('Cannot create Sidetrip button: Action button container not found.');
    // Try again later as the UI might still be loading
    setTimeout(createToggleButton, 1000);
    return;
  }
  
  // Log information about the action button container
  debugLog('Found action button container:', actionButtonContainer);
  debugLog(`Action button container has ${actionButtonContainer.children.length} children`);
  if (DEBUG) {
    // In debug mode, log details about existing buttons
    Array.from(actionButtonContainer.children).forEach((child, index) => {
      debugLog(`Child ${index}: ${child.tagName} - ${child.textContent.trim().substring(0, 20)}...`);
    });
  }
  

  // --- Create the Sidetrip Button Structure (mimicking ChatGPT buttons) ---

  // Outer div (mimics the structure around Reason/Search buttons)
  const wrapperDiv = document.createElement('div');
  // Add view transition name if needed, copying from target DOM
  wrapperDiv.style.viewTransitionName = 'var(--vt-composer-reason-action)'; 

  // Span container
  const spanContainer = document.createElement('span');
  spanContainer.className = 'inline-block';
  spanContainer.setAttribute('data-state', 'closed'); // Mimic Radix state

  // Button container div (apply main styling here)
  const buttonContainerDiv = document.createElement('div');
  // Apply classes from the target DOM for the button group look
  buttonContainerDiv.classList.add(...(isEnhancementEnabled ? BUTTON_ENABLED_CLASSES : BUTTON_DISABLED_CLASSES));

  // The actual button element
  const sidetripButton = document.createElement('button');
  sidetripButton.className = 'flex h-full min-w-8 items-center justify-center p-2';
  sidetripButton.setAttribute('aria-label', 'Sidetrip');
  sidetripButton.setAttribute('type', 'button');
  sidetripButton.setAttribute('aria-pressed', isEnhancementEnabled.toString());
  sidetripButton.setAttribute('data-state', 'closed'); // Mimic Radix state
  sidetripButton.setAttribute('data-sidetrip-button', 'true'); // Unique identifier
  sidetripButton.title = isEnhancementEnabled ? 
    'Sidetrip context enhancement is enabled (click to disable)' : 
    'Sidetrip context enhancement is disabled (click to enable)';

  // SVG Icon - using a lightbulb icon for Sidetrip
  // Create SVG element
  const svgIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svgIcon.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svgIcon.setAttribute('version', '1.1');
  svgIcon.setAttribute('viewBox', '0 0 411 411');
  svgIcon.classList.add('h-[18px]', 'w-[18px]');
  
  // Add the paths from the logo SVG with updated colors
  // (black → white, white → transparent)
  const paths = [
    { d: "M 0.00 0.00 L 411.00 0.00 L 411.00 411.00 L 0.00 411.00 L 0.00 0.00 Z", fill:"#2F2F2F" },
    { d: "M 198.98 25.01 C 205.65 24.88 212.32 25.08 219.00 24.96 C 228.67 24.81 238.12 26.69 247.59 28.49 C 262.67 31.33 277.48 37.17 291.34 43.64 C 303.73 50.28 315.74 57.31 326.18 66.84 C 338.02 76.36 348.13 87.71 357.08 99.95 C 372.29 122.51 383.79 148.09 387.86 175.12 C 389.63 188.99 390.90 202.43 389.50 216.41 C 387.97 243.28 379.85 269.98 366.20 293.18 C 363.50 298.40 360.37 303.12 356.73 307.72 C 349.25 317.95 341.07 328.18 331.30 336.30 C 312.17 353.68 289.41 366.82 264.81 374.75 C 254.80 377.28 244.69 380.27 234.42 381.46 C 221.88 382.82 209.49 383.81 196.89 382.34 C 181.79 381.66 167.77 377.82 153.36 373.64 C 146.08 371.39 139.22 367.76 132.16 364.84 C 115.35 356.78 99.88 345.42 86.24 332.76 C 63.64 310.48 45.84 281.90 38.03 251.00 C 34.74 240.14 32.79 229.29 32.16 217.95 C 31.62 197.52 31.53 178.19 37.38 158.39 C 40.23 149.07 42.58 139.74 47.01 131.00 C 52.01 118.19 59.54 107.53 67.24 96.23 C 82.56 77.12 99.91 60.33 121.55 48.51 C 145.21 34.78 171.68 26.77 198.98 25.01 Z", fill:"#ffffff" },
    { d: "M 214.00 48.96 C 221.48 48.79 228.61 50.13 236.00 50.97 C 243.43 51.85 250.81 53.70 257.88 56.14 C 264.47 58.50 271.11 60.14 277.19 63.78 C 296.17 72.80 313.62 85.71 327.31 101.69 C 346.64 123.46 358.87 150.49 363.78 179.11 C 365.83 194.76 365.91 210.33 364.02 225.99 C 363.22 234.77 360.53 242.75 358.26 251.21 C 356.74 256.97 354.28 262.32 351.74 267.69 C 346.48 280.42 338.37 292.07 329.76 302.76 C 315.61 320.04 297.72 333.88 277.69 343.70 C 262.74 350.62 246.95 355.33 230.61 357.53 C 220.84 358.44 211.42 359.85 201.59 358.50 C 186.86 357.50 172.30 354.65 158.40 349.60 C 147.19 346.01 136.49 339.64 126.30 333.72 C 113.87 326.01 102.87 314.76 92.89 304.12 C 80.22 289.09 69.98 271.58 64.14 252.75 C 60.35 241.60 57.26 229.78 56.86 217.96 C 56.49 211.93 55.62 206.05 56.04 199.98 C 56.92 186.86 57.76 171.95 62.85 159.70 C 68.99 165.70 75.09 171.76 81.21 177.79 C 84.11 180.88 87.12 183.30 87.02 187.95 C 87.04 201.96 87.00 216.03 86.93 230.05 C 86.48 235.35 89.93 237.45 93.21 240.79 C 99.09 245.98 103.62 252.32 109.73 257.27 C 115.41 263.13 121.70 268.55 126.87 274.86 C 123.31 282.23 122.70 290.67 125.62 298.35 C 130.56 308.67 143.08 314.53 154.16 311.16 C 166.76 307.69 175.17 293.04 170.44 280.60 C 168.09 272.02 160.09 266.08 151.65 264.34 C 145.51 263.03 140.59 265.17 134.90 266.95 L 134.83 266.97 L 134.90 266.95 C 134.43 267.06 133.96 267.16 133.49 267.27 C 121.91 255.29 110.00 243.57 98.22 231.78 C 95.31 229.03 96.08 225.64 95.91 222.00 C 96.20 212.63 95.72 203.26 96.16 193.90 C 98.95 195.77 101.41 197.86 103.74 200.27 C 109.63 206.33 115.62 212.29 121.47 218.39 C 119.99 222.62 117.76 226.37 117.81 230.98 C 117.64 239.90 122.46 249.46 130.94 253.10 C 142.02 259.91 157.57 254.69 163.38 243.36 C 167.98 235.12 166.60 224.49 160.80 217.20 C 156.51 212.07 150.48 208.76 143.77 208.20 C 138.19 207.50 133.74 209.67 128.76 211.75 C 125.64 209.38 122.93 206.60 120.25 203.75 C 113.43 196.90 106.59 190.08 99.70 183.29 C 97.60 181.20 96.53 179.33 96.41 176.33 C 95.60 162.93 96.18 149.43 95.98 136.00 C 95.76 131.79 96.86 127.07 95.88 122.99 C 93.23 118.90 88.91 116.00 85.94 112.07 C 89.24 107.33 93.06 103.05 97.03 98.87 C 104.79 105.76 111.76 113.56 119.26 120.74 C 121.61 123.16 124.64 125.46 126.29 128.42 C 126.64 130.04 126.46 131.82 126.36 133.46 C 125.70 140.97 126.10 148.45 125.93 156.01 C 126.00 159.33 125.82 163.33 127.91 166.11 C 130.14 169.10 133.13 171.59 135.75 174.25 C 153.76 192.24 171.74 210.26 189.75 228.25 C 192.62 230.95 195.41 233.66 197.80 236.81 C 195.66 241.41 194.49 245.89 194.82 251.02 C 194.14 264.98 209.36 276.42 222.65 273.66 C 231.17 272.07 239.75 265.39 241.61 256.61 C 243.04 251.18 243.06 245.54 240.68 240.36 C 236.79 230.85 226.16 225.10 216.09 226.07 C 212.31 226.63 208.74 228.23 205.16 229.54 C 182.73 207.32 160.63 184.91 138.28 162.72 C 136.47 160.92 136.03 159.61 135.97 157.06 C 135.84 147.03 136.17 136.97 136.02 126.94 C 136.10 124.46 135.02 123.23 133.37 121.61 C 123.35 111.86 113.43 102.11 104.22 91.58 C 105.63 89.85 107.41 87.12 109.86 87.05 C 113.05 88.95 115.62 92.14 118.26 94.74 C 169.12 145.78 220.85 197.14 271.60 248.21 C 266.70 257.19 265.98 268.04 272.71 276.28 C 275.42 279.19 278.85 283.57 283.04 284.16 C 287.52 285.10 292.28 285.45 296.81 284.73 C 305.52 283.14 312.65 276.38 314.92 267.86 C 317.17 260.94 315.28 253.52 311.48 247.54 C 307.47 241.37 300.15 238.03 292.99 237.45 C 287.98 237.03 282.84 239.44 278.15 240.96 C 274.76 238.33 271.71 235.35 268.74 232.26 C 222.58 185.71 176.01 139.77 129.89 93.12 C 125.68 88.69 120.99 84.94 117.08 80.25 C 119.23 78.57 121.47 77.05 123.88 75.76 C 127.03 78.39 129.94 81.27 132.75 84.25 C 147.38 98.94 162.16 113.54 176.70 128.30 C 178.67 130.26 180.09 131.01 182.94 131.03 C 192.64 131.17 202.36 130.83 212.05 130.97 C 216.88 130.63 219.60 135.36 222.77 138.23 C 228.22 143.96 234.14 149.26 239.45 155.11 C 234.85 163.36 234.07 174.22 239.94 182.05 C 247.11 192.25 262.06 195.28 272.64 188.66 C 278.67 185.34 282.61 178.42 283.82 171.81 C 285.26 161.20 278.57 149.21 268.17 145.85 C 260.57 143.69 253.23 145.05 246.07 147.95 C 238.22 139.77 230.45 131.59 222.07 123.94 C 220.45 122.45 219.27 122.02 217.06 121.98 C 207.36 121.82 197.65 122.18 187.95 122.02 C 182.96 122.12 180.01 118.43 176.71 115.29 C 161.98 100.14 146.54 85.57 132.05 70.20 C 140.11 65.58 148.53 61.26 157.36 58.31 C 164.88 55.70 172.70 52.72 180.61 51.57 C 183.36 50.82 185.48 54.10 187.31 55.69 C 195.64 64.65 205.02 72.73 212.99 81.99 C 211.21 87.05 209.43 91.71 209.66 97.21 C 210.29 106.69 216.57 115.44 225.84 118.15 C 235.28 121.70 245.31 118.08 252.04 111.03 C 256.63 106.47 257.64 99.79 257.49 93.60 C 257.39 86.53 252.98 79.95 247.79 75.48 C 238.98 70.56 229.05 70.97 219.97 75.01 C 215.62 71.60 212.33 67.50 208.32 63.68 C 203.79 58.98 198.94 54.91 194.93 49.75 C 201.39 48.43 207.46 49.10 214.00 48.96 Z", fill:"#2F2F2F" },
    { d: "M 229.38 81.41 C 233.67 80.26 238.76 80.95 242.36 83.67 C 248.06 88.40 249.73 95.65 246.33 102.34 C 241.76 111.32 228.52 112.90 222.25 104.76 C 215.33 96.70 219.53 84.49 229.38 81.41 Z", fill:"#2F2F2F" },
    { d: "M 100.28 106.27 C 100.75 106.75 100.75 106.75 100.28 106.27 Z", fill: "#ffffff" },
    { d: "M 107.28 112.27 C 107.75 112.75 107.75 112.75 107.28 112.27 Z", fill: "#ffffff" },
    { d: "M 80.70 120.27 C 82.77 122.04 85.21 124.02 86.44 126.49 C 87.31 129.13 87.04 132.24 87.08 135.00 C 86.80 146.67 87.25 158.35 86.87 170.01 C 81.79 165.76 77.54 160.79 72.72 156.28 C 70.34 154.05 68.08 151.66 66.07 149.09 C 69.65 138.81 74.29 129.10 80.70 120.27 Z", fill: "#2F2F2F" },
    { d: "M 261.92 154.02 C 272.89 155.44 278.91 170.57 270.08 178.24 C 264.44 186.51 250.68 183.93 246.81 175.21 C 241.33 165.43 251.02 152.21 261.92 154.02 Z", fill: "#2F2F2F" },
    { d: "M 141.36 217.36 C 148.64 216.94 156.20 223.10 156.54 230.58 C 157.42 237.01 153.42 243.08 147.60 245.61 C 139.74 248.91 130.23 244.12 128.00 235.94 C 125.18 227.24 132.40 217.79 141.36 217.36 Z", fill: "#2F2F2F" },
    { d: "M 216.41 235.40 C 225.47 233.72 234.94 242.67 232.91 251.91 C 231.41 258.24 226.16 264.73 219.01 264.19 C 211.99 264.84 205.80 259.22 204.31 252.63 C 202.94 244.47 208.23 236.87 216.41 235.40 Z", fill: "#2F2F2F" },
    { d: "M 121.28 247.27 C 121.75 247.75 121.75 247.75 121.28 247.27 Z", fill: "#ffffff" },
    { d: "M 288.35 247.34 C 296.72 244.99 307.10 253.07 306.05 261.97 C 305.74 268.24 301.66 273.74 295.62 275.58 C 288.15 277.80 280.17 273.57 277.77 266.20 C 274.97 258.12 279.87 249.03 288.35 247.34 Z", fill: "#2F2F2F" },
    { d: "M 134.83 266.97 L 134.90 266.95 L 134.83 266.97 Z", fill: "#ffffff" },
    { d: "M 146.38 273.35 C 152.73 272.81 159.40 276.44 161.23 282.80 C 164.64 292.22 156.48 304.08 146.00 302.06 C 135.33 301.96 129.17 287.64 135.46 279.50 C 137.98 275.79 142.09 274.03 146.38 273.35 Z", fill: "#2F2F2F" },
    { d: "M 345.28 277.27 C 345.75 277.75 345.75 277.75 345.28 277.27 Z", fill: "#ffffff" },
    { d: "M 100.28 347.27 C 100.75 347.75 100.75 347.75 100.28 347.27 Z", fill: "#ffffff" }
  ];
  
  // Create and append all paths to the SVG
  paths.forEach(pathData => {
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', pathData.d);
    path.setAttribute('fill', pathData.fill);
    svgIcon.appendChild(path);
  });

  // Text Span container
  const textSpan = document.createElement('span');

  // Text Div
  const textDiv = document.createElement('div');
  textDiv.className = '[display:var(--force-hide-label)] ps-1 pe-1 whitespace-nowrap';
  textDiv.textContent = 'Sidetrip';

  // --- Assemble the Button ---
  textSpan.appendChild(textDiv);
  sidetripButton.appendChild(svgIcon);
  sidetripButton.appendChild(textSpan);
  buttonContainerDiv.appendChild(sidetripButton);
  spanContainer.appendChild(buttonContainerDiv);
  wrapperDiv.appendChild(spanContainer);

  // --- Add Click Listener ---
  sidetripButton.addEventListener('click', function() {
    isEnhancementEnabled = !isEnhancementEnabled;

    // Update visual state
    buttonContainerDiv.classList.remove(...BUTTON_ENABLED_CLASSES, ...BUTTON_DISABLED_CLASSES);
    buttonContainerDiv.classList.add(...(isEnhancementEnabled ? BUTTON_ENABLED_CLASSES : BUTTON_DISABLED_CLASSES));
    sidetripButton.setAttribute('aria-pressed', isEnhancementEnabled.toString());
    sidetripButton.title = isEnhancementEnabled ? 
      'Sidetrip context enhancement is enabled (click to disable)' : 
      'Sidetrip context enhancement is disabled (click to enable)';

    // Save preference
    chrome.storage.sync.set({ isEnhancementEnabled: isEnhancementEnabled }, function() {
      debugLog('Saved enhancement preference:', isEnhancementEnabled);
    });

    // Show notification
    showNotification(`Sidetrip context enhancement ${isEnhancementEnabled ? 'ENABLED' : 'DISABLED'}`, false, 3000);
    console.log('[Sidetrip DeepContext] Toggle state changed:', isEnhancementEnabled);
  });

  // --- Insert the Button into the DOM ---
  // Insert as second-to-last element if possible, otherwise just append
  if (actionButtonContainer.children.length > 0) {
    actionButtonContainer.insertBefore(wrapperDiv, actionButtonContainer.lastChild);
    debugLog('Sidetrip button inserted as second-to-last in the action button container.');
  } else {
    actionButtonContainer.appendChild(wrapperDiv);
    debugLog('Action button container was empty, Sidetrip button appended.');
  }
  console.log('[Sidetrip DeepContext] Sidetrip button added with state:', isEnhancementEnabled);

  // --- Remove the old button if it exists ---
  const oldButtonContainer = document.getElementById('context-enhancer-buttons');
  if (oldButtonContainer) {
    oldButtonContainer.remove();
    debugLog('Removed old context enhancer button container.');
  }
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
    console.log('[Sidetrip DeepContext] Loaded preferences inside loadPreferences:', result);
    
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
      console.log('[Sidetrip DeepContext] Enhancement state inside loadPreferences:', isEnhancementEnabled);
    }
    
    // Update DEBUG setting if present
    if (result.debugMode !== undefined) {
      DEBUG = result.debugMode;
      console.log('[Sidetrip DeepContext] Debug mode:', DEBUG ? 'enabled' : 'disabled');
    }
  });
}

// Toggle debug mode
function toggleDebugMode() {
  DEBUG = !DEBUG;
  console.log('[Sidetrip DeepContext] Debug mode:', DEBUG ? 'enabled' : 'disabled');
  
  // Save to storage
  chrome.storage.sync.set({ debugMode: DEBUG }, function() {
    console.log('[Sidetrip DeepContext] Saved debug mode preference:', DEBUG);
  });
  
  // Show notification
  showNotification(`Debug mode ${DEBUG ? 'enabled' : 'disabled'}`);
}

// Setup event listeners
function setupEventListeners() {
  debugLog('Setting up event listeners');
  console.log('[Sidetrip DeepContext] Setting up event listeners, isEnhancementEnabled:', isEnhancementEnabled);
  
  // Listen for form submissions
  document.addEventListener('submit', function(event) {
    debugLog('Form submit event detected:', event.target);
    console.log('[Sidetrip DeepContext] Form submit detected, isSubmitting:', isSubmitting, 'isEnhancementEnabled:', isEnhancementEnabled);
    
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
      console.log('[Sidetrip DeepContext] Enter keypress detected, isSubmitting:', isSubmitting, 'isEnhancementEnabled:', isEnhancementEnabled);
      
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
      console.log('[Sidetrip DeepContext] Submit button click detected, isEnhancementEnabled:', isEnhancementEnabled);
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
        console.log('[Sidetrip DeepContext] Enhancement state updated from storage:', isEnhancementEnabled);
        
        // Update toggle button if it exists
        const toggleButton = document.querySelector('[data-sidetrip-button="true"]');
        if (toggleButton) {
          // Update the aria-pressed attribute
          toggleButton.setAttribute('aria-pressed', isEnhancementEnabled.toString());
          toggleButton.title = isEnhancementEnabled ? 
            'Sidetrip context enhancement is enabled (click to disable)' : 
            'Sidetrip context enhancement is disabled (click to enable)';
          
          // Update the styling by finding the parent div that contains the classes
          const buttonContainerDiv = toggleButton.closest('div.inline-flex');
          if (buttonContainerDiv) {
            // Remove all classes and add the appropriate ones
            buttonContainerDiv.classList.remove(...BUTTON_ENABLED_CLASSES, ...BUTTON_DISABLED_CLASSES);
            buttonContainerDiv.classList.add(...(isEnhancementEnabled ? BUTTON_ENABLED_CLASSES : BUTTON_DISABLED_CLASSES));
          }
        }
        
        // Show notification
        showNotification(`Sidetrip context enhancement ${isEnhancementEnabled ? 'ENABLED' : 'DISABLED'}`, false, 3000);
      }
      
      // Update debug mode if changed
      if (changes.debugMode !== undefined) {
        DEBUG = changes.debugMode.newValue;
        console.log('[Sidetrip DeepContext] Debug mode updated:', DEBUG);
      }
    }
  });
  
  // Listen for messages from popup
  chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
    console.log('[Sidetrip DeepContext] Received message:', message);
    
    if (message.action === 'updateEnhancementState') {
      isEnhancementEnabled = message.isEnabled;
      console.log('[Sidetrip DeepContext] Enhancement state updated from message:', isEnhancementEnabled);
      
      // Update toggle button if it exists
      const toggleButton = document.querySelector('[data-sidetrip-button="true"]');
      if (toggleButton) {
        // Update the aria-pressed attribute
        toggleButton.setAttribute('aria-pressed', isEnhancementEnabled.toString());
        toggleButton.title = isEnhancementEnabled ? 
          'Sidetrip context enhancement is enabled (click to disable)' : 
          'Sidetrip context enhancement is disabled (click to enable)';
        
        // Update the styling by finding the parent div that contains the classes
        const buttonContainerDiv = toggleButton.closest('div.inline-flex');
        if (buttonContainerDiv) {
          // Remove all classes and add the appropriate ones
          buttonContainerDiv.classList.remove(...BUTTON_ENABLED_CLASSES, ...BUTTON_DISABLED_CLASSES);
          buttonContainerDiv.classList.add(...(isEnhancementEnabled ? BUTTON_ENABLED_CLASSES : BUTTON_DISABLED_CLASSES));
        }
      }
      
      // Show notification
      showNotification(`Sidetrip context enhancement ${isEnhancementEnabled ? 'ENABLED' : 'DISABLED'}`, false, 3000);
      
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
      showNotification('Sidetrip DeepContext is active');
    }
  });
  
  // Watch for DOM changes that might affect our UI elements
  const observer = new MutationObserver((mutations) => {
    // Check if buttons are missing (throttled)
    if (!document.querySelector('[data-sidetrip-button="true"]')) {
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
  console.log('[Sidetrip DeepContext] Initializing extension');
  
  // Load preferences right away to get the correct toggle state
  chrome.storage.sync.get(['domSelectors', 'lastErrorTime', 'isEnhancementEnabled', 'debugMode'], function(result) {
    console.log('[Sidetrip DeepContext] Loaded preferences:', result);
    
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
      console.log('[Sidetrip DeepContext] Initial enhancement state:', isEnhancementEnabled);
    }
    
    // Update DEBUG setting if present
    if (result.debugMode !== undefined) {
      DEBUG = result.debugMode;
      console.log('[Sidetrip DeepContext] Debug mode:', DEBUG ? 'enabled' : 'disabled');
    }
    
    // Continue initialization after loading preferences
    continueInitialization();
  });
}

// Continue initialization after preferences are loaded
function continueInitialization() {
  // Set up the button observer to detect when the submit button appears or changes
  setupButtonObserver();
  
  // Periodically check for UI elements and ensure buttons exist (backup for observer)
  const periodicUICheck = setInterval(() => {
    const elements = getDomElements();
    
    // Log the current state periodically in debug mode
    if (DEBUG) {
      debugLog('Periodic UI check - current state:', {
        form: !!elements.form,
        textarea: !!elements.textarea,
        hasContent: elements.hasContent,
        buttonExists: elements.buttonExists,
        isButtonDisabled: elements.isButtonDisabled,
        isButtonClickable: elements.isButtonClickable
      });
    }
    
    if (elements.form && elements.textarea) {
      // Check if the toggle button exists
      if (!document.querySelector('[data-sidetrip-button="true"]')) {
        console.log('[Sidetrip DeepContext] Toggle button not found, creating it');
        createToggleButton();
      }
      
      // If all is well, clear the interval after a while (still keeping observer)
      if (document.querySelector('[data-sidetrip-button="true"]')) {
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
    if (elements.form && elements.textarea) {
      debugLog('All required elements found, initializing UI');
      
      // Check if we've already created the buttons
      const hasToggleButton = !!document.querySelector('[data-sidetrip-button="true"]');
      
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
console.log('Sidetrip DeepContext is active');
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
    debugElement.textContent = 'Sidetrip DeepContext Active (Debug Mode)';
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
    testButton.addEventListener('click', async () => {
      debugLog('Test button clicked');
      const elements = getDomElements();
      
      // Check if textarea has content
      let hasContent = false;
      if (elements.textarea) {
        if (elements.textarea.tagName.toLowerCase() === 'textarea') {
          hasContent = !!elements.textarea.value.trim();
        } else if (elements.textarea.getAttribute('contenteditable') === 'true') {
          hasContent = !!elements.textarea.textContent.trim();
        }
      }
      
      if (!hasContent) {
        // If no content, show notification
        showNotification('Please enter text in the ChatGPT input field first', true);
        return;
      }
      
      // Check if submit button exists and is clickable
      if (!elements.submitButton) {
        showNotification('Submit button not found. Waiting for it to appear...', true);
        
        // Try to wait for button to appear
        const result = await waitForSubmitButton(10, 300);
        if (!result.success) {
          showNotification(`Failed to find submit button: ${result.reason}`, true);
          return;
        }
        
        showNotification('Submit button found and ready!', false);
        return;
      }
      
      // If button exists but is disabled
      if (elements.submitButton && elements.isButtonDisabled) {
        showNotification('Submit button is disabled. Attempting to enable...', true);
        
        // Try to enable the button
        const enabled = checkAndEnableSubmitButton(elements.submitButton, elements.textarea);
        if (!enabled) {
          showNotification('Failed to enable submit button', true);
          return;
        }
        
        showNotification('Successfully enabled submit button!', false);
        return;
      }
      
      // If everything looks good, trigger the interception
      showNotification('Triggering intercept submission...', false);
      interceptSubmission({
        target: elements.form || document.body,
        preventDefault: () => {},
        stopPropagation: () => {}
      });
    });
    document.body.appendChild(testButton);
    
    // Create a button to analyze DOM
    const analyzeButton = document.createElement('button');
    analyzeButton.textContent = 'Analyze DOM';
    analyzeButton.style.position = 'fixed';
    analyzeButton.style.top = '70px';
    analyzeButton.style.right = '10px';
    analyzeButton.style.padding = '5px 10px';
    analyzeButton.style.background = '#FFA500';
    analyzeButton.style.color = 'white';
    analyzeButton.style.border = 'none';
    analyzeButton.style.borderRadius = '4px';
    analyzeButton.style.fontSize = '12px';
    analyzeButton.style.zIndex = '10000';
    analyzeButton.addEventListener('click', () => {
      analyzeDomStructure(true); // Force full analysis
      showNotification('DOM Analysis complete. Check console logs.', false);
    });
    document.body.appendChild(analyzeButton);
  }, 2000);
}

// Function to check if button is disabled and try to enable it
function checkAndEnableSubmitButton(submitButton, textarea) {
  // If button doesn't exist, we can't enable it
  if (!submitButton) {
    debugLog('Cannot enable button - button does not exist in DOM');
    return false;
  }
  
  // If textarea doesn't exist, we can't check content
  if (!textarea) {
    debugLog('Cannot enable button - textarea does not exist');
    return false;
  }
  
  // If button is not disabled, no need to do anything
  if (!submitButton.disabled) {
    debugLog('Button is already enabled');
    return true;
  }
  
  debugLog('Submit button is disabled, attempting to check why');
  
  // Check if textarea has content - this is usually a requirement for the button to be enabled
  let hasContent = false;
  if (textarea.tagName.toLowerCase() === 'textarea') {
    hasContent = !!textarea.value.trim();
  } else if (textarea.getAttribute('contenteditable') === 'true') {
    hasContent = !!textarea.textContent.trim();
  }
    
  debugLog('Textarea has content:', hasContent);
  
  if (!hasContent) {
    debugLog('Textarea is empty, this may be why the button is disabled');
    return false;
  }
  
  // Try to manually enable the button - this might not work if the site has other validation
  // but is worth trying in some cases
  try {
    debugLog('Trying to dispatch more events to ensure content is recognized');
    
    // Dispatch additional events that might trigger enable logic
    textarea.dispatchEvent(new Event('change', { bubbles: true }));
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
    
    // Check if that worked
    if (!submitButton.disabled) {
      debugLog('Button is now enabled after dispatching events');
      return true;
    }
    
    debugLog('Button is still disabled after dispatching events');
    
    // As a last resort, try to directly modify disabled property
    // This is not recommended and will likely be overridden by the site's JavaScript,
    // but in some cases it might help
    if (DEBUG) {
      debugLog('In debug mode, attempting to forcibly enable button (not recommended)');
      submitButton.disabled = false;
      return !submitButton.disabled; // Check if it worked
    }
  } catch (e) {
    debugLog('Error trying to enable button:', e);
  }
  
  return false;
}

// Function to wait for submit button to appear after content is added
async function waitForSubmitButton(maxAttempts = 10, delayMs = 200) {
  debugLog('Waiting for submit button to appear...');
  
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    attempts++;
    
    // Get current DOM state
    const elements = getDomElements();
    
    // If button exists and is clickable, we're done
    if (elements.buttonExists && !elements.isButtonDisabled) {
      debugLog(`Submit button found and clickable after ${attempts} attempts`);
      return {
        success: true,
        elements: elements
      };
    }
    
    // If textarea has no content, button won't appear
    if (!elements.hasContent) {
      debugLog('Textarea has no content, submit button will not appear');
      return {
        success: false,
        reason: 'no_content',
        elements: elements
      };
    }
    
    // If button exists but is disabled, try to enable it
    if (elements.buttonExists && elements.isButtonDisabled) {
      debugLog('Button exists but is disabled, attempting to enable');
      const enabled = checkAndEnableSubmitButton(elements.submitButton, elements.textarea);
      
      if (enabled) {
        debugLog('Successfully enabled button');
        // Re-get elements to check the updated state
        const updatedElements = getDomElements();
        return {
          success: true,
          elements: updatedElements 
        };
      }
    }
    
    // If we reach here, button either doesn't exist or couldn't be enabled
    // Wait before trying again
    debugLog(`Attempt ${attempts}/${maxAttempts}: Button not ready yet, waiting ${delayMs}ms...`);
    
    // Use increasing delays for later attempts
    const adjustedDelay = delayMs * (1 + attempts / 5);
    
    // Wait for the specified delay
    await new Promise(resolve => setTimeout(resolve, adjustedDelay));
  }
  
  // If we reach here, we've exceeded max attempts
  debugLog(`Failed to find clickable submit button after ${maxAttempts} attempts`);
  return {
    success: false,
    reason: 'timeout',
    elements: getDomElements() // Get final state
  };
}

// Setup a MutationObserver to watch for button appearance
function setupButtonObserver() {
  if (window.buttonObserver) {
    window.buttonObserver.disconnect();
    debugLog('Disconnected existing button observer');
  }
  
  debugLog('Setting up MutationObserver to watch for button appearance');
  
  const observer = new MutationObserver((mutations) => {
    // Check if any mutations affected buttons
    let buttonChanged = false;
    let textareaChanged = false;
    
    mutations.forEach(mutation => {
      // Check if the mutation involves adding nodes
      if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
        // Check if any of the added nodes are buttons or contain buttons
        mutation.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if node is a button
            if (node.tagName === 'BUTTON') {
              buttonChanged = true;
              
              // Log details if it looks like a submit button
              if (node.textContent?.includes('Send') || 
                  node.getAttribute('data-testid')?.includes('send') ||
                  node.id === 'composer-submit-button') {
                debugLog('Observed new submit button added to DOM:', node);
              }
            } 
            // Or if it contains buttons
            else if (node.querySelectorAll) {
              const buttons = node.querySelectorAll('button');
              if (buttons.length > 0) {
                buttonChanged = true;
                debugLog(`Observed ${buttons.length} buttons added inside a container`);
              }
            }
          }
        });
      }
      
      
      // Check for attribute changes on existing buttons
      if (mutation.type === 'attributes' && 
          mutation.target.tagName === 'BUTTON' && 
          mutation.attributeName === 'disabled') {
        buttonChanged = true;
        
        if (mutation.target.getAttribute('data-testid')?.includes('send')) {
          const isDisabled = mutation.target.disabled;
          debugLog(`Observed submit button disabled state changed to: ${isDisabled}`);
        }
      }
      
      // Check for textarea/contenteditable content changes
      if (mutation.target.tagName === 'TEXTAREA' || 
          (mutation.target.getAttribute && mutation.target.getAttribute('contenteditable') === 'true')) {
        textareaChanged = true;
      }
    });
    
    // If buttons changed, log the current state
    if (buttonChanged || textareaChanged) {
      const elements = getDomElements();
      debugLog('DOM changed, current elements state:', {
        hasContent: elements.hasContent,
        buttonExists: elements.buttonExists,
        buttonDisabled: elements.isButtonDisabled
      });
    }
  });
  
  // Start observing the body with configuration
  observer.observe(document.body, {
    childList: true,     // Watch for added/removed nodes
    subtree: true,       // Watch the entire subtree
    attributes: true,    // Watch for attribute changes
    attributeFilter: ['disabled', 'contenteditable', 'data-testid', 'id'] // Only these attributes
  });
  
  // Store the observer for later reference
  window.buttonObserver = observer;
  
  debugLog('Button observer setup complete');
  return observer;
} 