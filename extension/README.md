# Sidetrip DeepContext

This Chrome extension enhances your ChatGPT interactions by automatically adding relevant context to your prompts before sending them to ChatGPT.

## Features

- Intercepts prompts sent to ChatGPT
- Enriches prompts with personalized context from a local API
- Customizable DOM selectors for compatibility with ChatGPT UI changes
- Visual notifications for success and error states
- Error handling with automatic bypass for 2 minutes after errors

## Installation

### Developer Mode Installation

1. Clone or download this repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right corner
4. Click "Load unpacked" and select the `extension` folder
5. The extension should now appear in your Chrome toolbar

### Requirements

- Chrome browser (or any Chromium-based browser like Edge, Brave, etc.)
- Local API server running on `http://localhost:8000` with a `/getContext` endpoint

## Usage

1. Make sure your local API server is running
2. Navigate to ChatGPT (https://chat.openai.com/)
3. Type your prompt as usual
4. When you press Enter or click the submit button, the extension will:
   - Intercept your prompt
   - Send it to the local API to get enhanced context
   - Replace the prompt with the enhanced version
   - Submit the enhanced prompt to ChatGPT

## Configuration

If ChatGPT's UI changes and the extension stops working properly:

1. Click on the extension icon in the toolbar
2. Update the CSS selectors for the form, textarea, or submit button
3. Click "Save Settings"
4. Refresh the ChatGPT page

To reset to default settings, click "Reset to Default" in the extension popup.

## Troubleshooting

- If you see an error notification, the extension will stop intercepting prompts for 2 minutes
- Check the console for more detailed error messages
- Verify that your local API server is running and accessible
- Try updating the DOM selectors in the extension settings

## Development

### Files Overview

- `manifest.json`: Extension configuration and permissions
- `content.js`: Main script that intercepts and enhances ChatGPT prompts
- `popup/popup.html`: Configuration UI for DOM selectors
- `popup/popup.js`: Handles saving and loading configuration

### API Interface

The extension sends POST requests to `http://localhost:8000/getContext` with:

```json
{
  "source": "chatgpt",
  "user_id": "admin",
  "query": "Your original prompt"
}
```

The API should respond with:

```json
{
  "status": "success",
  "prompt": "Enhanced prompt with context",
  "documents": [...] // Optional context documents
}
``` 