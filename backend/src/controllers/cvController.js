const axios = require('axios');
const cloudinary = require('../config/cloudinary');
const { query } = require('../config/db');

const AI_BASE = process.env.AI_API_URL || 'http://localhost:8000';
const AI_KEY = process.env.AI_API_KEY || process.env.AI_ENGINE_API_KEY || '';

const SUPPORTED_ROLES = [
  'AI Engineer', 'Backend Developer', 'Business Analyst',
  'Business Intelligence Analyst', 'Cloud Engineer', 'Cyber Security Analyst',
  'Data Analyst', 'Data Engineer', 'Data Scientist',
  'Database Administrator', 'DevOps Engineer', 'ERP Consultant',
  'Embedded/IoT Engineer', 'Frontend Developer', 'Full Stack Developer',
  'General IT Specialist', 'IT Consultant', 'Machine Learning Engineer',
  'Mobile Developer', 'Network Engineer', 'Product Manager',
  'QA Engineer', 'Robotics Engineer', 'Security Engineer',
  'Site Reliability Engineer', 'Software Engineer', 'Solutions Architect',
];

const uploadToCloudinary = (buffer, originalname) =>
  new Promise((resolve, reject) => {
    const safeName = originalname
      .replace(/\.[^/.]+$/, '')         // strip extension
      .replace(/[^a-zA-Z0-9]/g, '_')    // only alphanumeric + underscore
      .replace(/__+/g, '_')             // collapse multiple underscores
      .slice(0, 80);

    const uploadStream = cloudinary.uploader.upload_stream(
      {
        resource_type: 'raw',
        public_id: `qlop/cv/cv_${Date.now()}_${safeName}.pdf`,
      },
      (error, result) => {
        if (error) return reject(error);
        resolve(result.secure_url);
      }
    );
    uploadStream.end(buffer);
  });

const analyzeCV = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        status: 'fail',
        message: 'CV file not found. Ensure the field name is "cv_file".',
      });
    }

    // 1. Upload ke Cloudinary
    let cvUrl;
    try {
      cvUrl = await uploadToCloudinary(req.file.buffer, req.file.originalname);
    } catch (uploadError) {
      console.error('[cvController.analyzeCV] Gagal upload ke Cloudinary:', uploadError.message);
      return res.status(502).json({
        status: 'error',
        message: 'Failed to upload file to Cloudinary. Please try again.',
      });
    }

    // 2. AI Engine Phase 1 — extract CVProfile
    let cvProfile, extractMetadata;
    try {
      const aiRes = await axios.post(
        `${AI_BASE}/api/v1/cv/extract`,
        { cloudinary_url: cvUrl },
        { 
          headers: { 'X-API-Key': AI_KEY },
          timeout: 60000 
        }
      );
      // AI envelope: { status, code, data: CVProfile, metadata }
      cvProfile = aiRes.data?.data;
      extractMetadata = aiRes.data?.metadata || {};
      if (!cvProfile) throw new Error('AI Engine mengembalikan response kosong.');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      console.error('[cvController.analyzeCV] AI Engine error:', detail);
      return res.status(502).json({
        status: 'error',
        message: `AI Engine failed to extract CV: ${detail}`,
      });
    }

    // Ensure skills selalu flat string[]
    const skillsArray = Array.isArray(cvProfile.skills)
      ? cvProfile.skills.filter((s) => typeof s === 'string')
      : [];

    // 3. Simpan ke DB (termasuk extract_metadata)
    const insertResult = await query(
      `INSERT INTO cv_analyses
         (user_id, cv_url, profile_entities, extracted_skills, extract_metadata)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id, user_id, cv_url, profile_entities, extracted_skills,
                 extract_metadata, created_at`,
      [
        req.user.id,
        cvUrl,
        JSON.stringify(cvProfile),
        JSON.stringify(skillsArray),
        JSON.stringify(extractMetadata),
      ]
    );

    const row = insertResult.rows[0];

    return res.status(201).json({
      status: 'success',
      message: 'CV successfully extracted.',
      data: {
        id: row.id,
        cv_url: row.cv_url,
        profile_entities: row.profile_entities,   // full CVProfile
        extracted_skills: row.extracted_skills,   // string[]
        extract_metadata: row.extract_metadata,   // page_count, extraction_mode, dll
        created_at: row.created_at,
      },
    });
  } catch (error) {
    console.error('[cvController.analyzeCV]', error);
    return res.status(500).json({
      status: 'error',
      message: 'An error occurred while analyzing the CV.',
    });
  }
};

