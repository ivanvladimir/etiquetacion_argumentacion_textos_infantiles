from typing import Any

from arq.jobs import Job as ArqJob
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from ...api.dependencies import rate_limiter_dependency
from ...core.utils import queue
from ...schemas.job import Job

templates = Jinja2Templates(directory="src/app/api/v1/templates")

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/task", response_model=Job, status_code=201, dependencies=[Depends(rate_limiter_dependency)])
async def create_task(filename: str) -> dict[str, str]:
    """Create a new background task.

    Parameters
    ----------
    message: str
        The message or data to be processed by the task.

    Returns
    -------
    dict[str, str]
        A dictionary containing the ID of the created task.
    """
    if queue.pool is None:
        raise HTTPException(status_code=503, detail="Queue is not available")

    job = await queue.pool.enqueue_job("sample_background_task", filename)
    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    return {"id": job.job_id}


@router.get("/task")
@router.get("/task/{task_id}")
async def task_status(
    request: Request,
    task_id: str = "") -> HTMLResponse:
    """Get information about a specific background task.

    Parameters
    ----------
    task_id: str
        The ID of the task.

    Returns
    -------
    Optional[dict[str, Any]]
        A dictionary containing information about the task if found, or None otherwise.
    """
    if queue.pool is None:
        raise HTTPException(status_code=503, detail="Queue is not available")

    job = ArqJob(task_id, queue.pool)
    job_info = await job.info()
    if job_info is None:
        return None

    response = templates.TemplateResponse(
        request=request,
        name="task_status.html",
        context={
            'info':job_info.__dict__, 
            'status':str(await job.status())
        },
    )
    return response
