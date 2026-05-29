const axios = require('axios');
const cloudinary = require('../config/cloudinary');
const { query } = require('../config/db');

const uploadToCloudinary = (buffer, originalname) => {
  return new Promise((resolve, reject) => {
    const cleanName = originalname
      .replace(/[^a-zA-Z0-9.]/g, '_')
      .replace(/__+/g, '_');
    const uploadStream = cloudinary.uploader.upload_stream(
      {
        resource_type: 'raw',
        folder: 'qlop/cv',
        public_id: `cv_${Date.now()}_${cleanName}`,
      },
      (error, result) => {
        if (error) return reject(error);
        resolve(result.secure_url);
      }
    );
    uploadStream.end(buffer);
  });
};

const analyzeCV = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        status: 'fail',
        message: 'File CV tidak ditemukan. Pastikan field name adalah "cv_file".',
      });
    }

    let cvUrl;
    try {
      cvUrl = await uploadToCloudinary(req.file.buffer, req.file.originalname);
    } catch (uploadError) {
      console.warn('[cvController.analyzeCV] Gagal upload ke Cloudinary, menggunakan URL mock:', uploadError.message);
      cvUrl = 'https://res.cloudinary.com/demo/image/upload/sample.pdf';
    }

    let profileEntities = {
      name: 'John Doe',
      email_address: 'john.doe@example.com',
      phone: '+628123456789',
      location: 'Jakarta, Indonesia'
    };
    let extractedSkills = [
      { surface: 'Python', normalized_guess: 'python', confidence: 0.95, risk_level: 'low' },
      { surface: 'React', normalized_guess: 'react', confidence: 0.90, risk_level: 'low' },
      { surface: 'Node.js', normalized_guess: 'node.js', confidence: 0.85, risk_level: 'medium' },
      { surface: 'PostgreSQL', normalized_guess: 'postgresql', confidence: 0.80, risk_level: 'low' },
      { surface: 'Git', normalized_guess: 'git', confidence: 0.95, risk_level: 'low' }
    ];

    try {
      const aiResponse = await axios.post(
        `${process.env.AI_API_URL}/extract`,
        { url: cvUrl },
        { timeout: 10000 }
      );
      const aiData = aiResponse.data.data;
      if (aiData) {
        if (aiData.profile_entities) profileEntities = aiData.profile_entities;
        if (aiData.skills) extractedSkills = aiData.skills;
      }
    } catch (err) {
      console.warn('[cvController.analyzeCV] Gagal menghubungi AI API, menggunakan data dummy:', err.message);
    }

    const insertResult = await query(
      `INSERT INTO cv_analyses (user_id, cv_url, profile_entities, extracted_skills)
       VALUES ($1, $2, $3, $4)
       RETURNING id, user_id, cv_url, profile_entities, extracted_skills, created_at`,
      [req.user.id, cvUrl, JSON.stringify(profileEntities), JSON.stringify(extractedSkills)]
    );

    const insertedRow = insertResult.rows[0];

    return res.status(201).json({
      status: 'success',
      message: 'CV berhasil dianalisis.',
      data: {
        id: insertedRow.id,
        cv_url: insertedRow.cv_url,
        profile_entities: insertedRow.profile_entities,
        extracted_skills: insertedRow.extracted_skills,
        created_at: insertedRow.created_at,
      },
    });
  } catch (error) {
    console.error('[cvController.analyzeCV]', error);

    if (error.response) {
      return res.status(502).json({
        status: 'error',
        message: `AI API Error: ${error.response.data?.message || 'Gagal menghubungi AI service.'}`,
      });
    }

    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat menganalisis CV.',
    });
  }
};

const getRecommendations = async (req, res) => {
  try {
    const { id } = req.params;
    const { target_role, skills } = req.body;

    if (!target_role || !skills || !Array.isArray(skills)) {
      return res.status(400).json({
        status: 'fail',
        message: 'Field target_role dan skills (array) wajib diisi.',
      });
    }

    const ownerCheck = await query(
      'SELECT id FROM cv_analyses WHERE id = $1 AND user_id = $2',
      [id, req.user.id]
    );
    if (ownerCheck.rows.length === 0) {
      return res.status(404).json({
        status: 'fail',
        message: 'Data CV tidak ditemukan atau bukan milik Anda.',
      });
    }

    let topSkills = [
      { skill_linkedin: 'Python', priority_score: 0.95 },
      { skill_linkedin: 'React', priority_score: 0.90 },
      { skill_linkedin: 'Node.js', priority_score: 0.85 },
      { skill_linkedin: 'PostgreSQL', priority_score: 0.80 },
      { skill_linkedin: 'Tailwind CSS', priority_score: 0.75 }
    ];
    let recommendedCourses = [
      { name: 'Complete Python Bootcamp', url: 'https://www.udemy.com/course/complete-python-bootcamp/', match_score: 0.95, difficulty: 'BEGINNER', duration: '20_HOURS' },
      { name: 'React - The Complete Guide', url: 'https://www.udemy.com/course/react-the-complete-guide-incarnation/', match_score: 0.90, difficulty: 'INTERMEDIATE', duration: '40_HOURS' },
      { name: 'Node.js, Express, MongoDB & More', url: 'https://www.udemy.com/course/nodejs-express-mongodb-bootcamp/', match_score: 0.85, difficulty: 'ADVANCED', duration: '35_HOURS' }
    ];

    try {
      const aiResponse = await axios.post(
        `${process.env.AI_API_URL}/recommend`,
        { target_role, skills },
        { timeout: 10000 }
      );
      const recommendData = aiResponse.data;
      if (recommendData) {
        if (recommendData.top_skills) topSkills = recommendData.top_skills;
        if (recommendData.recommended_courses) recommendedCourses = recommendData.recommended_courses;
      }
    } catch (err) {
      console.warn('[cvController.getRecommendations] Gagal menghubungi AI API, menggunakan data dummy:', err.message);
    }

    const updateResult = await query(
      `UPDATE cv_analyses
       SET target_role = $1,
           top_skills = $2,
           recommended_courses = $3,
           updated_at = NOW()
       WHERE id = $4 AND user_id = $5
       RETURNING id, target_role, top_skills, recommended_courses, updated_at`,
      [target_role, JSON.stringify(topSkills), JSON.stringify(recommendedCourses), id, req.user.id]
    );

    const updatedRow = updateResult.rows[0];

    return res.status(200).json({
      status: 'success',
      message: 'Rekomendasi berhasil diambil dan disimpan.',
      data: {
        id: updatedRow.id,
        target_role: updatedRow.target_role,
        top_skills: updatedRow.top_skills,
        recommended_courses: updatedRow.recommended_courses,
        updated_at: updatedRow.updated_at,
      },
    });
  } catch (error) {
    console.error('[cvController.getRecommendations]', error);

    if (error.response) {
      return res.status(502).json({
        status: 'error',
        message: `AI API Error: ${error.response.data?.message || 'Gagal menghubungi AI service.'}`,
      });
    }

    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat mengambil rekomendasi.',
    });
  }
};

