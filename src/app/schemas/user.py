from datetime import datetime
from typing import Annotated
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema


class UserBase(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    username: Annotated[str, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    institution: Annotated[str, Field(default="Prepa 3 UNAM")]
    description: Annotated[str, Field(default="Textos de estiudiantes de preparatoria en la UNAM.")]
 

class User(TimestampSchema, UserBase, UUIDSchema, PersistentDeletion):
    hashed_password: str
    is_superuser: bool = False
    tier_id: int | None = None


class UserRead(BaseModel):
    id: int
    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    username: Annotated[str, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    institution: Annotated[str, Field(min_length=2, examples=["Prepa 3 UNAM"])]
    description: Annotated[str, Field(min_length=2, examples=["Textos de estudiantes de preparatoria en la UNAM."])]
    tier_id: int | None

class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")
    password: Annotated[str, Field(pattern=r"^.{8,}|[0-9]+|[A-Z]+|[a-z]+|[^a-zA-Z0-9]+$", examples=["Str1ngst!"])]

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-z0-9]+$', v):
            raise ValueError('Usuario debe contener solo minúsculas y números')
        return v

    @validator('password')
    def validate_password(cls, v):
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(not c.isalnum() for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                'La contraseña debe contener mayúsculas, minúsculas, números y caracteres especiales'
            )
        return v

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', v):
            raise ValueError('El nombre solo puede contener letras y espacios')
        return v



class UserCreateInternal(UserBase):
    hashed_password: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str | None, Field(min_length=2, max_length=30, examples=["User Userberg"], default=None)]
    institution: Annotated[str | None, Field(min_length=2, examples=["Prepa 3 UNAM"], default=None)]
    description: Annotated[str | None, Field(min_length=2, examples=["Textos de estudiantes de preparatoria en la UNAM."], default=None)]
    username: Annotated[
        str | None, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userberg"], default=None)
    ]
    email: Annotated[EmailStr | None, Field(examples=["user.userberg@example.com"], default=None)]


class UserUpdateInternal(UserUpdate):
    updated_at: datetime


class UserTierUpdate(BaseModel):
    tier_id: int


class UserDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime


class UserRestoreDeleted(BaseModel):
    is_deleted: bool
