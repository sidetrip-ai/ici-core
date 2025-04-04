/**
 * WhatsApp Service - Main Entry Point
 */
const express = require('express');
const http = require('http');
const path = require('path');
const cors = require('cors');
const WebSocket = require('ws');
const whatsAppClient = require('./client/whatsapp-client');
const eventEmitter = require('./utils/event-emitter');
const config = require('../config');

// Import API routes
const authRoutes = require('./api/routes/auth');
const messagesRoutes = require('./api/routes/messages');

// Create Express app
const app = express();
const server = http.createServer(app);

// Use middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static files from 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// Use API routes
app.use('/api', authRoutes);
app.use('/api', messagesRoutes);

// Root route redirects to index.html
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    success: false,
    message: 'Route not found'
  });
});

// WebSocket server
const wss = new WebSocket.Server({ 
  server: server,
  path: '/ws'
});

// WebSocket connection handler
wss.on('connection', (ws) => {
  console.log('WebSocket client connected');
  
  // Send initial status on connection
  ws.send(JSON.stringify({
    type: 'status',
    data: whatsAppClient.getStatus()
  }));
  
  // Event handlers
  const handleQr = (data) => {
    ws.send(JSON.stringify({
      type: 'qr',
      data: {
        timestamp: data.timestamp,
        hasQrCode: true
      }
    }));
  };
  
  const handleStatusChange = (status) => {
    ws.send(JSON.stringify({
      type: 'status',
      data: whatsAppClient.getStatus()
    }));
  };
  
  // Register event listeners
  eventEmitter.on('whatsapp.qr', handleQr);
  eventEmitter.on('whatsapp.ready', handleStatusChange);
  eventEmitter.on('whatsapp.disconnected', handleStatusChange);
  eventEmitter.on('whatsapp.auth_failure', handleStatusChange);
  
  // Handle WebSocket messages (like ping)
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      
      if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  });
  
  // Handle WebSocket close
  ws.on('close', () => {
    console.log('WebSocket client disconnected');
    
    // Remove event listeners
    eventEmitter.off('whatsapp.qr', handleQr);
    eventEmitter.off('whatsapp.ready', handleStatusChange);
    eventEmitter.off('whatsapp.disconnected', handleStatusChange);
    eventEmitter.off('whatsapp.auth_failure', handleStatusChange);
  });
});

// Initialize WhatsApp client
whatsAppClient.initialize()
  .then(() => {
    console.log('WhatsApp client initialized');
  })
  .catch((error) => {
    console.error('Failed to initialize WhatsApp client:', error);
  });

// Start the server
const port = config.port || 3000;
server.listen(port, () => {
  console.log(`WhatsApp service running on port ${port}`);
  console.log(`Web interface available at http://localhost:${port}/`);
}); 