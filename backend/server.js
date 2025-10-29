const express = require("express");
const cors = require("cors");

const userRoutes = require("./routes/userRoutes");
const fileRoutes = require("./routes/fileRoutes");
const pipelineRoutes = require("./routes/pipelineRoutes");

const app = express();
app.use(cors());
app.use(express.json());

// ✅ Use only userRoutes for login/signup
app.use("/api/users", require("./routes/userRoutes"));
app.use("/api/files", fileRoutes);
app.use("/api/pipelines", pipelineRoutes);

// Health check
app.get("/api/hello", (req, res) => {
  res.json({ message: "Hello from backend!" });
});

const PORT = 5000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`✅ Server running at http://0.0.0.0:${PORT}`);
});
