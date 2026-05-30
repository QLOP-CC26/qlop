const request = require('supertest');
const createApp = require('../src/app');

describe('App basic routes', () => {
  test('GET / returns 200 and api running message', async () => {
    const app = createApp();
    const res = await request(app).get('/');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('status', 'success');
    expect(res.body).toHaveProperty('message', 'API is running');
  });
});
