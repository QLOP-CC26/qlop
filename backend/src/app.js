require('dotenv').config();

const express = require('express');
const multer = require('multer');
const ClientError = require('./exceptions/ClientError');

// Services and validators will be required lazily or injected for tests
const usersAPI = require('./api/users');
const authenticationsAPI = require('./api/authentications');

const createApp = ({ usersService, authenticationsService, UsersValidator, AuthenticationsValidator } = {}) => {
  const app = express();

  app.use(express.json());

  // health endpoint
  app.get('/', (req, res) => {
    res.status(200).json({ status: 'success', message: 'QLOP API is running' });
  });

  // instantiate defaults if not provided
  const UsersService = require('./services/postgres/UsersService');
  const AuthenticationsService = require('./services/postgres/AuthenticationsService');
  const UsersValidatorModule = require('./validators/users');
  const AuthenticationsValidatorModule = require('./validators/authentications');

  const usersSvc = usersService || new UsersService();
  const authSvc = authenticationsService || new AuthenticationsService();
  const usersVal = UsersValidator || UsersValidatorModule;
  const authVal = AuthenticationsValidator || AuthenticationsValidatorModule;

  app.use('/users', usersAPI.register(usersSvc, usersVal));
  app.use('/authentications', authenticationsAPI.register(authSvc, usersSvc, authVal));

  // 404 handler
  app.use((req, res) => {
    res.status(404).json({ status: 'fail', message: 'Route not found' });
  });

  // error handler
  app.use((err, req, res, next) => {
    if (err instanceof multer.MulterError) {
      return res.status(400).json({ status: 'fail', message: err.message });
    }

    if (err instanceof ClientError) {
      return res.status(err.statusCode).json({ status: 'fail', message: err.message });
    }

    return res.status(500).json({ status: 'error', message: 'Sorry, a server error occurred.' });
  });

  return app;
};

module.exports = createApp;
