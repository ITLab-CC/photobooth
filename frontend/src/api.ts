/* 
   Übersicht aller Endpunkte (laut Python-Backend):

   1) Auth:
      - POST   /api/v1/auth/token
      - GET    /api/v1/auth/status
      - GET    /api/v1/auth/logout
      - GET    /api/v1/auth/sessions
      - GET    /api/v1/auth/session/logout/{token}

   2) Gallery:
      - POST   /api/v1/gallery
      - GET    /api/v1/galleries
      - PUT    /api/v1/gallery/{gallery_id}/expiration
      - PUT    /api/v1/gallery/{gallery_id}/pin
      - PUT    /api/v1/gallery/{gallery_id}/pin/set
      - POST   /api/v1/gallery/{gallery_id}/image
      - GET    /api/v1/gallery/{gallery_id}/qr
      - GET    /api/v1/gallery/{gallery_id}/images/pin/{pin}
      - GET    /api/v1/gallery/{gallery_id}/image/{image_id}/pin/{pin}
      - DELETE /api/v1/gallery/{gallery_id}/image/{image_id}
      - DELETE /api/v1/gallery/{gallery_id}
      - DELETE /api/v1/gallery/{gallery_id}/pin/{pin}

   3) Image:
      - GET    /api/v1/images
      - GET    /api/v1/image/{image_id}

   4) Background:
      - POST   /api/v1/background
      - GET    /api/v1/backgrounds
      - GET    /api/v1/background/{background_id}
      - DELETE /api/v1/background/{background_id}

   5) Image Processing:
      - POST   /api/v1/image/process

   6) Print:
      - POST   /api/v1/print
      - GET    /api/v1/print
      - DELETE /api/v1/print/{print_id}
      - DELETE /api/v1/print
*/

const BASE_URL = "https://photo.it-lab.cc"; 

