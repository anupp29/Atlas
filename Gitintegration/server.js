import express from "express";
import { getFile, updateFile } from "./githubService.js";
import { editCode } from "./aiService.js";

const app = express();
app.use(express.urlencoded({ extended: true }));

app.post("/slack/command", async (req, res) => {
  try {
    const instruction = req.body.text;
    
    // Send immediate response to Slack
    res.send("⏳ Processing your code edit...");

    // GitHub config
    const owner = "Khetesh-Deore";
    const repo = "wadaje-motors";
    const path = "test.js";

    // Get file from GitHub
    const { content, sha } = await getFile(owner, repo, path);
    console.log("📄 Retrieved file from GitHub");

    // Edit code with AI
    const updatedCode = await editCode(content, instruction);
    console.log("🤖 AI edited the code");

    // Update file on GitHub
    await updateFile(owner, repo, path, updatedCode, sha);
    console.log("✅ File updated on GitHub");
  } catch (error) {
    console.error("❌ Error:", error.message);
  }
});

app.listen(3000, () => console.log("🚀 Server running on port 3000"));
