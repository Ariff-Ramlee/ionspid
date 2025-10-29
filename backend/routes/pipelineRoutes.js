const express = require("express");
const {
  startPipeline,
  getPipeline,
  createJobForFile,
  getJobs,
  getAllJobs
} = require("../controllers/pipelineController");
const { authMiddleware } = require("../middleware/authMiddleware");

const router = express.Router();

// Specific routes FIRST
router.post("/create-job", authMiddleware, createJobForFile);
router.get("/jobs", authMiddleware, getJobs);
router.get("/all-jobs", authMiddleware, getAllJobs);

// Then more general routes
router.post("/", authMiddleware, startPipeline);
router.get("/:id", authMiddleware, getPipeline);

module.exports = router;
