from functools import partial

from tortoise.contrib.fastapi import RegisterTortoise

from app.env import settings

TORTOISE_CONFIG: dict[str, str | dict[str, str | dict[str, str | list[str]]]] = {
    "connections": {"default": str(settings.DB_URL)},
    "apps": {
        "main": {
            "models": ["app.orm.models"],
            "default_connection": "default",
            "migrations": "app.orm.migrations",
        }
    },
}

register_orm = partial(
    RegisterTortoise,
    config=TORTOISE_CONFIG,
)


# TODO: Add logging for dev environment
