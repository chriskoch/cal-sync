#!/usr/bin/env python3
"""
Minimal test to verify lifespan execution.
Run this in the container to test if lifespan works.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test lifespan that uses print() instead of logging."""
    print("=" * 50)
    print("LIFESPAN STARTUP EXECUTING")
    print("=" * 50)

    with open("/tmp/lifespan_test.txt", "w") as f:
        f.write("Lifespan executed successfully\n")

    yield

    print("=" * 50)
    print("LIFESPAN SHUTDOWN EXECUTING")
    print("=" * 50)


app = FastAPI(
    title="Lifespan Test",
    version="1.0.0",
    lifespan=test_lifespan,
)


@app.get("/")
def read_root():
    return {"message": "Test app"}


@app.get("/check")
def check_lifespan():
    """Check if lifespan executed by reading the file."""
    try:
        with open("/tmp/lifespan_test.txt", "r") as f:
            content = f.read()
        return {"lifespan_executed": True, "content": content}
    except FileNotFoundError:
        return {"lifespan_executed": False, "error": "File not found"}


if __name__ == "__main__":
    uvicorn.run("test_lifespan:app", host="0.0.0.0", port=8001)
