from timetabler.config import get_settings


def run() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "timetabler.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
    )


if __name__ == "__main__":
    run()