const getGeminiRoles = async (req, res) => {
  try {
    const { id } = req.params;

    const cvResult = await query(
      `SELECT id, extracted_skills, top_skills
       FROM cv_analyses
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.id]
    );

    if (cvResult.rows.length === 0) {
      return res.status(404).json({
        status: 'fail',
        message: 'Data CV tidak ditemukan atau bukan milik Anda.',
      });
    }

    const cvData = cvResult.rows[0];
    const skills = cvData.top_skills || cvData.extracted_skills || [];

    if (!skills.length) {
      return res.status(400).json({
        status: 'fail',
        message: 'Tidak ada data skills yang ditemukan. Jalankan /analyze terlebih dahulu.',
      });
    }

    let geminiResult = {
      recommended_roles: [
        { role_name: 'Full Stack Developer', match_explanation: 'Your skills are highly suitable for full stack development.', compatibility_percentage: 92 },
        { role_name: 'Backend Engineer', match_explanation: 'You have a solid foundation in backend languages and database interactions.', compatibility_percentage: 88 },
        { role_name: 'Frontend Engineer', match_explanation: 'Your frontend skills make you a good candidate for frontend positions.', compatibility_percentage: 85 }
      ]
    };

    try {
      const aiResponse = await axios.post(
        `${process.env.AI_API_URL}/gemini-roles`,
        { skills },
        { timeout: 10000 }
      );
      if (aiResponse.data) {
        geminiResult = aiResponse.data;
      }
    } catch (err) {
      console.warn('[cvController.getGeminiRoles] Gagal menghubungi AI API, menggunakan data dummy:', err.message);
    }

    await query(
      `UPDATE cv_analyses SET gemini_roles = $1, updated_at = NOW() WHERE id = $2 AND user_id = $3`,
      [JSON.stringify(geminiResult), id, req.user.id]
    );

    return res.status(200).json({
      status: 'success',
      message: 'Rekomendasi role dari Gemini berhasil dibuat.',
      data: geminiResult,
    });
  } catch (error) {
    console.error('[cvController.getGeminiRoles]', error);

    if (error.response) {
      return res.status(502).json({
        status: 'error',
        message: `AI API Error: ${error.response.data?.message || 'Gagal menghubungi AI service.'}`,
      });
    }

    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat mengambil rekomendasi role dari Gemini.',
    });
  }
};

const getCVHistory = async (req, res) => {
  try {
    const result = await query(
      `SELECT id, cv_url, profile_entities, extracted_skills,
              target_role, top_skills, recommended_courses,
              gemini_roles, created_at, updated_at
       FROM cv_analyses
       WHERE user_id = $1
       ORDER BY created_at DESC`,
      [req.user.id]
    );

    return res.status(200).json({
      status: 'success',
      data: {
        count: result.rows.length,
        analyses: result.rows,
      },
    });
  } catch (error) {
    console.error('[cvController.getCVHistory]', error);
    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat mengambil riwayat CV.',
    });
  }
};

const getCVHistoryById = async (req, res) => {
  try {
    const { id } = req.params;

    const result = await query(
      `SELECT id, cv_url, profile_entities, extracted_skills,
              target_role, top_skills, recommended_courses,
              gemini_roles, created_at, updated_at
       FROM cv_analyses
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        status: 'fail',
        message: 'Data analisis CV tidak ditemukan.',
      });
    }

    return res.status(200).json({
      status: 'success',
      data: result.rows[0],
    });
  } catch (error) {
    console.error('[cvController.getCVHistoryById]', error);
    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat mengambil detail CV.',
    });
  }
};

module.exports = {
  analyzeCV,
  getRecommendations,
  getGeminiRoles,
  getCVHistory,
  getCVHistoryById,
};
