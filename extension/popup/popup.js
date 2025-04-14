// Default DOM selectors
const DEFAULT_SELECTORS = {
  form: 'form',
  textarea: 'textarea[data-id="root"]',
  submitButton: 'button[data-testid="send-button"]'
};

// DOM Elements
const formSelectorInput = document.getElementById('formSelector');
const textareaSelectorInput = document.getElementById('textareaSelector');
const submitButtonSelectorInput = document.getElementById('submitButtonSelector');
const saveButton = document.getElementById('saveBtn');
const resetButton = document.getElementById('resetBtn');
const enhancementToggle = document.getElementById('enhancementToggle');
const debugToggle = document.getElementById('debugToggle');
const exportButton = document.getElementById('exportBtn');
const clearDataButton = document.getElementById('clearDataBtn');
const statusMsg = document.getElementById('statusMsg');
const requestCountElem = document.getElementById('requestCount');
const avgTimeElem = document.getElementById('avgTime');
const successRateElem = document.getElementById('successRate');

// Load saved selectors
function loadSavedSelectors() {
  chrome.storage.sync.get(['domSelectors'], function(result) {
    if (result.domSelectors) {
      formSelectorInput.value = result.domSelectors.form || DEFAULT_SELECTORS.form;
      textareaSelectorInput.value = result.domSelectors.textarea || DEFAULT_SELECTORS.textarea;
      submitButtonSelectorInput.value = result.domSelectors.submitButton || DEFAULT_SELECTORS.submitButton;
    } else {
      resetToDefaults();
    }
  });
}

// Load toggle settings
function loadToggleSettings() {
  chrome.storage.sync.get(['isEnhancementEnabled', 'debugMode'], function(result) {
    enhancementToggle.checked = result.isEnhancementEnabled !== false; // Default to true
    debugToggle.checked = !!result.debugMode; // Default to false
  });
}

// Load API stats
function loadApiStats() {
  chrome.storage.local.get(['apiRequests'], function(result) {
    const requests = result.apiRequests || [];
    
    // Update stats
    requestCountElem.textContent = requests.length;
    
    if (requests.length > 0) {
      // Calculate average time
      const totalTime = requests.reduce((sum, req) => sum + req.duration, 0);
      const avgTime = Math.round(totalTime / requests.length);
      avgTimeElem.textContent = `${avgTime}ms`;
      
      // Calculate success rate
      const successCount = requests.filter(req => req.status === 'success').length;
      const successRate = Math.round((successCount / requests.length) * 100);
      successRateElem.textContent = `${successRate}%`;
    } else {
      avgTimeElem.textContent = '0ms';
      successRateElem.textContent = '0%';
    }
  });
}

// Save selectors to storage
function saveSelectors() {
  const selectors = {
    form: formSelectorInput.value.trim() || DEFAULT_SELECTORS.form,
    textarea: textareaSelectorInput.value.trim() || DEFAULT_SELECTORS.textarea,
    submitButton: submitButtonSelectorInput.value.trim() || DEFAULT_SELECTORS.submitButton
  };
  
  chrome.storage.sync.set({ domSelectors: selectors }, function() {
    showStatus('Settings saved successfully!', 'success');
  });
}

// Reset to default selectors
function resetToDefaults() {
  formSelectorInput.value = DEFAULT_SELECTORS.form;
  textareaSelectorInput.value = DEFAULT_SELECTORS.textarea;
  submitButtonSelectorInput.value = DEFAULT_SELECTORS.submitButton;
  
  chrome.storage.sync.set({ domSelectors: DEFAULT_SELECTORS }, function() {
    showStatus('Reset to default settings', 'success');
  });
}

// Toggle context enhancement
function toggleEnhancement() {
  const isEnabled = enhancementToggle.checked;
  chrome.storage.sync.set({ isEnhancementEnabled: isEnabled }, function() {
    showStatus(`Context enhancement ${isEnabled ? 'enabled' : 'disabled'}`, 'success');
    
    // Notify any open tabs
    chrome.tabs.query({url: ['*://chat.openai.com/*', '*://chatgpt.com/*']}, function(tabs) {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, { action: 'updateEnhancementState', isEnabled: isEnabled });
      });
    });
  });
}

// Toggle debug mode
function toggleDebugMode() {
  const isEnabled = debugToggle.checked;
  chrome.storage.sync.set({ debugMode: isEnabled }, function() {
    showStatus(`Debug mode ${isEnabled ? 'enabled' : 'disabled'}`, 'success');
  });
}

// Export API request data
function exportApiData() {
  chrome.storage.local.get(['apiRequests'], function(result) {
    const requests = result.apiRequests || [];
    
    if (requests.length === 0) {
      showStatus('No API request data to export', 'error');
      return;
    }
    
    // Create and download JSON file
    const jsonData = JSON.stringify(requests, null, 2);
    const blob = new Blob([jsonData], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // Create download link
    const a = document.createElement('a');
    a.href = url;
    a.download = `chatgpt-enhancer-data-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
    
    showStatus(`Exported ${requests.length} API requests`, 'success');
  });
}

// Clear API request data
function clearApiData() {
  if (confirm('Are you sure you want to clear all API request data?')) {
    chrome.storage.local.set({ apiRequests: [] }, function() {
      showStatus('API request data cleared', 'success');
      loadApiStats(); // Refresh stats
    });
  }
}

// Show status message
function showStatus(message, type) {
  statusMsg.textContent = message;
  statusMsg.className = 'status ' + type;
  statusMsg.style.display = 'block';
  
  setTimeout(() => {
    statusMsg.style.display = 'none';
  }, 3000);
}

// Event Listeners
saveButton.addEventListener('click', saveSelectors);
resetButton.addEventListener('click', resetToDefaults);
enhancementToggle.addEventListener('change', toggleEnhancement);
debugToggle.addEventListener('change', toggleDebugMode);
exportButton.addEventListener('click', exportApiData);
clearDataButton.addEventListener('click', clearApiData);

// Initialize
document.addEventListener('DOMContentLoaded', function() {
  loadSavedSelectors();
  loadToggleSettings();
  loadApiStats();
}); 