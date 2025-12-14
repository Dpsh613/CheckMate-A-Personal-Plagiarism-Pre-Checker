import chromadb
from sentence_transformers import SentenceTransformer
from transformers import pipeline 
import torch 
from utils import extract_text_with_metadata, chunk_text_with_page_mapping
import os
from difflib import SequenceMatcher
import re

# --- CONFIGURATION ---
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"

# --- THRESHOLDS (Your Tuned Settings) ---
SEMANTIC_PARAPHRASE_CUTOFF = 0.25   # Strict Paraphrase Detection
SEMANTIC_TOPIC_CUTOFF = 0.40        # Topic/Concept Detection
SEQUENCE_THRESHOLD = 0.70           # Exact Word Matching

# --- AI DETECTION SETUP ---
try:
    print("Loading AI Detector (may take a moment for first download)...")
    device = 0 if torch.cuda.is_available() else -1 
    AI_CLASSIFIER = pipeline(
        "text-classification", 
        model="roberta-base-openai-detector", 
        device=device
    )
    print("AI Detector loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load AI Detector. Skipping AI check. Error: {e}")
    AI_CLASSIFIER = None

def clean_for_matching(text):
    if not text: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def calculate_structural_score(text1, text2):
    clean1 = clean_for_matching(text1)
    clean2 = clean_for_matching(text2)
    return SequenceMatcher(None, clean1, clean2).ratio()

def check_ai_probability(text):
    if AI_CLASSIFIER is None: return 0.0, "Skipped"
    if len(text.split()) < 30: return 0.0, "Too Short"
    try:
        result = AI_CLASSIFIER(text[:512], truncation=True)[0]
        if result['label'] == 'Fake':
            return result['score'], "🤖 AI LIKELY"
        else:
            return (1 - result['score']), "👤 HUMAN"
    except:
        return 0.0, "Error"

def check_paper(paper_path):
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print(f"Scanning: {paper_path}...")
    pages_data = extract_text_with_metadata(paper_path)
    input_chunks = chunk_text_with_page_mapping(pages_data)
    
    total_chunks = len(input_chunks)
    
    # --- SCORING VARIABLES ---
    total_plagiarism_risk = 0.0
    total_ai_risk = 0.0
    topic_match_count = 0 
    
    # NEW: Dictionary to track risk per file
    # Format: { "book_name.pdf": 3.4, "other_book.pdf": 1.0 }
    source_contributions = {} 

    print(f"\nAnalyzing {total_chunks} segments against database...")

    for i, item in enumerate(input_chunks):
        chunk_text = item['text']
        student_page = item['page']
        
        # --- 1. PLAGIARISM CHECK ---
        embedding = model.encode([chunk_text]).tolist()
        
        results = collection.query(
            query_embeddings=embedding,
            n_results=5,
            include=["metadatas", "documents", "distances"]
        )
        
        if not results['documents'][0]: continue

        best_match_status = None
        highest_plagiarism_risk = 0.0 
        best_metadata = None
        best_scores = (0, 0)
        is_topic_match = False

        for j in range(len(results['documents'][0])):
            db_text = results['documents'][0][j]
            distance = results['distances'][0][j]
            metadata = results['metadatas'][0][j]
            
            semantic_percent = 1 - distance 
            structural_percent = calculate_structural_score(chunk_text, db_text)

            current_status = None
            current_risk = 0.0
            
            # --- CATEGORY LOGIC ---
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
                if highest_plagiarism_risk == 0: 
                    is_topic_match = True
            
            if current_risk > highest_plagiarism_risk:
                highest_plagiarism_risk = current_risk
                best_match_status = current_status
                best_metadata = metadata
                best_scores = (semantic_percent, structural_percent)
                is_topic_match = False
            
            if highest_plagiarism_risk == 0 and is_topic_match and current_risk == 0:
                best_match_status = "🟢 TOPIC MATCH"
                best_metadata = metadata
                best_scores = (semantic_percent, structural_percent)
        
        # --- 2. AI AUTHORSHIP CHECK ---
        ai_score, ai_status = check_ai_probability(chunk_text)
        total_ai_risk += ai_score
        
        # --- REPORTING ---
        print(f"\n--- Segment {i+1} (Page {student_page}) ---")
        
        if best_match_status:
            print(f"PLAGIARISM: {best_match_status} (Risk: {highest_plagiarism_risk})")
            if highest_plagiarism_risk > 0.0:
                 print(f"   Source: {best_metadata['source']} (Page {best_metadata['page']})")
                 print(f"   Semantic: {round(best_scores[0]*100)}% | Structural: {round(best_scores[1]*100)}%")
        else:
            print("PLAGIARISM: ✅ Original")

        ai_percentage = round(ai_score * 100)
        if ai_score > 0.8:
            print(f"AUTHORSHIP: 🔴 {ai_status} ({ai_percentage}%)")
        elif ai_score > 0.5:
             print(f"AUTHORSHIP: 🟡 SUSPICIOUS ({ai_percentage}%)")
        else:
             print(f"AUTHORSHIP: 🟢 {ai_status} ({ai_percentage}%)")
        
        # --- RECORD SCORES ---
        total_plagiarism_risk += highest_plagiarism_risk
        
        # NEW: Add the specific risk to the specific source file
        if highest_plagiarism_risk > 0.0:
            source_name = best_metadata['source']
            # If bucket doesn't exist, create it. Add risk to bucket.
            source_contributions[source_name] = source_contributions.get(source_name, 0.0) + highest_plagiarism_risk

        if highest_plagiarism_risk == 0 and best_match_status == "🟢 TOPIC MATCH":
            topic_match_count += 1

    # --- FINAL CALCULATION ---
    if total_chunks > 0:
        final_plagiarism_percentage = (total_plagiarism_risk / total_chunks) * 100
        final_ai_percentage = (total_ai_risk / total_chunks) * 100
        topic_relevance_percentage = (topic_match_count / total_chunks) * 100
    else:
        final_plagiarism_percentage = 0.0
        final_ai_percentage = 0.0
        topic_relevance_percentage = 0.0
    
    print("\n========================================")
    print(f"REPORT SUMMARY")
    print(f"----------------------------------------")
    print(f"🚨 PLAGIARISM RISK:   {round(final_plagiarism_percentage, 2)}%")
    
    # NEW: PRINT SOURCE BREAKDOWN
    if source_contributions:
        print(f"   --- Sources Breakdown ---")
        # Sort by highest contribution first
        sorted_sources = sorted(source_contributions.items(), key=lambda x: x[1], reverse=True)
        for src, risk_sum in sorted_sources:
            # Calculate % contribution of this file to the total paper
            src_percentage = (risk_sum / total_chunks) * 100
            print(f"   📄 {src}: {round(src_percentage, 2)}%")
    
    print(f"----------------------------------------")
    print(f"🤖 AI GENERATION RISK: {round(final_ai_percentage, 2)}%")
    print(f"📚 TOPIC RELEVANCE:    {round(topic_relevance_percentage, 2)}%")
    print("========================================")

if __name__ == "__main__":
    check_paper("papers_to_check/test.pdf")
