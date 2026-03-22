import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function editCode(code, instruction) {
  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content: "You are a coding assistant. Return only updated code.",
      },
      {
        role: "user",
        content: `Code:\n${code}\n\nInstruction:\n${instruction}`,
      },
    ],
  });

  return response.choices[0].message.content;
}