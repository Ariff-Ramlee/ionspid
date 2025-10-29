const express = require("express");
const cors = require("cors");

const app = express();
app.use(cors());

app.get("/test", (req, res) => {
  console.log("✅ /test was hit!");
  res.send("Backend is reachable on LAN!");
});

const PORT = 5000;
app.listen(PORT, "0.0.0.0", () => {
  console.log(`🚀 Server running at http://0.0.0.0:${PORT}`);
});
