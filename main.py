from contextlib import asynccontextmanager
from datetime import datetime
from math import ceil
import os
from typing import AsyncIterator, Dict, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.datastructures import Headers

import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from setup import setup
from db_connection import MongoDBConnection
from session import Session, SessionManager

# ---------------------------
# Redis Connection
# ---------------------------
REDIS_URL = "redis://127.0.0.1:6379"


# ---------------------------
# MongoDB Connection
# ---------------------------
# TODO: Replace with .env variables!!!
MONGODB_HOST = "localhost:27017"
MONGODB_DB_NAME = "photo_booth"

# Setup the DB with all collections, roles and users
setup() # TODO: Remove this in production!!!

# Create alle System Users
# TODO: Replace with .env variables!!!
System: Dict[str, MongoDBConnection] = {
    "login_manager": MongoDBConnection(
        mongo_uri=MONGODB_HOST,
        user="login_manager",
        password="login_manager",
        db_name=MONGODB_DB_NAME
    ),
    "photo_booth": MongoDBConnection(
        mongo_uri=MONGODB_HOST,
        user="photo_booth",
        password="photo_booth",
        db_name=MONGODB_DB_NAME
    ),
    "img_viewer": MongoDBConnection(
        mongo_uri=MONGODB_HOST,
        user="img_viewer",
        password="img_viewer",
        db_name=MONGODB_DB_NAME
    ),
    "old_img_eraser": MongoDBConnection(
        mongo_uri=MONGODB_HOST,
        user="old_img_eraser",
        password="old_img_eraser",
        db_name=MONGODB_DB_NAME
    )
}

# ---------------------------
# FastAPI App Initialization
# ---------------------------
# Identify the service by the Service-Name header or the IP address
async def service_name_identifier(request: Request) -> Union[str, Headers]:
    if request.client is None:
        return "unknown"
    return request.headers.get("Service-Name") or request.client.host  # Identify by IP if no header

async def rate_limit_exceeded_callback(request: Request, response: Response, pexpire: int) -> None:
    """
    default callback when too many requests
    :param request:
    :param pexpire: The remaining milliseconds
    :param response:
    :return:
    """
    expire = ceil(pexpire / 1000)

    raise HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        f"Too Many Requests. Retry after {expire} seconds.",
        headers={"Retry-After": str(expire)},
    )

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis_connection = redis.from_url(REDIS_URL, encoding="utf8", decode_responses=True)
    await FastAPILimiter.init(
        redis_connection,
        identifier=service_name_identifier,
        http_callback=rate_limit_exceeded_callback,
        )
    try:
        yield
    finally:
        for conn in System.values():
            conn.close()
        await FastAPILimiter.close()

app = FastAPI(
    lifespan=lifespan,
    title="Photo Booth",
    description="A simple photo booth application.",
    version="1.0",
)

# ---------------------------
# CORS Middleware
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    # TODO: Replace with .env variables!!!
    allow_origins=["http://localhost:5173"],  # Allowed Origins from the frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Authentication Dependencies
# ---------------------------
security = HTTPBearer()

# Session Manager for getting the user session
SM = SessionManager()

# get session from token
async def auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Session:
    token = credentials.credentials
    session = await SM.get_session(token)
    if session is None:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return session

# ---------------------------
# Auth Endpoints
# ---------------------------
# Auth models
class AuthRequest(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    last_login: Optional[datetime]
    roles: list[str]

class AuthResponse(BaseModel):
    token: str
    creation_date: datetime
    expiration_date: datetime
    user: User

@app.post("/api/v1/auth/token", response_model=AuthResponse, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def api_auth_login(auth: AuthRequest) -> AuthResponse:
    try:
        session: Session = await SM.login(System["login_manager"], auth.username, auth.password)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    return AuthResponse(
        token=session._id,
        creation_date=session.creation_date,
        expiration_date=session.expiration_date,
        user=User(
            username=session.user.username,
            last_login=session.user.last_login,
            roles=session.user.roles
        )
    )

# Auth status
@app.get("/api/v1/auth/status", response_model=AuthResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_auth_status(session: Session = Depends(auth)) -> AuthResponse:
    return AuthResponse(
        token=session._id,
        creation_date=session.creation_date,
        expiration_date=session.expiration_date,
        user=User(
                    username=session.user.username,
                    last_login=session.user.last_login,
                    roles=session.user.roles
                )
    )

# Logout model
class OK(BaseModel):
    ok: bool

# Logout endpoint
@app.get("/api/v1/auth/logout", response_model=OK, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def api_auth_logout(session: Session = Depends(auth)) -> OK:
    await session.logout()
    return OK(ok=True)


























# ---------------------------
# Webpage
# ---------------------------
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# Catch-all route: For any path, serve the index.html so React can handle routing.
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_react_app(full_path: str) -> FileResponse:
    index_path = os.path.join("frontend/dist", "index.html")
    return FileResponse(index_path)


# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)