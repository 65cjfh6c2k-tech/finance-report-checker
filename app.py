from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from finance_checker import analyze_workbook, save_report_outputs


PROJECT_ROOT = Path(__file__).resolve().parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"
DOWNLOAD_BASE_URL = "http://127.0.0.1:8000/download"

app = FastAPI(title="Finance Report Checker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "Finance Report Checker API is running",
    }


def build_download_urls(workbook_filename: str) -> dict:
    return {
        "html_report": f"{DOWNLOAD_BASE_URL}/report.html",
        "json_report": f"{DOWNLOAD_BASE_URL}/report.json",
        "checked_excel": f"{DOWNLOAD_BASE_URL}/checked_{workbook_filename}",
    }


@app.post("/analyze")
async def analyze_upload(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx files are supported.",
        )

    UPLOADS_DIR.mkdir(exist_ok=True)
    upload_path = UPLOADS_DIR / filename
    upload_path.write_bytes(await file.read())

    try:
        report = analyze_workbook(str(upload_path))
        save_report_outputs(upload_path, report)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not analyze workbook: {error}",
        ) from error

    report["downloads"] = build_download_urls(filename)
    return report


@app.get("/download/{filename}")
def download_file(filename: str):
    safe_filename = Path(filename).name
    is_allowed_report = safe_filename in {"report.html", "report.json"}
    is_allowed_workbook = (
        safe_filename.startswith("checked_") and safe_filename.endswith(".xlsx")
    )

    if safe_filename != filename or not (is_allowed_report or is_allowed_workbook):
        raise HTTPException(
            status_code=400,
            detail="This file is not available for download.",
        )

    file_path = PROJECT_ROOT / safe_filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Requested file was not found.",
        )

    return FileResponse(file_path, filename=safe_filename)
