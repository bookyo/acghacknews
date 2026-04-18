import json
import logging
import random
import sys
from contextlib import asynccontextmanager
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.body_limit import BodyLimitMiddleware

from app.config import Settings
from app.db import init_db
from app.repository import FeedRepository
from app.routers import admin as admin_router
from app.routers import feed as feed_router
from app.routers import health as health_router


def _configure_logging(log_level: str) -> None:
    """Configure structured JSON logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            json.dumps(
                {
                    "timestamp": "%(asctime)s",
                    "level": "%(levelname)s",
                    "logger": "%(name)s",
                    "message": "%(message)s",
                }
            )
        )
    )
    root_logger.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application instance.

    Args:
        settings: Optional Settings instance. If not provided, settings are
                  loaded from environment variables / .env file.

    Returns:
        A configured FastAPI application.
    """
    if settings is None:
        settings = Settings()

    _configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    # Store settings and repo on app.state via closures so they are
    # accessible even without entering the lifespan.
    repo = FeedRepository(settings.database_path)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """Application lifespan: startup and shutdown hooks."""
        # --- Startup ---
        logger.info("Initializing database")
        await init_db(settings.database_path)

        # Defer heavy orchestrator creation to lifespan so test clients
        # can create the app without triggering network-dependent init.
        orchestrator = None
        try:
            from app.orchestrator import FetchOrchestrator

            orchestrator = FetchOrchestrator(settings)
        except Exception as exc:
            logger.warning("Could not create FetchOrchestrator: %s", exc)

        scheduler = AsyncIOScheduler()

        if orchestrator is not None:
            # Check if a catch-up fetch is needed on startup
            if await orchestrator.should_fetch_on_startup():
                logger.info("Running startup catch-up fetch")
                try:
                    result = await orchestrator.run_fetch_cycle()
                    logger.info("Startup fetch result: %s", result)
                except Exception as e:
                    logger.error("Startup fetch failed: %s", e)

            # Schedule periodic fetch cycle with jitter (0-60s)
            jitter_seconds = random.randint(0, 60)
            fetch_interval_seconds = (
                settings.fetch_interval_minutes * 60 + jitter_seconds
            )

            scheduler.add_job(
                orchestrator.run_fetch_cycle,
                "interval",
                seconds=fetch_interval_seconds,
                id="fetch_cycle",
                name="Fetch cycle",
                max_instances=1,
            )

            # Schedule daily cleanup at 04:00 UTC
            scheduler.add_job(
                orchestrator.run_cleanup,
                "cron",
                hour=4,
                minute=0,
                id="daily_cleanup",
                name="Daily cleanup",
                max_instances=1,
            )

            scheduler.start()
            logger.info(
                "Scheduler started: fetch every %dm (+%ds jitter), "
                "cleanup at 04:00 UTC",
                settings.fetch_interval_minutes,
                jitter_seconds,
            )

        yield

        # --- Shutdown ---
        if orchestrator is not None:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")

    app = FastAPI(
        title="ACG Feed API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Key"],
    )

    # Admin rate limit: 10 requests per 60 seconds per IP
    app.add_middleware(
        RateLimitMiddleware,
        path_prefixes=["/api/admin"],
        max_requests=10,
        window_seconds=60,
    )

    # Request body size limit: 1 MB
    app.add_middleware(BodyLimitMiddleware, max_bytes=1_048_576)

    # Security response headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Store settings and repo on app.state
    app.state.settings = settings
    app.state.repo = repo

    # Dependency injection: override the placeholder get_repo / get_settings
    # functions in each router module so they return the real instances.
    def _get_repo() -> FeedRepository:
        return app.state.repo

    def _get_settings() -> Settings:
        return app.state.settings

    feed_router.get_repo = _get_repo
    feed_router.get_settings = _get_settings
    health_router.get_repo = _get_repo
    health_router.get_settings = _get_settings
    admin_router.get_repo = _get_repo
    admin_router.get_settings = _get_settings

    # Include routers
    app.include_router(feed_router.router)
    app.include_router(health_router.router)
    app.include_router(admin_router.router)

    return app


app = create_app()
