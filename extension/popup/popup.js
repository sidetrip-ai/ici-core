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
    const apiRequests = result.apiRequests || [];
    const apiStatsSection = document.getElementById('apiStatsSection');
    
    if (apiRequests.length === 0) {
      requestCountElem.textContent = '0';
      avgTimeElem.textContent = '0ms';
      successRateElem.textContent = '0%';
      apiStatsSection.classList.remove('has-dual-times');
      return;
    }
    
    // Process the data to add derived fields for better analysis
    const processedRequests = apiRequests.map(req => {
      const processed = {...req};
      
      // For backward compatibility with old data format
      if (!processed.networkDuration && processed.duration) {
        processed.networkDuration = processed.duration;
      }
      
      // If we only have networkDuration but no totalDuration, use networkDuration for both
      if (processed.networkDuration && !processed.totalDuration) {
        processed.totalDuration = processed.networkDuration;
      }
      
      // If we only have totalDuration but no networkDuration, estimate network as 90% of total
      if (!processed.networkDuration && processed.totalDuration) {
        processed.networkDuration = Math.round(processed.totalDuration * 0.9);
      }
      
      return processed;
    });
    
    // Calculate stats
    const count = processedRequests.length;
    
    // Calculate average total duration (including processing)
    const totalDurations = processedRequests.map(req => req.totalDuration || 0);
    const avgTotalTime = totalDurations.length > 0 
      ? Math.round(totalDurations.reduce((sum, time) => sum + time, 0) / totalDurations.length) 
      : 0;
    
    // Calculate average network time
    const networkDurations = processedRequests.map(req => req.networkDuration || 0);
    const avgNetworkTime = networkDurations.length > 0 
      ? Math.round(networkDurations.reduce((sum, time) => sum + time, 0) / networkDurations.length) 
      : 0;
    
    // Calculate success rate
    const successCount = processedRequests.filter(req => req.status === 'success').length;
    const successRate = Math.round((successCount / count) * 100);
    
    // Update the DOM elements with the stats
    requestCountElem.textContent = count;
    
    // Always show both network and total times if they're available and different enough to be meaningful
    if (avgNetworkTime > 0 && avgTotalTime > 0 && Math.abs(avgNetworkTime - avgTotalTime) > 2) {
      avgTimeElem.textContent = `${avgNetworkTime}/${avgTotalTime}ms`;
      avgTimeElem.title = `Network: ${avgNetworkTime}ms / Total: ${avgTotalTime}ms (includes parsing time)`;
      apiStatsSection.classList.add('has-dual-times');
    } else {
      // Otherwise just show the total time
      avgTimeElem.textContent = `${avgTotalTime}ms`;
      avgTimeElem.title = `Average response time: ${avgTotalTime}ms`;
      apiStatsSection.classList.remove('has-dual-times');
    }
    
    successRateElem.textContent = `${successRate}%`;
    
    // Log the statistics for debugging
    console.log('[Sidetrip DeepContext] API Stats:', {
      requestCount: count,
      avgNetworkTime: avgNetworkTime,
      avgTotalTime: avgTotalTime,
      successRate: successRate,
      showingDualTimes: avgNetworkTime > 0 && avgTotalTime > 0 && Math.abs(avgNetworkTime - avgTotalTime) > 2
    });
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
    
    // Process data to add additional derived fields and ensure consistent format
    const processedRequests = requests.map(req => {
      // Start with a copy of the request
      const processed = { ...req };
      
      // Ensure networkDuration is populated
      if (!processed.networkDuration && processed.duration) {
        // For backward compatibility with old data format
        processed.networkDuration = processed.duration;
      }
      
      // Ensure timestamps are consistently named
      if (processed.timestamp && processed.responseTimestamp) {
        processed.startTime = processed.timestamp;
        processed.endNetworkTime = processed.responseTimestamp;
        
        // Calculate network time if not present but timestamps are available
        if (!processed.networkDuration) {
          try {
            const startTime = new Date(processed.timestamp).getTime();
            const endTime = new Date(processed.responseTimestamp).getTime();
            processed.networkDuration = endTime - startTime;
          } catch (e) {
            // If timestamp parsing fails, keep networkDuration as is
          }
        }
      }
      
      // If we have endTime but no totalDuration
      if (processed.endTime && processed.timestamp && !processed.totalDuration) {
        try {
          const startTime = new Date(processed.timestamp).getTime();
          const endTime = new Date(processed.endTime).getTime();
          processed.totalDuration = endTime - startTime;
        } catch (e) {
          // If timestamp parsing fails, keep totalDuration as is
        }
      }
      
      // Add calculated timing information
      if (processed.networkDuration && processed.totalDuration) {
        processed.parsingDuration = processed.totalDuration - processed.networkDuration;
      }
      
      return processed;
    });
    
    // Create and download JSON file
    const jsonData = JSON.stringify(processedRequests, null, 2);
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