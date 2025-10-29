// controllers/userController.js
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const pool = require("../db");

// Generate JWT
const generateToken = (user) =>
  jwt.sign(
    { id: user.user_id, email: user.email, role: user.staff_role },
    process.env.JWT_SECRET || "secret",
    { expiresIn: "7d" }
  );

// POST /api/users/signup
const signupUser = async (req, res) => {
  const { full_name, staff_role, email, password } = req.body;

  if (!full_name || !email || !password) {
    return res.status(400).json({ error: "Please fill in all required fields" });
  }

  try {
    // hash the password and store in password_hash
    const hashedPassword = await bcrypt.hash(password, 10);

    const result = await pool.query(
      `INSERT INTO users (full_name, staff_role, email, password_hash)
       VALUES ($1, $2, $3, $4) RETURNING user_id, full_name, staff_role, email`,
      [full_name, staff_role || "Intern", email, hashedPassword]
    );

    const user = result.rows[0];
    res.json({
      user,
      token: generateToken(user),
    });
  } catch (err) {
    console.error("signupUser error:", err);
    // handle unique email constraint
    if (err.code === "23505") {
      return res.status(400).json({ error: "Email already registered" });
    }
    res.status(500).json({ error: "User registration failed" });
  }
};

// POST /api/users/login
const loginUser = async (req, res) => {
  const { email, password } = req.body;

  try {
    const result = await pool.query(
      "SELECT user_id, full_name, staff_role, email, password_hash FROM users WHERE email = $1",
      [email]
    );
    const user = result.rows[0];

    if (!user) return res.status(401).json({ error: "Invalid credentials" });

    // compare provided password with password_hash
    const isMatch = await bcrypt.compare(password, user.password_hash || "");
    if (!isMatch) return res.status(401).json({ error: "Invalid credentials" });

    // prepare returned user object without password_hash
    const returnedUser = {
      user_id: user.user_id,
      full_name: user.full_name,
      staff_role: user.staff_role,
      email: user.email,
    };

    res.json({
      user: returnedUser,
      token: generateToken(returnedUser),
    });
  } catch (err) {
    console.error("loginUser error:", err);
    res.status(500).json({ error: "Login failed" });
  }
};

// GET /api/users/me
const getProfile = async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT user_id, full_name, staff_role, email FROM users WHERE user_id = $1",
      [req.user.id]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error("getProfile error:", err);
    res.status(500).json({ error: "Failed to fetch profile" });
  }
};

module.exports = { signupUser, loginUser, getProfile };
