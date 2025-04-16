import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import fnmatch
from math import ceil
import os
import re
from typing import AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple, Union

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_limiter import FastAPILimiter
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel
import redis.asyncio as redis
from starlette.datastructures import Headers
import uvicorn

from img_server.db_connection import MongoDBConnection
from img_server.session import Session, SessionManager
from img_server.user import User
from img_server.role import Role, Endpoint, Method

URL: str = "http://localhost:8000"
REDIS_URL: str = "redis://localhost:6379"

System: MongoDBConnection = MongoDBConnection(
                mongo_uri="localhost:27017",
                user="admin", # type: ignore
                password="admin", # type: ignore
                db_name="photo_booth",
                admin=True
            )


# ---------------------------
# Setup db
# ---------------------------
# This will create the database and the collections if they do not exist
Role.db_create_collection(System)
# Create default roles
if not Role.db_find_by_rolename(System, "boss"):
    boss_role = Role.new(
        db_connection=System,
        rolename="boss",
        api_endpoints=[
            Endpoint(
                method=Method.ANY,
                path_filter="/*"
            )
        ]
    )
    user_role = Role.new(
        db_connection=System,
        rolename="user",
        api_endpoints=[
            Endpoint(
                method=Method.GET,
                path_filter="/api/v1/auth/*"
            ),
            Endpoint(
                method=Method.POST,
                path_filter="/api/v1/auth/*"
            ),
            Endpoint(
                method=Method.PUT,
                path_filter="/api/v1/auth/*"
            ),
            Endpoint(
                method=Method.DELETE,
                path_filter="/api/v1/auth/*"
            )
        ]
    )

USER_ROLE = Role.db_find_by_rolename(System, "user")
if USER_ROLE is None:
    raise Exception("User role not found. Pls reinitialize the database.")

BOSE_ROLE = Role.db_find_by_rolename(System, "boss")
if BOSE_ROLE is None:
    raise Exception("Boss role not found. Pls reinitialize the database.")

User.db_create_collection(System)
# check if admin user exists
if not User.db_find_by_username(System, "admin"):
    User.new(
        db_connection=System,
        username="admin",
        password="admin",
        roles_id=[BOSE_ROLE.id]
    )

    User.new(
        db_connection=System,
        username="user",
        password="user",
        roles_id=[USER_ROLE.id]
    )

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
        System.close()
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
    allow_origins=[URL],  # Allowed Origins from the frontend
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

def check_role(role: Role, request: Endpoint) -> bool:
    """
    Check if the given role grants access to the specified endpoint.
    It converts the role's endpoint patterns into regexes; any '*' is replaced with '.*'.
    """
    for endpoint in role.api_endpoints:
        # check if the request method is the same
        if endpoint.method != Method.ANY and endpoint.method != request.method:
            continue

        # Escape special regex characters, then replace the escaped wildcard with regex equivalent.
        regex_pattern = '^' + re.escape(endpoint.path_filter).replace(r'\*', '.*') + '$'
        if re.match(regex_pattern, request.path_filter):
            return True
    return False

def get_user_from_session(session: Session) -> User:
    # get user
    user_id = session.user_id
    user = User.db_find_by_id(System, user_id)
    if user is None:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return user

# get session from token
def auth(required_roles: Optional[List[Optional[Role]]] = None) -> Callable[[Request, HTTPAuthorizationCredentials], Awaitable[object]]:
    """
    Authentication dependency that returns a session if access is granted.
    It first checks if the user has one of the required roles directly.
    If not, it checks the request path against the API endpoint patterns defined in each role.
    
    The API endpoint is printed/formatted (e.g., GET-/endpoint) as indicated in the docstring.
    """
    async def new_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> object:
        token = credentials.credentials
        session = await SM.get_session(token)
        if session is None:
            raise HTTPException(status_code=403, detail="Invalid authentication token")

        # get user
        user = get_user_from_session(session)
        
        user_role_ids = user.roles

        # Fetch all roles from the database.
        roles_db = Role.db_find_all(System)
        user_roles = [user_role for user_role in roles_db.values() if user_role._id in user_role_ids]

        user_roles_names = [role.rolename for role in user_roles]
        
        # If specific required roles are provided, check if the user has at least one of them.
        if required_roles is not None:
            if any(role.rolename in user_roles_names for role in required_roles if role is not None):
                return session

        # current request method and path
        new_request = Endpoint(
            method=Method(request.method),
            path_filter=request.url.path
        )


        # Build a list of Role objects corresponding to the user's roles.
        roles_list = [role_obj for role_id, role_obj in roles_db.items() if role_id in user_role_ids]

        # Check if any of the user's roles permit access to the requested endpoint.
        for role_obj in roles_list:
            if check_role(role_obj, new_request):
                return session

        # If no matching role endpoint pattern is found, deny access.
        raise HTTPException(status_code=403, detail="Access forbidden")

    return new_auth


# ---------------------------
# Auth Endpoints
# ---------------------------
# Auth models
class AuthRequest(BaseModel):
    username: str
    password: str

class AuthUser(BaseModel):
    id: str
    username: str
    roles: list[str]
    last_login: Optional[datetime]

class AuthResponse(BaseModel):
    token: str
    creation_date: datetime
    expiration_date: datetime
    user: AuthUser

@app.post(
    "/api/v1/auth/token",
    response_model=AuthResponse,
    dependencies=[Depends(RateLimiter(times=5, minutes=1))],
    description="Authenticate a user with a username and password. Creates a new session token and returns detailed session information."
)
async def api_auth_login(auth: AuthRequest) -> AuthResponse:
    """Authenticate a user and create a new session token."""
    try:
        session, user = await SM.login(System, auth.username, auth.password)
    except Exception as e:
        if str(e) == "User not found":
            raise HTTPException(status_code=404, detail="Username or password are wrong")
        elif str(e) == "Incorrect password":
            raise HTTPException(status_code=403, detail="Username or password are wrong")
        else:
            raise e
    
    return AuthResponse(
        token=session._id,
        creation_date=session.creation_date,
        expiration_date=session.expiration_date,
        user=AuthUser(
            id=user._id,
            username=user.username,
            last_login=user.last_login,
            roles=user.roles
        )
    )


@app.get(
    "/api/v1/auth/status",
    response_model=AuthResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Return the current authentication sessions details, including token and user information."
)
async def api_auth_status(session: Session = Depends(auth())) -> AuthResponse:
    """Check the current authentication session status."""

    # get user
    user = get_user_from_session(session)

    return AuthResponse(
        token=session._id,
        creation_date=session.creation_date,
        expiration_date=session.expiration_date,
        user=AuthUser(
            id=user._id,
            username=user.username,
            roles=user.roles,
            last_login=user.last_login
        )
    )

# Logout model
class OK(BaseModel):
    ok: bool

@app.get(
    "/api/v1/auth/logout",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=5, minutes=1))],
    description="Logout the current user session, invalidating the session token."
)
async def api_auth_logout(session: Session = Depends(auth())) -> OK:
    await session.logout()
    return OK(ok=True)


class AuthSessionResponse(BaseModel):
    sessions: List[AuthResponse]

@app.get(
    "/api/v1/auth/sessions",
    response_model=AuthSessionResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="For administrative users: Retrieve a list of all active sessions with detailed session information."
)
async def api_auth_session(session: Session = Depends(auth([BOSE_ROLE]))) -> AuthSessionResponse:
    sessions = await SM.get_sessions()
    return_sessions: List[AuthResponse] = []
    for s in sessions.values():

        # get user
        user = get_user_from_session(s)

        return_sessions.append(AuthResponse(
            token=s._id,
            creation_date=s.creation_date,
            expiration_date=s.expiration_date,
            user=AuthUser(
                id=user._id,
                username=user.username,
                roles=user.roles,
                last_login=user.last_login
            )
        ))

    return AuthSessionResponse(sessions=return_sessions)


@app.get(
    "/api/v1/auth/session/logout/{token}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=5, minutes=1))],
    description="For administrators only: Logout a specific session identified by its token."
)
async def api_auth_session_logout(token: str, session: Session = Depends(auth([BOSE_ROLE]))) -> OK:
   
    s = await SM.get_session(token)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await s.logout()
    return OK(ok=True)













# ---------------------------
# Webpage
# ---------------------------
app.mount("/assets", StaticFiles(directory="../frontend/dist/assets"), name="assets")

# Catch-all route: For any path, serve the index.html so React can handle routing.
@app.get(
    "/{full_path:path}",
    response_class=HTMLResponse,
    description="Catch-all route that serves the React application’s index.html for any unspecified path."
)
async def serve_react_app(full_path: str) -> FileResponse:
    index_path = os.path.join("../frontend/dist", "index.html")
    return FileResponse(index_path)


# ---------------------------
# Main
# ---------------------------
async def main() -> None:
    # Configure the server (this does not call asyncio.run() internally)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    # Run the server asynchronously
    await asyncio.gather(
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())