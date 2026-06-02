require('dotenv').config();

const express = require('express');
const cors = require('cors');
const multer = require('multer');

const authRoutes = require('./routes/authRoutes');
const cvRoutes = require('./routes/cvRoutes');

const createApp = () => {
  const app = express();

  const allowedOrigins = process.env.FRONTEND_URL
    ? process.env.FRONTEND_URL.split(',').map((o) => o.trim().replace(/\/$/, ''))
    : [];

  app.use(cors({
    origin: (origin, callback) => {
      // Izinkan jika tidak ada origin (seperti API tester Postman, curl, dll)
      if (!origin) return callback(null, true);

      const cleanOrigin = origin.trim().replace(/\/$/, '');
      const isAllowed =
        allowedOrigins.length === 0 ||
        allowedOrigins.includes(cleanOrigin) ||
        process.env.FRONTEND_URL === '*';

      if (isAllowed) {
        return callback(null, true);
      }

      console.warn(`[CORS Blocked] Origin: ${origin}. Allowed Origins:`, allowedOrigins);
      return callback(new Error('Not allowed by CORS'));
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  }));

  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  app.get('/', (req, res) => {
    res.status(200).json({
      status: 'success',
      message: 'QLOP API is running',
      version: '2.0.0',
      timestamp: new Date().toISOString(),
    });
  });

  app.use('/api/auth', authRoutes);
  app.use('/api/cv', cvRoutes);

  app.use((req, res) => {
    res.status(404).json({
      status: 'fail',
      message: `Route ${req.method} ${req.originalUrl} not found.`,
    });
  });

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    if (err instanceof multer.MulterError) {
      return res.status(400).json({ status: 'fail', message: `Upload error: ${err.message}` });
    }

    if (err.message && err.message.includes('Unsupported file format')) {
      return res.status(400).json({ status: 'fail', message: err.message });
    }

    console.error('[Global Error Handler]', err);
    return res.status(500).json({ status: 'error', message: 'Internal server error occurred.' });
  });

  return app;
};

module.exports = createApp;
