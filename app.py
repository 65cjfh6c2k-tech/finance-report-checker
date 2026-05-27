import os
import re
import shutil
import time
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from finance_checker.ai_insights import (
    generate_ai_insights,
    has_management_memo,
    render_management_memo_markdown,
)
from finance_checker import analyze_workbook, save_report_outputs


PROJECT_ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
JOBS_DIR = RUNTIME_DIR / "jobs"
DOWNLOAD_BASE_URL = "http://127.0.0.1:8000/download"
DEFAULT_MAX_UPLOAD_MB = 10
DEFAULT_JOB_TTL_MINUTES = 60

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


def build_download_urls(job_id: str, checked_filename: str) -> dict:
    return {
        "html_report": f"{DOWNLOAD_BASE_URL}/{job_id}/report.html",
        "json_report": f"{DOWNLOAD_BASE_URL}/{job_id}/report.json",
        "checked_excel": f"{DOWNLOAD_BASE_URL}/{job_id}/{checked_filename}",
    }


@app.post("/analyze")
async def analyze_upload(file: UploadFile = File(...), include_ai: bool = False):
    print(f"include_ai: {include_ai}")
    cleanup_old_jobs()

    original_filename = Path(file.filename or "").name
    safe_filename = sanitize_workbook_filename(original_filename)
    if safe_filename is None:
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx files are supported.",
        )

    job_id = str(uuid4())
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    upload_path = job_dir / "input.xlsx"
    checked_filename = f"checked_{safe_filename}"

    try:
        upload_bytes = await file.read()
        enforce_upload_size(upload_bytes)
        upload_path.write_bytes(upload_bytes)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Could not save uploaded workbook.",
        ) from error

    try:
        report = analyze_workbook(str(upload_path))
        report["workbook"] = safe_filename
        report["downloads"] = build_download_urls(job_id, checked_filename)
        if include_ai:
            report["ai_insights"] = generate_ai_insights(report)
            if has_management_memo(report["ai_insights"]):
                memo_path = job_dir / "management_memo.md"
                memo_path.write_text(
                    render_management_memo_markdown(report["ai_insights"]),
                    encoding="utf-8",
                )
                report["downloads"][
                    "management_memo_md"
                ] = f"{DOWNLOAD_BASE_URL}/{job_id}/management_memo.md"

        save_report_outputs(
            upload_path,
            report,
            output_dir=job_dir,
            checked_filename=checked_filename,
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Could not analyze workbook.",
        ) from error

    return report


@app.get("/download/{job_id}/{filename}")
def download_file(job_id: str, filename: str):
    if not is_valid_job_id(job_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid download request.",
        )

    safe_filename = Path(filename).name
    is_allowed_report = safe_filename in {
        "report.html",
        "report.json",
        "management_memo.md",
    }
    is_allowed_workbook = (
        safe_filename.startswith("checked_") and safe_filename.endswith(".xlsx")
    )

    if safe_filename != filename or not (is_allowed_report or is_allowed_workbook):
        raise HTTPException(
            status_code=400,
            detail="This file is not available for download.",
        )

    job_dir = (JOBS_DIR / job_id).resolve()
    file_path = (job_dir / safe_filename).resolve()
    if job_dir not in file_path.parents:
        raise HTTPException(
            status_code=400,
            detail="Invalid download request.",
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Requested file was not found.",
        )

    return FileResponse(file_path, filename=safe_filename)


def max_upload_bytes() -> int:
    raw_value = os.getenv("MAX_UPLOAD_MB", str(DEFAULT_MAX_UPLOAD_MB))
    try:
        max_mb = float(raw_value)
    except ValueError:
        max_mb = DEFAULT_MAX_UPLOAD_MB
    return int(max_mb * 1024 * 1024)


def job_ttl_seconds() -> float:
    raw_value = os.getenv("JOB_TTL_MINUTES", str(DEFAULT_JOB_TTL_MINUTES))
    try:
        ttl_minutes = float(raw_value)
    except ValueError:
        ttl_minutes = DEFAULT_JOB_TTL_MINUTES
    return max(ttl_minutes, 0) * 60


def cleanup_old_jobs():
    if not JOBS_DIR.exists():
        return

    jobs_root = JOBS_DIR.resolve()
    cutoff = time.time() - job_ttl_seconds()

    for job_dir in JOBS_DIR.iterdir():
        try:
            if not job_dir.is_dir() or not is_valid_job_id(job_dir.name):
                continue

            resolved_job_dir = job_dir.resolve()
            if resolved_job_dir.parent != jobs_root:
                continue

            if job_dir.stat().st_mtime > cutoff:
                continue

            shutil.rmtree(resolved_job_dir)
            print(f"Cleaned expired job folder: {job_dir.name}")
        except Exception as error:
            print(
                "Warning: could not clean expired job folder "
                f"{job_dir.name}: {error.__class__.__name__}"
            )


def enforce_upload_size(upload_bytes: bytes):
    if len(upload_bytes) > max_upload_bytes():
        raise HTTPException(
            status_code=413,
            detail="Uploaded file is too large.",
        )


def sanitize_workbook_filename(filename: str):
    original_name = Path(filename or "").name
    if Path(original_name).suffix.lower() != ".xlsx":
        return None

    stem = Path(original_name).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not safe_stem:
        safe_stem = "workbook"
    return f"{safe_stem[:120]}.xlsx"


def is_valid_job_id(job_id: str) -> bool:
    try:
        return str(UUID(job_id)) == job_id
    except ValueError:
        return False
