const express = require('express');
const authMiddleware = require('../middlewares/authMiddleware');
const { uploadCV } = require('../middlewares/uploadMiddleware');
const {
  analyzeCV,
  getRecommendations,
  getCareerPivot,
  getRoles,
  getCVHistory,
  getCVHistoryById,
  deleteCVHistory,
} = require('../controllers/cvController');

const router = express.Router();

router.use(authMiddleware);

// Phase 1 – upload + extract CV via AI Engine
router.post('/analyze', uploadCV, analyzeCV);

// Phase 2 – skill gap analysis against a target role
router.put('/recommend/:id', getRecommendations);

// Phase 3 – career pivot radar (LLM-powered)
router.post('/career-pivot/:id', getCareerPivot);

// Utility – get list of valid roles from AI Engine
router.get('/roles', getRoles);

// History
router.get('/history', getCVHistory);
router.get('/history/:id', getCVHistoryById);
router.delete('/history/:id', deleteCVHistory);

module.exports = router;
