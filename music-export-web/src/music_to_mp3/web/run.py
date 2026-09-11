"""Run the web application with Uvicorn."""

import uvicorn


def main() -> None:
    """Start the ASGI web service."""

    uvicorn.run(
        "music_to_mp3.web.main:app",
        host="0.0.0.0",
        port=8000,
        proxy_headers=True,
    )
