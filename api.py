import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# --- IMPORT YOUR LOGIC ---
# This is the magic line. We import the function from checker.py
from checker import analyze_document

app = FastAPI()

# Enable CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "./temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.post("/analyze")
async def analyze_endpoint(file: UploadFile = File(...)):
    # 1. Validate
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # 2. Save Temp
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 3. CALL THE LOGIC (From checker.py)
        # We just pass the path, checker.py does all the heavy lifting
        results = analyze_document(file_path)
        
        # 4. Cleanup
        os.remove(file_path)
        
        # 5. Return JSON
        return JSONResponse(content=results)

    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)