/**
 * cvController.js — QLOP Backend
 * Aligned with AI Engine API_CONTRACT.md v2.1
 *
 *  Phase 1 – POST /api/cv/analyze
 *    → Upload PDF ke Cloudinary
 *    → AI Engine: POST /api/v1/cv/extract { cloudinary_url }
 *    → Response: CVProfile + metadata (page_count, extraction_mode, ner_model_version)
 *    → DB: profile_entities, extracted_skills, extract_metadata
 *
 *  Phase 2 – PUT /api/cv/recommend/:id
 *    → AI Engine: POST /api/v1/cv/analyze { profile: CVProfile, target_role }
 *    → Response: { profile, target_role, skill_gap, course_recommendations, readiness_score }
 *    → DB: target_role, top_skills ({ skill_gap, readiness_score }), recommended_courses, analyze_metadata
 *    → Simpan full analyze_data untuk dikirim as-is ke Phase 3
 *
 *  Phase 3 – POST /api/cv/career-pivot/:id
 *    → AI Engine: POST /api/v1/cv/career-pivot (body = analyze data as-is dari Phase 2)
 *    → Response: CareerPivotOutput + metadata (llm_model, roles_evaluated, processing_time_ms)
 *    → DB: gemini_roles, pivot_metadata
 */

const axios = require('axios');
const cloudinary = require('../config/cloudinary');
const { query } = require('../config/db');

const AI_BASE = process.env.AI_API_URL || 'http://localhost:8000';

// 27 roles persis dari API_CONTRACT.md — dipakai sebagai fallback getRoles
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
        // Folder encoded in public_id (no separate `folder` param) to avoid signature mismatch.
        // .pdf suffix required so AI Engine can validate the file as a PDF.
        public_id: `qlop/cv/cv_${Date.now()}_${safeName}.pdf`,
      },
      (error, result) => {
        if (error) return reject(error);
        resolve(result.secure_url);
      }
    );
    uploadStream.end(buffer);
  });

// ---------------------------------------------------------------------------
// Phase 1 – analyzeCV
// POST /api/cv/analyze   (multipart/form-data, field: cv_file)
// ---------------------------------------------------------------------------
const analyzeCV = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        status: 'fail',
        message: 'File CV tidak ditemukan. Pastikan field name adalah "cv_file".',
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
        message: 'Gagal mengupload file ke Cloudinary. Coba lagi.',
      });
    }

    // 2. AI Engine Phase 1 — extract CVProfile
    let cvProfile, extractMetadata;
    try {
      const aiRes = await axios.post(
        `${AI_BASE}/api/v1/cv/extract`,
        { cloudinary_url: cvUrl },
        { timeout: 30000 }
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
        message: `AI Engine gagal mengekstrak CV: ${detail}`,
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
      message: 'CV berhasil diekstrak.',
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
      message: 'Terjadi kesalahan saat menganalisis CV.',
    });
  }
};

// ---------------------------------------------------------------------------
// Phase 2 – getRecommendations
// PUT /api/cv/recommend/:id   (JSON body: { target_role, profile? })
// ---------------------------------------------------------------------------
const getRecommendations = async (req, res) => {
  try {
    const { id } = req.params;
    const { target_role, profile: profileOverride } = req.body;

    if (!target_role || typeof target_role !== 'string' || !target_role.trim()) {
      return res.status(400).json({
        status: 'fail',
        message: 'Field target_role wajib diisi.',
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
        message: 'Data CV tidak ditemukan atau bukan milik Anda.',
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
        { timeout: 60000 }
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
        message: `AI Engine gagal menganalisis skill gap: ${detail}`,
      });
    }

    const { skill_gap, course_recommendations, readiness_score } = analyzeData;

    // Simpan ke DB:
    // - top_skills: { skill_gap, readiness_score } (dipakai Phase 3)
    // - analyze_metadata: cv_skills_count, processing_time_ms, dll
    // - analyze_data: full response dari AI (dikirim as-is ke Phase 3)
    // - Jika user mengedit profile di frontend (profileOverride), simpan juga
    //   profile_entities dan extracted_skills yang sudah diedit ke DB
    //   agar history menampilkan data yang benar (bukan data awal extract).
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
      message: 'Analisis skill gap berhasil.',
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
      message: 'Terjadi kesalahan saat menganalisis skill gap.',
    });
  }
};

