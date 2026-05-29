require('dotenv').config();

const createApp = require('./app');

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Promise Rejection at:', promise, '\nReason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

const init = async () => {
  try {
    const app = createApp();
    const PORT = process.env.PORT || 5000;
    const HOST = process.env.HOST || 'localhost';

    app.listen(PORT, HOST, () => {
      console.log(`QLOP API running on http://${HOST}:${PORT}`);
    });
  } catch (error) {
    console.error('Fatal error during server initialization:', error);
    process.exit(1);
  }
};

init();