async function request<T>(
  method: string,
  url: string,
  token?: string,
  body?: any
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${url}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Fehler bei ${method} ${url}: ` + errorText);
  }

  return (await res.json()) as T;
}

// =============== 1) Auth-Interfaces & Funktionen ===============
export interface AuthRequest {
  username: string;
  password: string;
}

export interface AuthUser {
  username: string;
  last_login?: string; 
  roles: string[];
}

export interface AuthResponse {
  token: string;
  creation_date: string;   
  expiration_date: string; 
  user: AuthUser;
}

export interface AuthSession {
  token: string;
  creation_date: string;
  expiration_date: string;
  user: AuthUser;
}
export interface AuthSessionResponse {
  sessions: AuthSession[];
}

// 1.1) POST /api/v1/auth/token
export async function login(
  username: string,
  password: string
): Promise<AuthResponse> {
  return await request<AuthResponse>("POST", "/api/v1/auth/token", undefined, {
    username,
    password,
  });
}

// 1.2) GET /api/v1/auth/status
export async function getAuthStatus(token: string): Promise<AuthResponse> {
  return await request<AuthResponse>("GET", "/api/v1/auth/status", token);
}

// 1.3) GET /api/v1/auth/logout
export async function logout(token: string): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>("GET", "/api/v1/auth/logout", token);
}

// 1.4) GET /api/v1/auth/sessions
export async function getSessions(token: string): Promise<AuthSessionResponse> {
  return await request<AuthSessionResponse>(
    "GET",
    "/api/v1/auth/sessions",
    token
  );
}

// 1.5) GET /api/v1/auth/session/logout/{token}
export async function logoutSession(
  adminToken: string,
  sessionTokenToLogout: string
): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>(
    "GET",
    `/api/v1/auth/session/logout/${sessionTokenToLogout}`,
    adminToken
  );
}

// =============== 2) Gallery-Interfaces & Funktionen ===============
export interface GalleryRequest {
  expiration_time?: string; // ISO-String
  images?: string[];
  pin?: string;
}

export interface GalleryResponse {
  gallery_id: string;
  creation_time: string;   // ISO-String
  expiration_time: string; // ISO-String
  images: string[];
  pin_set: boolean;
}

export interface GalleryListResponse {
  galleries: GalleryResponse[];
}

export interface GalleryPinRequest {
  pin?: string | null;
}

export interface ResponseImage {
  image_id: string;
  gallery: string;
}
export interface GalleryImageListResponse {
  images: ResponseImage[];
}

export interface GalleryExpirationRequest {
  expiration_time: string; // ISO-String
}

// 2.1) POST /api/v1/gallery
export async function createGallery(
  token: string,
  payload?: GalleryRequest
): Promise<GalleryResponse> {
  return await request<GalleryResponse>("POST", "/api/v1/gallery", token, payload);
}

// 2.2) GET /api/v1/galleries
export async function listGalleries(token: string): Promise<GalleryListResponse> {
  return await request<GalleryListResponse>("GET", "/api/v1/galleries", token);
}

// 2.3) PUT /api/v1/gallery/{gallery_id}/expiration
export async function updateGalleryExpiration(
  token: string,
  galleryId: string,
  expirationTime: string // ISO-String
): Promise<GalleryResponse> {
  const body: GalleryExpirationRequest = { expiration_time: expirationTime };
  return await request<GalleryResponse>(
    "PUT",
    `/api/v1/gallery/${galleryId}/expiration`,
    token,
    body
  );
}

// 2.4) PUT /api/v1/gallery/{gallery_id}/pin
export async function updateGalleryPin(
  token: string,
  galleryId: string,
  newPin: string
): Promise<GalleryResponse> {
  const body: GalleryPinRequest = { pin: newPin };
  return await request<GalleryResponse>(
    "PUT",
    `/api/v1/gallery/${galleryId}/pin`,
    token,
    body
  );
}

// 2.5) PUT /api/v1/gallery/{gallery_id}/pin/set
export async function setGalleryPin(
  token: string,
  galleryId: string,
  pin: string
): Promise<GalleryResponse> {
  const body: GalleryPinRequest = { pin };
  return await request<GalleryResponse>(
    "PUT",
    `/api/v1/gallery/${galleryId}/pin/set`,
    token,
    body
  );
}

// 2.6) POST /api/v1/gallery/{gallery_id}/image
export interface GalleryImageRequest {
  image_base64: string;
}
export interface GalleryImageResponse {
  image_id: string;
  gallery: string;
}
export async function addGalleryImage(
  token: string,
  galleryId: string,
  base64: string,
  pin?: string // optional, wenn euer Endpoint es zulässt
): Promise<GalleryImageResponse> {
  // Evtl. muss der pin in den Body oder Query-Param? 
  // Im Code oben sieht man, dass der pin in den Body kommt, 
  // aber es kann je nach Implementierung variieren.
  const body: any = { image_base64: base64 };
  if (pin) {
    body.pin = pin;
  }
  return await request<GalleryImageResponse>(
    "POST",
    `/api/v1/gallery/${galleryId}/image`,
    token,
    body
  );
}

// 2.7) GET /api/v1/gallery/{gallery_id}/qr
// Gibt ein StreamingResponse (PNG) zurück – hier ein Blob
export async function getGalleryQR(token: string, galleryId: string): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/api/v1/gallery/${galleryId}/qr`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Fehler beim Laden des QR-Codes`);
  }
  return await res.blob();
}

// 2.8) GET /api/v1/gallery/{gallery_id}/images/pin/{pin}
export async function getGalleryImagesByPin(
  galleryId: string,
  pin: string
): Promise<GalleryImageListResponse> {
  // Hier kein Token nötig, da laut Code "img_viewer" oder Public?
  // Dein Python-Code nutzt "img_viewer", also nur Basic-Call:
  const res = await fetch(`${BASE_URL}/api/v1/gallery/${galleryId}/images/pin/${pin}`);
  if (!res.ok) {
    throw new Error(`Fehler beim Laden der Galerie-Bilder (PIN)`);
  }
  return await res.json();
}

// 2.9) GET /api/v1/gallery/{gallery_id}/image/{image_id}/pin/{pin}
// Gibt ein PNG-Stream zurück
export async function getGalleryImageByPin(
  galleryId: string,
  imageId: string,
  pin: string
): Promise<Blob> {
  const res = await fetch(
    `${BASE_URL}/api/v1/gallery/${galleryId}/image/${imageId}/pin/${pin}`
  );
  if (!res.ok) {
    throw new Error(`Fehler beim Laden eines Bildes (PIN)`);
  }
  return await res.blob();
}

// 2.10) DELETE /api/v1/gallery/{gallery_id}/image/{image_id}
export async function deleteGalleryImage(
  token: string,
  galleryId: string,
  imageId: string
): Promise<GalleryResponse> {
  return await request<GalleryResponse>(
    "DELETE",
    `/api/v1/gallery/${galleryId}/image/${imageId}`,
    token
  );
}

// 2.11) DELETE /api/v1/gallery/{gallery_id}
export async function deleteGallery(
  token: string,
  galleryId: string
): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>(
    "DELETE",
    `/api/v1/gallery/${galleryId}`,
    token
  );
}

// 2.12) DELETE /api/v1/gallery/{gallery_id}/pin/{pin}
export async function deleteGalleryWithPin(
  galleryId: string,
  pin: string
): Promise<{ ok: boolean }> {
  // Laut Backend kein Token nötig, da es nur den Pin prüft
  const res = await fetch(
    `${BASE_URL}/api/v1/gallery/${galleryId}/pin/${pin}`,
    { method: "DELETE" }
  );
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`Fehler bei Galerie-Löschung mit PIN: ${errorText}`);
  }
  return await res.json();
}

// =============== 3) Image-Interfaces & Funktionen ===============
export interface ImageListResponse {
  images: {
    image_id: string;
    gallery: string | null;
  }[];
}

// 3.1) GET /api/v1/images
export async function listImages(token: string): Promise<ImageListResponse> {
  return await request<ImageListResponse>("GET", "/api/v1/images", token);
}

// 3.2) GET /api/v1/image/{image_id}
// Gibt ein PNG-Stream zurück
export async function getImage(token: string, imageId: string): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/api/v1/image/${imageId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Fehler beim Laden eines Bildes`);
  }
  return await res.blob();
}

