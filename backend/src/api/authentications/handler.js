const TokenManager = require('../../tokenize/TokenManager');

class AuthenticationsHandler {
  constructor(authenticationsService, usersService, validator) {
    this._authenticationsService = authenticationsService;
    this._usersService = usersService;
    this._validator = validator;

    this.postAuthenticationHandler = this.postAuthenticationHandler.bind(this);
    this.putAuthenticationHandler = this.putAuthenticationHandler.bind(this);
    this.deleteAuthenticationHandler = this.deleteAuthenticationHandler.bind(this);
  }

  async postAuthenticationHandler(req, res, next) {
    try {
      this._validator.validateLoginPayload(req.body);
      const { username, password } = req.body;

      const userId = await this._usersService.verifyUserCredential(username, password);

      const accessToken = TokenManager.generateAccessToken({ id: userId });
      const refreshToken = TokenManager.generateRefreshToken({ id: userId });

      await this._authenticationsService.addRefreshToken(refreshToken);

      res.status(201).json({
        status: 'success',
        data: {
          accessToken,
          refreshToken,
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async putAuthenticationHandler(req, res, next) {
    try {
      this._validator.validateRefreshTokenPayload(req.body);
      const { refreshToken } = req.body;

      // verify token signature
      const artifacts = TokenManager.verifyRefreshToken(refreshToken);

      // verify token exists in DB
      await this._authenticationsService.verifyRefreshToken(refreshToken);

      const accessToken = TokenManager.generateAccessToken({ id: artifacts.id });

      res.status(200).json({
        status: 'success',
        data: {
          accessToken,
        },
      });
    } catch (error) {
      next(error);
    }
  }

  async deleteAuthenticationHandler(req, res, next) {
    try {
      this._validator.validateRefreshTokenPayload(req.body);
      const { refreshToken } = req.body;

      await this._authenticationsService.verifyRefreshToken(refreshToken);
      await this._authenticationsService.deleteRefreshToken(refreshToken);

      res.status(200).json({
        status: 'success',
        message: 'Refresh token berhasil dihapus',
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = AuthenticationsHandler;
