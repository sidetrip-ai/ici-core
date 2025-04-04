/**
 * Utility to format WhatsApp messages into a standardized format
 */

/**
 * Format a WhatsApp message object into a standardized format
 * @param {object} message - WhatsApp message object
 * @returns {object} Formatted message
 */
function formatMessage(message) {
  // Basic message info
  const formattedMessage = {
    id: message.id._serialized || message.id,
    timestamp: message.timestamp * 1000, // Convert to milliseconds
    from: message.from,
    fromMe: message.fromMe,
    chatId: message.chatId || message.from,
    type: message.type,
  };

  // Handle different message types
  switch (message.type) {
    case 'chat':
      formattedMessage.body = message.body;
      break;
      
    case 'image':
      formattedMessage.body = message.caption || '';
      formattedMessage.mimetype = message.mimetype;
      formattedMessage.hasMedia = true;
      break;
      
    case 'video':
      formattedMessage.body = message.caption || '';
      formattedMessage.mimetype = message.mimetype;
      formattedMessage.hasMedia = true;
      break;
      
    case 'audio':
      formattedMessage.body = '';
      formattedMessage.mimetype = message.mimetype;
      formattedMessage.hasMedia = true;
      break;
      
    case 'document':
      formattedMessage.body = message.caption || '';
      formattedMessage.filename = message.filename;
      formattedMessage.mimetype = message.mimetype;
      formattedMessage.hasMedia = true;
      break;
      
    case 'location':
      formattedMessage.body = message.body || '';
      formattedMessage.location = {
        latitude: message.location.latitude,
        longitude: message.location.longitude,
        description: message.location.description || ''
      };
      break;
      
    case 'contact':
      formattedMessage.body = '';
      formattedMessage.contacts = message.vCards.map(vcard => ({ vcard }));
      break;
      
    default:
      formattedMessage.body = message.body || '';
  }

  // Handle optional properties if they exist
  if (message.quotedMsg) {
    formattedMessage.quotedMessage = {
      id: message.quotedMsg.id._serialized || message.quotedMsg.id,
      body: message.quotedMsg.body || '',
      type: message.quotedMsg.type
    };
  }

  // Add metadata
  formattedMessage.metadata = {
    source: 'whatsapp',
    raw: { messageType: message.type }
  };

  return formattedMessage;
}

/**
 * Format chat data into a standardized format
 * @param {object} chat - WhatsApp chat object
 * @returns {object} Formatted chat
 */
function formatChat(chat) {
  return {
    id: chat.id._serialized || chat.id,
    name: chat.name || '',
    isGroup: chat.isGroup,
    timestamp: chat.timestamp * 1000, // Convert to milliseconds
    unreadCount: chat.unreadCount,
    metadata: {
      source: 'whatsapp'
    }
  };
}

/**
 * Format contact data into a standardized format
 * @param {object} contact - WhatsApp contact object
 * @returns {object} Formatted contact
 */
function formatContact(contact) {
  return {
    id: contact.id._serialized || contact.id,
    name: contact.name || contact.pushname || '',
    number: contact.number,
    metadata: {
      source: 'whatsapp',
      isMyContact: contact.isMyContact
    }
  };
}

module.exports = {
  formatMessage,
  formatChat,
  formatContact
}; 