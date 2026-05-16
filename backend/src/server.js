require('dotenv').config();

const UsersService = require('./services/postgres/UsersService');
const AuthenticationsService = require('./services/postgres/AuthenticationsService');
const UsersValidator = require('./validators/users');
const AuthenticationsValidator = require('./validators/authentications');

const createApp = require('./app');

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

const init = async () => {
  try {
    const usersService = new UsersService();
    const authenticationsService = new AuthenticationsService();

    const app = createApp({
      usersService,
      authenticationsService,
      UsersValidator,
      AuthenticationsValidator,
    });

    const port = process.env.PORT || 5000;
    const host = process.env.HOST || 'localhost';

    app.listen(port, host, () => {
      console.log(`Server running on http://${host}:${port}`);
    });
  } catch (error) {
    console.error('Fatal error during initialization:', error);
    process.exit(1);
  }
};

init();