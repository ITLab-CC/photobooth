import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import time
import io
from math import ceil
import os
from typing import AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple, Union

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.datastructures import Headers

import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import qrcode
import uvicorn

from background import Background
from gallery import Gallery
from img import IMG
from frame import FRAME
from printer import PrinterQueueItem
from process_img import IMGReplacer
from setup import check_dotenv, setup
from db_connection import MongoDBConnection
from session import Session, SessionManager

check_dotenv()
# ---------------------------
# Redis Connection
# ---------------------------
REDIS_URL: str = os.getenv("REDIS_URL") # type: ignore


# ---------------------------
# MongoDB Connection
# ---------------------------
MONGODB_HOST: str = os.getenv("MONGODB_URL") # type: ignore
MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME") # type: ignore

# ---------------------------
# URL
# ---------------------------
URL: str = os.getenv("BASE_URL") # type: ignore

# Create alle System Users
System: Dict[str, MongoDBConnection] = {}
while True:
    try:
        System = {
            "login_manager": MongoDBConnection(
                mongo_uri=MONGODB_HOST,
                user=os.getenv("LOGIN_MANAGER"), # type: ignore
                password=os.getenv("LOGIN_MANAGER_PASSWORD"), # type: ignore
                db_name=MONGODB_DB_NAME
            ),
            "img_viewer": MongoDBConnection(
                mongo_uri=MONGODB_HOST,
                user=os.getenv("IMG_VIEWER"), # type: ignore
                password=os.getenv("IMG_VIEWER_PASSWORD"), # type: ignore
                db_name=MONGODB_DB_NAME
            ),
            "old_img_eraser": MongoDBConnection(
                mongo_uri=MONGODB_HOST,
                user=os.getenv("OLD_IMG_ERASER"), # type: ignore
                password=os.getenv("OLD_IMG_ERASER_PASSWORD"), # type: ignore
                db_name=MONGODB_DB_NAME
            ),
        }
        break
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}. Retrying in 5 seconds.")
        time.sleep(5)


# ---------------------------
# Values
# ---------------------------
str_gallery_expiration: str = os.getenv("GALLERY_EXPIRATION_SECONDS") # type: ignore
GALLERY_EXPIRATION = timedelta(seconds=int(str_gallery_expiration))


# ---------------------------
# Old img eraser
# ---------------------------
async def old_img_eraser() -> None:
    while True:
        try:
            # check every minute if there are galleries that are expired
            await asyncio.sleep(5)  # adjusted to 60 seconds as per comment
            db = System["old_img_eraser"]
            galleries = Gallery.db_find_all(db)

            for g in galleries:
                if g.expiration_time.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    # delete all images
                    IMG.db_delete_by_gallery(db, g._id)
                    # delete gallery
                    g.db_delete(db)
                    print(f"Deleted gallery {g._id}")
        except Exception as e:
            print(f"Error in old_img_eraser: {e}")


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

# get session from token
def auth(required_roles: Optional[List[str]] = None) -> Callable[[HTTPAuthorizationCredentials], Awaitable[Session]]:
    async def new_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Session:
        token = credentials.credentials
        session = await SM.get_session(token)
        if session is None:
            raise HTTPException(status_code=403, detail="Invalid authentication token")
        
        user = session.user
        # Check if user has at least one of the required roles
        if required_roles is not None:
            if not any(role in user.roles for role in required_roles):
                raise HTTPException(status_code=403, detail="Permission denied")
        return session
    return new_auth

# ---------------------------
# Auth Endpoints
# ---------------------------
# Auth models
class AuthRequest(BaseModel):
    username: str
    password: str