const getRecommendations = async (req, res) => {
  try {
    const { id } = req.params;
    const { target_role, profile: profileOverride } = req.body;

    if (!target_role || typeof target_role !== 'string' || !target_role.trim()) {
      return res.status(400).json({
        status: 'fail',
        message: 'The target_role field is required.',
      });
    }

    // Ambil CVProfile dari DB
    const cvResult = await query(
      `SELECT id, profile_entities, extracted_skills
       FROM cv_analyses
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.id]
    );
    if (cvResult.rows.length === 0) {
      return res.status(404).json({
        status: 'fail',
        message: 'CV data not found or does not belong to you.',
      });
    }

    const cvRow = cvResult.rows[0];
    // Gunakan profile override dari frontend (user mungkin edit) atau fallback ke DB
    const cvProfile = profileOverride || cvRow.profile_entities || {};

    // Normalise skills → flat string[]
    if (cvProfile.skills && Array.isArray(cvProfile.skills)) {
      cvProfile.skills = cvProfile.skills
        .map((s) => (typeof s === 'string' ? s : s.surface || s.normalized_guess || ''))
        .filter(Boolean);
    } else {
      const stored = cvRow.extracted_skills;
      cvProfile.skills = Array.isArray(stored) ? stored : [];
    }

    const trimmedRole = target_role.trim();

    // AI Engine Phase 2 — analyze
    let analyzeData, analyzeMetadata;
    try {
      const aiRes = await axios.post(
        `${AI_BASE}/api/v1/cv/analyze`,
        { profile: cvProfile, target_role: trimmedRole },
        { 
          headers: { 'X-API-Key': AI_KEY },
          timeout: 60000 
        }
      );
      // AI envelope data: { profile, target_role, skill_gap, course_recommendations, readiness_score }
      analyzeData = aiRes.data?.data;
      analyzeMetadata = aiRes.data?.metadata || {};
      if (!analyzeData) throw new Error('AI Engine mengembalikan response kosong.');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      console.error('[cvController.getRecommendations] AI Engine error:', detail);
      return res.status(502).json({
        status: 'error',
        message: `AI Engine failed to analyze skill gap: ${detail}`,
      });
    }

    const { skill_gap, course_recommendations, readiness_score } = analyzeData;

    const skillsToSave = Array.isArray(cvProfile.skills)
      ? cvProfile.skills.filter((s) => typeof s === 'string')
      : [];

    const updateResult = await query(
      `UPDATE cv_analyses
       SET target_role         = $1,
           top_skills          = $2,
           recommended_courses = $3,
           analyze_metadata    = $4,
           profile_entities    = $5,
           extracted_skills    = $6,
           updated_at          = NOW()
       WHERE id = $7 AND user_id = $8
       RETURNING id, target_role, top_skills, recommended_courses,
                 analyze_metadata, updated_at`,
      [
        trimmedRole,
        JSON.stringify({ skill_gap, readiness_score }),
        JSON.stringify(course_recommendations || []),
        JSON.stringify({
          ...analyzeMetadata,
          // Simpan juga full analyze_data untuk Phase 3
          _analyze_payload: analyzeData,
        }),
        JSON.stringify(cvProfile),
        JSON.stringify(skillsToSave),
        id,
        req.user.id,
      ]
    );

    const updatedRow = updateResult.rows[0];

    return res.status(200).json({
      status: 'success',
      message: 'Skill gap analysis successful.',
      data: {
        id: updatedRow.id,
        target_role: updatedRow.target_role,
        skill_gap,
        readiness_score,
        course_recommendations: course_recommendations || [],
        analyze_metadata: analyzeMetadata,
        updated_at: updatedRow.updated_at,
      },
    });
  } catch (error) {
    console.error('[cvController.getRecommendations]', error);
    return res.status(500).json({
      status: 'error',
      message: 'An error occurred while analyzing the skill gap.',
    });
  }
};

const getCareerPivot = async (req, res) => {
  try {
    const { id } = req.params;

    const cvResult = await query(
      `SELECT id, profile_entities, target_role, top_skills,
              recommended_courses, analyze_metadata
       FROM cv_analyses
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.id]
    );
    if (cvResult.rows.length === 0) {
      return res.status(404).json({
        status: 'fail',
        message: 'CV data not found or does not belong to you.',
      });
    }

    const row = cvResult.rows[0];

    if (!row.target_role || !row.top_skills) {
      return res.status(400).json({
        status: 'fail',
        message: 'Please run the skill gap analysis first (PUT /api/cv/recommend/:id).',
      });
    }

    // Cek apakah ada full analyze_payload tersimpan (contract: kirim as-is ke career-pivot)
    const savedAnalyzePayload = row.analyze_metadata?._analyze_payload;

    let careerPivotBody;
    if (savedAnalyzePayload) {
      // Gunakan full analyze data as-is (seperti yang disarankan contract)
      careerPivotBody = savedAnalyzePayload;
    } else {
      // Fallback: construct manual dari kolom terpisah
      const { skill_gap, readiness_score } = row.top_skills;
      careerPivotBody = {
        profile: row.profile_entities || {},
        target_role: row.target_role,
        skill_gap: skill_gap || { matched_skills: [], missing_skills: [] },
        course_recommendations: row.recommended_courses || [],
        readiness_score: readiness_score || { score: 0, matched_skills: [], interpretation: '' },
      };
    }

    // AI Engine Phase 3 — career pivot
    let careerPivotData, pivotMetadata;
    try {
      const aiRes = await axios.post(
        `${AI_BASE}/api/v1/cv/career-pivot`,
        careerPivotBody,
        { 
          headers: { 'X-API-Key': AI_KEY },
          timeout: 120000 
        }
      );
      careerPivotData = aiRes.data?.data;
      pivotMetadata = aiRes.data?.metadata || {};
      if (!careerPivotData) throw new Error('AI Engine mengembalikan response kosong.');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      console.error('[cvController.getCareerPivot] AI Engine error:', detail);
      return res.status(502).json({
        status: 'error',
        message: `AI Engine failed to analyze career pivot: ${detail}`,
      });
    }

    // Simpan hasil ke DB
    await query(
      `UPDATE cv_analyses
       SET career_pivot  = $1,
           pivot_metadata = $2,
           updated_at    = NOW()
       WHERE id = $3 AND user_id = $4`,
      [
        JSON.stringify(careerPivotData),
        JSON.stringify(pivotMetadata),
        id,
        req.user.id,
      ]
    );

    return res.status(200).json({
      status: 'success',
      message: 'Career pivot analysis successful.',
      data: careerPivotData,
      metadata: pivotMetadata,
    });
  } catch (error) {
    console.error('[cvController.getCareerPivot]', error);
    return res.status(500).json({
      status: 'error',
      message: 'An error occurred while analyzing the career pivot.',
    });
  }
};

