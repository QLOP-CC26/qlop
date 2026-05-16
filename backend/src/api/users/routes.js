const express = require('express');

const routes = (handler) => {
  const router = express.Router();

  router.post('/', (req, res, next) => handler.postUserHandler(req, res, next));

  return router;
};

module.exports = routes;
