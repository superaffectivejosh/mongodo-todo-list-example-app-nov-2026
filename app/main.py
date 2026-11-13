"""A small, real CRUD API: insert, find/get, set, and delete with Beanie."""

from contextlib import asynccontextmanager
from pathlib import Path

import certifi
from beanie import PydanticObjectId, init_beanie
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.models import Task, TaskInput, TaskOutput, utc_now

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = None
    try:
        settings = Settings()
        options = {"tlsCAFile": certifi.where(), "tls": True} if settings.uri.startswith("mongodb+srv://") else {}
        client = AsyncMongoClient(settings.uri, serverSelectionTimeoutMS=10000, tz_aware=True, **options)
        app.state.client = client
        app.state.database_name = settings.database_name
        await client.admin.command("ping")
        await init_beanie(database=client[settings.database_name], document_models=[Task])
    except (PyMongoError, ValidationError, ValueError):
        # Driver and settings errors can include parts of the connection string.
        raise RuntimeError("MongoDB startup failed. Check the URI, database name, credentials, and network access.") from None
    else:
        yield
    finally:
        if client is not None:
            await client.close()


app = FastAPI(title="Little Wins API", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"], www_redirect=False)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def local_security(request: Request, call_next):
    # JSON mutations and same-origin requests only; no cross-origin CORS access.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"detail": "Cross-origin changes are not allowed."}, status_code=403)
        media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
        if request.method in {"POST", "PUT", "PATCH"} and media_type != "application/json":
            return JSONResponse({"detail": "Send application/json."}, status_code=415)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; object-src 'none'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(PyMongoError)
async def database_error(request: Request, exc: PyMongoError):
    return JSONResponse(status_code=503, content={"detail": "MongoDB is unavailable. Your change was not confirmed. Please try again."})


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health(request: Request):
    await request.app.state.client.admin.command("ping")
    return {"status": "connected", "database": request.app.state.database_name, "collection": "tasks"}


@app.get("/api/tasks", response_model=list[TaskOutput])
async def list_tasks():
    return [TaskOutput.from_document(task) for task in await Task.find_all().sort("-created_at").to_list()]


async def require_task(task_id: PydanticObjectId) -> Task:
    task = await Task.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="This task no longer exists. Refresh your board.")
    return task


@app.get("/api/tasks/{task_id}", response_model=TaskOutput)
async def read_task(task_id: PydanticObjectId):
    return TaskOutput.from_document(await require_task(task_id))


@app.post("/api/tasks", response_model=TaskOutput, status_code=201)
async def create_task(data: TaskInput):
    task = Task(**data.model_dump())
    await task.insert()
    return TaskOutput.from_document(task)


@app.put("/api/tasks/{task_id}", response_model=TaskOutput)
async def update_task(task_id: PydanticObjectId, data: TaskInput):
    task = await require_task(task_id)
    await task.set({**data.model_dump(), "updated_at": utc_now()})
    return TaskOutput.from_document(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: PydanticObjectId):
    task = await require_task(task_id)
    await task.delete()
    return Response(status_code=204)
