from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from ..core.config import settings

class FileSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit file upload size"""

    def __init__(self, app: FastAPI, max_file_size: int = 10 * 1024 * 1024) -> None:
        super().__init__(app)
        self.max_file_size = max_file_size
        self.max_file_size_mb = max_file_size / (1024 * 1024)

    async def dispatch(self, request: Request, call_next):
        # Mark that this middleware has been applied
        request.state.file_size_limit_checked = True

        # Only check for POST requests with multipart/form-data
        if request.method == "POST" and "multipart/form-data" in request.headers.get("content-type", ""):
            content_length = request.headers.get("content-length")
            
            if content_length and int(content_length) > self.max_file_size:
                return Response(
                    status_code=413,
                    content={
                        "detail": f"File size exceeds maximum allowed size of {self.max_file_size:.0f}MB"
                    }
                )
        
        response = await call_next(request)
        return response

