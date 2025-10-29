const express = require("express");
const multer = require("multer");
const { uploadFile, getFile, getAllFiles } = require("../controllers/fileController");
const { authMiddleware } = require("../middleware/authMiddleware");

const router = express.Router();

// ✅ Use memory storage only, validation done in controller
const storage = multer.memoryStorage();
const upload = multer({ storage });

// Routes
router.post(
  "/upload",
  authMiddleware,
  upload.fields([
    { name: "file", maxCount: 1 },
    { name: "metadata_file", maxCount: 1 },
  ]),
  uploadFile
);

router.get("/:id", authMiddleware, getFile);
router.get("/", authMiddleware, getAllFiles);

module.exports = router;
