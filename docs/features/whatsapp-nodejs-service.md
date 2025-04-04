# WhatsApp Node.js Service Specification

## Overview

This document outlines the technical specifications for the WhatsApp Node.js service component. This service will act as a bridge between WhatsApp Web JS and our Python-based ingestor framework, providing a RESTful API and WebSocket interface for WhatsApp data retrieval.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                 WhatsApp Node.js Service                │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌───────────────┐  ┌────────────────┐  │
│ │ WhatsApp    │  │ Express API   │  │ WebSocket      │  │
│ │ Web JS      │  │ Server        │  │ Server         │  │
│ │ Client      │  │               │  │                │  │
│ └─────┬───────┘  └───────┬───────┘  └────────┬───────┘  │
│       │                  │                   │          │
│       │                  │                   │          │
│ ┌─────┴──────────────────┴───────────────────┴───────┐  │
│ │                Message Store                       │  │
│ │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │  │
│ │ │ Message     │  │ Chat        │  │ Contact     │ │  │
│ │ │ Cache       │  │ Cache       │  │ Cache       │ │  │
│ │ └─────────────┘  └─────────────┘  └─────────────┘ │  │
│ └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. WhatsApp Web JS Client

The client component will handle:
- WhatsApp Web connection through Puppeteer
- QR code generation for authentication
- Event listeners for message events
- Chat and contact management

```javascript
// whatsapp-client.js
const { Client } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const EventEmitter = require('events');

class WhatsAppClient extends EventEmitter {
  constructor(config) {
    super();
    this.client = null;
    this.config = config;
    this.isReady = false;
    this.qrCode = null;
  }
  
  async initialize() {
    this.client = new Client(this.config.clientOptions);
    
    this.client.on('qr', async (qr) => {
      this.qrCode = await qrcode.toDataURL(qr);
      this.emit('qr', this.qrCode);
    });
    
    this.client.on('ready', () => {
      this.isReady = true;
      this.emit('ready');
    });
    
    this.client.on('message_create', (message) => {
      const formattedMessage = this._formatMessage(message);
      this.emit('message', formattedMessage);
    });
    
    await this.client.initialize();
  }
  
  async getStatus() {
    return {
      ready: this.isReady,
      qrCode: this.qrCode
    };
  }
  
  async getChats() {
    if (!this.isReady) return [];
    const chats = await this.client.getChats();
    return chats.map(chat => this._formatChat(chat));
  }
  
  async getMessages(chatId, options = {}) {
    if (!this.isReady) return [];
    const chat = await this.client.getChatById(chatId);
    const messages = await chat.fetchMessages(options);
    return messages.map(msg => this._formatMessage(msg));
  }
  
  _formatMessage(message) {
    return {
      id: message.id.id,
      conversation_id: message.from,
      date: message.timestamp * 1000, // Convert to ISO string in the API layer
      text: message.body,
      from_user: message.fromMe,
      sender_id: message.author || message.from,
      source: 'whatsapp'
    };
  }
  
  _formatChat(chat) {
    return {
      id: chat.id._serialized,
      name: chat.name || "",
      last_message: chat.lastMessage ? {
        id: chat.lastMessage.id.id,
        date: chat.lastMessage.timestamp * 1000,
        text: chat.lastMessage.body
      } : null,
      last_updated: chat.timestamp * 1000,
      total_messages: chat.unreadCount // Not actual total
    };
  }
}

module.exports = WhatsAppClient;
```

### 2. Express API Server

The API server will provide RESTful endpoints for:
- Client initialization and status
- Chat listing
- Message retrieval with filtering options

```javascript
// api-server.js
const express = require('express');
const cors = require('cors');

class APIServer {
  constructor(whatsappClient, messageStore, config) {
    this.app = express();
    this.whatsappClient = whatsappClient;
    this.messageStore = messageStore;
    this.config = config;
    this.setupMiddleware();
    this.setupRoutes();
  }
  
  setupMiddleware() {
    this.app.use(express.json());
    this.app.use(cors());
  }
  
  setupRoutes() {
    // Authentication and status
    this.app.get('/initialize', async (req, res) => {
      try {
        const status = await this.whatsappClient.getStatus();
        res.json(status);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
    
    this.app.get('/status', async (req, res) => {
      try {
        const status = await this.whatsappClient.getStatus();
        res.json(status);
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
    
    // Conversations/chats
    this.app.get('/conversations', async (req, res) => {
      try {
        const conversations = await this.messageStore.getConversations();
        res.json({ conversations });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
    
    // Messages with optional filtering
    this.app.get('/messages', async (req, res) => {
      try {
        const since = req.query.since ? new Date(req.query.since) : null;
        const until = req.query.until ? new Date(req.query.until) : null;
        
        const messages = await this.messageStore.getMessages({ since, until });
        const conversations = await this.messageStore.getConversations();
        
        res.json({ 
          conversations,
          messages 
        });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
    
    // Messages for specific conversation
    this.app.get('/messages/:conversationId', async (req, res) => {
      try {
        const { conversationId } = req.params;
        const since = req.query.since ? new Date(req.query.since) : null;
        const until = req.query.until ? new Date(req.query.until) : null;
        
        const messages = await this.messageStore.getMessagesForConversation(
          conversationId, 
          { since, until }
        );
        
        res.json({ messages });
      } catch (error) {
        res.status(500).json({ error: error.message });
      }
    });
  }
  
  start() {
    const port = this.config.port || 3000;
    this.server = this.app.listen(port, () => {
      console.log(`API server listening on port ${port}`);
    });
    return this.server;
  }
  
  stop() {
    if (this.server) {
      this.server.close();
    }
  }
}

module.exports = APIServer;
```

