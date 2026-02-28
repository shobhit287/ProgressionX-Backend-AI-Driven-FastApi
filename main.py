from fastapi import FastAPI
from core.config import settings

from features.users import users_router
# from features.auth import auth_router
from core.exception_handlers import BaseDomainError, domain_exception_handler

app = FastAPI(title="ProgressionX API", version="1.0.0")

@app.get(f"{settings.API_PREFIX}/health", tags=["Health"])
async def health():
    return {"status": "server is running"}


#add middlewares
app.add_exception_handler(BaseDomainError, domain_exception_handler)


#add routers
app.include_router(users_router.router, prefix=settings.API_PREFIX)
# app.include_router(auth_router.router, prefix=settings.API_PREFIX)