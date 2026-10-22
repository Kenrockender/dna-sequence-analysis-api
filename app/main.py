from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.errors import ValidationError
from app.services.reference import load_reference
from app.routers import align, translate, analyze

app = FastAPI(
    title="DNA Sequence Analysis API",
    description="Align DNA sequences and translate to protein",
    version="1.0.0"
)

# serve file static (HTML, JS, CSS) dari folder /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    # load referensi sekali waktu server nyala
    load_reference()
    print("Reference sequence loaded successfully")


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    # handle error validasi kita sendiri, kembalikan 422
    return JSONResponse(
        status_code=422,
        content={"error": exc.error_code, "detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    # handle error validasi dari FastAPI, format ulang supaya konsisten
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = " -> ".join(str(loc) for loc in first["loc"])
        msg = first["msg"]
        error_detail = f"{field}: {msg}"
    else:
        error_detail = "Validation error"

    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "detail": error_detail}
    )


# daftarkan semua router dengan prefix /api
app.include_router(align.router, prefix="/api", tags=["align"])
app.include_router(translate.router, prefix="/api", tags=["translate"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])


@app.get("/")
async def root():
    # redirect ke web UI
    return RedirectResponse(url="/static/index.html")


@app.get("/api")
async def api_root():
    return {
        "message": "DNA Sequence Analysis API",
        "docs": "/docs",
        "endpoints": ["/api/align", "/api/translate", "/api/analyze"]
    }
