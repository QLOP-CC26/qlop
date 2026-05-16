class UsersHandler {
  constructor(service, validator) {
    this._service = service;
    this._validator = validator;

    this.postUserHandler = this.postUserHandler.bind(this);
  }

  async postUserHandler(req, res, next) {
    try {
      this._validator.validateUserPayload(req.body);
      const { username, password, fullname } = req.body;

      const userId = await this._service.addUser({ username, password, fullname });

      res.status(201).json({
        status: 'success',
        message: 'User berhasil ditambahkan',
        data: {
          userId,
        },
      });
    } catch (error) {
      next(error);
    }
  }
}

module.exports = UsersHandler;
