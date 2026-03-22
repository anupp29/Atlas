import dotenv from "dotenv";
dotenv.config();

import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

export async function editCode(code, instruction) {
  const model = genAI.getGenerativeModel({ model: "gemini-3-flash-preview" });
  
  const response = await model.generateContent(
    `You are a coding assistant. Return only updated code without explanations.\n\nCode:\n${code}\n\nInstruction:\n${instruction}`
  );
  
  return response.response.text();
}