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
from ...crud.crud_users import crud_users
from ...schemas.job import Job

import uuid

templates = Jinja2Templates(directory="src/app/api/templates")

router = APIRouter(tags=["utils"])

@router.post("/analyze", response_model=Job, status_code=201)#, dependencies=[Depends(rate_limiter_dependency)])
async def analyze_text(
        current_user: Annotated[dict, Depends(get_current_user)],
        text: str = Form(...), 
        filename: str = Form(...),
):
    if not current_user:
        raise ForbiddenException()

    if queue.pool is None:
        raise HTTPException(status_code=503, detail="No exíste cola de trabajos")

    job = await queue.pool.enqueue_job("sample_background_task", filename)
    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    return {
        "id": job.job_id
    }
