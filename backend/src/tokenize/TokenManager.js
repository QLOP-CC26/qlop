const Jwt = require('jsonwebtoken');
const InvariantError = require('../exceptions/InvariantError');

const TokenManager = {
  generateAccessToken: (payload) => {
    const expiresIn = process.env.ACCESS_TOKEN_AGE || '1800s';
    return Jwt.sign(payload, process.env.ACCESS_TOKEN_KEY, { expiresIn });
  },
  generateRefreshToken: (payload) => Jwt.sign(payload, process.env.REFRESH_TOKEN_KEY),
  verifyAccessToken: (accessToken) => {
    try {
      const artifacts = Jwt.verify(accessToken, process.env.ACCESS_TOKEN_KEY);
      return artifacts;
    } catch (error) {
      throw new InvariantError('Access token tidak valid');
    }
  },
  verifyRefreshToken: (refreshToken) => {
    try {
      const artifacts = Jwt.verify(refreshToken, process.env.REFRESH_TOKEN_KEY);
      return artifacts;
    } catch (error) {
      throw new InvariantError('Refresh token tidak valid');
    }
  },
  decodePayload: (token) => Jwt.decode(token),
};

module.exports = TokenManager;
