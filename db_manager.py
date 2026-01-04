import os
import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_from_pdf, get_sentences_from_text

# --- CONFIGURATION ---
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"
DATA_FOLDER = "dataset_pdfs"

# Ensure dataset folder exists
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# --- INITIALIZE CHROMA & MODEL ---
print("⏳ Loading Database Model...")
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# Load Model (used for generating embeddings)
model = SentenceTransformer('all-MiniLM-L6-v2') 
print("✅ Database Model Loaded.")

# --- FUNCTIONS ---

def get_all_files_in_db():
    """Returns a list of unique filenames currently stored in the dataset folder."""
    if not os.path.exists(DATA_FOLDER):
        return []
    # We use the file system as the source of truth for the list
    return [f for f in os.listdir(DATA_FOLDER) if f.endswith('.pdf')]

def add_file_to_db(file_path, filename):
    """
    Extracts sentences from a PDF and adds them to the Chroma vector database.
    """
    print(f"Processing {filename}...")
    
    # 1. Extract Text (using pdfplumber via utils)
    pages_data = extract_text_from_pdf(file_path)
    if not pages_data:
        return False, "Extraction failed or PDF is empty."

    # 2. Split into Sentences (using Spacy via utils)
    sentences_data = get_sentences_from_text(pages_data)
    
    if not sentences_data:
        return False, "No valid text sentences found."

    # 3. Prepare Batch Data
    documents = [item['text'] for item in sentences_data]
    metadatas = [{"source": filename, "page": item['page']} for item in sentences_data]
    ids = [f"{filename}_{i}" for i in range(len(sentences_data))]
    
    # 4. Generate Embeddings
    embeddings = model.encode(documents).tolist()

    # 5. Add to Chroma Database
    collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    return True, f"Successfully indexed {len(documents)} sentences."

def delete_file_from_db(filename):
    """
    Removes a file from the Chroma database and deletes the physical PDF.
    """
    try:
        # 1. Remove vectors from Chroma where source == filename
        collection.delete(where={"source": filename})
        
        # 2. Remove the actual file from disk
        file_path = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True, f"Deleted {filename} from database and disk."
        else:
            return True, f"Deleted vectors for {filename}, but file was missing from disk."
            
    except Exception as e:
        print(f"Error deleting {filename}: {e}")
        return False, str(e)

def reset_db():
    """
    Wipes the entire collection. Use with caution.
    """
    try:
        client.delete_collection(COLLECTION_NAME)
        client.create_collection(COLLECTION_NAME)
        return True, "Database completely reset."
    except Exception as e:
        return False, str(e)
