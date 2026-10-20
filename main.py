import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import shutil
import torch
import time
from collections import deque
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
import uvicorn

from background import Background
from PIL import Image
from thumbnails import png_to_webp_thumbnail
from gallery import Gallery
from img import IMG
from frame import FRAME
from printer import PrinterQueueItem
from event_config import DEFAULT_START_TEXT, EventConfig
from process_img import IMGReplacer, resize_with_crop_or_pad
from face_smiley_replacer import replace_faces_with_smileys_dnn
from face_props import PROP_STYLES, apply_face_props
from looks import LOOKS, apply_look
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
            await asyncio.sleep(30)
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

# get image without pin (photo booth)
@app.get(
    "/api/v1/gallery/{gallery_id}/image/{image_id}",
    dependencies=[Depends(RateLimiter(times=50, seconds=1))],
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
    dependencies=[Depends(RateLimiter(times=100, seconds=1))],
    description="Retrieve a specific image by ID as PNG, or as a small WebP thumbnail with thumb=true. Responses are cacheable."
)
async def api_image_get(
    image_id: str,
    request: Request,
    thumb: bool = False,
    session: Session = Depends(auth(["boss", "photo_booth", "printer"]))
) -> Response:
    db = session.mongodb_connection

    # Photos never change after they are saved, so the id is a valid ETag.
    etag = f'"{image_id}-{"thumb" if thumb else "full"}"'
    cache_headers = {"ETag": etag, "Cache-Control": "private, max-age=3600, immutable"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=cache_headers)

    png_bytes = IMG.db_find_png_bytes(db, image_id)
    if png_bytes is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if thumb:
        return Response(content=png_to_webp_thumbnail(png_bytes), media_type="image/webp", headers=cache_headers)
    return Response(content=png_bytes, media_type="image/png", headers=cache_headers)


# ---------------------------
# Background Endpoints
# ---------------------------
# Background models
class BackgroundRequest(BaseModel):
    image_base64: str
    name: str = ""

class BackgroundResponse(BaseModel):
    background_id: str
    name: str = ""
    active: bool = True

class BackgroundPatchRequest(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None

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

    img.name = background_img.name.strip()
    img.db_save(db)

    return BackgroundResponse(background_id=img._id, name=img.name, active=img.active)

class BackgroundListResponse(BaseModel):
    backgrounds: List[BackgroundResponse]

# get all backgrounds
@app.get(
    "/api/v1/backgrounds",
    response_model=BackgroundListResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve all backgrounds (id, name, active flag). With only_active=true, hidden backgrounds are left out."
)
async def api_background_list(only_active: bool = False, session: Session = Depends(auth(["boss", "photo_booth"]))) -> BackgroundListResponse:
    db = session.mongodb_connection

    return_backgrounds: List[BackgroundResponse] = [
        BackgroundResponse(**meta)
        for meta in Background.db_find_meta(db, only_active=only_active)
    ]

    return BackgroundListResponse(backgrounds=return_backgrounds)

# get background
@app.get(
    "/api/v1/background/{background_id}",
    dependencies=[Depends(RateLimiter(times=100, seconds=1))],
    description="Retrieve a background image by its ID as PNG, or as a small WebP thumbnail with thumb=true. Responses are cacheable."
)
async def api_background_get(
    background_id: str,
    request: Request,
    thumb: bool = False,
    session: Session = Depends(auth(["boss", "photo_booth"]))
) -> Response:
    db = session.mongodb_connection

    # Backgrounds never change after upload, so the id is a valid ETag.
    etag = f'"{background_id}-{"thumb" if thumb else "full"}"'
    cache_headers = {"ETag": etag, "Cache-Control": "private, max-age=86400, immutable"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=cache_headers)

    if thumb:
        content = Background.db_find_thumbnail_bytes(db, background_id)
        media_type = "image/webp"
    else:
        content = Background.db_find_png_bytes(db, background_id)
        media_type = "image/png"

    if content is None:
        raise HTTPException(status_code=404, detail="Background image not found")

    return Response(content=content, media_type=media_type, headers=cache_headers)

# rename or (de)activate a background
@app.patch(
    "/api/v1/background/{background_id}",
    response_model=BackgroundResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=1))],
    description="Change the name or the active flag of a background. Inactive backgrounds are not offered to guests but stay in the archive."
)
async def api_background_patch(background_id: str, patch: BackgroundPatchRequest, session: Session = Depends(auth(["boss"]))) -> BackgroundResponse:
    db = session.mongodb_connection

    name = patch.name.strip() if patch.name is not None else None
    if not Background.db_set_meta(db, background_id, name=name, active=patch.active):
        raise HTTPException(status_code=404, detail="Background image not found")

    for meta in Background.db_find_meta(db):
        if meta["background_id"] == background_id:
            return BackgroundResponse(**meta)
    raise HTTPException(status_code=404, detail="Background image not found")

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
    background_scale: float = 1.0
    background_offset: Tuple[int, int] = (0, 0)
    background_crop: Tuple[int, int, int, int] = (0, 0, 0, 0)
    qr_position: Tuple[int, int] = (0, 0)
    qr_scale: float = 1.0
    is_active: bool = False


