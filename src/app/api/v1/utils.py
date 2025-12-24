from typing import Annotated, Any, cast, AsyncGenerator

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...api.dependencies import rate_limiter_dependency
from ...core.exceptions.http_exceptions import ForbiddenException, NotFoundException
from ...core.utils.cache import cache
from ...core.utils import queue
from ...core.worker.utils import sanitize_filename
from ...crud.crud_users import crud_users
from ...schemas.job import Job

import uuid

templates = Jinja2Templates(directory="src/app/api/v1/templates")

router = APIRouter(tags=["utils"])

@router.post("/analyze", status_code=201)#, dependencies=[Depends(rate_limiter_dependency)])
async def analyze_text(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    text: str | None = Form(None), 
    filename : str | None = Form(None), ) -> HTMLResponse:
    if not current_user:
        raise ForbiddenException()

    if queue.pool is None:
        raise HTTPException(status_code=503, detail="No exíste cola de trabajos")

    if text:
        job = await queue.pool.enqueue_job("predict_task", "infantiles-argumentation-xlm-roberta", f"{sanitize_filename(text[:20]).replace(' ','_')}", text)
    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    job_info = await job.info()

    response = templates.TemplateResponse(
        request=request,
        name="task_status.html",
        context={
            'info':job_info.__dict__, 
            'task_id': job.job_id,
            'status':str(await job.status()),
            'result':await job.result_info(),
        }
    )
    return response
