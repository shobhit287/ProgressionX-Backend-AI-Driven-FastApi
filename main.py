from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from core.exception_handlers import BaseDomainError, domain_exception_handler

app = FastAPI(title="ProgressionX API", version="1.0.0", docs_url=f"{settings.API_PREFIX}/docs")

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
app.include_router(workout_session_router.router, prefix=settings.API_PREFIX)
app.include_router(exercise_set_router.router, prefix=settings.API_PREFIX)
app.include_router(weight_log_router.router, prefix=settings.API_PREFIX)
app.include_router(analytics_router.router, prefix=settings.API_PREFIX)
app.include_router(ai_router.router, prefix=settings.API_PREFIX)
