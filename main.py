from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from core.config import settings

from features.users import users_router
from features.auth import auth_router
from features.workout_split import workout_split_router
from features.split_exercise import split_exercise_router
from features.workout_session import workout_session_router
from features.exercise_set import exercise_set_router
from features.weight_log import weight_log_router
from features.analytics import analytics_router
from features.ai_analysis import ai_router
from features.diet import diet_router as diet_router_module
from features.export import export_router
from features.admin import admin_router
from core.exception_handlers import BaseDomainError, domain_exception_handler
from core.rate_limiter import limiter, rate_limit_exceeded_handler

# Disable Swagger / ReDoc in production
_is_production = settings.ENV.lower() == "production"

app = FastAPI(
    title="ProgressionX API",
    version="1.0.0",
    docs_url=None if _is_production else f"{settings.API_PREFIX}/docs",
    redoc_url=None if _is_production else f"{settings.API_PREFIX}/redoc",
    openapi_url=None if _is_production else f"{settings.API_PREFIX}/openapi.json",
)

# Return a clear message when someone tries to access docs in production
if _is_production:
    @app.get(f"{settings.API_PREFIX}/docs")
    @app.get(f"{settings.API_PREFIX}/redoc")
    @app.get(f"{settings.API_PREFIX}/openapi.json")
    async def docs_disabled(request: Request):
        return JSONResponse(
            status_code=403,
            content={"error": {"code": 403, "message": "API documentation is disabled in production."}},
        )

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.PORTAL_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
async def health():
    return {"status": "server is running"}


#add middlewares
app.add_exception_handler(BaseDomainError, domain_exception_handler)


#add routers
app.include_router(users_router.router, prefix=settings.API_PREFIX)
app.include_router(auth_router.router, prefix=settings.API_PREFIX)
app.include_router(workout_split_router.router, prefix=settings.API_PREFIX)
app.include_router(split_exercise_router.router, prefix=settings.API_PREFIX)
app.include_router(split_exercise_router.exercises_router, prefix=settings.API_PREFIX)
app.include_router(workout_session_router.router, prefix=settings.API_PREFIX)
app.include_router(exercise_set_router.router, prefix=settings.API_PREFIX)
app.include_router(weight_log_router.router, prefix=settings.API_PREFIX)
app.include_router(analytics_router.router, prefix=settings.API_PREFIX)
app.include_router(ai_router.router, prefix=settings.API_PREFIX)
app.include_router(diet_router_module.router, prefix=settings.API_PREFIX)
app.include_router(export_router.router, prefix=settings.API_PREFIX)
app.include_router(admin_router.router, prefix=settings.API_PREFIX)
