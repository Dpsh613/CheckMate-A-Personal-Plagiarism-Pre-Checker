import os
import shutil
import uvicorn
import jwt
import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from checker import analyze_document
from db_manager import add_file_to_db, delete_source_from_db, get_all_indexed_sources
from arxiv_manager import search_arxiv_metadata, download_specific_arxiv_paper
from auth_db import create_user, get_user_by_email, verify_password, create_verification_token, verify_user_token, create_password_reset_token, reset_password_with_token
from email_service import send_verification_email, send_password_reset_email

load_dotenv()

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

FRONTEND_URLS = os.getenv("FRONTEND_URLS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

# CORS Lockdown
app.add_middleware(
    CORSMiddleware,
    allow_origins=[url.strip() for url in FRONTEND_URLS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

UPLOAD_FOLDER = "./temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

class UserAuthRequest(BaseModel):
    email: str
    password: str

class UserPasswordResetRequest(BaseModel):
    token: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ArxivDownloadRequest(BaseModel):
    pdf_url: str
    title: str

@app.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, user: UserAuthRequest):
    success, msg = create_user(user.email, user.password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    token = create_verification_token(user.email)
    email_sent = send_verification_email(user.email, token)
    
    if not email_sent:
        return {"status": "success", "message": "Account created, but failed to send verification email."}
        
    return {"status": "success", "message": "Account created! Please check your email to verify."}

@app.get("/verify")
@limiter.limit("10/minute")
async def verify_email(request: Request, token: str):
    success, msg = verify_user_token(token)
    if not success:
        return HTMLResponse(content=f"<html><body><h2>Verification Failed</h2><p>{msg}</p></body></html>", status_code=400)
    
    return HTMLResponse(content="<html><body><h2>Verification Successful!</h2><p>You can now close this window and log in to CheckMate.</p></body></html>")

@app.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, response: Response, user: UserAuthRequest):
    db_user = get_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not db_user["is_verified"]:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")
        
    token = create_access_token(data={"sub": db_user["id"]})
    
    # Set HttpOnly Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60, # 7 days in seconds
        secure=False # Set to True in production with HTTPS
    )
    
    return {"status": "success", "email": user.email}

@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return {"status": "success", "message": "Logged out successfully"}

@app.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, req: ForgotPasswordRequest):
    # Always return a generic success message to prevent email enumeration
    user = get_user_by_email(req.email)
    if user:
        token = create_password_reset_token(req.email)
        send_password_reset_email(req.email, token)
    return {"status": "success", "message": "If an account with that email exists, we have sent a password reset link."}

@app.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, req: UserPasswordResetRequest):
    success, msg = reset_password_with_token(req.token, req.new_password)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": "Password successfully reset. You can now log in."}

@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_endpoint(request: Request, file: UploadFile = File(...), user_id: int = Depends(get_current_user)):
    # Security: File Extension Validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".txt"]:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are allowed.")
    
    # Security: UUID Filename Renaming to prevent Path Traversal
    safe_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    
    # Security: Chunked read to prevent Memory Exhaustion DoS
    MAX_SIZE = 5 * 1024 * 1024
    total_size = 0
    
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024): # 1MB chunks
            total_size += len(chunk)
            if total_size > MAX_SIZE:
                os.remove(file_path)
                raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")
            buffer.write(chunk)
        
    try:
        results = analyze_document(user_id, file_path)
        return JSONResponse(content=results)
    finally:
        if os.path.exists(file_path): os.remove(file_path)

@app.get("/database/files")
@limiter.limit("20/minute")
async def get_files(request: Request, user_id: int = Depends(get_current_user)):
    files = get_all_indexed_sources(user_id)
    return {"files": files}

@app.delete("/database/files/{filename}")
@limiter.limit("20/minute")
async def delete_from_db(request: Request, filename: str, user_id: int = Depends(get_current_user)):
    success, msg = delete_source_from_db(user_id, filename)
    return {"status": "success", "message": msg}

@app.get("/arxiv/search")
@limiter.limit("10/minute")
async def search_arxiv(request: Request, topic: str, user_id: int = Depends(get_current_user)):
    results = search_arxiv_metadata(topic)
    return {"results": results}

@app.post("/arxiv/download")
@limiter.limit("5/minute")
async def download_arxiv(request: Request, req: ArxivDownloadRequest, user_id: int = Depends(get_current_user)):
    success, msg = download_specific_arxiv_paper(req.pdf_url, req.title, lambda fpath, fname: add_file_to_db(user_id, fpath, fname))
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "success", "message": msg}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)