const pool = require("../db");

// @desc    Create or continue a pipeline job
// @route   POST /api/pipelines
const startPipeline = async (req, res) => {
  try {
    const { step_name, config, job_id, file_id } = req.body;
    const user_id = req.user.id || req.user.user_id; // handle both token styles

    let jobId = job_id;

    // If no job_id, create a new job
    if (!jobId) {
      if (!file_id) {
        return res
          .status(400)
          .json({ error: "file_id is required when creating a new job" });
      }

      const jobResult = await pool.query(
        `INSERT INTO jobs (title, description, timestamp_job, user_id, file_id)
         VALUES ($1, $2, NOW(), $3, $4) RETURNING job_id`,
        [
          `Analysis Job - ${step_name}`,
          `Pipeline started with step: ${step_name}`,
          user_id,
          file_id,
        ]
      );
      jobId = jobResult.rows[0].job_id;
    }

    // Insert pipeline step under this job
    const pipelineResult = await pool.query(
      `INSERT INTO pipelines (step_name, config, timestamp_step, job_id)
       VALUES ($1, $2, NOW(), $3) RETURNING *`,
      [step_name, config || {}, jobId]
    );

    res.json({
      message: "Pipeline step saved",
      job_id: jobId,
      pipeline: pipelineResult.rows[0],
    });
  } catch (err) {
    console.error("startPipeline error:", err);
    res.status(500).json({ error: "Failed to save pipeline step" });
  }
};

// @desc    Get a pipeline by id
// @route   GET /api/pipelines/:id
const getPipeline = async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM pipelines WHERE p_id = $1", [
      req.params.id,
    ]);
    if (result.rows.length === 0)
      return res.status(404).json({ error: "Pipeline not found" });
    res.json(result.rows[0]);
  } catch (err) {
    console.error("getPipeline error:", err);
    res.status(500).json({ error: "Failed to fetch pipeline" });
  }
};

// @desc    Create a job immediately after file upload
// @route   POST /api/pipelines/create-job
const createJobForFile = async (req, res) => {
  try {
    const { file_id } = req.body;
    const user_id = req.user.id || req.user.user_id;

    if (!file_id) {
      return res.status(400).json({ error: "file_id is required" });
    }

    const jobResult = await pool.query(
      `INSERT INTO jobs (title, description, timestamp_job, user_id, file_id)
       VALUES ($1, $2, NOW(), $3, $4) RETURNING *`,
      [
        `Analysis Job for File ${file_id}`,
        "Job created after upload",
        user_id,
        file_id,
      ]
    );

    res.json({ job: jobResult.rows[0] });
  } catch (err) {
    console.error("createJobForFile error:", err);
    res.status(500).json({ error: "Failed to create job" });
  }
};

// @desc    Get all jobs for the logged-in user
// @route   GET /api/pipelines/jobs
const getJobs = async (req, res) => {
  try {
    console.log("Decoded user from token:", req.user);

    const user_id = req.user.id || req.user.user_id;
    if (!user_id) {
      return res.status(401).json({ error: "Invalid token: no user id" });
    }

    const result = await pool.query(
      `SELECT j.job_id, j.title, j.description, j.timestamp_job,
              COALESCE(f.file_name, 'Unknown') AS file_name,
              COALESCE(u.full_name, 'Unknown') AS full_name, f.file_name, 
              f.file_place, f.file_timestamp, f.file_weather
       FROM jobs j
       LEFT JOIN files f ON j.file_id = f.file_id
       LEFT JOIN users u ON j.user_id = u.user_id
       WHERE j.user_id = $1
       ORDER BY j.timestamp_job DESC`,
      [user_id]
    );

    res.json({ jobs: result.rows });
  } catch (err) {
    console.error("getJobs error:", err);
    res.status(500).json({ error: "Failed to fetch jobs" });
  }
};

// @desc    Get ALL jobs (for admin or history view)
// @route   GET /api/pipelines/all-jobs
const getAllJobs = async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT 
        j.job_id, 
        j.title, 
        j.description, 
        j.timestamp_job,
        COALESCE(f.file_name, 'Unknown') AS file_name,
        COALESCE(u.full_name, 'Unknown') AS full_name,
        f.file_place, 
        f.file_timestamp, 
        f.file_weather
      FROM jobs j
      LEFT JOIN files f ON j.file_id = f.file_id
      LEFT JOIN users u ON j.user_id = u.user_id
      ORDER BY j.timestamp_job DESC;
    `);

    res.json({ jobs: result.rows });
  } catch (err) {
    console.error("getAllJobs error:", err);
    res.status(500).json({ error: "Failed to fetch all jobs" });
  }
};

const { exec } = require("child_process");

// @desc    Execute a specific pipeline CLI step
// @route   POST /api/pipelines/run-step
const runStep = async (req, res) => {
  try {
    const { command, args } = req.body;
    const user_id = req.user.id || req.user.user_id; // still available from auth

    if (!command) {
      return res.status(400).json({ error: "Missing command" });
    }

    // Build CLI command dynamically
    let cli = command;
    for (const [key, value] of Object.entries(args || {})) {
      if (typeof value === "boolean") {
        cli += value ? ` --${key}` : "";
      } else if (value !== "" && value !== null && value !== undefined) {
        cli += ` --${key} ${value}`;
      }
    }

    console.log(`🚀 [User ${user_id}] Executing CLI: ${cli}`);

    // Optional: record the run in the pipelines table
    await pool.query(
      `INSERT INTO pipelines (step_name, config, timestamp_step, job_id)
       VALUES ($1, $2, NOW(), NULL)`,
      [command, args]
    );

    // Execute or simulate CLI
    exec(cli, (error, stdout, stderr) => {
      if (error) {
        console.error(`❌ CLI Error: ${stderr}`);
        return res.status(500).json({ error: stderr });
      }
      res.json({ output: stdout || "✅ Step completed successfully." });
    });
  } catch (err) {
    console.error("runStep error:", err);
    res.status(500).json({ error: "Failed to execute pipeline step" });
  }
};


module.exports = {
  startPipeline,
  getPipeline,
  createJobForFile,
  getJobs,
  getAllJobs,
  runStep,
};
