const AuthenticationError = require('../exceptions/AuthenticationError');
const TokenManager = require('../tokenize/TokenManager');

const authenticate = (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;

    if (!authHeader) {
      throw new AuthenticationError('Token tidak ditemukan');
    }

    const token = authHeader.replace('Bearer ', '');
    const decoded = TokenManager.verifyAccessToken(token);

    req.auth = {
      userId: decoded.id,
    };

    next();
  } catch (error) {
    next(error);
  }
};

module.exports = authenticate;