### 3. WebSocket Server

The WebSocket server will broadcast events for:
- QR code updates
- Client ready status
- New messages
- Connection state changes

```javascript
// websocket-server.js
const WebSocket = require('ws');

class WebSocketServer {
  constructor(whatsappClient, config) {
    this.whatsappClient = whatsappClient;
    this.config = config;
    this.clients = new Set();
  }
  
  start(httpServer) {
    // Can be standalone or share HTTP server with Express
    const port = this.config.wsPort || 3001;
    
    if (httpServer) {
      this.wss = new WebSocket.Server({ server: httpServer });
    } else {
      this.wss = new WebSocket.Server({ port });
      console.log(`WebSocket server listening on port ${port}`);
    }
    
    this.wss.on('connection', (ws) => {
      this.clients.add(ws);
      
      // Send current state on connect
      const initialState = {
        type: 'status',
        data: {
          ready: this.whatsappClient.isReady,
          qrCode: this.whatsappClient.qrCode
        }
      };
      ws.send(JSON.stringify(initialState));
      
      ws.on('close', () => {
        this.clients.delete(ws);
      });
    });
    
    // Relay WhatsApp client events to WebSocket clients
    this.whatsappClient.on('qr', (qrCode) => {
      this.broadcast({
        type: 'qr',
        data: qrCode
      });
    });
    
    this.whatsappClient.on('ready', () => {
      this.broadcast({
        type: 'status',
        status: 'ready'
      });
    });
    
    this.whatsappClient.on('message', (message) => {
      this.broadcast({
        type: 'message',
        data: message
      });
    });
    
    return this.wss;
  }
  
  broadcast(data) {
    const message = JSON.stringify(data);
    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    }
  }
  
  stop() {
    if (this.wss) {
      this.wss.close();
    }
  }
}

module.exports = WebSocketServer;
```

### 4. Message Store

The message store will:
- Cache messages in memory (or database)
- Provide filtering capabilities
- Handle conversation metadata

```javascript
// message-store.js
class MessageStore {
  constructor() {
    this.messages = [];
    this.conversations = new Map();
    this.contacts = new Map();
  }
  
  addMessage(message) {
    // Add or update message in the store
    const existingIndex = this.messages.findIndex(m => m.id === message.id);
    
    if (existingIndex >= 0) {
      this.messages[existingIndex] = message;
    } else {
      this.messages.push(message);
    }
    
    // Update conversation data
    this.updateConversation(message);
    
    return message;
  }
  
  updateConversation(message) {
    const conversationId = message.conversation_id;
    
    if (!this.conversations.has(conversationId)) {
      this.conversations.set(conversationId, {
        id: conversationId,
        name: message.conversation_name || "",
        last_message: null,
        last_updated: null,
        total_messages: 0
      });
    }
    
    const conversation = this.conversations.get(conversationId);
    conversation.total_messages += 1;
    
    // Update last message if this is newer
    const messageDate = new Date(message.date);
    if (!conversation.last_updated || messageDate > new Date(conversation.last_updated)) {
      conversation.last_message = {
        id: message.id,
        date: message.date,
        text: message.text
      };
      conversation.last_updated = message.date;
    }
    
    return conversation;
  }
  
  setConversations(conversations) {
    // Bulk set conversations from client
    conversations.forEach(conversation => {
      this.conversations.set(conversation.id, conversation);
    });
  }
  
  getConversations() {
    return Array.from(this.conversations.values());
  }
  
  getMessages(options = {}) {
    let filteredMessages = [...this.messages];
    
    // Apply date filtering
    if (options.since) {
      filteredMessages = filteredMessages.filter(
        msg => new Date(msg.date) >= options.since
      );
    }
    
    if (options.until) {
      filteredMessages = filteredMessages.filter(
        msg => new Date(msg.date) <= options.until
      );
    }
    
    // Sort by date (newest first)
    return filteredMessages.sort(
      (a, b) => new Date(b.date) - new Date(a.date)
    );
  }
  
  getMessagesForConversation(conversationId, options = {}) {
    const allMessages = this.getMessages(options);
    return allMessages.filter(msg => msg.conversation_id === conversationId);
  }
  
  clear() {
    this.messages = [];
    this.conversations.clear();
    this.contacts.clear();
  }
}

module.exports = MessageStore;
```

