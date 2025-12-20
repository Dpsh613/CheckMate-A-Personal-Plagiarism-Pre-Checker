import chromadb
from sentence_transformers import SentenceTransformer
from transformers import pipeline 
import torch
from utils import extract_text_with_metadata, chunk_text_with_page_mapping
from difflib import SequenceMatcher
import re
import os

# --- CONFIGURATION & GLOBAL LOAD ---
# We load these GLOBALLY so they don't reload on every single API request (speed boost)
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"

print("⏳ Loading Models in checker.py...")
try:
    # 1. Load Chroma
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    
    # 2. Load Embedder
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 3. Load AI Detector
    device = 0 if torch.cuda.is_available() else -1 
    ai_classifier = pipeline("text-classification", model="roberta-base-openai-detector", device=device)
    print("✅ All Models Loaded Successfully.")
except Exception as e:
    print(f"❌ Error loading models: {e}")
    # In production, you might want to exit here if models fail

# --- THRESHOLDS ---
SEMANTIC_PARAPHRASE_CUTOFF = 0.25
SEMANTIC_TOPIC_CUTOFF = 0.40
SEQUENCE_THRESHOLD = 0.70

def clean_for_matching(text):
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def calculate_structural_score(text1, text2):
    clean1 = clean_for_matching(text1)
    clean2 = clean_for_matching(text2)
    return SequenceMatcher(None, clean1, clean2).ratio()

def check_ai_probability(text):
    if ai_classifier is None: return 0.0, "Skipped"
    if len(text.split()) < 30: return 0.0, "Too Short"
    try:
        result = ai_classifier(text[:512], truncation=True)[0]
        label = result['label']
        score = result['score']
        
        if label == 'Fake':
            return score, "AI LIKELY"
        else:
            return (1 - score), "HUMAN"
    except:
        return 0.0, "Error"

# --- MAIN CALLABLE FUNCTION ---
def analyze_document(paper_path):
    """
    This function takes a file path, runs all logic, and returns a Python Dict.
    It does NOT print results to the console.
    """
    
    # Extract Text
    pages_data = extract_text_with_metadata(paper_path)
    input_chunks = chunk_text_with_page_mapping(pages_data)
    
    total_chunks = len(input_chunks)
    total_plagiarism_risk = 0.0
    total_ai_risk = 0.0
    topic_match_count = 0 
    source_contributions = {} 
    detailed_segments = []

    for i, item in enumerate(input_chunks):
        chunk_text = item['text']
        student_page = item['page']
        
        # 1. Query DB
        embedding = model.encode([chunk_text]).tolist()
        results = collection.query(query_embeddings=embedding, n_results=5)
        
        best_match_status = "ORIGINAL"
        highest_plagiarism_risk = 0.0 
        best_metadata = {}
        best_scores = {"semantic": 0.0, "structural": 0.0}
        match_found = False

        if results['documents'] and results['documents'][0]:
            is_topic_match = False
            for j in range(len(results['documents'][0])):
                db_text = results['documents'][0][j]
                distance = results['distances'][0][j]
                metadata = results['metadatas'][0][j]
                
                semantic_percent = 1 - distance 
                structural_percent = calculate_structural_score(chunk_text, db_text)

                current_risk = 0.0
                current_status = None

                if structural_percent > SEQUENCE_THRESHOLD:
                    current_status = "🔴 EXACT COPY"
                    current_risk = 1.0 
                    is_topic_match = False
                elif distance < SEMANTIC_PARAPHRASE_CUTOFF:
                    current_status = "🟡 HEAVY PARAPHRASED" 
                    current_risk = 0.4
                    is_topic_match = False
                elif distance < SEMANTIC_TOPIC_CUTOFF:
                    current_status = "🟢 TOPIC MATCH"
                    current_risk = 0.0 
                    if highest_plagiarism_risk == 0: is_topic_match = True
                
                if current_risk > highest_plagiarism_risk:
                    highest_plagiarism_risk = current_risk
                    best_match_status = current_status
                    best_metadata = metadata
                    match_found = True
                    best_scores = {"semantic": round(semantic_percent*100,1), "structural": round(structural_percent*100,1)}
                    is_topic_match = False

                if highest_plagiarism_risk == 0 and is_topic_match and current_risk == 0:
                    best_match_status = "🟢 TOPIC MATCH"
                    best_metadata = metadata
                    match_found = True

        # 2. AI Check
        ai_score, ai_status = check_ai_probability(chunk_text)
        total_ai_risk += ai_score
        
        # 3. Aggregation
        total_plagiarism_risk += highest_plagiarism_risk
        
        if highest_plagiarism_risk > 0.0:
            src = best_metadata.get('source', 'Unknown')
            source_contributions[src] = source_contributions.get(src, 0.0) + highest_plagiarism_risk

        if highest_plagiarism_risk == 0 and best_match_status == "🟢 TOPIC MATCH":
            topic_match_count += 1

        # 4. Build Segment
        segment_data = {
            "id": i,
            "page": student_page,
            "text": chunk_text,
            "status": best_match_status,
            "plagiarism_risk_score": highest_plagiarism_risk,
            "ai_probability": round(ai_score * 100, 1),
            "ai_status": ai_status,
            "match_details": None
        }

        if match_found and best_match_status != "ORIGINAL":
            segment_data["match_details"] = {
                "source_doc": best_metadata.get('source'),
                "source_page": best_metadata.get('page'),
                "semantic_score": best_scores['semantic'],
                "structural_score": best_scores['structural']
            }
        
        detailed_segments.append(segment_data)

    # --- FINAL CALCULATIONS ---
    if total_chunks > 0:
        final_plagiarism_pct = (total_plagiarism_risk / total_chunks) * 100
        final_ai_pct = (total_ai_risk / total_chunks) * 100
        topic_relevance_pct = (topic_match_count / total_chunks) * 100
    else:
        final_plagiarism_pct = 0.0; final_ai_pct = 0.0; topic_relevance_pct = 0.0

    sources_list = []
    sorted_sources = sorted(source_contributions.items(), key=lambda x: x[1], reverse=True)
    for src, risk_sum in sorted_sources:
        src_pct = (risk_sum / total_chunks) * 100
        sources_list.append({"filename": src, "contribution_percent": round(src_pct, 2)})

    return {
        "summary": {
            "plagiarism_percent": round(final_plagiarism_pct, 2),
            "ai_percent": round(final_ai_pct, 2),
            "topic_relevance_percent": round(topic_relevance_pct, 2),
            "total_segments": total_chunks
        },
        "sources": sources_list,
        "segments": detailed_segments
    }



# ### Why this is better:
# 1.  **Zero Duplication:** If you change the `SEMANTIC_PARAPHRASE_CUTOFF` in `checker.py`, the API automatically uses the new value.
# 2.  **Cleaner API:** Your API file is readable. It just handles "web stuff" (uploads, errors, JSON), while `checker.py` handles "science stuff" (AI, vectors, math).
# 3.  **Testable:** You can still create a script to test `checker.py` without running a web server.