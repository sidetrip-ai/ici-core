const path = require('path');

/**
 * Configuration for the WhatsApp service
 */
module.exports = {
  // Server settings
  port: process.env.PORT || 3004,
  wsPort: process.env.WS_PORT || 3005,
  
  // WhatsApp client settings
  clientOptions: {
    puppeteer: {
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
  },
  
  // Session settings
  sessions: {
    dataPath: path.join(__dirname, "services", "whatsapp-service", "data", "sessions"),
    sessionFile: 'session.json'
  },
  
  // API settings
  api: {
    maxMessages: 1000, // Maximum number of messages to return in a single request
  }
}; 