### 5. Main Application

The main application will tie everything together:

```javascript
// index.js
const config = require('./config');
const WhatsAppClient = require('./whatsapp-client');
const APIServer = require('./api-server');
const WebSocketServer = require('./websocket-server');
const MessageStore = require('./message-store');

async function start() {
  // Create instances
  const messageStore = new MessageStore();
  const whatsappClient = new WhatsAppClient(config);
  const apiServer = new APIServer(whatsappClient, messageStore, config);
  const wsServer = new WebSocketServer(whatsappClient, config);
  
  // Listen for messages to store them
  whatsappClient.on('message', (message) => {
    messageStore.addMessage(message);
  });
  
  // Initialize components
  try {
    console.log('Starting WhatsApp client...');
    await whatsappClient.initialize();
    
    console.log('Starting API server...');
    const httpServer = apiServer.start();
    
    console.log('Starting WebSocket server...');
    wsServer.start(httpServer); // Share HTTP server if desired
    
    console.log('WhatsApp service initialized successfully');
    
    // Handle shutdown
    process.on('SIGINT', async () => {
      console.log('Shutting down...');
      wsServer.stop();
      apiServer.stop();
      process.exit(0);
    });
  } catch (error) {
    console.error('Failed to start service:', error);
    process.exit(1);
  }
}

start();
```

## API Specification

### RESTful Endpoints

#### 1. Authentication

**GET /initialize**

Initialize the WhatsApp client and generate QR code.

Response:
```json
{
  "ready": false,
  "qrCode": "data:image/png;base64,..."
}
```

**GET /status**

Check the current connection status.

Response:
```json
{
  "ready": true,
  "qrCode": null
}
```

#### 2. Conversations

**GET /conversations**

Retrieve all available conversations.

Response:
```json
{
  "conversations": [
    {
      "id": "1234567890@c.us",
      "name": "Contact Name",
      "last_message": {
        "id": "message_id",
        "date": "2023-06-15T10:30:00Z",
        "text": "Hello there"
      },
      "last_updated": "2023-06-15T10:30:00Z",
      "total_messages": 42
    }
  ]
}
```

#### 3. Messages

**GET /messages**

Retrieve all messages with optional date filtering.

Query Parameters:
- `since` (optional): ISO date string for messages after this date
- `until` (optional): ISO date string for messages before this date

Response:
```json
{
  "conversations": [...],
  "messages": [
    {
      "id": "unique_message_id",
      "conversation_id": "1234567890@c.us",
      "date": "2023-06-15T10:30:00Z",
      "text": "Message content",
      "from_user": true,
      "sender_id": "sender_id@c.us",
      "sender_name": "Sender Name",
      "conversation_name": "Contact Name",
      "source": "whatsapp"
    }
  ]
}
```

**GET /messages/:conversationId**

Retrieve messages for a specific conversation.

Query Parameters:
- `since` (optional): ISO date string
- `until` (optional): ISO date string

Response:
```json
{
  "messages": [...]
}
```

### WebSocket Events

The WebSocket server emits these events:

#### 1. QR Code Event

```json
{
  "type": "qr",
  "data": "data:image/png;base64,..."
}
```

#### 2. Status Event

```json
{
  "type": "status",
  "status": "ready"
}
```

#### 3. Message Event

```json
{
  "type": "message",
  "data": {
    "id": "unique_message_id",
    "conversation_id": "1234567890@c.us",
    "date": "2023-06-15T10:30:00Z",
    "text": "Message content",
    "from_user": true,
    "sender_id": "sender_id@c.us",
    "sender_name": "Sender Name",
    "conversation_name": "Contact Name",
    "source": "whatsapp"
  }
}
```

## Deployment

### Docker Configuration

```dockerfile
FROM node:18-slim

# Install dependencies for Puppeteer
RUN apt-get update && apt-get install -y \
    gconf-service \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libappindicator1 \
    libnss3 \
    lsb-release \
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --production

COPY . .

EXPOSE 3000
EXPOSE 3001

CMD ["node", "index.js"]
```

### Docker Compose

