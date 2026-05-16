const AuthenticationsHandler = require('./handler');
const routes = require('./routes');

module.exports = {
  name: 'authentications',
  register: (authenticationsService, usersService, validator) => {
    const authenticationsHandler = new AuthenticationsHandler(authenticationsService, usersService, validator);
    return routes(authenticationsHandler);
  },
};
