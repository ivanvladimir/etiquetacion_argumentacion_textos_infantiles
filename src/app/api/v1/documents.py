from datetime import datetime
import re

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
from ...core.db.docsearch import async_get_docsearch, get_meilisearch_client
from ...schemas.job import Job
from ...schemas.task import TaskCreate, TaskCreateInternal, TaskRead, TaskStatus, TaskUpdate

templates = Jinja2Templates(directory="src/app/api/v1/templates")

router = APIRouter(tags=["documents"])


@router.post("/document/{document_id}", status_code=201)#, dependencies=[Depends(rate_limiter_dependency)])
async def api_document(
    request: Request,
    document_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    docsearch: Annotated[AsyncGenerator, Depends(get_meilisearch_client)],
) -> HTMLResponse:
    if not current_user:
        raise ForbiddenException()

    doc = await docsearch.index('documents').get_document(
        document_id,
        fields=['name_document','text','created_by']
        )
    if 'created_by' in doc and doc['created_by'] != current_user['id']:
        raise ForbiddenException()

    response = templates.TemplateResponse(
        request=request,
        name="document.html",
        context={
            'name':doc['name_document'],
            'html':doc['text']
        }
    )
    return response

@router.get("/documents/", status_code=201)#, dependencies=[Depends(rate_limiter_dependency)])
async def api_docs(
    request: Request,
    docsearch: Annotated[AsyncGenerator, Depends(get_meilisearch_client)],
    current_user: Annotated[dict, Depends(get_current_user)],
    scope: str = 'collection',
    page: int = 0,
    page_size: int = 30,
) -> HTMLResponse:
    if not current_user:
        raise ForbiddenException()

    if scope == 'collection':
        filter= "(type = 'manual' OR type = 'labelled') AND created_by NOT EXISTS"
    else:
        filter= f"(type = 'manual' OR type = 'labelled') AND created_by = {current_user['id']}"

    docs = await docsearch.index('documents').get_documents(
        fields=['id','name_document','model','type','text'],
        filter=filter,
        offset=page*page_size,
        limit=page_size
        )

    if docs.total == 0:
        raise NotFoundException("No documents found for current user.")

    re_remove_tags=re.compile(r'<[^>]+>')
    documents=[]
    for ele in docs.results:
        t=re_remove_tags.sub('', ele['text'])
        ele['text']= t[:100] + "..." if len(t) > 100 else t
        documents.append(ele)

    response = templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={
            'documents':documents,
            'offset':page*page_size,
            'page':page,
            'scope':scope,
            'last_page': ((page + 1) * page_size + 1) > docs.total,
        }
    )
    return response

   

 
