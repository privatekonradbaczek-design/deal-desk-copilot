from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(service_name: str, log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON output.

    Must be called once at service startup before any logging occurs.
    Binds service_name to all subsequent log entries via contextvars.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    structlog.contextvars.bind_contextvars(service=service_name)


def bind_request_context(
    correlation_id: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Bind per-request context variables to structlog context."""
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        user_id=user_id,
        tenant_id=tenant_id,
    )


def clear_request_context() -> None:
    """Clear per-request context variables after request completes."""
    structlog.contextvars.unbind_contextvars("correlation_id", "user_id", "tenant_id")
