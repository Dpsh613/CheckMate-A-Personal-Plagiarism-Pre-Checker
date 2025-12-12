# import os
# import chromadb
# from sentence_transformers import SentenceTransformer
# from utils import extract_text_from_pdf, clean_text, chunk_text
# from tqdm import tqdm

# # --- CONFIGURATION ---
# DATA_FOLDER = "dataset_pdfs"  # Put your 700 books here
# DB_PATH = "./my_plagiarism_db" # Where the database file is saved
# COLLECTION_NAME = "condensed_matter" # CHANGE THIS when swapping subjects!
# # ---------------------

# def create_database():
#     # 1. Initialize AI Model and Database
#     print("Loading AI Model...")
#     model = SentenceTransformer('all-MiniLM-L6-v2')
    
#     client = chromadb.PersistentClient(path=DB_PATH)
    
#     # Delete collection if it exists (to start fresh) or get existing
#     try:
#         client.delete_collection(name=COLLECTION_NAME)
#         print(f"Deleted old collection: {COLLECTION_NAME}")
#     except:
#         pass
    
#     collection = client.create_collection(name=COLLECTION_NAME)

#     # 2. Process PDFs
#     pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    
#     if not pdf_files:
#         print(f"No PDFs found in {DATA_FOLDER}")
#         return

#     print(f"Processing {len(pdf_files)} books into '{COLLECTION_NAME}' database...")

#     for filename in tqdm(pdf_files):
#         file_path = os.path.join(DATA_FOLDER, filename)
        
#         # A. Extract
#         raw_text = extract_text_from_pdf(file_path)
#         clean_raw_text = clean_text(raw_text)
        
#         # B. Chunk
#         chunks = chunk_text(clean_raw_text)
        
#         if not chunks:
#             continue

#         # C. Embed (Convert text to numbers) & Add to DB
#         # We process in batches to be memory efficient
#         ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]
#         metadatas = [{"source": filename, "chunk_id": i} for i in range(len(chunks))]
#         embeddings = model.encode(chunks).tolist()
        
#         collection.add(
#             embeddings=embeddings,
#             documents=chunks,
#             metadatas=metadatas,
#             ids=ids
#         )

#     print(f"✅ Success! Database '{COLLECTION_NAME}' is ready.")

# if __name__ == "__main__":
#     create_database()

import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from utils import extract_text_with_metadata, chunk_text_with_page_mapping
from tqdm import tqdm

# --- CONFIGURATION ---
DATA_FOLDER = "dataset_pdfs"
DB_PATH = "./my_plagiarism_db"
# CHANGE THIS NAME for different subjects (e.g., "lie_algebra", "condensed_matter")
COLLECTION_NAME = "condensed_matter" 
# --------------------------

def create_database():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = chromadb.PersistentClient(path=DB_PATH)

    # Reset collection to ensure clean slate for this subject
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except:
        pass
    
    # Enforce Cosine distance for accurate similarity percentages
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"} 
    )

    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    print(f"Processing {len(pdf_files)} books for subject: '{COLLECTION_NAME}'...")

    for filename in tqdm(pdf_files):
        file_path = os.path.join(DATA_FOLDER, filename)
        
        # 1. Extract with Page Numbers
        pages_data = extract_text_with_metadata(file_path)
        
        # 2. Chunk
        chunks_data = chunk_text_with_page_mapping(pages_data)
        
        if not chunks_data:
            continue

        # 3. Prepare Data for DB
        documents = [item['text'] for item in chunks_data]
        metadatas = [{"source": filename, "page": item['page']} for item in chunks_data]
        ids = [f"{filename}_{i}" for i in range(len(chunks_data))]
        
        # 4. Embed and Add (Batch processing automatically handled by Chroma usually, 
        # but manual batching is safer for 700 books. Here we do file-by-file).
        embeddings = model.encode(documents).tolist()
        
        collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    print(f"✅ Database for '{COLLECTION_NAME}' is ready!")

if __name__ == "__main__":
    create_database()
