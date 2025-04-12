/**
 * WhatsApp Web.js client implementation
 */

const fs = require('fs');
const path = require('path');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const eventEmitter = require('../utils/event-emitter');
const config = require('../../config');

class WhatsAppClient {
  constructor() {
    this.client = null;
    this.status = 'DISCONNECTED';
    this.qrCode = null;
    this.qrCodeImage = null;
    this.lastQrTimestamp = null;
    this.sessionData = null;
    this.sessionFolder = path.join(config.sessions.dataPath);
    this.initialized = false;
    this.initializationPromise = null;
    this.contactsCache = new Map();
  }

  /**
   * Initialize the WhatsApp client
   */
  initialize() {
    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    this.initializationPromise = new Promise((resolve, reject) => {
      try {
        console.log('Initializing WhatsApp client...');
        
        // Ensure session directory exists
        if (!fs.existsSync(this.sessionFolder)) {
          fs.mkdirSync(this.sessionFolder, { recursive: true });
        }

        // Create client with LocalAuth
        this.client = new Client({
          authStrategy: new LocalAuth({ dataPath: this.sessionFolder }),
          puppeteer: config.clientOptions.puppeteer
        });
        
        // Set up event handlers
        this._setupEventHandlers();
        
        // Set status to initializing
        this.status = 'INITIALIZING';
        
        // Initialize the client
        this.client.initialize();
        
        this.initialized = true;
        resolve();
      } catch (error) {
        console.error('Error initializing WhatsApp client:', error);
        this.status = 'ERROR';
        reject(error);
      }
    });

    return this.initializationPromise;
  }

  /**
   * Set up event handlers for the WhatsApp client
   */
  _setupEventHandlers() {
    // QR code event
    this.client.on('qr', async (qr) => {
      console.log('QR Code received, scan to authenticate');
      this.qrCode = qr;
      this.lastQrTimestamp = Date.now();
      this.status = 'CONNECTING';
      
      try {
        // Generate QR code image
        this.qrCodeImage = await qrcode.toDataURL(qr);
        
        // Save QR code to file for easy access
        const qrImageBuffer = Buffer.from(this.qrCodeImage.split(',')[1], 'base64');
        fs.writeFileSync(path.join(this.sessionFolder, 'latest-qr.png'), qrImageBuffer);
        
        // Emit QR code event
        eventEmitter.emit('whatsapp.qr', { qrCode: qr, timestamp: this.lastQrTimestamp });
      } catch (error) {
        console.error('Error generating QR code image:', error);
      }
    });

    // Ready event
    this.client.on('ready', () => {
      console.log('WhatsApp client is ready');
      this.status = 'CONNECTED';
      this.qrCode = null;
      this.qrCodeImage = null;
      eventEmitter.emit('whatsapp.ready');
    });

    // Authentication failure event
    this.client.on('auth_failure', (error) => {
      console.error('WhatsApp authentication failed:', error);
      this.status = 'AUTH_FAILURE';
      eventEmitter.emit('whatsapp.auth_failure', { error });
    });

    // Disconnected event
    this.client.on('disconnected', (reason) => {
      console.log('WhatsApp client disconnected:', reason);
      this.status = 'DISCONNECTED';
      this.qrCode = null;
      this.qrCodeImage = null;
      eventEmitter.emit('whatsapp.disconnected', { reason });
    });

    // Message event
    this.client.on('message', async (message) => {
      // Format the message with quoted details before emitting
      const formattedMessage = await this._formatMessageWithQuotes(message);
      eventEmitter.emit('whatsapp.message', formattedMessage);
    });
  }

  /**
   * Get the current status of the WhatsApp client
   * @returns {Object} Status information
   */
  getStatus() {
    return {
      status: this.status,
      hasQrCode: !!this.qrCode,
      lastQrTimestamp: this.lastQrTimestamp,
      initialized: this.initialized
    };
  }

  /**
   * Get the latest QR code as an image
   * @returns {String|null} Data URL of the QR code image
   */
  getQrCodeImage() {
    return this.qrCodeImage;
  }

