const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { OAuth2Client } = require('google-auth-library');
const { query } = require('../config/db');

const generateToken = (user) =>
  jwt.sign(
    { id: user.id, email: user.email, name: user.name },
    process.env.ACCESS_TOKEN_KEY,
    { expiresIn: parseInt(process.env.ACCESS_TOKEN_AGE, 10) || '1800s' }
  );

const register = async (req, res) => {
  try {
    const { name, email, password } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({
        status: 'fail',
        message: 'Name, email, and password fields are required.',
      });
    }

    const existingUser = await query('SELECT id FROM users WHERE email = $1', [email]);
    if (existingUser.rows.length > 0) {
      return res.status(409).json({
        status: 'fail',
        message: 'Email is already registered. Please use another email.',
      });
    }

    const hashedPassword = await bcrypt.hash(password, 10);

    const result = await query(
      `INSERT INTO users (email, password, name)
       VALUES ($1, $2, $3)
       RETURNING id, email, name, created_at`,
      [email, hashedPassword, name]
    );

    const newUser = result.rows[0];
    const token = generateToken(newUser);

    return res.status(201).json({
      status: 'success',
      message: 'Registration successful.',
      data: {
        token,
        user: { id: newUser.id, name: newUser.name, email: newUser.email },
      },
    });
  } catch (error) {
    console.error('[authController.register]', error);
    return res.status(500).json({
      status: 'error',
      message: 'Internal server error occurred during registration.',
    });
  }
};

const login = async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        status: 'fail',
        message: 'Email and password fields are required.',
      });
    }

    const result = await query(
      'SELECT id, email, name, password FROM users WHERE email = $1',
      [email]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({
        status: 'fail',
        message: 'Incorrect email or password.',
      });
    }

    const user = result.rows[0];

    if (!user.password) {
      return res.status(401).json({
        status: 'fail',
        message: 'This account is registered via Google. Please use Google Login.',
      });
    }

    const isPasswordMatch = await bcrypt.compare(password, user.password);
    if (!isPasswordMatch) {
      return res.status(401).json({
        status: 'fail',
        message: 'Incorrect email or password.',
      });
    }

    const token = generateToken(user);

    return res.status(200).json({
      status: 'success',
      message: 'Login successful.',
      data: {
        token,
        user: { id: user.id, name: user.name, email: user.email },
      },
    });
  } catch (error) {
    console.error('[authController.login]', error);
    return res.status(500).json({
      status: 'error',
      message: 'Internal server error occurred during login.',
    });
  }
};

const googleAuth = async (req, res) => {
  try {
    const { id_token } = req.body;

    if (!id_token) {
      return res.status(400).json({
        status: 'fail',
        message: 'id_token is required.',
      });
    }

    const client = new OAuth2Client(process.env.GOOGLE_CLIENT_ID);
    const ticket = await client.verifyIdToken({
      idToken: id_token,
      audience: process.env.GOOGLE_CLIENT_ID,
    });

    const payload = ticket.getPayload();
    const { sub: googleId, email, name } = payload;

    let userResult = await query(
      'SELECT id, email, name FROM users WHERE google_id = $1 OR email = $2',
      [googleId, email]
    );

    let user;

    if (userResult.rows.length > 0) {
      user = userResult.rows[0];
      await query(
        'UPDATE users SET google_id = $1, updated_at = NOW() WHERE id = $2',
        [googleId, user.id]
      );
    } else {
      const insertResult = await query(
        `INSERT INTO users (email, name, google_id)
         VALUES ($1, $2, $3)
         RETURNING id, email, name`,
        [email, name, googleId]
      );
      user = insertResult.rows[0];
    }

    const token = generateToken(user);

    return res.status(200).json({
      status: 'success',
      message: 'Google login successful.',
      data: {
        token,
        user: { id: user.id, name: user.name, email: user.email },
      },
    });
  } catch (error) {
    console.error('[authController.googleAuth]', error);

    if (error.message && error.message.includes('Token used too late')) {
      return res.status(401).json({
        status: 'fail',
        message: 'Google token has expired.',
      });
    }

    return res.status(500).json({
      status: 'error',
      message: 'Internal server error occurred during Google token verification.',
    });
  }
};

module.exports = { register, login, googleAuth };
