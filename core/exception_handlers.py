from fastapi import Request
from fastapi.responses import JSONResponse

class BaseDomainError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code


async def domain_exception_handler(
    request: Request,
    exc: BaseDomainError
):
    return JSONResponse(
        status_code=exc.code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )