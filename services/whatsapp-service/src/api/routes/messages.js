/**
 * WhatsApp messages routes
 */

const express = require('express');
const whatsAppClient = require('../../client/whatsapp-client');

const router = express.Router();

/**
 * GET /api/messages
 * Fetch messages from a specific chat
 */
router.get('/messages', async (req, res) => {
  try {
    const { chatId, limit } = req.query;
    
    if (!chatId) {
      return res.status(400).json({
        success: false,
        message: 'Chat ID is required'
      });
    }
    
    // Check if client is connected
    const status = whatsAppClient.getStatus();
    if (status.status !== 'CONNECTED') {
      return res.status(400).json({
        success: false,
        message: `WhatsApp is not connected. Current status: ${status.status}`
      });
    }
    
    // Fetch messages
    const messages = await whatsAppClient.fetchMessages(
      chatId, 
      limit ? parseInt(limit, 10) : 2000
    );
    
    res.json({
      success: true,
      messages
    });
  } catch (error) {
    console.error('Error fetching messages:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch messages'
    });
  }
});

/**
 * GET /api/fetch-all
 * Fetch all messages from all chats, optionally since a date
 */
router.get('/fetch-all', async (req, res) => {
  try {
    const { since } = req.query;
    
    // Check if client is connected
    const status = whatsAppClient.getStatus();
    if (status.status !== 'CONNECTED') {
      return res.status(400).json({
        success: false,
        message: `WhatsApp is not connected. Current status: ${status.status}`
      });
    }
    
    // Parse since date if provided
    let sinceDate = null;
    if (since) {
      try {
        sinceDate = new Date(since);
      } catch (error) {
        return res.status(400).json({
          success: false,
          message: 'Invalid date format for since parameter'
        });
      }
    }
    
    // Fetch all messages
    const data = await whatsAppClient.fetchAllMessages(sinceDate);
    
    res.json({
      success: true,
      ...data
    });
  } catch (error) {
    console.error('Error fetching all messages:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch messages'
    });
  }
});

/**
 * GET /api/chats
 * Get a list of all chats
 */
router.get('/chats', async (req, res) => {
  try {
    // Check if client is connected
    const status = whatsAppClient.getStatus();
    if (status.status !== 'CONNECTED') {
      return res.status(400).json({
        success: false,
        message: `WhatsApp is not connected. Current status: ${status.status}`
      });
    }
    
    // Fetch all chats
    const data = await whatsAppClient.fetchAllMessages();
    
    res.json({
      success: true,
      chats: data.conversations
    });
  } catch (error) {
    console.error('Error fetching chats:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch chats'
    });
  }
});

module.exports = router; 