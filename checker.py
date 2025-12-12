import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_with_metadata, chunk_text_with_page_mapping
import os
from difflib import SequenceMatcher
import re

# --- CONFIGURATION ---
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"

# --- TUNED THRESHOLDS ---
# 1. Semantic Threshold (Distance):
#    0.30 was too strict (missed your 69% match). 
#    We change it to 0.38 (allows matches down to ~62%).
SEMANTIC_PARAPHRASE_CUTOFF = 0.38  
SEMANTIC_TOPIC_CUTOFF = 0.50

# 2. Word Match Threshold:
SEQUENCE_THRESHOLD = 0.70 

def clean_for_matching(text):
    """
    Removes non-alphanumeric characters (like * or -) and lowercases.
    This fixes the issue where adding a '**Title**' broke the match.
    """
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def calculate_structural_score(text1, text2):
    # Compare "cleaned" versions to ignore headers/formatting
    clean1 = clean_for_matching(text1)
    clean2 = clean_for_matching(text2)
    return SequenceMatcher(None, clean1, clean2).ratio()

def check_paper(paper_path):
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print(f"Scanning: {paper_path}...")
    
    # Use your existing utils (They are perfect)
    pages_data = extract_text_with_metadata(paper_path)
    input_chunks = chunk_text_with_page_mapping(pages_data)
    
    total_chunks = len(input_chunks)
    plagiarism_score = 0.0
    
    print(f"\nAnalyzing {total_chunks} segments against database...")

    # --- OUTER LOOP ---
    for i, item in enumerate(input_chunks):
        chunk_text = item['text']
        student_page = item['page']
        
        embedding = model.encode([chunk_text]).tolist()
        
        # Query DB (Fetch top 5 candidates)
        results = collection.query(
            query_embeddings=embedding,
            n_results=5,
            include=["metadatas", "documents", "distances"]
        )
        
        if not results['documents'][0]: continue

        # Reset "Best Match" variables for THIS chunk
        best_match_status = None
        highest_risk_score = 0.0
        best_metadata = None
        best_scores = (0, 0) # (semantic, structural)

        # --- INNER LOOP: CHECK TOP 5 CANDIDATES ---
        for j in range(len(results['documents'][0])):
            db_text = results['documents'][0][j]
            distance = results['distances'][0][j]
            metadata = results['metadatas'][0][j]
            
            # 1. Calculate Scores
            semantic_percent = 1 - distance 
            structural_percent = calculate_structural_score(chunk_text, db_text)

            current_status = None
            current_risk = 0.0
            
            # 2. Determine Category
            
            # CASE A: High Word Overlap (Copy Paste)
            # The clean_for_matching function ensures we catch this even with Headers/Titles
            if structural_percent > SEQUENCE_THRESHOLD:
                current_status = "🔴 EXACT COPY"
                current_risk = 1.0 

            # CASE B: High Semantic Match (Paraphrased / AI)
            # Relaxed threshold (0.38) catches your LSM Theorem example
            elif distance < SEMANTIC_PARAPHRASE_CUTOFF:
                current_status = "🟡 PARAPHRASED (AI?)"
                current_risk = 0.75 

            # CASE C: Topic Match
            elif distance < SEMANTIC_TOPIC_CUTOFF:
                 current_status = "🟢 TOPIC MATCH"
                 current_risk = 0.1
            
            # 3. Keep the worst violation found
            if current_risk > highest_risk_score:
                highest_risk_score = current_risk
                best_match_status = current_status
                best_metadata = metadata
                best_scores = (semantic_percent, structural_percent)

        # --- RECORD RESULT ---
        plagiarism_score += highest_risk_score
        
        if best_match_status:
            print(f"\n{best_match_status}")
            print(f"   Student Page: {student_page} | Source: {best_metadata['source']} (Page {best_metadata['page']})")
            print(f"   Semantic Match: {round(best_scores[0]*100)}% | Word Match: {round(best_scores[1]*100)}%")
            print(f"   Snippet: '{chunk_text[:80]}...'")

    # Final Score
    if total_chunks > 0:
        final_percentage = (plagiarism_score / total_chunks) * 100
    else:
        final_percentage = 0.0
    
    print("\n========================================")
    print(f"Final Plagiarism Risk: {round(final_percentage, 2)}%")
    print("========================================")

if __name__ == "__main__":
    check_paper("papers_to_check/test.pdf")
