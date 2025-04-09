const WebSocket = require('ws');
const logger = require('../utils/logger');
const config = require('../../config');
const { formatMessage } = require('../utils/message-formatter');

class WebSocketServer {
  constructor() {
    this.server = null;
    this.clients = new Map(); // Map of sessionId -> Set of connected clients
  }

  /**
   * Initialize the WebSocket server
   */
  initialize() {
    const port = config.wsPort;
    
    // Create WebSocket server
    this.server = new WebSocket.Server({ port });
    logger.info(`WebSocket server started on port ${port}`);

    // Setup event handlers
    this.server.on('connection', this.handleConnection.bind(this));
    this.server.on('error', (error) => {
      logger.error(`WebSocket server error: ${error.message}`, { error: error.stack });
    });
  }

  /**
   * Handle new WebSocket connection
   * @param {WebSocket} ws - WebSocket connection
   * @param {object} req - HTTP request
   */
  handleConnection(ws, req) {
    const ip = req.socket.remoteAddress;
    logger.info(`New WebSocket connection from ${ip}`);
    
    // Handle initial message with session information
    let sessionId = null;
    
    ws.on('message', (message) => {
      try {
        const data = JSON.parse(message);
        
        // Handle registration message
        if (data.type === 'register' && data.sessionId) {
          sessionId = data.sessionId;
          this.registerClient(sessionId, ws);
          logger.info(`WebSocket client registered for session ${sessionId}`);
          
          // Send confirmation
          this.sendToClient(ws, {
            type: 'registered',
            sessionId: sessionId
          });
        }
      } catch (error) {
        logger.error(`Error handling WebSocket message: ${error.message}`, { error: error.stack });
      }
    });

    // Handle connection close
    ws.on('close', () => {
      if (sessionId) {
        this.unregisterClient(sessionId, ws);
        logger.info(`WebSocket client disconnected from session ${sessionId}`);
      } else {
        logger.info(`Unregistered WebSocket client disconnected`);
      }
    });

    // Handle errors
    ws.on('error', (error) => {
      logger.error(`WebSocket client error: ${error.message}`, { 
        sessionId, 
        error: error.stack
      });
    });

    // Set initial timeout for registration
    const registrationTimeout = setTimeout(() => {
      if (!sessionId) {
        logger.warn(`WebSocket client did not register within timeout period, closing connection`);
        ws.terminate();
      }
    }, 30000); // 30 seconds

    // Clear timeout if connection closes
    ws.on('close', () => {
      clearTimeout(registrationTimeout);
    });
  }

  /**
   * Register a client for a specific session
   * @param {string} sessionId - Session ID
   * @param {WebSocket} ws - WebSocket connection
   */
  registerClient(sessionId, ws) {
    if (!this.clients.has(sessionId)) {
      this.clients.set(sessionId, new Set());
    }
    
    this.clients.get(sessionId).add(ws);
  }

  /**
   * Unregister a client from a session
   * @param {string} sessionId - Session ID
   * @param {WebSocket} ws - WebSocket connection to unregister
   */
  unregisterClient(sessionId, ws) {
    if (this.clients.has(sessionId)) {
      this.clients.get(sessionId).delete(ws);
      
      // Clean up if no clients are left for this session
      if (this.clients.get(sessionId).size === 0) {
        this.clients.delete(sessionId);
      }
    }
  }

  /**
   * Send message to a specific WebSocket client
   * @param {WebSocket} ws - WebSocket connection
   * @param {object} data - Data to send
   */
  sendToClient(ws, data) {
    if (ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(data));
      } catch (error) {
        logger.error(`Error sending message to WebSocket client: ${error.message}`, { 
          error: error.stack
        });
      }
    }
  }

  /**
   * Broadcast message to all clients for a specific session
   * @param {string} sessionId - Session ID
   * @param {object} data - Data to broadcast
   */
  broadcast(sessionId, data) {
    if (!this.clients.has(sessionId)) {
      return;
    }
    
    const clients = this.clients.get(sessionId);
    const message = JSON.stringify(data);
    
    let sentCount = 0;
    clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(message);
          sentCount++;
        } catch (error) {
          logger.error(`Error broadcasting to client: ${error.message}`, { 
            sessionId, 
            error: error.stack
          });
        }
      }
    });
    
    logger.debug(`Broadcast message to ${sentCount}/${clients.size} clients for session ${sessionId}`);
  }

  /**
   * Broadcast a WhatsApp connection state change
   * @param {string} sessionId - Session ID
   * @param {object} state - Connection state data
   */
  broadcastConnectionState(sessionId, state) {
    this.broadcast(sessionId, {
      type: 'connection_update',
      sessionId,
      state
    });
  }

  /**
   * Broadcast a WhatsApp message
   * @param {string} sessionId - Session ID
   * @param {object} message - WhatsApp message
   */
  broadcastMessage(sessionId, message) {
    const formattedMessage = formatMessage(message);
    
    this.broadcast(sessionId, {
      type: 'message',
      sessionId,
      message: formattedMessage
    });
  }

  /**
   * Close WebSocket server
   */
  close() {
    if (this.server) {
      this.server.close();
      this.server = null;
      this.clients.clear();
      logger.info('WebSocket server closed');
    }
  }
}

// Create singleton instance
const wsServer = new WebSocketServer();

module.exports = wsServer; 