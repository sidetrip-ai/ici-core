const WhatsAppClient = require('./whatsapp-client');
const logger = require('../utils/logger');

/**
 * Manager for multiple WhatsApp client instances
 */
class ClientManager {
  constructor() {
    this.clients = new Map();
  }

  /**
   * Get or create a WhatsApp client
   * @param {string} sessionId - Session identifier
   * @returns {Promise<WhatsAppClient>} WhatsApp client instance
   */
  async getOrCreateClient(sessionId) {
    if (!sessionId) {
      throw new Error('Session ID is required');
    }

    // Return existing client if it exists
    if (this.clients.has(sessionId)) {
      logger.debug(`Using existing client for session ${sessionId}`);
      return this.clients.get(sessionId);
    }

    try {
      // Create new client
      logger.info(`Creating new client for session ${sessionId}`);
      const client = new WhatsAppClient(sessionId);
      this.clients.set(sessionId, client);
      
      // Initialize the client
      await client.initialize();
      return client;
    } catch (error) {
      logger.error(`Failed to create client: ${error.message}`, { sessionId, error: error.stack });
      throw error;
    }
  }

  /**
   * Get a client by session ID
   * @param {string} sessionId - Session identifier
   * @returns {WhatsAppClient|null} WhatsApp client instance or null if not found
   */
  getClient(sessionId) {
    return this.clients.get(sessionId) || null;
  }

  /**
   * Close and destroy a client session
   * @param {string} sessionId - Session identifier
   * @returns {Promise<boolean>} Success status
   */
  async closeClient(sessionId) {
    const client = this.clients.get(sessionId);
    if (!client) {
      logger.warn(`Client session ${sessionId} not found for closing`);
      return false;
    }

    try {
      logger.info(`Closing client session ${sessionId}`);
      await client.destroy();
      this.clients.delete(sessionId);
      return true;
    } catch (error) {
      logger.error(`Error closing client: ${error.message}`, { sessionId, error: error.stack });
      return false;
    }
  }

  /**
   * Logout a client session
   * @param {string} sessionId - Session identifier
   * @returns {Promise<boolean>} Success status
   */
  async logoutClient(sessionId) {
    const client = this.clients.get(sessionId);
    if (!client) {
      logger.warn(`Client session ${sessionId} not found for logout`);
      return false;
    }

    try {
      logger.info(`Logging out client session ${sessionId}`);
      await client.logout();
      this.clients.delete(sessionId);
      return true;
    } catch (error) {
      logger.error(`Error logging out client: ${error.message}`, { sessionId, error: error.stack });
      return false;
    }
  }

  /**
   * Get all active clients
   * @returns {Array<object>} List of client info
   */
  getAllClientInfo() {
    const clientInfoList = [];
    
    for (const [sessionId, client] of this.clients.entries()) {
      clientInfoList.push(client.getInfo());
    }
    
    return clientInfoList;
  }

  /**
   * Close all client sessions
   * @returns {Promise<void>}
   */
  async closeAllClients() {
    logger.info(`Closing all WhatsApp client sessions (${this.clients.size} clients)`);
    
    const closePromises = [];
    for (const [sessionId, client] of this.clients.entries()) {
      closePromises.push(client.destroy().catch(error => {
        logger.error(`Error closing client ${sessionId}: ${error.message}`, { error: error.stack });
      }));
    }
    
    await Promise.all(closePromises);
    this.clients.clear();
  }
}

// Create singleton instance
const clientManager = new ClientManager();

module.exports = clientManager; 