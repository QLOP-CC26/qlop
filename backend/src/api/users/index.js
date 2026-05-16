const UsersHandler = require('./handler');
const routes = require('./routes');

module.exports = {
  name: 'users',
  register: (service, validator) => {
    const usersHandler = new UsersHandler(service, validator);
    return routes(usersHandler);
  },
};
