"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.errors import ValidationError
from app.services.reference import load_reference
from app.routers import align, translate, analyze


# Create FastAPI app
app = FastAPI(
    title="DNA Sequence Analysis API",
    description="Align DNA sequences and translate to protein",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    """Load reference sequence on startup."""
    load_reference()
    print("Reference sequence loaded successfully")


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle custom validation errors with 422 status."""
    return JSONResponse(
        status_code=422,
        content={
            "error": exc.error_code,
            "detail": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors with consistent 422 format."""
    # Extract first error for simpler message
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        field = " -> ".join(str(loc) for loc in first_error["loc"])
        message = first_error["msg"]
        error_detail = f"{field}: {message}"
    else:
        error_detail = "Validation error"
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": error_detail
        }
    )


# Include routers
app.include_router(align.router, prefix="/api", tags=["align"])
app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])


@app.get("/")
async def root():
    """Root endpoint - redirect to web UI."""
    return RedirectResponse(url="/static/index.html")


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {
        "message": "DNA Sequence Analysis API",
        "docs": "/docs",
        "endpoints": ["/api/align", "/api/translate", "/api/analyze"]
    }
