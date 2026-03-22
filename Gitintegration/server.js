import express from "express";

const app = express();
app.use(express.urlencoded({ extended: true }));

app.post("https://overfloridly-partakable-ilene.ngrok-free.dev/slack/command", (req, res) => {
  console.log("User input:", req.body.text);
  res.send("✅ Slack bot working!");
});

app.listen(3000, () => console.log("Server running on 3000"));
