import os
import torch
import chromadb
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline
from difflib import SequenceMatcher
from utils import extract_text_from_pdf, get_sentences_from_text, normalize_text
import re

# CONFIG
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"

print("⏳ Loading Models...")
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)
model = SentenceTransformer('all-MiniLM-L6-v2')

try:
    device = 0 if torch.cuda.is_available() else -1
    ai_classifier = pipeline("text-classification", model="roberta-base-openai-detector", device=device)
except:
    ai_classifier = None
print("✅ Models Loaded.")

def calculate_patchwriting_score(student_text, db_text):
    """
    Returns coverage % and total matching words.
    """
    # Tokenize
    s_words = re.findall(r'\w+', student_text.lower())
    db_words = re.findall(r'\w+', db_text.lower())
    
    if not s_words or not db_words: return 0.0, 0
    
    matcher = SequenceMatcher(None, s_words, db_words)
    total_matching_words = 0
    
    # Common Scientific Stopwords (We don't count matches if it's ONLY these)
    # e.g., "results of the" -> ignored. "results of the lithium" -> counted.
    stopwords = {'the', 'of', 'and', 'in', 'to', 'a', 'is', 'for', 'with', 'on', 'at', 'by', 'this', 'are', 'it', 'from', 'as', 'be', 'that', 'or', 'an', 'was', 'were'}

    for block in matcher.get_matching_blocks():
        # Block must be at least 3 words long
        if block.size >= 3:
            # Get the actual words in this block
            matched_phrase = s_words[block.a : block.a + block.size]
            
            # CHECK: Does this block contain at least one NON-STOPWORD?
            # If the block is "and in the", we ignore it.
            # If the block is "magnetic field applied", we count it.
            has_content_word = any(w not in stopwords for w in matched_phrase)
            
            if has_content_word:
                total_matching_words += block.size

    coverage = total_matching_words / len(s_words)
    return coverage, total_matching_words

def analyze_document(paper_path):
    if not os.path.exists(paper_path): return {"error": "File not found"}

    pages_data = extract_text_from_pdf(paper_path)
    input_sentences = get_sentences_from_text(pages_data)
    total_sentences = len(input_sentences)
    
    if total_sentences == 0: return {"error": "No text extracted."}

    plagiarized_count = 0
    ai_risk_total = 0.0
    source_contributions = {}
    detailed_segments = []

    input_texts = [item['text'] for item in input_sentences]
    input_embeddings = model.encode(input_texts, convert_to_tensor=True)

    for i, item in enumerate(input_sentences):
        sent_text = item['text']
        sent_embedding = input_embeddings[i]
        page_num = item['page']

        # Query DB
        results = collection.query(
            query_embeddings=sent_embedding.tolist(), 
            n_results=5,
            include=["documents", "metadatas"] 
        )

        best_match_type = "ORIGINAL"
        best_score = 0.0
        best_source = None
        best_match_text = None

        if results['documents'] and results['documents'][0]:
            candidates_docs = results['documents'][0]
            candidates_meta = results['metadatas'][0]

            for idx, db_doc in enumerate(candidates_docs):
                score, matched_count = calculate_patchwriting_score(sent_text, db_doc)
                
                # --- STRICTER THRESHOLDS ---
                current_type = "ORIGINAL"
                
                if score > 0.85: 
                    current_type = "🔴 EXACT MATCH"
                elif score > 0.40: 
                    current_type = "🟡 PATCHWORK / PARAPHRASED"
                elif score > 0.25: # Raised from 0.15 to 0.25 to kill noise
                    current_type = "🟠 POTENTIAL MATCH"
                
                if score > best_score:
                    best_score = score
                    best_match_type = current_type
                    best_source = candidates_meta[idx]['source']
                    best_match_text = db_doc

        # Counters
        if "EXACT" in best_match_type: plagiarized_count += 1
        elif "PATCHWORK" in best_match_type: plagiarized_count += 1
        elif "POTENTIAL" in best_match_type: plagiarized_count += 0.3 # Reduced weight

        # Only add source if match is significant (> 25%)
        if best_source and best_score > 0.25:
            source_contributions[best_source] = source_contributions.get(best_source, 0) + 1

        # AI Check
        ai_prob = 0
        if ai_classifier and len(sent_text.split()) > 5:
            try:
                res = ai_classifier(sent_text[:512], truncation=True)[0]
                if res['label'] == 'Fake': ai_prob = res['score']
            except: pass
        ai_risk_total += ai_prob

        detailed_segments.append({
            "text": sent_text,
            "page": page_num,
            "status": best_match_type,
            "score": round(best_score * 100, 1),
            "source": best_source if best_score > 0.25 else None,
            "matched_db_text": best_match_text if best_score > 0.25 else None
        })

    final_plag_percent = min((plagiarized_count / total_sentences) * 100, 100)
    final_ai_percent = (ai_risk_total / total_sentences) * 100

    sources_list = [{"filename": k, "count": v} for k, v in sorted(source_contributions.items(), key=lambda x: x[1], reverse=True)]

    return {
        "summary": {
            "plagiarism_percent": round(final_plag_percent, 2),
            "ai_percent": round(final_ai_percent, 2),
            "total_sentences": total_sentences,
            "matched_sentences": round(plagiarized_count, 1)
        },
        "sources": sources_list,
        "segments": detailed_segments
    }