class FramePatchRequest(BaseModel):
    image_base64: Optional[str] = None
    background_scale: float = 1.0
    background_offset: Tuple[int, int] = (0, 0)
    background_crop: Tuple[int, int, int, int] = (0, 0, 0, 0)
    qr_position: Tuple[int, int] = (0, 0)
    qr_scale: float = 1.0


def _frame_to_response(img: FRAME) -> FrameResponse:
    crop = img.background_crop
    if isinstance(crop, int):
        crop = (crop, crop, crop, crop)
    return FrameResponse(
        frame_id=img._id,
        background_scale=img.background_scale,
        background_offset=(img.background_offset[0], img.background_offset[1]),
        background_crop=crop,
        qr_position=(img.qr_position[0], img.qr_position[1]),
        qr_scale=img.qr_scale,
        is_active=img.is_active,
    )


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

    return _frame_to_response(img)

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
    return FrameListResponse(frames=[_frame_to_response(img) for img in frames])


# update frame alignment (and optionally the image itself)
@app.patch(
    "/api/v1/frame/{frame_id}",
    response_model=FrameResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Update an existing frame's image and/or alignment values (scale/offset/crop/QR)."
)
async def api_frame_update(frame_id: str, patch: FramePatchRequest, session: Session = Depends(auth(["boss"]))) -> FrameResponse:
    db = session.mongodb_connection

    img = FRAME.db_find(db, frame_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Frame image not found")

    if patch.image_base64 is not None:
        try:
            new_img = FRAME.from_base64(patch.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        img.frame = new_img.frame

    img.background_scale = patch.background_scale
    img.background_offset = patch.background_offset
    img.background_crop = patch.background_crop
    img.qr_position = patch.qr_position
    img.qr_scale = patch.qr_scale
    img.db_update(db)

    return _frame_to_response(img)


# set a frame as the active one used by the kiosk
@app.post(
    "/api/v1/frame/{frame_id}/activate",
    response_model=OK,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Mark a frame as the active frame used by the kiosk. Unmarks all other frames."
)
async def api_frame_activate(frame_id: str, session: Session = Depends(auth(["boss"]))) -> OK:
    db = session.mongodb_connection

    img = FRAME.db_find(db, frame_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Frame image not found")

    FRAME.db_set_active(db, frame_id)

    return OK(ok=True)

# get frame
@app.get(
    "/api/v1/frame/{frame_id}",
    dependencies=[Depends(RateLimiter(times=20, seconds=1))],
    description="Retrieve a frame image by its ID and return it as a streaming PNG response."
)
async def api_frame_get(frame_id: str, request: Request, session: Session = Depends(auth(["boss", "photo_booth"]))) -> Response:
    db = session.mongodb_connection

    png_bytes = FRAME.db_find_png_bytes(db, frame_id)
    if png_bytes is None:
        raise HTTPException(status_code=404, detail="Frame image not found")

    # A frame image can be replaced via PATCH, so the ETag is derived from its content.
    etag = f'"{hashlib.md5(png_bytes).hexdigest()}"'
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)

    return Response(content=png_bytes, media_type="image/png", headers=headers)

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
# Settings Endpoints
# ---------------------------
# Default values used when no settings document has been saved yet.
# Kept in sync with the frontend's build-time fallbacks in frontend/src/config/event.ts.
SETTINGS_DEFAULTS = {
    "title": "IT-Lab 2026",
    "subtitle": "ENTEGA • Darmstadt",
    "brand_name": "ENTEGA",
    "pin_fail_redirect_url": "https://www.entega.ag/karriere/ausbildung-duales-studium-berufsorientierung/ausbildung/",
    "start_text": DEFAULT_START_TEXT,
    "has_logo": False,
}

MAX_LOGO_SIDE = 600


class SettingsRequest(BaseModel):
    title: str
    subtitle: str
    brand_name: str
    pin_fail_redirect_url: str
    start_text: str = DEFAULT_START_TEXT


class SettingsResponse(BaseModel):
    title: str
    subtitle: str
    brand_name: str
    pin_fail_redirect_url: str
    start_text: str = DEFAULT_START_TEXT
    has_logo: bool = False


def _settings_response(config: EventConfig, has_logo: bool) -> SettingsResponse:
    return SettingsResponse(
        title=config.title,
        subtitle=config.subtitle,
        brand_name=config.brand_name,
        pin_fail_redirect_url=config.pin_fail_redirect_url,
        start_text=config.start_text,
        has_logo=has_logo,
    )


@app.get(
    "/api/v1/settings",
    response_model=SettingsResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Retrieve the event title/branding settings. Returns built-in defaults if none have been saved yet."
)
async def api_settings_get(session: Session = Depends(auth(["boss", "photo_booth"]))) -> SettingsResponse:
    db = session.mongodb_connection

    config = EventConfig.db_find(db)
    if config is None:
        return SettingsResponse(**SETTINGS_DEFAULTS)

    return _settings_response(config, EventConfig.db_has_logo(db))


@app.put(
    "/api/v1/settings",
    response_model=SettingsResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Update the event title/branding settings (creates the settings document if it doesn't exist yet)."
)
async def api_settings_update(settings: SettingsRequest, session: Session = Depends(auth(["boss"]))) -> SettingsResponse:
    db = session.mongodb_connection

    existing = EventConfig.db_find(db)
    config = EventConfig(
        title=settings.title,
        subtitle=settings.subtitle,
        brand_name=settings.brand_name,
        pin_fail_redirect_url=settings.pin_fail_redirect_url,
        start_text=settings.start_text.strip() or DEFAULT_START_TEXT,
    )
    if existing is None:
        config.db_save(db)
    else:
        config.db_update(db)

    return _settings_response(config, EventConfig.db_has_logo(db))


class LogoRequest(BaseModel):
    image_base64: str


@app.put(
    "/api/v1/settings/logo",
    response_model=SettingsResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Upload an additional event logo shown next to the fixed IT-Lab logo on the photo booth. It is scaled down to at most 600 px and stored as PNG."
)
async def api_settings_logo_put(logo: LogoRequest, session: Session = Depends(auth(["boss"]))) -> SettingsResponse:
    db = session.mongodb_connection

    try:
        img = Image.open(io.BytesIO(base64.b64decode(logo.image_base64))).convert("RGBA")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image")
    img.thumbnail((MAX_LOGO_SIDE, MAX_LOGO_SIDE), Image.Resampling.LANCZOS)
    png = io.BytesIO()
    img.save(png, format="PNG")

    config = EventConfig.db_find(db)
    if config is None:
        config = EventConfig(**{k: v for k, v in SETTINGS_DEFAULTS.items() if k != "has_logo"})
        config.db_save(db)
    EventConfig.db_set_logo(db, png.getvalue())
    return _settings_response(config, True)


@app.delete(
    "/api/v1/settings/logo",
    response_model=SettingsResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=1))],
    description="Remove the uploaded event logo. The IT-Lab logo always stays."
)
async def api_settings_logo_delete(session: Session = Depends(auth(["boss"]))) -> SettingsResponse:
    db = session.mongodb_connection

    EventConfig.db_set_logo(db, None)
    config = EventConfig.db_find(db) or EventConfig(**{k: v for k, v in SETTINGS_DEFAULTS.items() if k != "has_logo"})
    return _settings_response(config, False)


