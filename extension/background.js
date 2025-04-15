// Background script for Sidetrip DeepContext

// Enhanced logging function
function debugLog(...args) {
  chrome.storage.sync.get(['debugMode'], function(result) {
    if (result.debugMode) {
      console.log('[Sidetrip DeepContext]', ...args);
    }
  });
}

// Log that the background script is running
console.log('[Sidetrip DeepContext] Background script loaded');

// Listen for installation or update
chrome.runtime.onInstalled.addListener((details) => {
  console.log('Extension installed or updated:', details.reason);
  
  // Reset any error cooldown on installation/update
  chrome.storage.sync.set({ lastErrorTime: 0 });
});

// Listen for tab updates to inject our script
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Only run for ChatGPT pages and when the page is fully loaded
  if (tab.url && 
      (tab.url.includes('chat.openai.com') || tab.url.includes('chatgpt.com')) && 
      changeInfo.status === 'complete') {
    console.log('ChatGPT page loaded, tab ID:', tabId);
    
    // Use scripting API to execute a script that confirms our content script is running
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      function: checkContentScriptRunning
    }).catch(error => {
      console.error('Error executing script:', error);
    });
  }
});

// Function to check if content script is running
function checkContentScriptRunning() {
  console.log('Checking if Sidetrip DeepContext content script is running...');
  
  // Check if our debug element exists
  const debugElement = document.querySelector('div[data-chatgpt-enhancer="debug-indicator"]');
  
  // if (!debugElement) {
  //   console.warn('Debug element not found, content script may not be running properly');
    
  //   // Create a notification to alert the user
  //   const notificationDiv = document.createElement('div');
  //   notificationDiv.textContent = 'Sidetrip DeepContext may not be working properly. Please check the console or try reloading.';
  //   notificationDiv.style.position = 'fixed';
  //   notificationDiv.style.top = '0';
  //   notificationDiv.style.left = '0';
  //   notificationDiv.style.right = '0';
  //   notificationDiv.style.padding = '10px';
  //   notificationDiv.style.backgroundColor = '#f44336';
  //   notificationDiv.style.color = 'white';
  //   notificationDiv.style.textAlign = 'center';
  //   notificationDiv.style.zIndex = '10000';
  //   document.body.appendChild(notificationDiv);
    
  //   // Try to force the content script to run some functions
  //   window.postMessage({ type: 'CHATGPT_ENHANCER_CHECK' }, '*');
  // } else {
  //   console.log('Content script appears to be running properly');
  // }
  
  // Attempt to identify common ChatGPT elements
  const chatInput = document.querySelector('textarea[data-id="root"]') || 
                    document.querySelector('textarea[placeholder*="Send a message"]') ||
                    document.querySelector('textarea[class*="text-input"]');
  
  const sendButton = document.querySelector('button[data-testid="send-button"]') ||
                     document.querySelector('button[aria-label*="Send message"]') ||
                     Array.from(document.querySelectorAll('button')).find(btn => 
                       btn.textContent.includes('Send') || 
                       btn.querySelector('svg[data-icon="send"]')
                     );
  
  console.log('ChatGPT input element found:', !!chatInput);
  console.log('ChatGPT send button found:', !!sendButton);
  
  if (chatInput) {
    console.log('ChatGPT input element attributes:', 
      Array.from(chatInput.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
  }
  
  if (sendButton) {
    console.log('ChatGPT send button attributes:', 
      Array.from(sendButton.attributes).map(attr => `${attr.name}="${attr.value}"`).join(', '));
  }
  
  // Recommend proper selectors
  if (chatInput || sendButton) {
    console.log('Recommended selectors based on page analysis:');
    if (chatInput) {
      console.log(`textarea: '${getOptimalSelector(chatInput)}'`);
    }
    if (sendButton) {
      console.log(`submitButton: '${getOptimalSelector(sendButton)}'`);
    }
  }
}

// Helper function to generate optimal CSS selector for an element
function getOptimalSelector(element) {
  // Try to use data-* attributes first
  for (const attr of element.attributes) {
    if (attr.name.startsWith('data-') && attr.value) {
      return `${element.tagName.toLowerCase()}[${attr.name}="${attr.value}"]`;
    }
  }
  
  // Try id
  if (element.id) {
    return `#${element.id}`;
  }
  
  // Try classes
  if (element.className && typeof element.className === 'string') {
    const classes = element.className.split(' ').filter(c => c && !c.includes(':'));
    if (classes.length > 0) {
      return `${element.tagName.toLowerCase()}.${classes[0]}`;
    }
  }
  
  // Fallback to tag name
  return element.tagName.toLowerCase();
} 