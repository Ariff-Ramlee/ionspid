const fs = require("fs");
const path = require("path");
const pool = require("../db");

// ✅ Allowed file types
const allowedExtensions = [".pod5", ".xls", ".xlsx"];

// ✅ Upload directory (ensure exists)
const uploadDir = path.join(__dirname, "..", "uploads");
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

// @desc    Upload a file
// @route   POST /api/files/upload
const uploadFile = async (req, res) => {
  try {
    const file = req.files?.file ? req.files.file[0] : null;
    const metaFile = req.files?.metadata_file ? req.files.metadata_file[0] : null;
    const { place, timestamp, weather } = req.body;

    if (!file) return res.status(400).json({ error: "No main file uploaded" });

    // ✅ Validate extension
    const ext = path.extname(file.originalname).toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      return res.status(400).json({ error: "Invalid file type" });
    }

    // ✅ Save file to uploads directory
    const filePath = path.join(uploadDir, file.originalname);
    fs.writeFileSync(filePath, file.buffer);

    // ✅ Insert metadata into DB
    const result = await pool.query(
      `INSERT INTO files (file_name, file_type, file_size, file_place, file_timestamp, file_weather)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [
        file.originalname,
        file.mimetype,
        file.size,
        place || null,
        timestamp || new Date(),
        weather || null,
      ]
    );

    res.json({ file: result.rows[0] });
  } catch (err) {
    console.error("uploadFile error:", err);
    res.status(500).json({ error: "File upload failed" });
  }
};


// @desc    Get a single file
// @route   GET /api/files/:id
const getFile = async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM files WHERE file_id = $1", [
      req.params.id,
    ]);
    if (result.rows.length === 0) return res.status(404).json({ error: "File not found" });
    res.json(result.rows[0]);
  } catch (err) {
    console.error("getFile error:", err);
    res.status(500).json({ error: "Failed to fetch file" });
  }
};

// @desc    Get all files
// @route   GET /api/files
const getAllFiles = async (req, res) => {
  try {
    const result = await pool.query("SELECT * FROM files ORDER BY file_id DESC");
    res.json(result.rows);
  } catch (err) {
    console.error("getAllFiles error:", err);
    res.status(500).json({ error: "Failed to fetch files" });
  }
};

module.exports = { uploadFile, getFile, getAllFiles, allowedExtensions, uploadDir };
