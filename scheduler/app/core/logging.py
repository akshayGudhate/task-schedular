from __future__ import annotations

import logging
import sys

import structlog

# add service name to the event dict
def _add_service_name(logger: object, method: str, event_dict: dict) -> dict:
    # needed when multiple services share an aggregator
    event_dict["service"] = "scheduler"
    return event_dict


# setup logging
def setup_logging(debug: bool = False) -> None:
    # shared processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # merges request_id, task_id etc from middleware
        _add_service_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        renderer = structlog.dev.ConsoleRenderer()   # human-readable for local dev
    else:
        renderer = structlog.processors.JSONRenderer()  # json for prod aggregators

    # configure structlog
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
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
