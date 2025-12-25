import uuid
from datetime import datetime


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
from ...crud.crud_tasks import crud_tasks
from ...core.db.database import async_get_db
from ...core.db.docsearch import async_get_docsearch
from ...schemas.job import Job
from ...schemas.task import TaskCreate, TaskCreateInternal, TaskRead, TaskStatus

templates = Jinja2Templates(directory="src/app/api/v1/templates")

router = APIRouter(tags=["utils"])

@router.post("/analyze", status_code=201)#, dependencies=[Depends(rate_limiter_dependency)])
async def analyze_text(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    docsearch: Annotated[AsyncGenerator, Depends(async_get_docsearch)],
    text: str | None = Form(None), 
    filename : str | None = Form(None), ) -> HTMLResponse:
    if not current_user:
        raise ForbiddenException()

    if queue.pool is None:
        raise HTTPException(status_code=503, detail="No exíste cola de trabajos")

    if text:
        document_name=f"{sanitize_filename(text[:30]).replace(' ','_')}"
        document_id=uuid.uuid4().hex
        job = await queue.pool.enqueue_job("predict_task", "infantiles-argumentation-xlm-roberta", document_id, document_name, text)
        job_status = str(await job.status())
        task_internal = TaskCreateInternal(**{
            "created_by_user_id": current_user['id'],
            "name":document_name,
            "task_id": job.job_id,
            "document_id":document_id,
            "status":TaskStatus.STARTING
        })
        await docsearch.index("documents").add_documents([{
                'id': document_id,
                'text':text,
                'name_document':document_name,
                'type':'original',
                'created_by': current_user['id'],
                'created_at': datetime.now().isoformat()
            }])
        created_task = await crud_tasks.create(db=db, object=task_internal)

    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    job_info = await job.info()

    response = templates.TemplateResponse(
        request=request,
        name="task_status.html",
        context={
            'info':job_info.__dict__, 
            'task_id': job.job_id,
            'status':job_status,
            'result':await job.result_info(),
        }
    )
    return response
