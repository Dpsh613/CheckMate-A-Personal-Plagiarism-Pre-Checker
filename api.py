import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# IMPORT LOGIC
from checker import analyze_document
from db_manager import add_file_to_db, delete_file_from_db, get_all_files_in_db

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# SETUP FOLDERS
UPLOAD_FOLDER = "./temp_uploads"
DATASET_FOLDER = "dataset_pdfs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATASET_FOLDER, exist_ok=True)

# --- 1. EXISTING ENDPOINT (Analyze) ---
@app.post("/analyze")
async def analyze_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # analyze_document now handles model loading internally
        results = analyze_document(file_path)
        return JSONResponse(content=results)
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Robust cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

# --- 2. NEW: GET FILES LIST ---
@app.get("/database/files")
async def get_files():
    files = get_all_files_in_db()
    return {"files": files}

# --- 3. NEW: UPLOAD TO DATABASE ---
@app.post("/database/upload")
async def upload_to_db(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    file_path = os.path.join(DATASET_FOLDER, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Removed 'global_model' argument to match new db_manager logic
        success, message = add_file_to_db(file_path, file.filename)
        return {"status": "success", "message": message, "filename": file.filename}
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. NEW: DELETE FROM DATABASE ---
@app.delete("/database/files/{filename}")
async def delete_from_db(filename: str):
    try:
        success, message = delete_file_from_db(filename)
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)