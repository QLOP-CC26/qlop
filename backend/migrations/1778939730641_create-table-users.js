/* eslint-disable camelcase */

exports.up = (pgm) => {
  pgm.sql('CREATE EXTENSION IF NOT EXISTS pgcrypto;');

  pgm.createTable('users', {
    id: {
      type: 'UUID',
      primaryKey: true,
      default: pgm.func('gen_random_uuid()'),
    },
    email: {
      type: 'VARCHAR(255)',
      unique: true,
      notNull: true,
    },
    password: {
      type: 'VARCHAR(255)',
      notNull: false,
    },
    google_id: {
      type: 'VARCHAR(255)',
      unique: true,
      notNull: false,
    },
    name: {
      type: 'VARCHAR(255)',
      notNull: true,
    },
    created_at: {
      type: 'TIMESTAMP',
      default: pgm.func('NOW()'),
    },
    updated_at: {
      type: 'TIMESTAMP',
      default: pgm.func('NOW()'),
    },
  });
};

exports.down = (pgm) => {
  pgm.dropTable('users');
};
