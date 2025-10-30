const express = require("express");
const {
  startPipeline,
  getPipeline,
  createJobForFile,
  getJobs,
  getAllJobs,
  runStep,
} = require("../controllers/pipelineController");
const { authMiddleware } = require("../middleware/authMiddleware");
const { exec } = require("child_process");

const router = express.Router();

/* =========================================================
   🧬 Existing Routes
   ========================================================= */
router.post("/create-job", authMiddleware, createJobForFile);
router.get("/jobs", authMiddleware, getJobs);
router.get("/all-jobs", authMiddleware, getAllJobs);
router.post("/", authMiddleware, startPipeline);
router.get("/:id", authMiddleware, getPipeline);
router.post("/run-step", authMiddleware, runStep);


module.exports = router;
