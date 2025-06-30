from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routes import router as v1_router
from app.core.config import settings
from app.core.logging import init_logging

def create_app() -> FastAPI:
    init_logging()
    app = FastAPI(title=settings.PROJECT_NAME,
                  version=settings.VERSION,
                  docs_url="/docs" if settings.DEBUG else None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOW_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    app.include_router(v1_router, prefix=settings.API_PREFIX)
    return app

app = create_app()