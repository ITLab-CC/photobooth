from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import io
from math import ceil
import os
from typing import AsyncIterator, Dict, List, Optional, Union

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

from background import Background
from gallery import Gallery
from img import IMG
from process_img import IMGReplacer
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
# Values
# ---------------------------
GALLERY_EXPIRATION = timedelta(days=7)


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

class AuthUser(BaseModel):
    username: str
    last_login: Optional[datetime]
    roles: list[str]

class AuthResponse(BaseModel):
    token: str
    creation_date: datetime
    expiration_date: datetime
    user: AuthUser

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
        user=AuthUser(
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
        user=AuthUser(
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

class AuthSessionResponse(BaseModel):
    sessions: List[AuthResponse]

# get session
@app.get("/api/v1/auth/sessions", response_model=AuthSessionResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_auth_session(session: Session = Depends(auth)) -> AuthSessionResponse:
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

# logout a sepcific session
@app.get("/api/v1/auth/session/logout/{token}", response_model=OK, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def api_auth_session_logout(token: str, session: Session = Depends(auth)) -> OK:
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
@app.post("/api/v1/gallery", response_model=GalleryResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_create(gallery: Optional[GalleryRequest] = None) -> GalleryResponse:
    # system photo_booth
    db = System["photo_booth"]

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

@app.get("/api/v1/galleries", response_model=GalleryListResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_list(session: Session = Depends(auth)) -> GalleryListResponse:
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

@app.put("/api/v1/gallery/{gallery_id}/expiration", response_model=GalleryResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_change_expiration(gallery_id: str, expiration: GalleryExpirationRequest, session: Session = Depends(auth)) -> GalleryResponse:
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

@app.put("/api/v1/gallery/{gallery_id}/pin", response_model=GalleryResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_change_pin(gallery_id: str, pin: Optional[GalleryPinRequest] = None, session: Session = Depends(auth)) -> GalleryResponse:
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
@app.put("/api/v1/gallery/{gallery_id}/pin/set", response_model=GalleryResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_set_pin(gallery_id: str, pin: GalleryPinRequest) -> GalleryResponse:
    db = System["photo_booth"]

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
    gallery: str

@app.post("/api/v1/gallery/{gallery_id}/image", response_model=ResponseImage, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_add_image(gallery_id: str, image: GalleryImageRequest) -> ResponseImage:
    db = System["photo_booth"]

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

    return ResponseImage(image_id=img._id, gallery=img.gallery)

# get image with pin
@app.get("/api/v1/gallery/{gallery_id}/image/{image_id}/pin/{pin}", dependencies=[Depends(RateLimiter(times=1, seconds=1))])
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

# remove image
@app.delete("/api/v1/gallery/{gallery_id}/image/{image_id}", response_model=GalleryResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_remove_image(gallery_id: str, image_id: str, session: Session = Depends(auth)) -> GalleryResponse:
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

    return GalleryResponse(
        gallery_id=g._id,
        creation_time=g.creation_time,
        expiration_time=g.expiration_time,
        images=g.images,
        pin_set=True if g.pin_hash is not None else False
    )

# delete gallery
@app.delete("/api/v1/gallery/{gallery_id}", response_model=OK, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_gallery_delete(gallery_id: str, session: Session = Depends(auth)) -> OK:
    db = session.mongodb_connection

    g = Gallery.db_find(db, gallery_id)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # delete all images
    IMG.db_delete_by_gallery(db, gallery_id)

    g.db_delete(db)

    return OK(ok=True)


# ---------------------------
# Image Endpoints
# ---------------------------
# Image models
class ImageResponse(BaseModel):
    image_id: str
    gallery: Optional[str]

class ImageListResponse(BaseModel):
    images: List[ImageResponse]

# get all images
@app.get("/api/v1/images", response_model=ImageListResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_image_list(session: Session = Depends(auth)) -> ImageListResponse:
    db = session.mongodb_connection

    images = IMG.db_find_all(db)
    return_images: List[ImageResponse] = []
    for img in images:
        return_images.append(ImageResponse(
            image_id=img._id,
            gallery=img.gallery
        ))

    return ImageListResponse(images=return_images)

# get image
@app.get("/api/v1/image/{image_id}", dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_image_get(image_id: str, session: Session = Depends(auth)) -> StreamingResponse:
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

# add background
@app.post("/api/v1/background", response_model=BackgroundResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_background_add(background_img: BackgroundRequest, session: Session = Depends(auth)) -> BackgroundResponse:
    db = session.mongodb_connection

    try:
        img = Background.from_base64(background_img.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    img.db_save(db)

    return BackgroundResponse(background_id=img._id)

# get background
@app.get("/api/v1/background/{background_id}", response_model=BackgroundResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_background_get(background_id: str) -> StreamingResponse:
    db = System["img_viewer"]

    img = Background.db_find(db, background_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Background image not found")
    
    img_bytes_io = io.BytesIO()
    img.img.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)

    return StreamingResponse(content=img_bytes_io, media_type="image/png")

class BackgroundListResponse(BaseModel):
    backgrounds: List[BackgroundResponse]

# get all backgrounds
@app.get("/api/v1/backgrounds", response_model=BackgroundListResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_background_list() -> BackgroundListResponse:
    db = System["img_viewer"]

    backgrounds = Background.db_find_all(db)
    return_backgrounds: List[BackgroundResponse] = []
    for img in backgrounds:
        return_backgrounds.append(BackgroundResponse(
            background_id=img._id
        ))

    return BackgroundListResponse(backgrounds=return_backgrounds)

# delete background
@app.delete("/api/v1/background/{background_id}", response_model=OK, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_background_delete(background_id: str, session: Session = Depends(auth)) -> OK:
    db = session.mongodb_connection

    img = Background.db_find(db, background_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Background image not found")
    
    img.db_delete(db)

    return OK(ok=True)

# ---------------------------
# Img processing Endpoints
# ---------------------------
# Image processing models
class ImageProcessRequest(BaseModel):
    image_id: str
    image_background_id: str
    refine_foreground: bool = False

class ImageProcessResponse(BaseModel):
    image_id: str
    gallery: Optional[str]

# Load AI model for image processing
Replacer = IMGReplacer()

# process image
@app.post("/api/v1/image/process", response_model=ImageProcessResponse, dependencies=[Depends(RateLimiter(times=1, seconds=1))])
async def api_image_process(image: ImageProcessRequest) -> ImageProcessResponse:
    db = System["photo_booth"]

    # get the image
    img = IMG.db_find(db, image.image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # get the background image
    background_img = Background.db_find(db, image.image_background_id)
    if background_img is None:
        raise HTTPException(status_code=404, detail="Background image not found")

    # process the image
    try:
        processed_img = Replacer.replace_background(img.img, background_img.img, image.refine_foreground)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error processing image: " + str(e))
    
    # save the processed image
    processed_img_for_db = IMG(img=processed_img, gallery=img.gallery)
    processed_img_for_db.db_save(db)

    # add the processed image to the gallery
    g = Gallery.db_find(db, img.gallery)
    if g is None:
        raise HTTPException(status_code=404, detail="Gallery not found")
    
    g.db_add_image(db, processed_img_for_db._id)

    # retrun new img id
    return ImageProcessResponse(image_id=processed_img_for_db._id, gallery=processed_img_for_db.gallery)



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
    print("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