  /**
   * Generate a new QR code by resetting the client
   * @returns {Promise<Boolean>} Success status
   */
  async generateNewQrCode() {
    if (!this.initialized) {
      await this.initialize();
    }

    if (this.status === 'CONNECTED') {
      return { success: false, message: 'Already connected' };
    }

    try {
      // Logout and reinitialize to get a new QR code
      await this.logout();
      
      // Re-initialize the client
      this.client.initialize();
      
      return { success: true, message: 'QR code generation initiated' };
    } catch (error) {
      console.error('Error generating new QR code:', error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Logout from WhatsApp Web
   * @returns {Promise<Object>} Success status
   */
  async logout() {
    if (!this.initialized || !this.client) {
      return { success: false, message: 'Client not initialized' };
    }

    try {
      await this.client.logout();
      this.status = 'DISCONNECTED';
      this.qrCode = null;
      this.qrCodeImage = null;
      return { success: true };
    } catch (error) {
      console.error('Error logging out:', error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Fetch messages from a chat
   * @param {String} chatId Chat ID
   * @param {Number} limit Maximum number of messages to fetch
   * @returns {Promise<Array>} Messages
   */
  async fetchMessages(chatId, limit = Infinity) {
    if (!this.initialized || this.status !== 'CONNECTED') {
      throw new Error(`WhatsApp session not connected. Current status: ${this.status}`);
    }

    try {
      // Get chat by ID
      const chat = await this.client.getChatById(chatId);
      
      // Fetch messages
      const messages = await chat.fetchMessages({ limit });
      
      // Use Promise.all to format all messages with quoted details in parallel
      return await Promise.all(messages.map(msg => this._formatMessageWithQuotes(msg)));
    } catch (error) {
      console.error(`Error fetching messages for chat ${chatId}:`, error);
      throw error;
    }
  }

  /**
   * Fetch all messages from all chats since a given date
   * @param {Date} since Date to fetch messages from
   * @returns {Promise<Object>} Messages and conversations
   */
  async fetchChats(since = null) {
    if (!this.initialized || this.status !== 'CONNECTED') {
      throw new Error(`WhatsApp session not connected. Current status: ${this.status}`);
    }

    try {
      // Get all chats
      const chats = await this.client.getChats();
      const conversations = chats.map(chat => ({
        id: chat.id._serialized,
        name: chat.name,
        isGroup: chat.isGroup,
        timestamp: chat.timestamp,
        unreadCount: chat.unreadCount
      }));

      return conversations;
    } catch (error) {
      console.error('Error fetching all messages:', error);
      throw error;
    }
  }

  /**
   * Get current user information
   * @returns {Promise<Object>} User info
   */
  async getUserInfo() {
    if (!this.initialized || this.status !== 'CONNECTED') {
      throw new Error(`WhatsApp session not connected. Current status: ${this.status}`);
    }

    try {
      // Get the user info directly from the client.info property
      const info = this.client.info;
      
      // Ensure we have the necessary data
      if (!info || !info.wid) {
        throw new Error('User information not available');
      }
      
      return {
        id: info.wid._serialized,
        name: info.pushname || 'Unknown',
        platform: info.platform || 'unknown',
        isMe: true,
        // Additional details that might be available
        phone: info.wid.user,
        device: info.platform
      };
    } catch (error) {
      console.error('Error getting user info:', error);
      throw error;
    }
  }

  /**
   * Get contact information by ID
   * @param {String} contactId Contact ID
   * @returns {Promise<Object>} Contact information
   */
  async getContactById(contactId) {
    if (!this.initialized || this.status !== 'CONNECTED') {
      throw new Error(`WhatsApp session not connected. Current status: ${this.status}`);
    }

    try {
      // Check if contact exists in cache
      if (this.contactsCache.has(contactId)) {
        return this.contactsCache.get(contactId);
      }
      
      // If not in cache, get contact by ID from client
      const contact = await this.client.getContactById(contactId);
      
      if (!contact) {
        throw new Error(`Contact not found: ${contactId}`);
      }
      
      // Add to cache
      this.contactsCache.set(contactId, contact);
      
      return contact;
    } catch (error) {
      console.error(`Error fetching contact information for ${contactId}:`, error);
      throw error;
    }
  }

  /**
   * Get multiple contacts by their IDs
   * @param {Array<String>} contactIds Array of contact IDs
   * @returns {Promise<Object>} Object mapping contact IDs to contact information
   */
  async getContactsByIds(contactIds) {
    if (!this.initialized || this.status !== 'CONNECTED') {
      throw new Error(`WhatsApp session not connected. Current status: ${this.status}`);
    }

    const results = {};
    const errors = [];

    // Process contacts in parallel
    await Promise.all(contactIds.map(async (contactId) => {
      try {
        // Try to get from cache first, then fallback to getContactById
        // which itself will update the cache if needed
        const contact = await this.getContactById(contactId);
        if (contact) {
          results[contactId] = contact;
        } else {
          errors.push({ id: contactId, error: 'Contact not found' });
        }
      } catch (error) {
        console.error(`Error fetching contact information for ${contactId}:`, error);
        errors.push({ id: contactId, error: error.message || 'Unknown error' });
      }
    }));

    return { contacts: results, errors: errors.length > 0 ? errors : undefined };
  }

  /**
   * Format a WhatsApp message into a standardized format
   * @param {Object} msg WhatsApp message object
   * @returns {Object} Formatted message
   */
  _formatMessage(msg, authorName) {
    // Log message keys for debugging
    console.log('WhatsApp Message Keys:', Object.keys(msg));
    console.log('Message Type:', msg.type);
    
    const formattedMessage = {
      id: msg.id._serialized,
      body: msg.body,
      type: msg.type,
      timestamp: msg.timestamp * 1000, // Convert to milliseconds
      from: msg.from,
      author: msg.author || msg.from,
      authorName: authorName,
      chatId: msg.chatId || (msg.chat && msg.chat.id._serialized),
      isForwarded: msg.isForwarded,
      hasQuotedMsg: msg.hasQuotedMsg,
      vCards: msg.vCards,
      mentionedIds: msg.mentionedIds,
      isStatus: msg.isStatus,
      isStarred: msg.isStarred,
      broadcast: msg.broadcast
    };
    
    // Add quoted message details if available
    if (msg.hasQuotedMsg) {
      try {
        // Get the quoted message if immediately available
        if (msg._data && msg._data.quotedMsg) {
          console.log('Quoted Message Keys:', Object.keys(msg._data.quotedMsg));
          
          formattedMessage.quotedMsgId = msg._data.quotedMsg.id._serialized;
          formattedMessage.quotedMsg = {
            body: msg._data.quotedMsg.body || '',
            type: msg._data.quotedMsg.type,
            timestamp: msg._data.quotedMsg.timestamp ? msg._data.quotedMsg.timestamp * 1000 : null,
            sender: msg._data.quotedMsg.author || msg._data.quotedMsg.from
          };
        } 
        // If not immediately available, add the reference IDs
        else {
          formattedMessage.quotedMsgId = msg._data.quotedStanzaID || null;
          formattedMessage.quotedParticipant = msg._data.quotedParticipant || null;
          formattedMessage.quotedRemoteJid = msg._data.quotedRemoteJid || null;
        }
      } catch (error) {
        console.error('Error processing quoted message:', error);
        // Still indicate that it's a reply even if we couldn't extract the details
        formattedMessage.quotedMsgId = 'unknown';
      }
    }
    
    return formattedMessage;
  }

  /**
   * Format a WhatsApp message with its full quoted message details
   * This method should be used when fetching messages for ingestor
   * @param {Object} msg WhatsApp message object
   * @returns {Promise<Object>} Formatted message with quoted message details
   */
  async _formatMessageWithQuotes(msg) {
    const authorId = msg.author || msg.from;
    let authorName;
    try {
      authorName = await this.getContactById(authorId);
    } catch(e) {
      console.log({
        msg: msg,
        authorId: authorId,
        authorName: authorName,
        error: e
      })
      console.error("Error formatting message with quotes", e);
      throw e;
    }
    // Start with the basic formatted message
    const formattedMessage = this._formatMessage(msg, authorName); 
    
    // If this is a reply, try to fetch the quoted message
    if (msg.hasQuotedMsg && !formattedMessage.quotedMsg) {
      try {
        const quotedMsg = await msg.getQuotedMessage();
        if (quotedMsg) {
          console.log('Fetched Quoted Message Keys:', Object.keys(quotedMsg));
          
          formattedMessage.quotedMsgId = quotedMsg.id._serialized;
          formattedMessage.quotedMsg = {
            body: quotedMsg.body || '',
            type: quotedMsg.type,
            timestamp: quotedMsg.timestamp ? quotedMsg.timestamp * 1000 : null,
            sender: quotedMsg.author || quotedMsg.from
          };
        }
      } catch (error) {
        console.error('Error fetching quoted message details:', error);
      }
    }
    
    return formattedMessage;
  }
}

// Singleton instance
const whatsAppClient = new WhatsAppClient();

module.exports = whatsAppClient; 