from datetime import timedelta
from typing import Annotated, Optional
import jwt

from fastapi import APIRouter, Depends, Request, Response, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timedelta

from pydantic import BaseModel, Field, EmailStr, validator, ValidationError

from ...core.config import settings
from ...core.db.database import async_get_db
from ...api.dependencies import get_current_superuser, get_current_user
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.utils import queue
from ...core.schemas import Token
from ...schemas.user import UserCreate, UserRead, UserCreateInternal
from ...crud.crud_users import crud_users
from ...core.exceptions.http_exceptions import DuplicateValueException, ForbiddenException, NotFoundException, CustomException
from ...core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenType,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
)

router = APIRouter(tags=["login"])

@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    user = await authenticate_user(username_or_email=form_data.username, password=form_data.password, db=db)
    if not user:
        raise UnauthorizedException("Wrong username, email or password.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

    refresh_token = await create_refresh_token(data={"sub": user["username"]})
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=max_age
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/check_auth_status")
async def check_auth_status(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict[str, str]:
    if not current_user:
        raise ForbiddenException()

    return JSONResponse(content={"authenticated": 'true', 
                                 "current_user": {'name':current_user['name'], 'username':current_user['username'], 'is_superuser':current_user['is_superuser'], 'email':current_user['email'], 'id':current_user['id']
                                                  }
                                 })

@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: Request, db: AsyncSession = Depends(async_get_db)) -> dict[str, str]:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise UnauthorizedException("Refresh token missing.")

    user_data = await verify_token(refresh_token, TokenType.REFRESH, db)
    if not user_data:
        raise UnauthorizedException("Invalid refresh token.")

    new_access_token = await create_access_token(data={"sub": user_data.username_or_email})
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/register")
async def register_user(
        request: Request,
        db: Annotated[AsyncSession, Depends(async_get_db)],
        name: str = Form(...),
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        institution: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
) -> dict[str, str]:

    try:
        user = UserCreate(
            name=name,
            username=username,
            email=email,
            password=password,
            institution=institution or None,
            description=description or None,
        )
        email_row = await crud_users.exists(db=db, email=user.email)
        if email_row:
            raise DuplicateValueException("Email is already registered")

        username_row = await crud_users.exists(db=db, username=user.username)
        if username_row:
            raise DuplicateValueException("Username not available")

        user_internal_dict = user.model_dump()
        user_internal_dict["hashed_password"] = get_password_hash(password=user_internal_dict["password"])
        del user_internal_dict["password"]

        user_internal = UserCreateInternal(**user_internal_dict)
        created_user = await crud_users.create(
            db=db, 
            object=user_internal,
            schema_to_select=UserRead,
            return_as_model=True
        )

        user_read = await crud_users.get(db=db, id=created_user.id, schema_to_select=UserRead)
        if user_read is None:
            raise NotFoundException("Created user not found.")

        payload = {
            "email": user_read['email'],
            "exp": datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES),
            "type": "email_verification"
        }
        verification_token = jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM)

        job = await queue.pool.enqueue_job(
            "send_email_task",
            "Correo de verificación de cuenta para AATI",
            [user_read['email']],
            f"""
            <p>Su correo {user_read['email']} ha sido registrado exitosamente en AATI. Para verificar su cuenta, por favor haga clic en el siguiente enlace:</p>

            <p><a href="{request.url_for("email_verification")}?token={verification_token}">Verificar mi cuenta</a></p>

            <p>Si usted no se registró en AATI, por favor ignore este correo.</p>
            """,
        )

        if not job:
            raise CustomException(422, f"Error al enviar correo, contactar al administrador.")


        return JSONResponse(content={
            "status": "success",
            "message": f"Cuenta creada de forma exitosa.\nSe enviará un correo a {user.email} para verificar la cuenta.",
            "user": {
                "name": user.name,
                "username": user.username,
                "email": user.email
            }
        })
    except ValidationError as exc:
        raise CustomException(422, f"Error en los valores propocionados")



@router.post("/verify_email")
async def api_verify_email(
        request: Request,
) -> dict[str, str]:

    try:
        data = await request.json()
        payload = jwt.decode(data['token'], settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM])

        email: str = payload.get("email")
        token_type: str = payload.get("type")
        expires_at = datetime.fromtimestamp(payload.get("exp")).isoformat()

        if email is None or token_type != "email_verification":
            raise CustomException(401, f"El token proporcionado es incorrecto.")
        
        return JSONResponse(
            content={
                "status": "success", 
                "message": "Email verificado de forma correcta; ya podrás acceder a la plataforma.",
                "redirect_url": f"{request.url_for('main')}"
            })
    
    except jwt.ExpiredSignatureError:
        raise CustomException(401, f"El token de verifiación ha expirado. Solicita un nuevo token.")
    except jwt.InvalidTokenError as e:
        raise CustomException(401, f"El token proporcionado es incorrecto.")



