// routes/userRoutes.js
const express = require("express");
const { signupUser, loginUser, getProfile } = require("../controllers/userController");
const { authMiddleware } = require("../middleware/authMiddleware");

const router = express.Router();

router.post("/signup", signupUser);
router.post("/login", loginUser);
router.get("/me", authMiddleware, getProfile);

module.exports = router;
