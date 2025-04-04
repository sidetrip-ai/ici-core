/**
 * WhatsApp authentication routes
 */

const express = require('express');
const whatsAppClient = require('../../client/whatsapp-client');
const eventEmitter = require('../../utils/event-emitter');

const router = express.Router();

/**
 * GET /api/status
 * Get the current status of the WhatsApp client
 */
router.get('/status', async (req, res) => {
  const status = whatsAppClient.getStatus();
  res.json(status);
});

/**
 * GET /api/qr
 * Get the current QR code or generate a new one
 */
router.get('/qr', async (req, res) => {
  try {
    // Initialize client if not already done
    if (!whatsAppClient.initialized) {
      await whatsAppClient.initialize();
    }

    // If already connected, return an error
    if (whatsAppClient.status === 'CONNECTED') {
      return res.status(400).json({
        success: false,
        message: 'Already connected to WhatsApp'
      });
    }

    // If we have a QR code that's less than 2 minutes old, return it
    const qrCodeImage = whatsAppClient.getQrCodeImage();
    if (qrCodeImage && whatsAppClient.lastQrTimestamp && 
        Date.now() - whatsAppClient.lastQrTimestamp < 120000) {
      // Set content type to image/png
      res.setHeader('Content-Type', 'image/png');
      
      // Convert data URL to buffer and send
      const imgData = qrCodeImage.split(',')[1];
      const imgBuffer = Buffer.from(imgData, 'base64');
      return res.send(imgBuffer);
    }

    // Generate a new QR code if none exists or it's too old
    const result = await whatsAppClient.generateNewQrCode();
    
    if (!result.success) {
      return res.status(500).json({
        success: false,
        message: result.message || 'Failed to generate QR code'
      });
    }

    // Wait for a new QR code to be generated (with a timeout)
    let timeoutId = null;
    const waitForQrCode = new Promise((resolve, reject) => {
      // Set a timeout
      timeoutId = setTimeout(() => {
        reject(new Error('Timeout waiting for QR code'));
      }, 10000);

      // Listen for QR code event
      const handler = (data) => {
        clearTimeout(timeoutId);
        resolve(data);
        eventEmitter.off('whatsapp.qr', handler); // Remove listener
      };

      eventEmitter.once('whatsapp.qr', handler);
    });

    try {
      await waitForQrCode;
      
      // Get the newly generated QR code
      const newQrCodeImage = whatsAppClient.getQrCodeImage();
      
      if (!newQrCodeImage) {
        return res.status(500).json({
          success: false,
          message: 'Failed to generate QR code image'
        });
      }
      
      // Set content type to image/png
      res.setHeader('Content-Type', 'image/png');
      
      // Convert data URL to buffer and send
      const imgData = newQrCodeImage.split(',')[1];
      const imgBuffer = Buffer.from(imgData, 'base64');
      return res.send(imgBuffer);
    } catch (timeoutError) {
      clearTimeout(timeoutId);
      return res.status(500).json({
        success: false,
        message: 'Timeout waiting for QR code'
      });
    }
  } catch (error) {
    console.error('Error in QR code generation:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Internal server error'
    });
  }
});

/**
 * POST /api/logout
 * Logout from WhatsApp Web
 */
router.post('/logout', async (req, res) => {
  try {
    const result = await whatsAppClient.logout();
    res.json(result);
  } catch (error) {
    console.error('Error in logout:', error);
    res.status(500).json({
      success: false,
      message: error.message || 'Internal server error'
    });
  }
});

module.exports = router; 