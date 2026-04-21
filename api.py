import os
import shutil
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from checker import analyze_document
from db_manager import add_file_to_db, delete_source_from_db, get_all_indexed_sources
from arxiv_manager import search_arxiv_metadata, download_specific_arxiv_paper

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "./temp_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class ArxivDownloadRequest(BaseModel):
    pdf_url: str
    title: str

@app.post("/analyze")
async def analyze_endpoint(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        results = analyze_document(file_path)
        return JSONResponse(content=results)
    finally:
        if os.path.exists(file_path): os.remove(file_path)

@app.get("/database/files")
async def get_files():
    files = get_all_indexed_sources()
    return {"files": files}

@app.delete("/database/files/{filename}")
async def delete_from_db(filename: str):
    success, msg = delete_source_from_db(filename)
    return {"status": "success", "message": msg}

@app.get("/arxiv/search")
async def search_arxiv(topic: str):
    results = search_arxiv_metadata(topic)
    return {"results": results}

@app.post("/arxiv/download")
async def download_arxiv(req: ArxivDownloadRequest):
    success, msg = download_specific_arxiv_paper(req.pdf_url, req.title, add_file_to_db)
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "success", "message": msg}

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)