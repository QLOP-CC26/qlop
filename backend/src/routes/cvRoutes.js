const express = require('express');
const authMiddleware = require('../middlewares/authMiddleware');
const { uploadCV } = require('../middlewares/uploadMiddleware');
const {
  analyzeCV,
  getRecommendations,
  getGeminiRoles,
  getCVHistory,
  getCVHistoryById,
} = require('../controllers/cvController');

const router = express.Router();

router.use(authMiddleware);

router.post('/analyze', uploadCV, analyzeCV);
router.put('/recommend/:id', getRecommendations);
router.post('/gemini-roles/:id', getGeminiRoles);
router.get('/history', getCVHistory);
router.get('/history/:id', getCVHistoryById);

module.exports = router;
