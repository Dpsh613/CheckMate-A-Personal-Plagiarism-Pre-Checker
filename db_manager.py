import os
import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_from_pdf, get_sliding_windows

DB_PATH = "./my_plagiarism_db"
client = chromadb.PersistentClient(path=DB_PATH)
model = SentenceTransformer('all-MiniLM-L6-v2') 

def get_user_collection(user_id):
    return client.get_or_create_collection(name=f"user_{user_id}_docs")

print("Database Model Loaded.")

def get_all_indexed_sources(user_id):
    """Returns sources currently embedded in ChromaDB, no PDFs needed."""
    collection = get_user_collection(user_id)
    try:
        data = collection.get(include=["metadatas"])
        if not data or not data["metadatas"]: return []
        sources = set(meta["source"] for meta in data["metadatas"])
        return list(sources)
    except:
        return []

def add_file_to_db(user_id, file_path, filename):
    print(f"Processing {filename} for user {user_id}...")
    collection = get_user_collection(user_id)
    pages_data = extract_text_from_pdf(file_path)
    if not pages_data:
        return False, "Extraction failed or PDF is empty."

    chunks_data = get_sliding_windows(pages_data)
    if not chunks_data:
        return False, "No valid text chunks found."

    documents = [item['text'] for item in chunks_data]
    metadatas = [{"source": filename, "page": item['page']} for item in chunks_data]
    ids = [f"{filename}_{i}" for i in range(len(chunks_data))]
    
    embeddings = model.encode(documents).tolist()

    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    return True, f"Successfully indexed {len(documents)} chunks."

def delete_source_from_db(user_id, filename):
    collection = get_user_collection(user_id)
    try:
        collection.delete(where={"source": filename})
        return True, f"Deleted vectors for {filename}."
    except Exception as e:
        return False, str(e)