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

@router.get("/search")
async def search(
    request: Request,
    q: str = Query(default="", description="Search term")) -> HTMLResponse:
    """
    Search for terms into the documents
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/search.html",
        context={
            "search_term": q,
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page": 'search',
        },
    )
    return response

@router.get("/documents")
async def docs(
    request: Request) -> HTMLResponse:
    """
    Shows a documents that are open to all users
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/documents.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "scope":"collection",
            "active_page":'docs',
            "active_menu":'collections'
        },
    )
    return response

@router.get("/mydocuments")
async def mydocs(
    request: Request) -> HTMLResponse:
    """
    Shows a document that belong to the user
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/documents.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "scope":"mydocs",
            "active_page":'docs',
            "active_menu":'mydocs'
        },
    )
    return response

@router.get("/register")
async def register(request: Request) -> HTMLResponse:
    """
    Registrar usuario
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/register.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page": 'register',
        },
    )
    return response

@router.get("/forgot_password")
async def forgot_password(request: Request) -> HTMLResponse:
    """
    Forma para capturar el correo del usuario que olvido su contraseña
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/forgot_password.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page": 'register',
        },
    )
    return response

@router.get("/reset_password")
async def reset_password(request: Request) -> HTMLResponse:
    """
    Forma para capturar el correo del usuario que olvido su contraseña
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/reset_password.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page": 'register',
        },
    )
    return response

@router.get("/email_verification")
async def email_verification(
        request: Request,
        token: str,
    ) -> HTMLResponse:
    """
    Validar usuario por correo
    """
    start_time = time.time()
    response = templates.TemplateResponse(
        request=request,
        name="user/email_verification.html",
        context={
            "elapsed_time_seconds": f"{time.time() - start_time:2.3f}",
            "active_page": 'register',
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
