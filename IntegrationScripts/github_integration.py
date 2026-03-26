"""
GitHub Integration - Modify and manage GitHub repositories
Standalone script for codebase changes
"""

import asyncio
import json
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import structlog
from pathlib import Path
import base64

logger = structlog.get_logger()


@dataclass
class GitHubConfig:
    """GitHub configuration"""
    token: str
    owner: str
    repo: str
    branch: str = "main"
    base_url: str = "https://api.github.com"


@dataclass
class FileChange:
    """File change in repository"""
    path: str
    content: str
    message: str
    branch: str = "main"
    sha: Optional[str] = None  # Required for updates


class GitHubIntegration:
    """Manage GitHub repository changes"""

    def __init__(self, config: GitHubConfig):
        """
        Initialize GitHub integration

        Args:
            config: GitHubConfig instance
        """
        self.config = config
        self.headers = {
            "Authorization": f"token {config.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
        }
        logger.info(
            "github_integration_initialized",
            owner=config.owner,
            repo=config.repo,
            branch=config.branch,
        )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to GitHub API

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data

        Returns:
            Response data
        """
        import aiohttp

        url = f"{self.config.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=data,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response_data = await response.json()

                    if response.status >= 400:
                        logger.error(
                            "github_api_error",
                            status=response.status,
                            endpoint=endpoint,
                            error=response_data,
                        )
                        raise Exception(f"GitHub API error: {response_data}")

                    return response_data

        except Exception as e:
            logger.error("github_request_error", error=str(e), endpoint=endpoint)
            raise

    async def get_file(self, path: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Get file from repository

        Args:
            path: File path in repository
            branch: Branch name (defaults to config branch)

        Returns:
            File data including content and SHA
        """
        branch = branch or self.config.branch
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}/contents/{path}"

        try:
            response = await self._make_request("GET", f"{endpoint}?ref={branch}")
            logger.info("file_retrieved", path=path, branch=branch)
            return response
        except Exception as e:
            logger.error("file_retrieval_error", path=path, error=str(e))
            raise

    async def create_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create file in repository

        Args:
            path: File path in repository
            content: File content
            message: Commit message
            branch: Branch name (defaults to config branch)

        Returns:
            Response data
        """
        branch = branch or self.config.branch
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}/contents/{path}"

        # Encode content to base64
        encoded_content = base64.b64encode(content.encode()).decode()

        data = {
            "message": message,
            "content": encoded_content,
            "branch": branch,
        }

        try:
            response = await self._make_request("PUT", endpoint, data)
            logger.info(
                "file_created",
                path=path,
                branch=branch,
                message=message,
            )
            return response
        except Exception as e:
            logger.error("file_creation_error", path=path, error=str(e))
            raise

    async def update_file(
        self,
        path: str,
        content: str,
        message: str,
        sha: str,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update file in repository

        Args:
            path: File path in repository
            content: New file content
            message: Commit message
            sha: Current file SHA (required for update)
            branch: Branch name (defaults to config branch)

        Returns:
            Response data
        """
        branch = branch or self.config.branch
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}/contents/{path}"

        # Encode content to base64
        encoded_content = base64.b64encode(content.encode()).decode()

        data = {
            "message": message,
            "content": encoded_content,
            "sha": sha,
            "branch": branch,
        }

        try:
            response = await self._make_request("PUT", endpoint, data)
            logger.info(
                "file_updated",
                path=path,
                branch=branch,
                message=message,
            )
            return response
        except Exception as e:
            logger.error("file_update_error", path=path, error=str(e))
            raise

    async def delete_file(
        self,
        path: str,
        message: str,
        sha: str,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete file from repository

        Args:
            path: File path in repository
            message: Commit message
            sha: Current file SHA (required for deletion)
            branch: Branch name (defaults to config branch)

        Returns:
            Response data
        """
        branch = branch or self.config.branch
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}/contents/{path}"

        data = {
            "message": message,
            "sha": sha,
            "branch": branch,
        }

        try:
            response = await self._make_request("DELETE", endpoint, data)
            logger.info(
                "file_deleted",
                path=path,
                branch=branch,
                message=message,
            )
            return response
        except Exception as e:
            logger.error("file_deletion_error", path=path, error=str(e))
            raise

    async def create_branch(
        self,
        branch_name: str,
        from_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create new branch

        Args:
            branch_name: New branch name
            from_branch: Source branch (defaults to config branch)

        Returns:
            Response data
        """
        from_branch = from_branch or self.config.branch

        try:
            # Get reference of source branch
            ref_endpoint = f"/repos/{self.config.owner}/{self.config.repo}/git/refs/heads/{from_branch}"
            ref_response = await self._make_request("GET", ref_endpoint)
            sha = ref_response["object"]["sha"]

            # Create new branch
            create_endpoint = f"/repos/{self.config.owner}/{self.config.repo}/git/refs"
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": sha,
            }

            response = await self._make_request("POST", create_endpoint, data)
            logger.info(
                "branch_created",
                branch_name=branch_name,
                from_branch=from_branch,
            )
            return response
        except Exception as e:
            logger.error("branch_creation_error", branch_name=branch_name, error=str(e))
            raise

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create pull request

        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (defaults to config branch)

        Returns:
            Response data
        """
        base_branch = base_branch or self.config.branch
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}/pulls"

        data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
        }

        try:
            response = await self._make_request("POST", endpoint, data)
            logger.info(
                "pull_request_created",
                title=title,
                head_branch=head_branch,
                base_branch=base_branch,
            )
            return response
        except Exception as e:
            logger.error("pull_request_creation_error", title=title, error=str(e))
            raise

    async def get_repository_info(self) -> Dict[str, Any]:
        """
        Get repository information

        Returns:
            Repository data
        """
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}"

        try:
            response = await self._make_request("GET", endpoint)
            logger.info("repository_info_retrieved")
            return response
        except Exception as e:
            logger.error("repository_info_error", error=str(e))
            raise

    async def list_files(
        self,
        path: str = "",
        branch: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List files in directory

        Args:
            path: Directory path
            branch: Branch name (defaults to config branch)

        Returns:
            List of files
        """
        branch = branch or self.config.branch
        endpoint = f"/repos/{self.config.owner}/{self.config.repo}/contents/{path}"

        try:
            response = await self._make_request("GET", f"{endpoint}?ref={branch}")
            if isinstance(response, list):
                logger.info("files_listed", path=path, count=len(response))
                return response
            else:
                logger.warning("unexpected_response_format", path=path)
                return []
        except Exception as e:
            logger.error("file_listing_error", path=path, error=str(e))
            raise

    async def batch_update_files(
        self,
        changes: List[FileChange],
        branch_name: Optional[str] = None,
        create_pr: bool = False,
        pr_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Batch update multiple files

        Args:
            changes: List of FileChange objects
            branch_name: Branch to commit to (creates new branch if provided)
            create_pr: Whether to create pull request
            pr_title: PR title if create_pr is True

        Returns:
            Response data
        """
        try:
            # Create branch if specified
            if branch_name and branch_name != self.config.branch:
                await self.create_branch(branch_name)
                commit_branch = branch_name
            else:
                commit_branch = self.config.branch

            results = []

            # Process each file change
            for change in changes:
                try:
                    # Get current file SHA if updating
                    if change.sha is None:
                        try:
                            file_data = await self.get_file(change.path, commit_branch)
                            change.sha = file_data["sha"]
                            # Update file
                            result = await self.update_file(
                                change.path,
                                change.content,
                                change.message,
                                change.sha,
                                commit_branch,
                            )
                        except:
                            # Create file if it doesn't exist
                            result = await self.create_file(
                                change.path,
                                change.content,
                                change.message,
                                commit_branch,
                            )
                    else:
                        # Update file with provided SHA
                        result = await self.update_file(
                            change.path,
                            change.content,
                            change.message,
                            change.sha,
                            commit_branch,
                        )

                    results.append({"path": change.path, "status": "success", "result": result})

                except Exception as e:
                    logger.error("batch_file_error", path=change.path, error=str(e))
                    results.append({"path": change.path, "status": "error", "error": str(e)})

            # Create PR if requested
            if create_pr and branch_name and branch_name != self.config.branch:
                pr_result = await self.create_pull_request(
                    title=pr_title or f"Update {len(changes)} files",
                    body=f"Batch update of {len(changes)} files",
                    head_branch=branch_name,
                )
                results.append({"type": "pull_request", "result": pr_result})

            logger.info(
                "batch_update_completed",
                file_count=len(changes),
                success_count=sum(1 for r in results if r.get("status") == "success"),
            )

            return {"results": results, "branch": commit_branch}

        except Exception as e:
            logger.error("batch_update_error", error=str(e))
            raise


async def example_usage():
    """Example usage of GitHub integration"""
    # Configuration
    config = GitHubConfig(
        token=os.getenv("GITHUB_TOKEN", "your_token_here"),
        owner="your_owner",
        repo="your_repo",
        branch="main",
    )

    # Create integration
    github = GitHubIntegration(config)

    try:
        # Get repository info
        repo_info = await github.get_repository_info()
        print(f"Repository: {repo_info['full_name']}")
        print(f"Description: {repo_info['description']}")

        # List files
        files = await github.list_files("src")
        print(f"\nFiles in src/: {len(files)}")

        # Create a file
        await github.create_file(
            path="test.txt",
            content="Hello, World!",
            message="Add test file",
        )

        # Batch update files
        changes = [
            FileChange(
                path="config.json",
                content='{"version": "1.0.1"}',
                message="Update version",
            ),
            FileChange(
                path="README.md",
                content="# Updated README",
                message="Update README",
            ),
        ]

        result = await github.batch_update_files(
            changes=changes,
            branch_name="feature/update",
            create_pr=True,
            pr_title="Update configuration and documentation",
        )

        print(f"\nBatch update result: {json.dumps(result, indent=2, default=str)}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(example_usage())