```yaml
version: '3'

services:
  whatsapp-service:
    build: ./whatsapp-service
    container_name: whatsapp-service
    ports:
      - "3000:3000"
      - "3001:3001"
    volumes:
      - ./data:/app/data
    environment:
      - NODE_ENV=production
      - PORT=3000
      - WS_PORT=3001
      - DATA_DIR=/app/data
```

## Testing Strategy

### Unit Tests

Example unit test for the MessageStore:

```javascript
// message-store.test.js
const { expect } = require('chai');
const MessageStore = require('../message-store');

describe('MessageStore', () => {
  let store;
  
  beforeEach(() => {
    store = new MessageStore();
  });
  
  it('should add a message', () => {
    const message = {
      id: 'msg1',
      conversation_id: 'conv1',
      date: '2023-06-15T10:30:00Z',
      text: 'Hello',
      from_user: true,
      sender_id: 'sender1',
      conversation_name: 'Test Conversation'
    };
    
    store.addMessage(message);
    const messages = store.getMessages();
    
    expect(messages).to.have.lengthOf(1);
    expect(messages[0]).to.deep.equal(message);
  });
  
  it('should filter messages by date', () => {
    const message1 = {
      id: 'msg1',
      conversation_id: 'conv1',
      date: '2023-06-15T10:30:00Z',
      text: 'Hello',
      from_user: true,
      sender_id: 'sender1'
    };
    
    const message2 = {
      id: 'msg2',
      conversation_id: 'conv1',
      date: '2023-06-16T10:30:00Z',
      text: 'World',
      from_user: true,
      sender_id: 'sender1'
    };
    
    store.addMessage(message1);
    store.addMessage(message2);
    
    const since = new Date('2023-06-16T00:00:00Z');
    const filtered = store.getMessages({ since });
    
    expect(filtered).to.have.lengthOf(1);
    expect(filtered[0].id).to.equal('msg2');
  });
});
```

### Integration Test with Mock WhatsApp Client

```javascript
// api-server.integration.test.js
const { expect } = require('chai');
const request = require('supertest');
const express = require('express');
const EventEmitter = require('events');
const APIServer = require('../api-server');
const MessageStore = require('../message-store');

class MockWhatsAppClient extends EventEmitter {
  constructor() {
    super();
    this.isReady = false;
    this.qrCode = 'mock-qr-code';
  }
  
  async getStatus() {
    return {
      ready: this.isReady,
      qrCode: this.qrCode
    };
  }
  
  async getChats() {
    return [];
  }
  
  async getMessages() {
    return [];
  }
}

describe('API Server', () => {
  let server;
  let app;
  let client;
  let messageStore;
  
  beforeEach(() => {
    client = new MockWhatsAppClient();
    messageStore = new MessageStore();
    server = new APIServer(client, messageStore, { port: 0 });
    app = server.app;
  });
  
  it('should return status', async () => {
    const response = await request(app).get('/status');
    
    expect(response.status).to.equal(200);
    expect(response.body).to.deep.equal({
      ready: false,
      qrCode: 'mock-qr-code'
    });
  });
  
  it('should return messages', async () => {
    const message = {
      id: 'msg1',
      conversation_id: 'conv1',
      date: '2023-06-15T10:30:00Z',
      text: 'Hello',
      from_user: true,
      sender_id: 'sender1'
    };
    
    messageStore.addMessage(message);
    
    const response = await request(app).get('/messages');
    
    expect(response.status).to.equal(200);
    expect(response.body.messages).to.have.lengthOf(1);
    expect(response.body.messages[0]).to.deep.equal(message);
  });
});
```

## Security Considerations

1. **Authentication**: The service doesn't implement authentication beyond the WhatsApp QR code. In production, consider adding API authentication.

2. **Data Protection**: 
   - Message data should be encrypted at rest
   - Session data should be securely stored
   - Implement HTTPS for API communication

3. **Rate Limiting**:
   - Add rate limiting to prevent abuse
   - Implement exponential backoff for API requests to WhatsApp

4. **Browser Security**:
   - Run Puppeteer with minimal permissions
   - Use seccomp filters to restrict system calls
   - Consider using a content security policy

## Error Handling

1. **WhatsApp Client Errors**
   - Handle authentication failures
   - Manage reconnection logic
   - Detect and recover from browser crashes

2. **API Errors**
   - Use proper HTTP status codes
   - Return informative error messages
   - Implement logging and monitoring

3. **Resilience Patterns**
   - Implement circuit breakers for external calls
   - Add graceful degradation for non-critical features
   - Use retry logic with exponential backoff

## Conclusion

This Node.js service provides a robust interface to WhatsApp Web JS, enabling communication with Python-based systems while maintaining the security and reliability needed for production use. By following these specifications, developers can implement a service that bridges the gap between WhatsApp's JavaScript API and Python applications. 