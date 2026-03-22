import { Octokit } from "@octokit/rest";

const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN,
});

export async function getFile(owner, repo, path) {
  const { data } = await octokit.repos.getContent({
    owner,
    repo,
    path,
  });

  const content = Buffer.from(data.content, "base64").toString();
  return { content, sha: data.sha };
}

export async function updateFile(owner, repo, path, newContent, sha) {
  await octokit.repos.createOrUpdateFileContents({
    owner,
    repo,
    path,
    message: "Updated by AI bot",
    content: Buffer.from(newContent).toString("base64"),
    sha,
  });
}