class AuthUser(BaseModel):
    username: str
    last_login: Optional[datetime]
    roles: list[str]

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
        session: Session = await SM.login(System["login_manager"], auth.username, auth.password)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    return AuthResponse(
        token=session._id,
        creation_date=session.creation_date,
        expiration_date=session.expiration_date,
        user=AuthUser(
            username=session.user.username,
            last_login=session.user.last_login,
            roles=session.user.roles
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
    return AuthResponse(
        token=session._id,
        creation_date=session.creation_date,
        expiration_date=session.expiration_date,
        user=AuthUser(
            username=session.user.username,
            last_login=session.user.last_login,
            roles=session.user.roles
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
async def api_auth_session(session: Session = Depends(auth(["boss"]))) -> AuthSessionResponse:
    if await session.is_admin() is False:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    sessions = await SM.get_sessions()
    return_sessions: List[AuthResponse] = []
    for s in sessions.values():
        return_sessions.append(AuthResponse(
            token=s._id,
            creation_date=s.creation_date,
            expiration_date=s.expiration_date,
            user=AuthUser(
                username=s.user.username,
                last_login=s.user.last_login,
                roles=s.user.roles
            )
        ))

    return AuthSessionResponse(sessions=return_sessions)


@app.get(
    "/api/v1/auth/session/logout/{token}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=5, minutes=1))],
    description="For administrators only: Logout a specific session identified by its token."
)
async def api_auth_session_logout(token: str, session: Session = Depends(auth(["boss"]))) -> OK:
    if await session.is_admin() is False:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    s = await SM.get_session(token)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await s.logout()
    return OK(ok=True)


# ---------------------------
# Gallery Endpoints
# ---------------------------
# Gallery models
class GalleryRequest(BaseModel):
    expiration_time: Optional[datetime] = None
    images: Optional[List[str]] = None
    pin: Optional[str] = None

class GalleryResponse(BaseModel):
    gallery_id: str
    creation_time: datetime
    expiration_time: datetime
    images: List[str]
    pin_set: bool

# create gallery
@app.post(
    "/api/v1/gallery",
    response_model=GalleryResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Create a new gallery. Optionally, specify images, a pin, and an expiration time (which must be in the future)."
)
async def api_gallery_create(gallery: Optional[GalleryRequest] = None, session: Session = Depends(auth(["boss", "photo_booth"]))) -> GalleryResponse:
    db = session.mongodb_connection

    if gallery is None:
        gallery = GalleryRequest()

    pin: Optional[str] = None
    salt: Optional[str] = None
    if gallery.pin is not None:
        # hash the pin
        pin, salt = Gallery.hash_pin(gallery.pin)

    # if images are set, check if they are valid
    if gallery.images is not None:
        for img_id in gallery.images:
            img = IMG.db_find(db, img_id)
            if img is None:
                raise HTTPException(status_code=404, detail="Image with id {img_id} not found")

    # check if the expiration time is in the future
    if gallery.expiration_time is not None and gallery.expiration_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Expiration time must be in the future")

    g = Gallery(
        creation_time=datetime.now(),
        expiration_time=gallery.expiration_time if gallery.expiration_time is not None else datetime.now() + GALLERY_EXPIRATION,
        images=gallery.images if gallery.images is not None else [],
        pin_hash=pin,
        pin_salt=salt
    )
    g.db_save(db)

    return GalleryResponse(
        gallery_id=g._id,
        creation_time=g.creation_time,
        expiration_time=g.expiration_time,
        images=g.images,
        pin_set=True if pin is not None else False
    )


# get gallerys
class GalleryListResponse(BaseModel):
    galleries: List[GalleryResponse]

@app.get(
    "/api/v1/galleries",
    response_model=GalleryListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a list of all galleries associated with the current user's session."
)
async def api_gallery_list(session: Session = Depends(auth(["boss"]))) -> GalleryListResponse:
    db = session.mongodb_connection

    galleries = Gallery.db_find_all(db)
    return_galleries: List[GalleryResponse] = []
    for g in galleries:
        return_galleries.append(GalleryResponse(
            gallery_id=g._id,
            creation_time=g.creation_time,
            expiration_time=g.expiration_time,
            images=g.images,
            pin_set=True if g.pin_hash is not None else False
        ))
    
    return GalleryListResponse(galleries=return_galleries)

# change expiration time
class GalleryExpirationRequest(BaseModel):
    expiration_time: datetime

@app.put(
    "/api/v1/gallery/{gallery_id}/expiration",
    response_model=GalleryResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Update the expiration time of an existing gallery. The new expiration time must be in the future."
)
async def api_gallery_change_expiration(gallery_id: str, expiration: GalleryExpirationRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> GalleryResponse:
    db = session.mongodb_connection

    # check if expiration time is in the future
    if expiration.expiration_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Expiration time must be in the future")

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure g.expiration_time is timezone-aware
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    g.expiration_time = expiration.expiration_time
    g.db_update(db)

    return GalleryResponse(
        gallery_id=g._id,
        creation_time=g.creation_time,
        expiration_time=g.expiration_time,
        images=g.images,
        pin_set=True if g.pin_hash is not None else False
    )

# change pin
class GalleryPinRequest(BaseModel):
    pin: Optional[str] = None

@app.put(
    "/api/v1/gallery/{gallery_id}/pin",
    response_model=GalleryResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Change the pin of an existing gallery. The endpoint validates that the gallery has not expired before updating."
)
async def api_gallery_change_pin(gallery_id: str, pin: Optional[GalleryPinRequest] = None, session: Session = Depends(auth(["boss"]))) -> GalleryResponse:
    db = session.mongodb_connection


    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    if pin is None:
        pin = GalleryPinRequest()

    g.db_set_pin(db, pin.pin)

    return GalleryResponse(
        gallery_id=g._id,
        creation_time=g.creation_time,
        expiration_time=g.expiration_time,
        images=g.images,
        pin_set=True if g.pin_hash is not None else False
    )

# set pin only if not set
@app.put(
    "/api/v1/gallery/{gallery_id}/pin/set",
    response_model=GalleryResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Set a pin for a gallery that does not already have one. This endpoint is used when a gallery’s pin needs to be initialized."
)
async def api_gallery_set_pin(gallery_id: str, pin: GalleryPinRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> GalleryResponse:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    if g.pin_hash is not None:
        raise HTTPException(status_code=400, detail="Gallery already has a pin")

    g.db_set_pin(db, pin.pin)

    return GalleryResponse(
        gallery_id=g._id,
        creation_time=g.creation_time,
        expiration_time=g.expiration_time,
        images=g.images,
        pin_set=True if g.pin_hash is not None else False
    )

# add image to gallery
class GalleryImageRequest(BaseModel):
    image_base64: str # base64 encoded image

class ResponseImage(BaseModel):
    image_id: str
    type: str
    gallery: str

@app.post(
    "/api/v1/gallery/{gallery_id}/image",
    response_model=ResponseImage,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Add a new image (provided as a base64 encoded string) to the specified gallery. The gallery must exist and be unexpired."
)
async def api_gallery_add_image(gallery_id: str, image: GalleryImageRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> ResponseImage:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    try:
        img = IMG.from_base64(image.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    img.gallery = gallery_id
    img.db_save(db)

    try:
        g.db_add_image(db, img._id)
    except Exception as e:
        # revert the image save
        img.db_delete(System["old_img_eraser"])
        raise HTTPException(status_code=500, detail=str(e))

    return ResponseImage(image_id=img._id, type=img.type, gallery=img.gallery)

# get qr-code url to gallery
@app.get(
    "/api/v1/gallery/{gallery_id}/qr",
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a QR code URL that links to the specified gallery."
)
async def api_gallery_qr(gallery_id: str, session: Session = Depends(auth(["boss", "photo_booth"]))) -> StreamingResponse:
    # find gallery
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    img_url = f"{URL}/gallery/?id={gallery_id}"
    qr_img = qrcode.make(img_url)

    img_bytes_io = io.BytesIO()
    qr_img.save(img_bytes_io)
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")

class GalleryImageListResponse(BaseModel):
    images: List[ResponseImage]

# get all images of a gallery without pin
@app.get(
    "/api/v1/gallery/{gallery_id}/images",
    response_model=GalleryImageListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve all images from a gallery without requiring a pin. The gallery must not be expired."
)
async def api_gallery_get_images(gallery_id: str, session: Session = Depends(auth(["boss", "photo_booth"]))) -> GalleryImageListResponse:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    images = g.images
    return_images: List[ResponseImage] = []
    for img_id in images:
        img = IMG.db_find(db, img_id)
        if img is not None:
            return_images.append(ResponseImage(image_id=img._id, type=img.type, gallery=img.gallery))

    return GalleryImageListResponse(images=return_images)

# check if gallery exists with pin
class GalleryCheckResponse(BaseModel):
    exists: bool

@app.get(
    "/api/v1/gallery/{gallery_id}",
    response_model=GalleryCheckResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Check if a gallery exists and if this gallery has a pin set."
)
async def api_gallery_check(gallery_id: str) -> GalleryCheckResponse:
    db = System["img_viewer"]

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        return GalleryCheckResponse(exists=False)
    
    return GalleryCheckResponse(exists=True if g.pin_hash is not None else False)

# get all images of a gallery with pin
@app.get(
    "/api/v1/gallery/{gallery_id}/images/pin/{pin}",
    response_model=GalleryImageListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve all images from a gallery using a valid gallery pin. The gallery must have a pin and not be expired."
)
async def api_gallery_get_images_with_pin(gallery_id: str, pin: str) -> GalleryImageListResponse:
    db = System["img_viewer"]

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    if g.pin_hash is None:
        raise HTTPException(status_code=400, detail="Gallery has no pin")

    if not g.validate_pin(pin):
        raise HTTPException(status_code=403, detail="Invalid pin")

    images = g.images
    return_images: List[ResponseImage] = []
    for img_id in images:
        img = IMG.db_find(db, img_id)
        if img is not None:
            return_images.append(ResponseImage(image_id=img._id, type=img.type, gallery=img.gallery))

    return GalleryImageListResponse(images=return_images)

# get image with pin
@app.get(
    "/api/v1/gallery/{gallery_id}/image/{image_id}/pin/{pin}",
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a specific image from a gallery using a valid pin. Verifies that the image belongs to the specified gallery."
)
async def api_gallery_get_image_with_pin(gallery_id: str, image_id: str, pin: str) -> StreamingResponse:
    db = System["img_viewer"]

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    if g.pin_hash is None:
        raise HTTPException(status_code=400, detail="Gallery has no pin")

    if not g.validate_pin(pin):
        raise HTTPException(status_code=403, detail="Invalid pin")

    img = IMG.db_find(db, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if img.gallery != gallery_id:
        raise HTTPException(status_code=400, detail="Image does not belong to this gallery")

    img_bytes_io = io.BytesIO()
    img.img.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")

# get image without pin (photo booth)
@app.get(
    "/api/v1/gallery/{gallery_id}/image/{image_id}",
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a specific image from a gallery without requiring a pin. Verifies that the image belongs to the specified gallery."
)
async def api_gallery_get_image(gallery_id: str, image_id: str, session: Session = Depends(auth(["boss", "photo_booth"]))) -> StreamingResponse:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    img = IMG.db_find(db, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if img.gallery != gallery_id:
        raise HTTPException(status_code=400, detail="Image does not belong to this gallery")

    img_bytes_io = io.BytesIO()
    img.img.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")

# remove image
@app.delete(
    "/api/v1/gallery/{gallery_id}/image/{image_id}",
    response_model=GalleryResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Remove an image from the specified gallery. Ensures that the gallery and image exist, and that the image belongs to the gallery."
)
async def api_gallery_remove_image(gallery_id: str, image_id: str, session: Session = Depends(auth(["boss"]))) -> GalleryResponse:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Ensure expiration time is timezone-aware before comparing
    exp_time = g.expiration_time if g.expiration_time.tzinfo else g.expiration_time.replace(tzinfo=timezone.utc)
    if exp_time < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Gallery has already expired")

    img = IMG.db_find(db, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if img.gallery != gallery_id:
        raise HTTPException(status_code=400, detail="Image does not belong to this gallery")

    img.db_delete(db)

    g.db_remove_image(db, image_id)

    # check if there is a print job for this image
    try:
        PrinterQueueItem.db_delete_by_img_id(db, image_id)
    except Exception as e:
        print(f"Error deleting print job: {e}")

    return GalleryResponse(
        gallery_id=g._id,
        creation_time=g.creation_time,
        expiration_time=g.expiration_time,
        images=g.images,
        pin_set=True if g.pin_hash is not None else False
    )

# delete gallery
@app.delete(
    "/api/v1/gallery/{gallery_id}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Delete an entire gallery and all of its associated images."
)
async def api_gallery_delete(gallery_id: str, session: Session = Depends(auth(["boss"]))) -> OK:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # delete all images
    IMG.db_delete_by_gallery(db, gallery_id)

    # delete all print jobs
    for img_id in g.images:
        try:
            PrinterQueueItem.db_delete_by_img_id(db, img_id)
        except Exception as e:
            print(f"Error deleting print job: {e}")

    g.db_delete(db)

    return OK(ok=True)


# remove gallery with pin and all img in it
@app.delete(
    "/api/v1/gallery/{gallery_id}/pin/{pin}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Remove a gallery and all of its associated images using a valid pin."
)
async def api_gallery_delete_with_pin(gallery_id: str, pin: str) -> OK:
    db = System["img_viewer"]

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    # validate pin
    if not g.validate_pin(pin):
        raise HTTPException(status_code=403, detail="Invalid pin")

    # delete all images
    IMG.db_delete_by_gallery(db, gallery_id)

    # delete all print jobs
    for img_id in g.images:
        try:
            PrinterQueueItem.db_delete_by_img_id(db, img_id)
        except Exception as e:
            print(f"Error deleting print job: {e}")
    
    g.db_delete(db)

    return OK(ok=True)


# ---------------------------
# Image Endpoints
# ---------------------------
# Image models
class ImageResponse(BaseModel):
    image_id: str
    type: str
    gallery: Optional[str]

class ImageListResponse(BaseModel):
    images: List[ImageResponse]

@app.get(
    "/api/v1/images",
    response_model=ImageListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a list of all images available in the database, along with their associated gallery (if any)."
)
async def api_image_list(session: Session = Depends(auth(["boss"]))) -> ImageListResponse:
    db = session.mongodb_connection

    images = IMG.db_find_all(db)
    return_images: List[ImageResponse] = []
    for img in images:
        return_images.append(ImageResponse(
            image_id=img._id,
            type=img.type,
            gallery=img.gallery
        ))

    return ImageListResponse(images=return_images)

# get image
@app.get(
    "/api/v1/image/{image_id}",
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a specific image by ID. Returns the image as a streaming PNG response."
)
async def api_image_get(image_id: str, session: Session = Depends(auth(["boss", "printer"]))) -> StreamingResponse:
    db = session.mongodb_connection

    img = IMG.db_find(db, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    
    img_bytes_io = io.BytesIO()
    img.img.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")


# ---------------------------
# Background Endpoints
# ---------------------------
# Background models
class BackgroundRequest(BaseModel):
    image_base64: str

class BackgroundResponse(BaseModel):
    background_id: str

@app.post(
    "/api/v1/background",
    response_model=BackgroundResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Upload a new background image. The image is provided as a base64 encoded string and saved to the database."
)
async def api_background_add(background_img: BackgroundRequest, session: Session = Depends(auth(["boss"]))) -> BackgroundResponse:
    db = session.mongodb_connection

    try:
        img = Background.from_base64(background_img.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    img.db_save(db)

    return BackgroundResponse(background_id=img._id)

class BackgroundListResponse(BaseModel):
    backgrounds: List[BackgroundResponse]

# get all backgrounds
@app.get(
    "/api/v1/backgrounds",
    response_model=BackgroundListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a list of all background images available in the database."
)
async def api_background_list(session: Session = Depends(auth(["boss", "photo_booth"]))) -> BackgroundListResponse:
    db = session.mongodb_connection

    backgrounds = Background.db_find_all(db)
    return_backgrounds: List[BackgroundResponse] = []
    for img in backgrounds:
        return_backgrounds.append(BackgroundResponse(
            background_id=img._id
        ))

    return BackgroundListResponse(backgrounds=return_backgrounds)

# get background
@app.get(
    "/api/v1/background/{background_id}",
    response_model=BackgroundResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a background image by its ID and return it as a streaming PNG response."
)
async def api_background_get(background_id: str, session: Session = Depends(auth(["boss", "photo_booth"]))) -> StreamingResponse:
    db = session.mongodb_connection

    img = Background.db_find(db, background_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Background image not found")
    
    img_bytes_io = io.BytesIO()
    img.img.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")

# delete background
@app.delete(
    "/api/v1/background/{background_id}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Delete a background image specified by its ID."
)
async def api_background_delete(background_id: str, session: Session = Depends(auth(["boss"]))) -> OK:
    db = session.mongodb_connection

    img = Background.db_find(db, background_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Background image not found")
    
    img.db_delete(db)

    # remove the background img from print jobs
    try:
        PrinterQueueItem.db_delete_by_img_id(db, background_id)
    except Exception as e:
        print(f"Error deleting print job: {e}")

    return OK(ok=True)


# ---------------------------
# Frame Endpoints
# ---------------------------
# Frame models
class FrameRequest(BaseModel):
    image_base64: str
    background_scale: float = 1.0
    background_offset: Tuple[int, int] = (0, 0)
    background_crop: Tuple[int, int, int, int] = (0, 0, 0, 0)
    qr_position: Tuple[int, int] = (0, 0)
    qr_scale: float = 1.0


class FrameResponse(BaseModel):
    frame_id: str

@app.post(
    "/api/v1/frame",
    response_model=FrameResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Upload a new frame image. The image is provided as a base64 encoded string and saved to the database."
)
async def api_frame_add(frame_img: FrameRequest, session: Session = Depends(auth(["boss"]))) -> FrameResponse:
    db = session.mongodb_connection

    try:
        img = FRAME.from_base64(frame_img.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    img.background_scale = frame_img.background_scale
    img.background_offset = frame_img.background_offset
    img.background_crop = frame_img.background_crop
    img.qr_position = frame_img.qr_position
    img.qr_scale = frame_img.qr_scale
    img.db_save(db)

    return FrameResponse(frame_id=img._id)

class FrameListResponse(BaseModel):
    frames: List[FrameResponse]

# get all frames
@app.get(
    "/api/v1/frames",
    response_model=FrameListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a list of all frame images available in the database."
)
async def api_frame_list(session: Session = Depends(auth(["boss", "photo_booth"]))) -> FrameListResponse:
    db = session.mongodb_connection

    frames = FRAME.db_find_all(db)
    return_frames: List[FrameResponse] = []
    for img in frames:
        return_frames.append(FrameResponse(
            frame_id=img._id
        ))

    return FrameListResponse(frames=return_frames)

# get frame
@app.get(
    "/api/v1/frame/{frame_id}",
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a frame image by its ID and return it as a streaming PNG response."
)
async def api_frame_get(frame_id: str, session: Session = Depends(auth(["boss", "photo_booth"]))) -> StreamingResponse:
    db = session.mongodb_connection

    img = FRAME.db_find(db, frame_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Frame image not found")
    
    img_bytes_io = io.BytesIO()
    img.frame.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")

# delete frame
@app.delete(
    "/api/v1/frame/{frame_id}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Delete a frame image specified by its ID."
)
async def api_frame_delete(frame_id: str, session: Session = Depends(auth(["boss"]))) -> OK:
    db = session.mongodb_connection

    img = FRAME.db_find(db, frame_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Frame image not found")
    
    img.db_delete(db)

    return OK(ok=True)


# ---------------------------
# Img processing Endpoints
# ---------------------------
# Image processing models
class ImageProcessRequest(BaseModel):
    image_id: str
    image_background_id: str
    img_frame_id: str
    refine_foreground: bool = False

class ImageProcessResponse(BaseModel):
    img_no_background: ImageResponse
    img_new_background: ImageResponse
    img_with_frame: ImageResponse

# Load AI model for image processing
Replacer = IMGReplacer()

@app.post(
    "/api/v1/image/process",
    response_model=ImageProcessResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Process an image by replacing its background using an AI model. Requires the target image ID and a background image ID. Optionally refine the foreground."
)
async def api_image_process(image: ImageProcessRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> ImageProcessResponse:
    db = session.mongodb_connection

    # get the image
    img = IMG.db_find(db, image.image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # add the processed image to the gallery
    g = Gallery.db_find(db, img.gallery)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # get the background image
    background_img = Background.db_find(db, image.image_background_id)
    if background_img is None:
        raise HTTPException(status_code=404, detail="Background image not found")

    # get the frame
    frame_img = FRAME.db_find(db, image.img_frame_id)
    if frame_img is None:
        raise HTTPException(status_code=404, detail="Frame image not found")

    # generate qr code
    try:
        gallery_id = g.id
        img_url = f"{URL}/gallery/?id={gallery_id}"
        qr_img = qrcode.make(img_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error generating QR code: " + str(e))

    # add qr code to the frame
    try:
        frame_with_qr = Replacer.add_qr_code(
            frame_img.frame,
            qr_img, # type: ignore
            frame_img.qr_position,
            frame_img.qr_scale
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error adding QR code to frame: " + str(e))

    # remove background
    try:
        img_no_background = Replacer.remove_background(img.img)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error removing background from image: " + str(e))

    # replace background
    try:
        img_with_new_background = Replacer.replace_background(
            img_no_background,
            background_img.img,
            image.refine_foreground,
            margin_ratio=0.9,
            apply_alpha_threshold=True
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error replacing background in image: " + str(e))
    
    # Add a Frame to the image
    try:
        img_with_frame = Replacer.add_frame(
            img_with_new_background,
            frame_with_qr,
            frame_img.background_scale,
            frame_img.background_offset,
            frame_img.background_crop
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error adding frame to image: " + str(e))

    # save img_no_background
    img_no_background_for_db = IMG(img=img_no_background, type="no-background", gallery=img.gallery)
    img_no_background_for_db.db_save(db)
    g.db_add_image(db, img_no_background_for_db._id)

    # save img_with_new_background
    img_with_new_background_for_db = IMG(img=img_with_new_background, type="new-background", gallery=img.gallery)
    img_with_new_background_for_db.db_save(db)
    g.db_add_image(db, img_with_new_background_for_db._id)

    # save the processed image
    img_with_frame_for_db = IMG(img=img_with_frame, type="with-frame", gallery=img.gallery)
    img_with_frame_for_db.db_save(db)
    g.db_add_image(db, img_with_frame_for_db._id)

    # retrun new img id
    return ImageProcessResponse(
        img_no_background = ImageResponse(
            image_id=img_no_background_for_db._id,
            type=img_no_background_for_db.type,
            gallery=img_no_background_for_db.gallery
            ),
        img_new_background = ImageResponse(
            image_id=img_with_new_background_for_db._id,
            type=img_with_new_background_for_db.type,
            gallery=img_with_new_background_for_db.gallery
            ),
        img_with_frame = ImageResponse(
            image_id=img_with_frame_for_db._id,
            type=img_with_frame_for_db.type,
            gallery=img_with_frame_for_db.gallery
            )
    )


# ---------------------------
# Print Endpoints
# ---------------------------
# Print models
class PrintRequest(BaseModel):
    image_id: str

class PrintResponse(BaseModel):
    id: str
    number: int
    img_id: str
    created_at: datetime


@app.post(
    "/api/v1/print",
    response_model=PrintResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Print an image by its ID. The image must be in the database."
)
async def api_print_image(print_req: PrintRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> PrintResponse:
    db = session.mongodb_connection

    img = IMG.db_find(db, print_req.image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # create a printer queue item
    item = PrinterQueueItem(
        img_id=img._id,
        number=PrinterQueueItem.get_next_number(db)
    )
    item.db_save(db)

    return PrintResponse(id=item._id, number=item.number, created_at=item.created_at, img_id=item.img_id)

@app.get(
    "/api/v1/print",
    response_model=List[PrintResponse],
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve a list of all print jobs in the printer queue."
)
async def api_print_list(session: Session = Depends(auth(["boss", "printer"]))) -> List[PrintResponse]:
    db = session.mongodb_connection

    items = PrinterQueueItem.db_find_all(db)
    return_items: List[PrintResponse] = []
    for item in items:
        return_items.append(PrintResponse(id=item._id, number=item.number, created_at=item.created_at, img_id=item.img_id))

    return return_items

@app.delete(
    "/api/v1/print/{print_id}",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Remove a print job from the printer queue by its ID."
)
async def api_print_remove(print_id: str, session: Session = Depends(auth(["boss", "printer"]))) -> OK:
    db = session.mongodb_connection

    item = PrinterQueueItem.db_find(db, print_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Print job not found")

    item.db_delete(db)

    return OK(ok=True)

# clear all print jobs
@app.delete(
    "/api/v1/print",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Clear all print jobs from the printer queue."
)
async def api_print_clear(session: Session = Depends(auth(["boss"]))) -> OK:
    db = session.mongodb_connection

    PrinterQueueItem.clear_queue(db)

    return OK(ok=True)




















# ---------------------------
# Webpage
# ---------------------------
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

# Catch-all route: For any path, serve the index.html so React can handle routing.
@app.get(
    "/{full_path:path}",
    response_class=HTMLResponse,
    description="Catch-all route that serves the React application’s index.html for any unspecified path."
)
async def serve_react_app(full_path: str) -> FileResponse:
    index_path = os.path.join("frontend/dist", "index.html")
    return FileResponse(index_path)


# ---------------------------
# Main
# ---------------------------
async def main() -> None:
    # Configure the server (this does not call asyncio.run() internally)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    # Run the server and the old_img_eraser concurrently.
    await asyncio.gather(
        server.serve(),
        old_img_eraser()
    )

if __name__ == "__main__":
    asyncio.run(main())