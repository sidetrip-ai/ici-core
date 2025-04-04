/**
 * Event emitter singleton for the WhatsApp service
 */

const EventEmitter = require('events');

// Create a singleton instance
const eventEmitter = new EventEmitter();

// Increase max listeners to avoid warnings when many modules listen
eventEmitter.setMaxListeners(20);

module.exports = eventEmitter; 