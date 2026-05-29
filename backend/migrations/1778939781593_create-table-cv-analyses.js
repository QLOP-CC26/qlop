/* eslint-disable camelcase */

exports.up = (pgm) => {
  pgm.createTable('cv_analyses', {
    id: {
      type: 'UUID',
      primaryKey: true,
      default: pgm.func('gen_random_uuid()'),
    },
    user_id: {
      type: 'UUID',
      notNull: true,
      references: '"users"',
      onDelete: 'CASCADE',
    },
    cv_url: {
      type: 'VARCHAR(500)',
      notNull: true,
    },
    profile_entities: {
      type: 'JSONB',
      notNull: false,
    },
    extracted_skills: {
      type: 'JSONB',
      notNull: false,
    },
    target_role: {
      type: 'VARCHAR(255)',
      notNull: false,
    },
    top_skills: {
      type: 'JSONB',
      notNull: false,
    },
    recommended_courses: {
      type: 'JSONB',
      notNull: false,
    },
    gemini_roles: {
      type: 'JSONB',
      notNull: false,
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
  pgm.dropTable('cv_analyses');
};