@app.get(
    "/api/v1/settings/logo",
    dependencies=[Depends(RateLimiter(times=5, seconds=1))],
    description="The uploaded event logo as PNG, or 404 if none was uploaded."
)
async def api_settings_logo_get(session: Session = Depends(auth(["boss", "photo_booth"]))) -> Response:
    db = session.mongodb_connection

    png = EventConfig.db_find_logo(db)
    if png is None:
        raise HTTPException(status_code=404, detail="No logo uploaded")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "private, no-cache"})


# ---------------------------
# Img processing Endpoints
# ---------------------------
# Image processing models
class ImageProcessRequest(BaseModel):
    image_id: str
    image_background_id: Optional[str] = None
    img_frame_id: str
    refine_foreground: bool = False
    random_stuff: bool = False
    light_match: bool = True  # adapt the person's light to the new background
    look: str = "none"  # one of looks.LOOKS: filters or neural styles applied to the whole photo
    magic_style: str = "smileys"  # "smileys" or one of face_props.PROP_STYLES

class ProcessingStats:
    """In-memory counters for the dashboard. Nothing about the photos is stored."""
    day: str = ""
    photos: int = 0
    magic_photos: int = 0
    durations: "deque[float]" = deque(maxlen=50)

    @classmethod
    def record(cls, seconds: float, magic: bool) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if cls.day != today:
            cls.day = today
            cls.photos = 0
            cls.magic_photos = 0
        cls.photos += 1
        if magic:
            cls.magic_photos += 1
        cls.durations.append(seconds)

