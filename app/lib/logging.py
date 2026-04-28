import logging

import structlog

from app.env import settings

_shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]

structlog.configure(
    processors=(
        [
            *_shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
        if settings.IS_PRODUCTION
        else [*_shared_processors, structlog.dev.ConsoleRenderer()]
    ),
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.INFO if settings.IS_PRODUCTION else logging.DEBUG
    ),
    context_class=dict,
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)


logger = structlog.get_logger().bind(service="docuchat")
