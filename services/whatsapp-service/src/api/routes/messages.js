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

    console.log(messages);
    
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
    const data = await whatsAppClient.fetchChats();
    
    res.json({
      success: true,
      chats: data,
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

    console.log(messages[0]);
    
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

/**
 * GET /api/contact/:contactId
 * Get contact information by ID
 */
router.get('/contact/:contactId', async (req, res) => {
  try {
    const { contactId } = req.params;
    
    if (!contactId) {
      return res.status(400).json({
        success: false,
        message: 'Contact ID is required'
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
    
    // Fetch contact information using the new method
    const contact = await whatsAppClient.getContactById(contactId);
    
    res.json({
      success: true,
      contact: {
        id: contact.id._serialized,
        name: contact.name,
        pushname: contact.pushname,
        shortName: contact.shortName,
        isGroup: contact.isGroup,
        isWAContact: contact.isWAContact,
        isMyContact: contact.isMyContact
      }
    });
  } catch (error) {
    console.error('Error fetching contact information:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch contact information'
    });
  }
});

/**
 * POST /api/contacts/batch
 * Get contact information for multiple IDs in batch
 */
router.post('/contacts/batch', async (req, res) => {
  try {
    const { contactIds } = req.body;
    
    if (!contactIds || !Array.isArray(contactIds) || contactIds.length === 0) {
      return res.status(400).json({
        success: false,
        message: 'contactIds array is required in request body'
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
    
    // Fetch contacts information in batch
    const result = await whatsAppClient.getContactsByIds(contactIds);
    
    // Format the response
    const formattedContacts = {};
    
    for (const [contactId, contact] of Object.entries(result.contacts)) {
      formattedContacts[contactId] = {
        id: contact.id._serialized,
        name: contact.name,
        pushname: contact.pushname,
        shortName: contact.shortName,
        isGroup: contact.isGroup,
        isWAContact: contact.isWAContact,
        isMyContact: contact.isMyContact
      };
    }
    
    res.json({
      success: true,
      contacts: formattedContacts,
      errors: result.errors
    });
  } catch (error) {
    console.error('Error fetching batch contact information:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Failed to fetch batch contact information'
    });
  }
});

module.exports = router; 