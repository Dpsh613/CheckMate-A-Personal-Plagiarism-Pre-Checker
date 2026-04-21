import os
import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_from_pdf, get_sliding_windows

DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"

print("⏳ Loading Database Model...")
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)
model = SentenceTransformer('all-MiniLM-L6-v2') 
print("✅ Database Model Loaded.")

def get_all_indexed_sources():
    """Returns sources currently embedded in ChromaDB, no PDFs needed."""
    try:
        data = collection.get(include=["metadatas"])
        if not data or not data["metadatas"]: return []
        sources = set(meta["source"] for meta in data["metadatas"])
        return list(sources)
    except:
        return []

def add_file_to_db(file_path, filename):
    print(f"Processing {filename}...")
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

def delete_source_from_db(filename):
    try:
        collection.delete(where={"source": filename})
        return True, f"Deleted vectors for {filename}."
    except Exception as e:
        return False, str(e)