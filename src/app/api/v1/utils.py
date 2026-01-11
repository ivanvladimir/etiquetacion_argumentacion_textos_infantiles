import uuid
import io
from datetime import datetime
from docx import Document

from typing import Annotated, Any, cast, AsyncGenerator

from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File
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
from ...core.config import settings
from ...core.utils.template_filters import naturaltime

import io

templates = Jinja2Templates(directory="src/app/api/v1/templates")
templates.env.filters["naturaltime"] = naturaltime

router = APIRouter(tags=["utils"])

@router.get("/search", status_code=201)
async def api_search(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    docsearch: Annotated[AsyncGenerator, Depends(get_meilisearch_client)],
    q: str | None = None,
    page: int = 1,
    results_per_page: int = 20,
    ) -> HTMLResponse:

    result = await docsearch.index("documents").search(
        q,
        hits_per_page=results_per_page,
        page=page,
        attributes_to_highlight = ['text'],
        attributes_to_crop = ['text'],
        highlight_pre_tag = '<mark>',
        highlight_post_tag = '</mark>',
        crop_length = 20,
        filter=["type = 'original'"]
    )

    response = templates.TemplateResponse(
        request=request,
        name="search_results.html",
        context={
            'documents': result.hits,
            'search_term': q,
            'page':page,
            'offset': (page - 1) * results_per_page,
            'last_page': ((page + 1) * results_per_page + 1) > result.total_hits,
        }
    )
    return response

 

@router.post("/analyze", status_code=201)
async def analyze_text(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    docsearch: Annotated[AsyncGenerator, Depends(get_meilisearch_client)],
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> HTMLResponse:
    if not current_user:
        raise ForbiddenException()
    if queue.pool is None:
        raise HTTPException(status_code=503, detail="No exíste cola de trabajos")
    
    # Validate that either text or file is provided
    if not text and not file:
        raise HTTPException(status_code=400, detail="Either text or file must be provided")
   
    # File size check only if middleware is not applied
    if file and not getattr(request.state, "file_size_limit_checked", False):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_FILE_SIZE:  # 10 MB
            raise HTTPException(
                status_code=413,
                detail="File size exceeds maximum allowed size of 10MB"
            )
    
    job = None
    
    # Process file if provided, otherwise use text
    if file:
        # Read file content
        try:
            file_content = await file.read()
            
            # Decode based on file type
            if file.content_type in ["text/plain", "application/json"]:
                text = file_content.decode("utf-8")
            elif file.content_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
                doc = Document(io.BytesIO(file_content))
                text = "\n".join([para.text for para in doc.paragraphs])
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")
            
            # Use original filename or generate from content
            document_name = sanitize_filename(file.filename or f"document_{uuid.uuid4().hex[:8]}")
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")
    
    else:
        # Original text processing
        document_name = sanitize_filename(f"text_{text[:50]}.txt").replace(" ", "_")
    
    # Create task and process (same as before)
    document_id = uuid.uuid4().hex
    document_id_ = uuid.uuid4().hex
    
    task_internal = TaskCreateInternal(**{
        "created_by_user_id": current_user['id'],
        "name": document_name,
        "document_id": document_id,
        "status": TaskStatus.STARTING
    })
    
    task_created = await crud_tasks.create(
        db=db,
        object=task_internal,
        schema_to_select=TaskRead,
        return_as_model=True
    )
    
    job = await queue.pool.enqueue_job(
        "predict_task",
        "infantiles-argumentation-xlm-roberta",
        document_id,
        document_id_,
        document_name,
        text,
        task=task_created.id,
        user=current_user['id']
    )
    
    if job is None:
        raise HTTPException(status_code=500, detail="Failed to create task")
    
    job_status = str(await job.status())
    values_update = TaskUpdate(**{'task_id': job.job_id})
    task_updated = await crud_tasks.update(
        db=db,
        object=values_update.model_dump(exclude_unset=True),
        id=task_created.id,
        schema_to_select=TaskRead
    )
    
    await docsearch.index("documents").add_documents([{
        'id': document_id,
        'id_labelled': document_id_,
        'text': text,
        'name_document': document_name,
        'type': 'original',
        'created_by': current_user['id'],
        'created_at': datetime.now().isoformat()
    }])
    
    job_info = await job.info()
    response = templates.TemplateResponse(
        request=request,
        name="task_status.html",
        context={
            'info': job_info.__dict__,
            'task_id': job.job_id,
            'status': job_status,
            'result': await job.result_info(),
        }
    )
    return response
