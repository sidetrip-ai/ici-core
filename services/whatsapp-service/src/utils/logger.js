/**
 * Simple logger utility for WhatsApp service
 */

// Log levels
const LOG_LEVELS = {
  ERROR: 'ERROR',
  WARNING: 'WARNING',
  INFO: 'INFO',
  DEBUG: 'DEBUG'
};

// Current log level
const currentLevel = process.env.LOG_LEVEL || LOG_LEVELS.INFO;

// Check if a level is enabled
const isLevelEnabled = (level) => {
  const levels = Object.values(LOG_LEVELS);
  const currentIndex = levels.indexOf(currentLevel);
  const levelIndex = levels.indexOf(level);
  
  return levelIndex <= currentIndex;
};

/**
 * Log a message at the specified level
 * @param {string} level - Log level
 * @param {string} message - Log message
 * @param {object} data - Additional data to log
 */
const log = (level, message, data = {}) => {
  if (!isLevelEnabled(level)) return;
  
  const timestamp = new Date().toISOString();
  const logData = {
    timestamp,
    level,
    message,
    ...data
  };
  
  console.log(JSON.stringify(logData));
};

// Export logger methods
module.exports = {
  error: (message, data) => log(LOG_LEVELS.ERROR, message, data),
  warn: (message, data) => log(LOG_LEVELS.WARNING, message, data),
  info: (message, data) => log(LOG_LEVELS.INFO, message, data),
  debug: (message, data) => log(LOG_LEVELS.DEBUG, message, data),
  LOG_LEVELS
}; 