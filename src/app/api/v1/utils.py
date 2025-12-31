import uuid
from datetime import datetime


from typing import Annotated, Any, cast, AsyncGenerator

from fastapi import APIRouter, Depends, Request, Form, HTTPException
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
from ...core.db.docsearch import async_get_docsearch, get_meilisearch_client
from ...schemas.job import Job
from ...schemas.task import TaskCreate, TaskCreateInternal, TaskRead, TaskStatus, TaskUpdate

templates = Jinja2Templates(directory="src/app/api/v1/templates")

router = APIRouter(tags=["utils"])

@router.post("/analyze", status_code=201)#, dependencies=[Depends(rate_limiter_dependency)])
async def analyze_text(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    docsearch: Annotated[AsyncGenerator, Depends(get_meilisearch_client)],
    text: str | None = Form(None), 
    filename : str | None = Form(None), ) -> HTMLResponse:
    if not current_user:
        raise ForbiddenException()

    if queue.pool is None:
        raise HTTPException(status_code=503, detail="No exíste cola de trabajos")

    job = None
    if text:
        document_name=f"{sanitize_filename(text[:30]).replace(' ','_')}"
        document_id=uuid.uuid4().hex
        task_internal = TaskCreateInternal(**{
            "created_by_user_id": current_user['id'],
            "name":document_name,
            "document_id":document_id,
            "status":TaskStatus.STARTING
        })
        task_created = await crud_tasks.create(db=db, object=task_internal, schema_to_select=TaskRead, return_as_model=True)
        job = await queue.pool.enqueue_job(
            "predict_task", 
            "infantiles-argumentation-xlm-roberta", 
            document_id, document_name, 
            text, 
            task=task_created.id,
            user=current_user['id'])

        if job is None:
            raise HTTPException(status_code=500, detail="Failed to create task")

        job_status = str(await job.status())

        values_update = TaskUpdate(**{'task_id':job.job_id})
        task_updated = await crud_tasks.update(db=db, object=values_update.model_dump(exclude_unset=True), id=task_created.id, schema_to_select=TaskRead)

        await docsearch.index("documents").add_documents([{
                    'id': document_id,
                    'text':text,
                    'name_document':document_name,
                    'type':'original',
                    'created_by': current_user['id'],
                    'created_at': datetime.now().isoformat()
                }])

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