// ---------------------------------------------------------------------------
// Phase 3 – getCareerPivot
// POST /api/cv/career-pivot/:id
// ---------------------------------------------------------------------------
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
        message: 'Data CV tidak ditemukan atau bukan milik Anda.',
      });
    }

    const row = cvResult.rows[0];

    if (!row.target_role || !row.top_skills) {
      return res.status(400).json({
        status: 'fail',
        message: 'Jalankan analisis skill gap terlebih dahulu (PUT /api/cv/recommend/:id).',
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
        { timeout: 120000 } // LLM bisa lambat
      );
      careerPivotData = aiRes.data?.data;
      pivotMetadata = aiRes.data?.metadata || {};
      if (!careerPivotData) throw new Error('AI Engine mengembalikan response kosong.');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      console.error('[cvController.getCareerPivot] AI Engine error:', detail);
      return res.status(502).json({
        status: 'error',
        message: `AI Engine gagal menganalisis career pivot: ${detail}`,
      });
    }

    // Simpan hasil ke DB
    await query(
      `UPDATE cv_analyses
       SET gemini_roles  = $1,
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
      message: 'Analisis career pivot berhasil.',
      data: careerPivotData,
      metadata: pivotMetadata,
    });
  } catch (error) {
    console.error('[cvController.getCareerPivot]', error);
    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat menganalisis career pivot.',
    });
  }
};

// ---------------------------------------------------------------------------
// GET /api/cv/roles — proxy ke AI Engine, fallback ke 27 role dari contract
// ---------------------------------------------------------------------------
const getRoles = async (req, res) => {
  try {
    const aiRes = await axios.get(`${AI_BASE}/api/v1/roles`, { timeout: 10000 });
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

// ---------------------------------------------------------------------------
// History endpoints
// ---------------------------------------------------------------------------
const getCVHistory = async (req, res) => {
  try {
    const result = await query(
      `SELECT id, cv_url, profile_entities, extracted_skills,
              target_role, top_skills, recommended_courses,
              gemini_roles, extract_metadata, analyze_metadata, pivot_metadata,
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
    return res.status(500).json({ status: 'error', message: 'Gagal mengambil riwayat CV.' });
  }
};

const getCVHistoryById = async (req, res) => {
  try {
    const { id } = req.params;
    const result = await query(
      `SELECT id, cv_url, profile_entities, extracted_skills,
              target_role, top_skills, recommended_courses,
              gemini_roles, extract_metadata, analyze_metadata, pivot_metadata,
              created_at, updated_at
       FROM cv_analyses
       WHERE id = $1 AND user_id = $2`,
      [id, req.user.id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ status: 'fail', message: 'Data analisis CV tidak ditemukan.' });
    }
    return res.status(200).json({ status: 'success', data: result.rows[0] });
  } catch (error) {
    console.error('[cvController.getCVHistoryById]', error);
    return res.status(500).json({ status: 'error', message: 'Gagal mengambil detail CV.' });
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
        message: 'Riwayat analisis tidak ditemukan atau Anda tidak memiliki akses.',
      });
    }

    // Delete it
    await query(
      'DELETE FROM cv_analyses WHERE id = $1 AND user_id = $2',
      [id, userId]
    );

    return res.status(200).json({
      status: 'success',
      message: 'Riwayat analisis berhasil dihapus.',
    });
  } catch (error) {
    console.error('[cvController.deleteCVHistory]', error);
    return res.status(500).json({
      status: 'error',
      message: 'Terjadi kesalahan saat menghapus riwayat analisis.',
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
