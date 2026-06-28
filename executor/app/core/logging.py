from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def _add_service_name(
    logger: object, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    # needed when multiple services share a log aggregator
    event_dict["service"] = "executor"
    return event_dict


def setup_logging(debug: bool = False) -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # merges request_id, task_id etc from middleware
        _add_service_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        renderer = structlog.dev.ConsoleRenderer()  # human-readable for local dev
    else:
        renderer = (
            structlog.processors.JSONRenderer()
        )  # structured JSON for prod aggregators

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # silence noisy stdlib loggers so they don't double-print
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
