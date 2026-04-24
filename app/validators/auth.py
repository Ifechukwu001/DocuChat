import re
from typing import Annotated

from pydantic import Field, BaseModel

from ._commons import String, EmailString


class RegisterSchema(BaseModel):
    """Register Schema."""

    email: EmailString
    password: Annotated[
        String,
        Field(
            min_length=8,
            max_length=128,
            pattern=re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$"),
        ),
    ]


class LoginSchema(BaseModel):
    """Login Schema."""

    email: EmailString
    password: Annotated[String, Field(min_length=1)]


class RefreshSchema(BaseModel):
    """Refresh Schema."""

    refresh_token: Annotated[String, Field(min_length=1)]
