"""Define HTML and JSON routes for the music export service."""

from pathlib import Path
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from music_to_mp3.selection import read_selection_file
from music_to_mp3.web.database import get_job, list_events, list_jobs
from music_to_mp3.web.jobs import request_cancellation, submit_job
from music_to_mp3.web.library import scan_library
from music_to_mp3.web.settings import get_settings

router = APIRouter()
template_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=template_dir)


def template_context(request: Request, **values: object) -> dict[str, object]:
    """Build the common Jinja template context.

    Args:
        request: Current HTTP request.
        **values: Page-specific values.

    Returns:
        Complete template context.
    """

    return {"request": request, "settings": get_settings(), **values}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """Render the dashboard with recent jobs.

    Args:
        request: Current HTTP request.

    Returns:
        HTML dashboard response.
    """

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        template_context(request, jobs=list_jobs()),
    )


@router.get("/library", response_class=HTMLResponse)
def library(request: Request, q: str = "") -> HTMLResponse:
    """Render searchable artist and album selections.

    Args:
        request: Current HTTP request.
        q: Optional artist or album substring.

    Returns:
        Full library page.
    """

    albums = scan_library(get_settings().source_root, q)
    return templates.TemplateResponse(
        request,
        "library.html",
        template_context(request, albums=albums, query=q),
    )


@router.get("/library/results", response_class=HTMLResponse)
def library_results(request: Request, q: str = "") -> HTMLResponse:
    """Return a filtered album-table fragment for HTMX.

    Args:
        request: Current HTTP request.
        q: Artist or album substring.

    Returns:
        HTML fragment containing search results.
    """

    albums = scan_library(get_settings().source_root, q)
    return templates.TemplateResponse(
        request,
        "partials/library_results.html",
        template_context(request, albums=albums),
    )


@router.post("/selections/validate", response_class=HTMLResponse)
async def validate_selection_upload(
    request: Request,
    selection_file: UploadFile = File(...),
) -> HTMLResponse:
    """Validate an uploaded selection file without starting a job.

    Args:
        request: Current HTTP request.
        selection_file: Browser-uploaded UTF-8 selection file.

    Returns:
        Validation summary fragment.
    """

    settings = get_settings()
    content = await selection_file.read(settings.max_selection_upload_bytes + 1)
    if len(content) > settings.max_selection_upload_bytes:
        message = "Selection file is larger than the configured limit"
        return templates.TemplateResponse(
            request,
            "partials/validation.html",
            template_context(request, valid=False, message=message),
            status_code=400,
        )
    try:
        text = content.decode("utf-8-sig")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as file:
            file.write(text)
            temporary_path = Path(file.name)
        try:
            selection = read_selection_file(temporary_path)
        finally:
            temporary_path.unlink(missing_ok=True)
        message = (
            f"Valid file: {len(selection.artists)} complete artist(s) and "
            f"{len(selection.albums)} individual album(s)."
        )
        valid = True
    except (UnicodeError, ValueError) as error:
        message = str(error)
        valid = False
    return templates.TemplateResponse(
        request,
        "partials/validation.html",
        template_context(request, valid=valid, message=message),
        status_code=200 if valid else 400,
    )


@router.post("/jobs")
async def create_export_job(
    selection_file: UploadFile | None = File(default=None),
    interactive_selection: list[str] = Form(default=[]),
    destination: str = Form(...),
    quality: int = Form(default=0),
    overwrite: bool = Form(default=False),
) -> RedirectResponse:
    """Create a job from an uploaded file or interactive selection.

    Args:
        selection_file: Optional uploaded UTF-8 selection file.
        interactive_selection: Artist/album selections from the browser.
        destination: Configured destination key.
        quality: LAME VBR quality from zero through nine.
        overwrite: Whether existing output files may be replaced.

    Returns:
        Redirect to the new job page.

    Raises:
        HTTPException: If no valid selection is supplied.
    """

    settings = get_settings()
    if selection_file and selection_file.filename:
        content = await selection_file.read(settings.max_selection_upload_bytes + 1)
        if len(content) > settings.max_selection_upload_bytes:
            raise HTTPException(413, "Selection file is too large")
        try:
            selection_text = content.decode("utf-8-sig")
        except UnicodeError as error:
            raise HTTPException(400, "Selection file must be UTF-8") from error
    else:
        selection_text = "\n".join(interactive_selection).strip()
    if not selection_text:
        raise HTTPException(400, "Upload a selection file or select albums")

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as file:
        file.write(selection_text)
        path = Path(file.name)
    try:
        read_selection_file(path)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    finally:
        path.unlink(missing_ok=True)

    try:
        job_id = submit_job(selection_text, destination, quality, overwrite)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_page(request: Request, job_id: str) -> HTMLResponse:
    """Render one job and its events.

    Args:
        request: Current HTTP request.
        job_id: Job identifier.

    Returns:
        Job details page.
    """

    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return templates.TemplateResponse(
        request,
        "job.html",
        template_context(request, job=job, events=list_events(job_id)),
    )


@router.get("/jobs/{job_id}/status", response_class=HTMLResponse)
def job_status(request: Request, job_id: str) -> HTMLResponse:
    """Return an HTMX job-status fragment.

    Args:
        request: Current HTTP request.
        job_id: Job identifier.

    Returns:
        Job status HTML fragment.
    """

    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return templates.TemplateResponse(
        request,
        "partials/job_status.html",
        template_context(request, job=job),
    )


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> RedirectResponse:
    """Request cancellation of a job.

    Args:
        job_id: Job identifier.

    Returns:
        Redirect back to the job page.
    """

    request_cancellation(job_id)
    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    """Download a completed local-output archive.

    Args:
        job_id: Job identifier.

    Returns:
        ZIP file response.
    """

    job = get_job(job_id)
    if job is None or job["status"] != "ready" or not job["download_name"]:
        raise HTTPException(404, "Download is not available")
    path = get_settings().download_root / str(job["download_name"])
    if not path.is_file():
        raise HTTPException(404, "Download has expired")
    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.get("/health")
def health() -> dict[str, str]:
    """Return a simple container health response.

    Returns:
        Health status mapping.
    """

    return {"status": "ok"}
