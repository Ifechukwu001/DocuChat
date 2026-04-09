import re
from typing import Annotated

from pydantic import Field, EmailStr, BaseModel, AfterValidator


class RegisterSchema(BaseModel):
    """Register Schema."""

    email: Annotated[EmailStr, AfterValidator(lambda v: v.lower().strip())]
    password: Annotated[
        str,
        Field(
            min_length=8,
            max_length=128,
            pattern=re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$"),
        ),
    ]


class LoginSchema(BaseModel):
    """Login Schema."""

    email: Annotated[EmailStr, AfterValidator(lambda v: v.lower().strip())]
    password: Annotated[str, Field(min_length=1)]


class RefreshSchema(BaseModel):
    """Refresh Schema."""

    refresh_token: Annotated[str, Field(min_length=1)]