class ImageProcessResponse(BaseModel):
    img_no_background: Optional[ImageResponse] = None
    img_new_background: ImageResponse
    img_with_frame: ImageResponse

# Load AI model for image processing
Replacer = IMGReplacer()

@app.post(
    "/api/v1/image/process",
    response_model=ImageProcessResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=1))],
    description="Process an image by replacing its background using an AI model. Requires the target image ID and a background image ID. Optionally refine the foreground."
)
async def api_image_process(image: ImageProcessRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> ImageProcessResponse:
    db = session.mongodb_connection
    started_at = time.perf_counter()

    if image.magic_style != "smileys" and image.magic_style not in PROP_STYLES:
        raise HTTPException(status_code=400, detail=f"Unknown magic_style: {image.magic_style}")
    if image.look not in LOOKS:
        raise HTTPException(status_code=400, detail=f"Unknown look: {image.look}")

    # get the image
    img = IMG.db_find(db, image.image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # add the processed image to the gallery
    g = Gallery.db_find(db, img.gallery)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # get the background image
    if image.image_background_id is not None:
        background_img = Background.db_find(db, image.image_background_id)
        if background_img is None:
            raise HTTPException(status_code=404, detail="Background image not found")
    else:
        background_img = None

    # get the frame
    frame_img = FRAME.db_find(db, image.img_frame_id)
    if frame_img is None:
        raise HTTPException(status_code=404, detail="Frame image not found")

    frame_with_qr = frame_img.frame

    # remove background
    if background_img is not None:
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
                apply_alpha_threshold=True,
                light_match=image.light_match
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error replacing background in image: " + str(e))
    else:
        # Dont replace the background but resize it to the size of the background image

        # get the size of the first background image
        # get any background image
        back_image_ids = Background.db_find_ids(db)
        if len(back_image_ids) == 0:
            raise HTTPException(status_code=404, detail="No background images found")

        first_background_img = Background.db_find(db, back_image_ids[0])
        if first_background_img is None:
            raise HTTPException(status_code=404, detail="No background images found")
        x_size, y_size = first_background_img.img.size

        # resize the image
        img_with_new_background = resize_with_crop_or_pad(img.img, (x_size, y_size))


    # magic: replace faces with smileys or put props (sunglasses, hats, crowns) on them
    if image.random_stuff:
        try:
            if image.magic_style == "smileys":
                img_with_new_background = replace_faces_with_smileys_dnn(
                    img_with_new_background
                    )
            else:
                img_with_new_background = apply_face_props(
                    img_with_new_background,
                    image.magic_style
                    )
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error applying magic to image: " + str(e))

    # look: artistic filter or neural style over the whole photo, before the frame is added
    if image.look != "none":
        try:
            img_with_new_background = apply_look(img_with_new_background, image.look)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Error applying look to image: " + str(e))

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
    img_no_background_return = None
    if background_img is not None:
        img_no_background_for_db = IMG(img=img_no_background, type="no-background", gallery=img.gallery)
        img_no_background_for_db.db_save(db)
        g.db_add_image(db, img_no_background_for_db._id)
        img_no_background_return = ImageResponse(
            image_id=img_no_background_for_db._id,
            type=img_no_background_for_db.type,
            gallery=img_no_background_for_db.gallery
        )

    # save img_with_new_background
    img_with_new_background_for_db = IMG(img=img_with_new_background, type="new-background", gallery=img.gallery)
    img_with_new_background_for_db.db_save(db)
    g.db_add_image(db, img_with_new_background_for_db._id)

    # save the processed image
    img_with_frame_for_db = IMG(img=img_with_frame, type="with-frame", gallery=img.gallery)
    img_with_frame_for_db.db_save(db)
    g.db_add_image(db, img_with_frame_for_db._id)

    ProcessingStats.record(time.perf_counter() - started_at, magic=image.random_stuff)

    # retrun new img id
    return ImageProcessResponse(
        img_no_background = img_no_background_return,
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
    amount: int = 1

class PrintResponse(BaseModel):
    id: str
    number: int
    img_id: str
    created_at: datetime


@app.post(
    "/api/v1/print",
    response_model=PrintResponse,
    dependencies=[Depends(RateLimiter(times=2, seconds=1))],
    description="Print an image by its ID. The image must be in the database."
)
async def api_print_image(print_req: PrintRequest, session: Session = Depends(auth(["boss", "photo_booth"]))) -> PrintResponse:
    db = session.mongodb_connection

    img = IMG.db_find(db, print_req.image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")

    # create a printer queue item
    for _ in range(print_req.amount):
        item = PrinterQueueItem(
            img_id=img._id,
            number=PrinterQueueItem.get_next_number(db)
        )
        item.db_save(db)

    return PrintResponse(id=item._id, number=item.number, created_at=item.created_at, img_id=item.img_id)

@app.get(
    "/api/v1/print",
    response_model=List[PrintResponse],
    dependencies=[Depends(RateLimiter(times=2, seconds=1))],
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
    dependencies=[Depends(RateLimiter(times=2, seconds=1))],
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
    dependencies=[Depends(RateLimiter(times=2, seconds=1))],
    description="Clear all print jobs from the printer queue."
)
async def api_print_clear(session: Session = Depends(auth(["boss"]))) -> OK:
    db = session.mongodb_connection

    PrinterQueueItem.clear_queue(db)

    return OK(ok=True)





















# ---------------------------
# Health Endpoint
# ---------------------------
class HealthCheck(BaseModel):
    ok: bool
    detail: str

class HealthResponse(BaseModel):
    database: HealthCheck
    gpu: HealthCheck
    model: HealthCheck
    disk: HealthCheck
    print_queue: HealthCheck
    backgrounds_total: int
    backgrounds_active: int
    photos_today: int
    magic_photos_today: int
    avg_processing_seconds: Optional[float] = None

@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    dependencies=[Depends(RateLimiter(times=2, seconds=1))],
    description="Status of database, GPU, AI model, disk and print queue plus simple counters for the admin dashboard."
)
async def api_health(session: Session = Depends(auth(["boss"]))) -> HealthResponse:
    db = session.mongodb_connection

    try:
        db.db.command("ping")
        database = HealthCheck(ok=True, detail="Verbunden")
    except Exception as e:
        database = HealthCheck(ok=False, detail=f"Nicht erreichbar: {e}")

    cuda = torch.cuda.is_available()
    gpu = HealthCheck(ok=cuda, detail=torch.cuda.get_device_name(0) if cuda else "Keine GPU, KI läuft langsam auf der CPU")
    model = HealthCheck(ok=Replacer.model is not None, detail="Geladen" if Replacer.model is not None else "Nicht geladen")

    free_gb = shutil.disk_usage("/").free / 1024**3
    disk = HealthCheck(ok=free_gb >= 5, detail=f"{free_gb:.1f} GB frei")

    try:
        jobs = PrinterQueueItem.db_find_all(db)
        if jobs:
            oldest = min(job.created_at for job in jobs)
            waiting_minutes = (datetime.now() - oldest.replace(tzinfo=None)).total_seconds() / 60
            print_queue = HealthCheck(
                ok=waiting_minutes < 10,
                detail=f"{len(jobs)} Auftrag/Aufträge, ältester wartet {waiting_minutes:.0f} min"
            )
        else:
            print_queue = HealthCheck(ok=True, detail="Warteschlange leer")
    except Exception as e:
        print_queue = HealthCheck(ok=False, detail=f"Nicht lesbar: {e}")

    try:
        metas = Background.db_find_meta(db)
    except Exception:
        metas = []

    durations = list(ProcessingStats.durations)
    return HealthResponse(
        database=database,
        gpu=gpu,
        model=model,
        disk=disk,
        print_queue=print_queue,
        backgrounds_total=len(metas),
        backgrounds_active=sum(1 for m in metas if m["active"]),
        photos_today=ProcessingStats.photos if ProcessingStats.day == datetime.now().strftime("%Y-%m-%d") else 0,
        magic_photos_today=ProcessingStats.magic_photos if ProcessingStats.day == datetime.now().strftime("%Y-%m-%d") else 0,
        avg_processing_seconds=round(sum(durations) / len(durations), 1) if durations else None,
    )

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
    config = uvicorn.Config(app, host="0.0.0.0", port=8085, log_level="info")
    server = uvicorn.Server(config)
    # Run the server and the old_img_eraser concurrently.
    await asyncio.gather(
        server.serve(),
        old_img_eraser()
    )

if __name__ == "__main__":
    asyncio.run(main())