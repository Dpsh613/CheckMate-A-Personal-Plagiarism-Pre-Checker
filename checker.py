import chromadb
from sentence_transformers import SentenceTransformer
from transformers import pipeline 
import torch
from utils import extract_text_with_metadata, chunk_text_with_page_mapping, split_into_sentences
from difflib import SequenceMatcher
import re
import os

# --- CONFIGURATION & GLOBAL LOAD ---
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"

print("⏳ Loading Models in checker.py...")
try:
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    model = SentenceTransformer('all-MiniLM-L6-v2')
    device = 0 if torch.cuda.is_available() else -1 
    ai_classifier = pipeline("text-classification", model="roberta-base-openai-detector", device=device)
    print("✅ All Models Loaded Successfully.")
except Exception as e:
    print(f"❌ Error loading models: {e}")

# --- THRESHOLDS ---
SEMANTIC_PARAPHRASE_CUTOFF = 0.35
SEMANTIC_TOPIC_CUTOFF = 0.45
SEQUENCE_THRESHOLD = 0.80

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
        if label == 'Fake': return score, "AI LIKELY"
        else: return (1 - score), "HUMAN"
    except:
        return 0.0, "Error"

# --- MAIN CALLABLE FUNCTION ---
def analyze_document(paper_path):
    pages_data = extract_text_with_metadata(paper_path)
    input_segments = split_into_sentences(pages_data) 
    
    total_segments = len(input_segments)
    total_plagiarism_risk = 0.0
    total_ai_risk = 0.0
    topic_match_count = 0 
    source_contributions = {} 
    detailed_segments = []

    for i, item in enumerate(input_segments):
        segment_text = item['text']
        student_page = item['page']
        
        # --- CRITICAL FIX: GET THE FLAG FROM UTILS ---
        is_eop = item.get('is_end_of_paragraph', False) 
        # ---------------------------------------------

        embedding = model.encode([segment_text]).tolist()
        results = collection.query(query_embeddings=embedding, n_results=10)
        
        best_match_status = "ORIGINAL"
        highest_plagiarism_risk = 0.0 
        best_metadata = {}
        best_scores = {"semantic": 0.0, "structural": 0.0}
        match_found = False

        if results['documents'] and results['documents'][0]:
            is_topic_match = False
            for j in range(len(results['documents'][0])):
                db_chunk_text = results['documents'][0][j]
                distance = results['distances'][0][j]
                metadata = results['metadatas'][0][j]
                
                structural_percent = calculate_structural_score(segment_text, db_chunk_text)
                semantic_percent = 1 - distance 

                current_risk = 0.0
                current_status = None

                if structural_percent > SEQUENCE_THRESHOLD:
                    current_status = "🔴 EXACT COPY"
                    current_risk = 1.0 
                elif distance < SEMANTIC_PARAPHRASE_CUTOFF:
                    current_status = "🟡 HEAVY PARAPHRASED" 
                    current_risk = 0.5 
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

        ai_score, ai_status = check_ai_probability(segment_text)
        total_ai_risk += ai_score
        total_plagiarism_risk += highest_plagiarism_risk
        
        if highest_plagiarism_risk > 0.0:
            src = best_metadata.get('source', 'Unknown')
            source_contributions[src] = source_contributions.get(src, 0.0) + highest_plagiarism_risk

        if highest_plagiarism_risk == 0 and best_match_status == "🟢 TOPIC MATCH":
            topic_match_count += 1

        segment_data = {
            "id": i,
            "page": student_page,
            "text": segment_text,
            "status": best_match_status,
            "plagiarism_risk_score": highest_plagiarism_risk,
            "ai_probability": round(ai_score * 100, 1),
            "ai_status": ai_status,
            "match_details": None,
            # --- CRITICAL FIX: PASS THE FLAG TO JSON ---
            "is_end_of_paragraph": is_eop 
            # -------------------------------------------
        }

        if match_found and best_match_status != "ORIGINAL":
            segment_data["match_details"] = {
                "source_doc": best_metadata.get('source'),
                "source_page": best_metadata.get('page'),
                "semantic_score": best_scores['semantic'],
                "structural_score": best_scores['structural']
            }
        
        detailed_segments.append(segment_data)

    if total_segments > 0:
        final_plagiarism_pct = (total_plagiarism_risk / total_segments) * 100
        final_ai_pct = (total_ai_risk / total_segments) * 100
        topic_relevance_pct = (topic_match_count / total_segments) * 100
    else:
        final_plagiarism_pct = 0.0; final_ai_pct = 0.0; topic_relevance_pct = 0.0

    sources_list = []
    sorted_sources = sorted(source_contributions.items(), key=lambda x: x[1], reverse=True)
    for src, risk_sum in sorted_sources:
        src_pct = (risk_sum / total_segments) * 100
        sources_list.append({"filename": src, "contribution_percent": round(src_pct, 2)})

    return {
        "summary": {
            "plagiarism_percent": round(final_plagiarism_pct, 2),
            "ai_percent": round(final_ai_pct, 2),
            "topic_relevance_percent": round(topic_relevance_pct, 2),
            "total_segments": total_segments
        },
        "sources": sources_list,
        "segments": detailed_segments
    }
