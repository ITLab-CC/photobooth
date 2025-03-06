from contextlib import asynccontextmanager
from datetime import datetime
import os
from typing import AsyncIterator, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from setup import setup
from db_connection import MongoDBConnection
from session import Session, SessionManager

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
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        # Close all mongodb connections
        for conn in System.values():
            conn.close()


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
    tocken = credentials.credentials
    session = await SM.get_session(tocken)
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

# Auth endpoint
@app.post("/api/v1/auth/token", response_model=AuthResponse)
async def login(auth: AuthRequest) -> AuthResponse:
    try:
        session: Session = await SM.login(System["login_manager"], auth.username, auth.password, None)
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
@app.get("/api/v1/auth/status", response_model=AuthResponse)
async def status(session: Session = Depends(auth)) -> AuthResponse:
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
@app.get("/api/v1/auth/logout", response_model=OK)
async def logout(session: Session = Depends(auth)) -> OK:
    await session.logout()
    return OK(ok=True)


























# ---------------------------
# Webpage
# ---------------------------
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# Catch-all route: For any path, serve the index.html so React can handle routing.
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_react_app(full_path: str):
    index_path = os.path.join("frontend/dist", "index.html")
    return FileResponse(index_path)


# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)