# WhatsApp Service

This service provides a REST API and WebSocket interface for integrating WhatsApp messaging into the ICI system. It uses the [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js) library to interact with WhatsApp Web.

## Features

- Multiple WhatsApp sessions management
- QR code authentication
- REST API for sending and receiving messages
- WebSocket interface for real-time updates
- Session persistence

## Directory Structure

```
whatsapp-service/
├── config.js           # Configuration file
├── data/
│   └── sessions/       # WhatsApp session data
├── package.json        # Dependencies and scripts
├── src/
│   ├── api/            # REST API endpoints
│   │   └── routes/     # API routes
│   ├── client/         # WhatsApp client implementation
│   ├── utils/          # Utility functions
│   ├── websocket/      # WebSocket server
│   └── index.js        # Main entry point
└── README.md           # This file
```

## API Endpoints

### Session Management

- `GET /api/sessions` - List all active WhatsApp sessions
- `POST /api/sessions` - Create a new WhatsApp session
- `GET /api/sessions/:sessionId` - Get session status
- `GET /api/sessions/:sessionId/qr` - Get QR code for session authentication
- `DELETE /api/sessions/:sessionId` - Logout and destroy a session

### Messaging

- `POST /api/messages/:sessionId/send` - Send a message
- `GET /api/messages/:sessionId/chats` - Get all chats
- `GET /api/messages/:sessionId/chat/:chatId` - Get messages from a specific chat
- `GET /api/messages/:sessionId/contacts` - Get all contacts

## WebSocket Interface

The WebSocket server provides real-time updates for:

- Connection state changes
- Incoming messages

### Events

- `connection_update` - When the connection state changes (e.g., QR code received, authenticated, connected)
- `message` - When a new message is received

## Installation and Setup

1. Install dependencies:
```
npm install
```

2. Start the service:
```
npm start
```

For development:
```
npm run dev
```

## Authentication Flow

1. Create a new session using the REST API
2. Retrieve the QR code using the API
3. Scan the QR code with your WhatsApp mobile app
4. Once authenticated, the session will be saved and can be reused

## Notes

- Puppeteer is required for WhatsApp Web interaction
- Session data is stored in the `data/sessions` directory
- Multiple WhatsApp accounts can be used simultaneously with different session IDs 