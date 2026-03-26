from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, list
from datetime import datetime
import structlog
from integration_orchestrator import IntegrationOrchestrator, IntegrationConfig, load_config_from_env
from log_monitor import LogSeverity, LogSource

logger = structlog.get_logger()

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

_orchestrator: Optional[IntegrationOrchestrator] = None


async def get_orchestrator() -> IntegrationOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        config = load_config_from_env()
        _orchestrator = IntegrationOrchestrator(config)
        await _orchestrator.initialize()
    return _orchestrator


class LogIngestRequest(BaseModel):
    source: str = Field(..., description="Log source: java, postgres, nodejs, redis, system")
    severity: str = Field(..., description="Log severity: CRITICAL, ERROR, WARNING, INFO, DEBUG")
    service_name: str = Field(..., description="Service name")
    message: str = Field(..., description="Log message")
    raw_payload: str = Field(..., description="Original log line")
    error_code: Optional[str] = Field(None, description="ATLAS error code")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class LogIngestResponse(BaseModel):
    log_id: str
    timestamp: str
    status: str = "success"


class FileUpdateRequest(BaseModel):
    file_path: str = Field(..., description="Repository file path")
    new_content: str = Field(..., description="New file content")
    commit_message: str = Field(..., description="Git commit message")


class FileUpdateResponse(BaseModel):
    file_path: str
    commit_sha: Optional[str]
    status: str


class BatchUpdateRequest(BaseModel):
    updates: list[dict] = Field(..., description="List of file updates")


class BatchUpdateResponse(BaseModel):
    successful: list[dict]
    failed: list[dict]


class PullRequestRequest(BaseModel):
    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR description")
    head_branch: str = Field(..., description="Feature branch name")


class PullRequestResponse(BaseModel):
    pr_number: Optional[int]
    status: str


class LogQueryResponse(BaseModel):
    logs: list[dict]
    count: int
    timestamp: str


class ChangeHistoryResponse(BaseModel):
    changes: list[dict]
    count: int
    timestamp: str


@router.post("/logs/ingest", response_model=LogIngestResponse)
async def ingest_log(
    request: LogIngestRequest,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> LogIngestResponse:
    try:
        source = LogSource[request.source.upper()]
        severity = LogSeverity[request.severity.upper()]
    except KeyError as e:
        logger.error("invalid_enum_value", error=str(e))
        raise HTTPException(status_code=422, detail=f"Invalid enum value: {str(e)}")
    
    try:
        log_id = await orchestrator.ingest_log(
            source=source,
            severity=severity,
            service_name=request.service_name,
            message=request.message,
            raw_payload=request.raw_payload,
            error_code=request.error_code,
            metadata=request.metadata
        )
        
        logger.info("log_ingested_via_api", log_id=log_id)
        
        return LogIngestResponse(
            log_id=log_id,
            timestamp=datetime.utcnow().isoformat(),
            status="success"
        )
    except Exception as e:
        logger.error("log_ingest_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/history", response_model=LogQueryResponse)
async def get_log_history(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> LogQueryResponse:
    try:
        source_enum = LogSource[source.upper()] if source else None
        severity_enum = LogSeverity[severity.upper()] if severity else None
    except KeyError as e:
        logger.error("invalid_query_enum", error=str(e))
        raise HTTPException(status_code=422, detail=f"Invalid enum value: {str(e)}")
    
    try:
        logs = await orchestrator.get_log_history(
            source=source_enum,
            severity=severity_enum,
            limit=limit
        )
        
        logger.info("log_history_retrieved", count=len(logs))
        
        return LogQueryResponse(
            logs=logs,
            count=len(logs),
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error("log_history_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/stats")
async def get_log_stats(
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> dict:
    try:
        stats = orchestrator.get_log_stats()
        logger.info("log_stats_retrieved")
        return stats
    except Exception as e:
        logger.error("log_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repository/file/update", response_model=FileUpdateResponse)
async def update_repository_file(
    request: FileUpdateRequest,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> FileUpdateResponse:
    try:
        commit_sha = await orchestrator.update_repository_file(
            file_path=request.file_path,
            new_content=request.new_content,
            commit_message=request.commit_message
        )
        
        logger.info("repository_file_updated", file_path=request.file_path, commit_sha=commit_sha)
        
        return FileUpdateResponse(
            file_path=request.file_path,
            commit_sha=commit_sha,
            status="success"
        )
    except Exception as e:
        logger.error("repository_file_update_failed", file_path=request.file_path, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repository/file/get")
async def get_repository_file(
    file_path: str,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> dict:
    try:
        content = await orchestrator.get_repository_file(file_path)
        
        if content is None:
            logger.warning("repository_file_not_found", file_path=file_path)
            raise HTTPException(status_code=404, detail="File not found")
        
        logger.info("repository_file_retrieved", file_path=file_path)
        
        return {
            "file_path": file_path,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("repository_file_get_failed", file_path=file_path, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repository/files/batch-update", response_model=BatchUpdateResponse)
async def batch_update_repository_files(
    request: BatchUpdateRequest,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> BatchUpdateResponse:
    try:
        results = await orchestrator.batch_update_repository_files(request.updates)
        
        logger.info(
            "batch_update_completed",
            successful=len(results["successful"]),
            failed=len(results["failed"])
        )
        
        return BatchUpdateResponse(
            successful=results["successful"],
            failed=results["failed"]
        )
    except Exception as e:
        logger.error("batch_update_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repository/pull-request", response_model=PullRequestResponse)
async def create_pull_request(
    request: PullRequestRequest,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> PullRequestResponse:
    try:
        pr_number = await orchestrator.create_pull_request(
            title=request.title,
            body=request.body,
            head_branch=request.head_branch
        )
        
        logger.info("pull_request_created", pr_number=pr_number)
        
        return PullRequestResponse(
            pr_number=pr_number,
            status="success"
        )
    except Exception as e:
        logger.error("pull_request_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repository/changes", response_model=ChangeHistoryResponse)
async def get_repository_change_history(
    limit: int = 50,
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> ChangeHistoryResponse:
    try:
        changes = await orchestrator.get_repository_change_history(limit=limit)
        
        logger.info("repository_change_history_retrieved", count=len(changes))
        
        return ChangeHistoryResponse(
            changes=changes,
            count=len(changes),
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error("repository_change_history_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health")
async def health_check(
    orchestrator: IntegrationOrchestrator = Depends(get_orchestrator)
) -> dict:
    try:
        log_stats = orchestrator.get_log_stats()
        
        return {
            "status": "healthy",
            "client_id": orchestrator.config.client_id,
            "log_monitor_active": orchestrator.log_monitor is not None,
            "github_sync_active": orchestrator.repo_sync is not None,
            "log_stats": log_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")