const getRoles = async (req, res) => {
  try {
    const aiRes = await axios.get(`${AI_BASE}/api/v1/roles`, { 
      headers: { 'X-API-Key': AI_KEY },
      timeout: 10000 
    });
    const roles = aiRes.data?.data?.roles || SUPPORTED_ROLES;
    const count = aiRes.data?.data?.count || roles.length;
    return res.status(200).json({ status: 'success', data: { roles, count } });
  } catch (err) {
    console.warn('[cvController.getRoles] AI Engine tidak tersedia, pakai fallback:', err.message);
    // Fallback ke 27 role hardcoded dari contract (tidak return error — dropdown harus tetap muncul)
    return res.status(200).json({
      status: 'success',
      data: { roles: SUPPORTED_ROLES, count: SUPPORTED_ROLES.length },
    });
  }
};

const getCVHistory = async (req, res) => {
  try {
    const result = await query(
      `SELECT id, cv_url, profile_entities, extracted_skills,
              target_role, top_skills, recommended_courses,
              career_pivot, extract_metadata, analyze_metadata, pivot_metadata,
              created_at, updated_at
       FROM cv_analyses
       WHERE user_id = $1
       ORDER BY created_at DESC`,
      [req.user.id]
    );
    return res.status(200).json({
      status: 'success',
      data: { count: result.rows.length, analyses: result.rows },
    });
  } catch (error) {
    console.error('[cvController.getCVHistory]', error);
    return res.status(500).json({ status: 'error', message: 'Failed to retrieve CV history.' });
  }
};

const getCVHistoryById = async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query(
      `SELECT id, cv_url, profile_entities, extracted_skills,
              target_role, top_skills, recommended_courses,
              career_pivot, extract_metadata, analyze_metadata, pivot_metadata,
              created_at, updated_at
       FROM cv_analyses
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ status: 'fail', message: 'CV analysis data not found.' });
    }
    return res.status(200).json({ status: 'success', data: result.rows[0] });
  } catch (error) {
    console.error('[cvController.getCVHistoryById]', error);
    return res.status(500).json({ status: 'error', message: 'Failed to retrieve CV details.' });
  }
};

const deleteCVHistory = async (req, res) => {
  try {
    const { id } = req.params;
    const userId = req.user.id;

    // Check if it exists and belongs to the user
    const checkRes = await query(
      'SELECT id FROM cv_analyses WHERE id = $1 AND user_id = $2',
      [id, userId]
    );

    if (checkRes.rows.length === 0) {
      return res.status(404).json({
        status: 'fail',
        message: 'Analysis history not found or you do not have access.',
      });
    }

    // Delete it
    await query(
      'DELETE FROM cv_analyses WHERE id = $1 AND user_id = $2',
      [id, userId]
    );

    return res.status(200).json({
      status: 'success',
      message: 'Analysis history successfully deleted.',
    });
  } catch (error) {
    console.error('[cvController.deleteCVHistory]', error);
    return res.status(500).json({
      status: 'error',
      message: 'An error occurred while deleting the analysis history.',
    });
  }
};

module.exports = {
  analyzeCV,
  getRecommendations,
  getCareerPivot,
  getRoles,
  getCVHistory,
  getCVHistoryById,
  deleteCVHistory,
};