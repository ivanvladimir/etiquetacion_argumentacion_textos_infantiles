import time
import os
import json

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

templates = Jinja2Templates(directory="src/app/front/templates")

router = APIRouter()

@router.get("/labelling")
async def labelling(request: Request) -> HTMLResponse:
    """
    Labeeling a text
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/labelling.html",
        context={"elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
                 "active_page":'labelling'},
    )
    return response

@router.get("/documents/")
async def docs(
    request: Request) -> HTMLResponse:
    """
    Shows a document
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/documents.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page":'docs'
        },
    )
    return response

@router.get("/document/{document_id}")
async def doc(
    document_id: str,
    request: Request) -> HTMLResponse:
    """
    Shows a document
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/document.html",
        context={
            "document_id": document_id,
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page":'docs'
        },
    )
    return response
