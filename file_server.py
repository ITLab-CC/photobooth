from contextlib import asynccontextmanager
import io
import base64
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncIterator, List, Optional

from mongodb_manager import MongoDBManager
from gallery import Gallery
from img import IMG
from PIL import Image

# ---------------------------
# Shutdown Event
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        mongo_manager.close()

app = FastAPI(lifespan=lifespan)

# ---------------------------
# Authentication Dependencies
# ---------------------------
# For demo purposes, we use a fixed username/password and token.
FAKE_USERNAME = "user"
FAKE_PASSWORD = "password"
FAKE_TOKEN = "fake-token"

security = HTTPBearer()


def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    if token != FAKE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return token


# ---------------------------
# Request and Response Models
# ---------------------------

# Auth models
class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    token_type: str
    expires_in: int


# Gallery models
class GalleryCreateRequest(BaseModel):
    expiration_time: datetime


class GalleryUpdateRequest(BaseModel):
    expiration_time: datetime


class GalleryResponse(BaseModel):
    id: str
    creation_time: datetime
    expiration_time: datetime


class GalleriesListResponse(BaseModel):
    galleries: List[GalleryResponse]


# Image models
class ImageCreateRequest(BaseModel):
    name: str
    description: str
    img: str  # base64-encoded image data
    gallery_id: Optional[str] = None


class ImageUpdateRequest(BaseModel):
    name: str
    description: str
    img: str  # base64-encoded image data
    gallery_id: Optional[str] = None


class ImageResponse(BaseModel):
    id: str
    name: str
    description: str
    url: str
    gallery_id: Optional[str] = None


class ImagesListResponse(BaseModel):
    images: List[ImageResponse]


# ---------------------------
# Initialize MongoDB Manager
# ---------------------------
mongo_manager = MongoDBManager(
    mongo_uri="localhost:27017",
    user="root",
    password="example",
    db_name="photobooth",
    images_collection_name="images",
    background_collection_name="backgrounds",
    gallery_collection_name="galleries"
)


# ---------------------------
# Auth Endpoints
# ---------------------------
@app.post("/api/v1/auth/token", response_model=AuthResponse)
def login(auth: AuthRequest) -> AuthResponse:
    if auth.username == FAKE_USERNAME and auth.password == FAKE_PASSWORD:
        return AuthResponse(token=FAKE_TOKEN, token_type="Bearer", expires_in=3600)
    raise HTTPException(status_code=400, detail="Incorrect username or password")


# ---------------------------
# Health Endpoint
# ---------------------------
@app.get("/api/v1/health")
def health() -> dict:
    # For simplicity, always return "ok".
    return {"status": "ok"}


# ---------------------------
# Gallery Endpoints
# ---------------------------
@app.post("/api/v1/gallerys", response_model=GalleryResponse)
def create_gallery(gallery_req: GalleryCreateRequest, token: str = Depends(get_current_token)) -> GalleryResponse:
    creation_time = datetime.utcnow()
    gallery = Gallery(creation_time=creation_time, expiration_time=gallery_req.expiration_time)
    try:
        mongo_manager.store_gallery(gallery, collection_name="galleries")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return GalleryResponse(id=gallery.id, creation_time=gallery.creation_time, expiration_time=gallery.expiration_time)


@app.get("/api/v1/gallerys", response_model=GalleriesListResponse)
def list_galleries(token: str = Depends(get_current_token)) -> GalleriesListResponse:
    try:
        galleries = mongo_manager.get_all_galleries(collection_name="galleries")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    response_galleries = [
        GalleryResponse(id=gal.id, creation_time=gal.creation_time, expiration_time=gal.expiration_time)
        for gal in galleries
    ]
    return GalleriesListResponse(galleries=response_galleries)


@app.put("/api/v1/gallerys/{gallery_id}", response_model=GalleryResponse)
def update_gallery(gallery_id: str, gallery_req: GalleryUpdateRequest, token: str = Depends(get_current_token)) -> GalleryResponse:
    try:
        gallery = mongo_manager.load_gallery(gallery_id, collection_name="galleries")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    gallery.expiration_time = gallery_req.expiration_time
    try:
        mongo_manager.update_gallery(gallery, collection_name="galleries")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return GalleryResponse(id=gallery.id, creation_time=gallery.creation_time, expiration_time=gallery.expiration_time)


@app.delete("/api/v1/gallerys/{gallery_id}")
def delete_gallery(gallery_id: str, token: str = Depends(get_current_token)) -> dict:
    try:
        mongo_manager.remove_gallery(gallery_id, collection_name="galleries")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}


# ---------------------------
# Image Endpoints
# ---------------------------
@app.post("/api/v1/images", response_model=ImageResponse)
def create_image(image_req: ImageCreateRequest, token: str = Depends(get_current_token)) -> ImageResponse:
    try:
        # Decode the base64 image data.
        image_bytes = base64.b64decode(image_req.img)
        image_file = io.BytesIO(image_bytes)
        pil_image = Image.open(image_file).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data")
    
    img_obj = IMG(
        img=pil_image,
        name=image_req.name,
        description=image_req.description,
        gallery=image_req.gallery_id,
    )
    try:
        mongo_manager.store_img(img_obj, collection_name="images")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return ImageResponse(
        id=img_obj.id,
        name=img_obj.name,
        description=img_obj.description,
        url=f"/api/v1/images/{img_obj.id}",
        gallery_id=img_obj.gallery,
    )


@app.get("/api/v1/images", response_model=ImagesListResponse)
def list_images(token: str = Depends(get_current_token)) -> ImagesListResponse:
    try:
        imgs = mongo_manager.get_all_imgs(collection_name="images")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    response_images = [
        ImageResponse(
            id=img.id,
            name=img.name,
            description=img.description,
            url=f"/api/v1/images/{img.id}",
            gallery_id=img.gallery,
        )
        for img in imgs
    ]
    return ImagesListResponse(images=response_images)


@app.get("/api/v1/images/{image_id}")
def get_image(image_id: str, token: str = Depends(get_current_token)) -> StreamingResponse:
    try:
        img_obj = mongo_manager.load_img(image_id, collection_name="images")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Convert the PIL image to a PNG byte stream.
    img_bytes_io = io.BytesIO()
    img_obj.img.save(img_bytes_io, format="PNG")
    img_bytes_io.seek(0)
    return StreamingResponse(img_bytes_io, media_type="image/png")


@app.put("/api/v1/images/{image_id}", response_model=ImageResponse)
def update_image(image_id: str, image_req: ImageUpdateRequest, token: str = Depends(get_current_token)) -> ImageResponse:
    try:
        # Decode the base64 image data.
        image_bytes = base64.b64decode(image_req.img)
        image_file = io.BytesIO(image_bytes)
        pil_image = Image.open(image_file).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data")
    
    try:
        img_obj = mongo_manager.load_img(image_id, collection_name="images")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Update fields.
    img_obj.name = image_req.name
    img_obj.description = image_req.description
    img_obj.img = pil_image
    img_obj.gallery = image_req.gallery_id
    try:
        mongo_manager.update_img(img_obj, collection_name="images")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return ImageResponse(
        id=img_obj.id,
        name=img_obj.name,
        description=img_obj.description,
        url=f"/api/v1/images/{img_obj.id}",
        gallery_id=img_obj.gallery,
    )


@app.delete("/api/v1/images/{image_id}")
def delete_image(image_id: str, token: str = Depends(get_current_token)) -> dict:
    try:
        mongo_manager.remove_img(image_id, collection_name="images")
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ok"}


# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)