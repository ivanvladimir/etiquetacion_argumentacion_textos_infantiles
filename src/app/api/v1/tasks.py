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
        raise HTTPException(status_code=503, detail="La cola de trabajos no está disponible")

    job = ArqJob(task_id, queue.pool)
    job_info = await job.info()
    if job_info is None:
        return None

    response = templates.TemplateResponse(
        request=request,
        name="task_status.html",
        context={
            'info':job_info.__dict__,
            'task_id':task_id,
            'status':str(await job.status()),
            'result':await job.result_info(),
        },
    )
    return response
