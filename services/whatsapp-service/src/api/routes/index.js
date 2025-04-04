const express = require('express');
const router = express.Router();
const sessionsRoutes = require('./sessions');
const messagesRoutes = require('./messages');
const logger = require('../../utils/logger');

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'whatsapp-service',
    timestamp: new Date().toISOString()
  });
});

// Mount routes
router.use('/sessions', sessionsRoutes);
router.use('/messages', messagesRoutes);

// Handle 404 for API routes
router.use((req, res) => {
  logger.warn(`API endpoint not found: ${req.method} ${req.originalUrl}`);
  res.status(404).json({
    success: false,
    error: 'API endpoint not found'
  });
});

module.exports = router; 