// =============== 4) Background-Interfaces & Funktionen ===============
export interface BackgroundRequest {
  image_base64: string;
}
export interface BackgroundResponse {
  background_id: string;
}
export interface BackgroundListResponse {
  backgrounds: BackgroundResponse[];
}

// 4.1) POST /api/v1/background
export async function createBackground(
  token: string,
  base64: string
): Promise<BackgroundResponse> {
  return await request<BackgroundResponse>(
    "POST",
    "/api/v1/background",
    token,
    { image_base64: base64 }
  );
}

// 4.2) GET /api/v1/backgrounds
export async function listBackgrounds(token: string): Promise<BackgroundListResponse> {
  return await request<BackgroundListResponse>("GET", "/api/v1/backgrounds", token);
}

// 4.3) GET /api/v1/background/{background_id}
// Gibt ein PNG-Stream zurück
export async function getBackground(
  token: string,
  backgroundId: string
): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/api/v1/background/${backgroundId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Fehler beim Laden eines Background-Bildes`);
  }
  return await res.blob();
}

// 4.4) DELETE /api/v1/background/{background_id}
export async function deleteBackground(
  token: string,
  backgroundId: string
): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>(
    "DELETE",
    `/api/v1/background/${backgroundId}`,
    token
  );
}

// =============== 5) Image Processing ===============
// POST /api/v1/image/process
export interface ImageProcessRequest {
  image_id: string;
  image_background_id: string;
  refine_foreground?: boolean;
}
export interface ImageProcessResponse {
  image_id: string;
  gallery?: string;
}

export async function processImage(
  token: string,
  payload: ImageProcessRequest
): Promise<ImageProcessResponse> {
  return await request<ImageProcessResponse>(
    "POST",
    "/api/v1/image/process",
    token,
    payload
  );
}

// =============== 6) Print ===============
// 6.1) POST /api/v1/print
export interface PrintRequest {
  image_id: string;
  amount?: number;
}
export interface PrintResponse {
  id: string;
  number: number;
  img_id: string;
  created_at: string;
}

export async function printImage(
  token: string,
  imageId: string,
  amount: number = 1
): Promise<PrintResponse> {
  const body: PrintRequest = { image_id: imageId, amount };
  return await request<PrintResponse>("POST", "/api/v1/print", token, body);
}

// 6.2) GET /api/v1/print
export async function listPrintJobs(token: string): Promise<PrintResponse[]> {
  return await request<PrintResponse[]>("GET", "/api/v1/print", token);
}

// 6.3) DELETE /api/v1/print/{print_id}
export async function deletePrintJob(
  token: string,
  printId: string
): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>(
    "DELETE",
    `/api/v1/print/${printId}`,
    token
  );
}

// 6.4) DELETE /api/v1/print
export async function clearPrintQueue(token: string): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>("DELETE", "/api/v1/print", token);
}


// =============== 7) Frame ===============
export interface FrameRequest {
  image_base64: string;
}

export interface FrameResponse {
  frame_id: string;
}

export interface FrameListResponse {
  frames: FrameResponse[];
}

// 7.1) POST /api/v1/frames
export async function createFrame(
  token: string,
  base64: string
): Promise<FrameResponse> {
  return await request<FrameResponse>("POST", "/api/v1/frame", token, {
    image_base64: base64,
  });
}

// 7.2) GET /api/v1/frames
export async function listFrames(token: string): Promise<FrameListResponse> {
  return await request<FrameListResponse>("GET", "/api/v1/frames", token);
}

// 7.3) GET /api/v1/frame/{frame_id}
// Gibt ein PNG-Stream (oder anderes Bildformat) zurück
export async function getFrame(
  token: string,
  frameId: string
): Promise<Blob> {
  const res = await fetch(`${BASE_URL}/api/v1/frame/${frameId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error(`Fehler beim Laden eines Frame-Bildes`);
  }
  return await res.blob();
}

// 7.4) DELETE /api/v1/frame/{frame_id}
export async function deleteFrame(
  token: string,
  frameId: string
): Promise<{ ok: boolean }> {
  return await request<{ ok: boolean }>(
    "DELETE",
    `/api/v1/frame/${frameId}`,
    token
  );
}
