const express = require('express');
const router = express.Router();
const clientManager = require('../../client/client-manager');
const logger = require('../../utils/logger');

/**
 * GET /api/sessions
 * List all active WhatsApp sessions
 */
router.get('/', (req, res) => {
  try {
    const sessions = clientManager.getAllClientInfo();
    res.json({
      success: true,
      count: sessions.length,
      sessions
    });
  } catch (error) {
    logger.error(`Error listing sessions: ${error.message}`, { error: error.stack });
    res.status(500).json({
      success: false,
      error: 'Failed to list sessions'
    });
  }
});

/**
 * POST /api/sessions
 * Create a new WhatsApp session
 */
router.post('/', async (req, res) => {
  try {
    let { sessionId } = req.body;
    
    // Generate a random session ID if not provided
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`;
    }
    
    // Check if session already exists
    const existingClient = clientManager.getClient(sessionId);
    if (existingClient) {
      return res.status(409).json({
        success: false,
        error: `Session ${sessionId} already exists`,
        sessionId
      });
    }
    
    // Create new client
    const client = await clientManager.getOrCreateClient(sessionId);
    
    res.status(201).json({
      success: true,
      message: 'WhatsApp session created',
      session: client.getInfo()
    });
  } catch (error) {
    logger.error(`Error creating session: ${error.message}`, { error: error.stack });
    res.status(500).json({
      success: false,
      error: 'Failed to create WhatsApp session'
    });
  }
});

/**
 * GET /api/sessions/:sessionId
 * Get session status
 */
router.get('/:sessionId', (req, res) => {
  const { sessionId } = req.params;
  
  try {
    const client = clientManager.getClient(sessionId);
    if (!client) {
      return res.status(404).json({
        success: false,
        error: `Session ${sessionId} not found`
      });
    }
    
    res.json({
      success: true,
      session: client.getInfo()
    });
  } catch (error) {
    logger.error(`Error getting session ${sessionId}: ${error.message}`, { 
      sessionId, 
      error: error.stack 
    });
    res.status(500).json({
      success: false,
      error: 'Failed to get session status'
    });
  }
});

/**
 * GET /api/sessions/:sessionId/qr
 * Get QR code for session
 */
router.get('/:sessionId/qr', async (req, res) => {
  const { sessionId } = req.params;
  
  try {
    const client = clientManager.getClient(sessionId);
    if (!client) {
      return res.status(404).json({
        success: false,
        error: `Session ${sessionId} not found`
      });
    }
    
    if (client.status !== 'qr_received') {
      return res.status(400).json({
        success: false,
        error: `No QR code available for session ${sessionId}`,
        status: client.status
      });
    }
    
    const qrDataUrl = await client.generateQRCodeDataUrl();
    
    if (!qrDataUrl) {
      return res.status(404).json({
        success: false,
        error: 'QR code is not available'
      });
    }
    
    res.json({
      success: true,
      qrCode: qrDataUrl
    });
  } catch (error) {
    logger.error(`Error getting QR code for session ${sessionId}: ${error.message}`, { 
      sessionId, 
      error: error.stack 
    });
    res.status(500).json({
      success: false,
      error: 'Failed to get QR code'
    });
  }
});

/**
 * DELETE /api/sessions/:sessionId
 * Logout and destroy a session
 */
router.delete('/:sessionId', async (req, res) => {
  const { sessionId } = req.params;
  const { action = 'logout' } = req.query; // 'logout' or 'destroy'
  
  try {
    const client = clientManager.getClient(sessionId);
    if (!client) {
      return res.status(404).json({
        success: false,
        error: `Session ${sessionId} not found`
      });
    }
    
    // Perform the requested action
    let result = false;
    if (action === 'destroy') {
      result = await clientManager.closeClient(sessionId);
    } else {
      result = await clientManager.logoutClient(sessionId);
    }
    
    if (result) {
      res.json({
        success: true,
        message: `Session ${sessionId} ${action === 'destroy' ? 'destroyed' : 'logged out'}`
      });
    } else {
      res.status(500).json({
        success: false,
        error: `Failed to ${action === 'destroy' ? 'destroy' : 'logout'} session`
      });
    }
  } catch (error) {
    logger.error(`Error deleting session ${sessionId}: ${error.message}`, { 
      sessionId, 
      error: error.stack 
    });
    res.status(500).json({
      success: false,
      error: `Failed to delete session: ${error.message}`
    });
  }
});

module.exports = router; 