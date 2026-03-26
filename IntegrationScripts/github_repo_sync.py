import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional
import structlog
from dataclasses import dataclass
import httpx
import base64
import sqlite3
from contextlib import asynccontextmanager

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@dataclass
class GitHubConfig:
    token: str
    owner: str
    repo: str
    branch: str = "main"
    timeout: float = 10.0


@dataclass
class ChangeAuditRecord:
    change_id: str
    client_id: str
    timestamp: str
    file_path: str
    operation: str
    old_content: Optional[str]
    new_content: str
    commit_sha: Optional[str]
    pr_number: Optional[int]
    status: str
    error_message: Optional[str]


class GitHubRepoSyncDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS github_changes (
                    change_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    old_content TEXT,
                    new_content TEXT NOT NULL,
                    commit_sha TEXT,
                    pr_number INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_client_timestamp ON github_changes (client_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON github_changes (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON github_changes (file_path)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS github_sync_stats (
                    stat_id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    total_changes INTEGER NOT NULL,
                    successful_changes INTEGER NOT NULL,
                    failed_changes INTEGER NOT NULL,
                    last_sync TEXT NOT NULL,
                    UNIQUE(client_id)
                )
            """)
            conn.commit()
    
    async def insert_change(self, record: ChangeAuditRecord) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_change_sync, record)
    
    def _insert_change_sync(self, record: ChangeAuditRecord) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO github_changes
                    (change_id, client_id, timestamp, file_path, operation, 
                     old_content, new_content, commit_sha, pr_number, status, 
                     error_message, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.change_id,
                    record.client_id,
                    record.timestamp,
                    record.file_path,
                    record.operation,
                    record.old_content,
                    record.new_content,
                    record.commit_sha,
                    record.pr_number,
                    record.status,
                    record.error_message,
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
                logger.info("change_recorded", change_id=record.change_id, client_id=record.client_id)
        except Exception as e:
            logger.error("change_record_failed", error=str(e), change_id=record.change_id)
            raise
    
    async def query_changes(
        self,
        client_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._query_changes_sync,
            client_id,
            status,
            limit
        )
    
    def _query_changes_sync(
        self,
        client_id: str,
        status: Optional[str],
        limit: int
    ) -> list[dict]:
        query = "SELECT * FROM github_changes WHERE client_id = ?"
        params = [client_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


class GitHubRepoSync:
    def __init__(
        self,
        client_id: str,
        config: GitHubConfig,
        db_path: str
    ):
        if not client_id:
            raise ValueError("client_id is mandatory")
        
        self.client_id = client_id
        self.config = config
        self.db = GitHubRepoSyncDB(db_path)
        self._validate_config()
    
    def _validate_config(self) -> None:
        if not self.config.token:
            raise ValueError("GitHub token is mandatory")
        if not self.config.owner or not self.config.repo:
            raise ValueError("GitHub owner and repo are mandatory")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None
    ) -> dict:
        url = f"https://api.github.com/repos/{self.config.owner}/{self.config.repo}{endpoint}"
        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ATLAS-GitHubSync"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=data)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                response.raise_for_status()
                return response.json() if response.text else {}
        except httpx.HTTPError as e:
            logger.error("github_request_failed", method=method, endpoint=endpoint, error=str(e))
            raise
        except asyncio.TimeoutError:
            logger.error("github_request_timeout", method=method, endpoint=endpoint)
            raise
    
    async def get_file_content(self, file_path: str) -> Optional[str]:
        try:
            response = await self._make_request("GET", f"/contents/{file_path}?ref={self.config.branch}")
            if "content" in response:
                return base64.b64decode(response["content"]).decode("utf-8")
            return None
        except Exception as e:
            logger.error("get_file_failed", file_path=file_path, error=str(e))
            return None
    
    async def update_file(
        self,
        file_path: str,
        new_content: str,
        commit_message: str,
        old_content: Optional[str] = None
    ) -> Optional[str]:
        if not new_content:
            raise ValueError("new_content is mandatory")
        
        change_id = f"{self.client_id}_{file_path}_{datetime.utcnow().timestamp()}"
        
        try:
            current_content = await self.get_file_content(file_path)
            
            if current_content == new_content:
                logger.info("no_changes_needed", file_path=file_path)
                return None
            
            response = await self._make_request(
                "PUT",
                f"/contents/{file_path}",
                {
                    "message": commit_message,
                    "content": base64.b64encode(new_content.encode()).decode(),
                    "branch": self.config.branch,
                    "sha": await self._get_file_sha(file_path) if current_content else None
                }
            )
            
            commit_sha = response.get("commit", {}).get("sha")
            
            record = ChangeAuditRecord(
                change_id=change_id,
                client_id=self.client_id,
                timestamp=datetime.utcnow().isoformat(),
                file_path=file_path,
                operation="update",
                old_content=current_content,
                new_content=new_content,
                commit_sha=commit_sha,
                pr_number=None,
                status="success",
                error_message=None
            )
            
            await self.db.insert_change(record)
            logger.info("file_updated", file_path=file_path, commit_sha=commit_sha)
            
            return commit_sha
        except Exception as e:
            error_msg = str(e)
            record = ChangeAuditRecord(
                change_id=change_id,
                client_id=self.client_id,
                timestamp=datetime.utcnow().isoformat(),
                file_path=file_path,
                operation="update",
                old_content=old_content,
                new_content=new_content,
                commit_sha=None,
                pr_number=None,
                status="failed",
                error_message=error_msg
            )
            
            await self.db.insert_change(record)
            logger.error("file_update_failed", file_path=file_path, error=error_msg)
            raise
    
    async def _get_file_sha(self, file_path: str) -> Optional[str]:
        try:
            response = await self._make_request("GET", f"/contents/{file_path}?ref={self.config.branch}")
            return response.get("sha")
        except Exception:
            return None
    
    async def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str
    ) -> Optional[int]:
        try:
            response = await self._make_request(
                "POST",
                "/pulls",
                {
                    "title": title,
                    "body": body,
                    "head": head_branch,
                    "base": self.config.branch
                }
            )
            
            pr_number = response.get("number")
            logger.info("pull_request_created", pr_number=pr_number, title=title)
            
            return pr_number
        except Exception as e:
            logger.error("pull_request_creation_failed", error=str(e))
            raise
    
    async def batch_update_files(
        self,
        updates: list[dict]
    ) -> dict:
        results = {
            "successful": [],
            "failed": []
        }
        
        for update in updates:
            file_path = update.get("file_path")
            new_content = update.get("new_content")
            commit_message = update.get("commit_message", f"ATLAS: Update {file_path}")
            
            try:
                commit_sha = await self.update_file(
                    file_path,
                    new_content,
                    commit_message
                )
                
                if commit_sha:
                    results["successful"].append({
                        "file_path": file_path,
                        "commit_sha": commit_sha
                    })
            except Exception as e:
                results["failed"].append({
                    "file_path": file_path,
                    "error": str(e)
                })
        
        logger.info(
            "batch_update_completed",
            successful=len(results["successful"]),
            failed=len(results["failed"])
        )
        
        return results
    
    async def get_change_history(self, limit: int = 50) -> list[dict]:
        return await self.db.query_changes(self.client_id, limit=limit)


@asynccontextmanager
async def repo_sync_context(
    client_id: str,
    github_token: str,
    owner: str,
    repo: str,
    db_path: str
):
    config = GitHubConfig(
        token=github_token,
        owner=owner,
        repo=repo
    )
    
    sync = GitHubRepoSync(client_id, config, db_path)
    
    try:
        yield sync
    finally:
        logger.info("repo_sync_context_closed", client_id=client_id)


async def main():
    client_id = os.getenv("ATLAS_CLIENT_ID", "FINCORE_UK_001")
    github_token = os.getenv("GITHUB_TOKEN")
    github_owner = os.getenv("GITHUB_OWNER")
    github_repo = os.getenv("GITHUB_REPO")
    db_path = os.getenv("ATLAS_GITHUB_DB", "data/atlas_github.db")
    
    if not all([client_id, github_token, github_owner, github_repo]):
        logger.error("missing_required_env_vars")
        sys.exit(1)
    
    async with repo_sync_context(client_id, github_token, github_owner, github_repo, db_path) as sync:
        history = await sync.get_change_history()
        logger.info("change_history_retrieved", count=len(history))


if __name__ == "__main__":
    asyncio.run(main())
