import os
import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_with_metadata, chunk_text_with_page_mapping
from tqdm import tqdm

# --- CONFIGURATION ---
DATA_FOLDER = "dataset_pdfs"
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter" 
BATCH_SIZE = 100  # 100 CHUNKS
# --------------------------

def update_database():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    all_pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]
    
    # --- STEP 1: IDENTIFY NEW FILES ---
    # We do a quick check to see which files are NOT in the DB yet.
    print("Scanning database for existing files...")
    
    files_to_process = []
    for filename in all_pdf_files:
        existing = collection.get(where={"source": filename}, limit=1)
        if len(existing['ids']) == 0:
            files_to_process.append(filename)

    if len(files_to_process) == 0:
        print("✅ No new files to add. Database is up to date!")
        return

    print(f"Found {len(files_to_process)} new files to process.")

    # --- STEP 2: PROCESS ONLY NEW FILES ---
    # The progress bar now only reflects the actual work to be done
    for filename in tqdm(files_to_process):
        
        file_path = os.path.join(DATA_FOLDER, filename)
        
        # 1. Extract
        pages_data = extract_text_with_metadata(file_path)
        
        # 2. Chunk
        chunks_data = chunk_text_with_page_mapping(pages_data)
        
        if not chunks_data:
            print(f"Warning: No text found in {filename}")
            continue

        # 3. Prepare Data
        full_documents = [item['text'] for item in chunks_data]
        full_metadatas = [{"source": filename, "page": item['page']} for item in chunks_data]
        full_ids = [f"{filename}_{i}" for i in range(len(chunks_data))]
        
        # 4. Batch Add
        for i in range(0, len(full_documents), BATCH_SIZE):
            batch_docs = full_documents[i : i + BATCH_SIZE]
            batch_metas = full_metadatas[i : i + BATCH_SIZE]
            batch_ids = full_ids[i : i + BATCH_SIZE]
            
            batch_embeddings = model.encode(batch_docs).tolist()
            
            collection.add(
                embeddings=batch_embeddings,
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )

    print(f"✅ Successfully added {len(files_to_process)} new documents!")

if __name__ == "__main__":
    update_database()