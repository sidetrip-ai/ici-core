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

/**
 * GET /api/message-debug
 * Get a single message with detailed structure for debugging
 */
router.get('/message-debug', async (req, res) => {
  try {
    const { chatId, limit = 10 } = req.query;
    
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
    
    // Fetch a few messages for debugging
    const messages = await whatsAppClient.fetchMessages(chatId, parseInt(limit, 10));
    
    // Find the first message with a quoted message
    const replyMessage = messages.find(msg => msg.hasQuotedMsg);
    
    // Log all keys to console and return detailed structure
    if (replyMessage) {
      console.log('DEBUG: Reply Message Structure', JSON.stringify(replyMessage, null, 2));
      
      // Create a response with all available debug info
      const debugInfo = {
        messageKeys: Object.keys(replyMessage),
        message: replyMessage,
        hasQuotedMsg: replyMessage.hasQuotedMsg,
        quotedMsgId: replyMessage.quotedMsgId,
        quotedMsg: replyMessage.quotedMsg
      };
      
      res.json({
        success: true,
        debug: debugInfo
      });
    } else {
      res.json({
        success: true,
        message: 'No reply messages found in the first ' + limit + ' messages',
        sampleMessage: messages.length > 0 ? messages[0] : null
      });
    }
  } catch (error) {
    console.error('Error debugging messages:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to debug messages'
    });
  }
});

/**
 * GET /api/replies-info
 * Get statistics about quoted messages in a chat
 */
router.get('/replies-info', async (req, res) => {
  try {
    const { chatId } = req.query;
    
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
    const messages = await whatsAppClient.fetchMessages(chatId, 100);
    
    // Filter quoted messages
    const quotedMessages = messages.filter(msg => msg.hasQuotedMsg);
    
    // Get statistics
    const stats = {
      totalMessages: messages.length,
      quotedMessagesCount: quotedMessages.length,
      quotedPercentage: `${(quotedMessages.length / messages.length * 100).toFixed(1)}%`,
      hasDirectQuotedMsg: quotedMessages.some(msg => msg.quotedMsg),
      quotedMsgFieldsWhenAvailable: quotedMessages.length > 0 && quotedMessages[0].quotedMsg 
        ? Object.keys(quotedMessages[0].quotedMsg) 
        : [],
      quotedMessageSample: quotedMessages.length > 0 ? quotedMessages[0] : null
    };
    
    res.json({
      success: true,
      statistics: stats,
      quotedMessages: quotedMessages.length > 0 ? quotedMessages.slice(0, 5) : []
    });
  } catch (error) {
    console.error('Error getting quoted messages info:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to get quoted messages info'
    });
  }
});

module.exports = router; 