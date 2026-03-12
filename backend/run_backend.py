"""
Entry point for packaged backend executable.
"""
import uvicorn


def main() -> None:
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
