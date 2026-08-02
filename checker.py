import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_from_document, get_sliding_windows
import re

from db_manager import get_user_collection

model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_trigrams(words):
    return {" ".join(words[i:i+3]) for i in range(len(words)-2)}

def calculate_ngram_overlap(student_text, db_text):
    """
    Lightning fast CPU method. Matches 3-word chunks.
    Returns score and specific words to highlight.
    """
    s_words = re.findall(r'\b\w+\b', student_text.lower())
    db_words = re.findall(r'\b\w+\b', db_text.lower())
    
    if len(s_words) < 3 or len(db_words) < 3: return 0.0, set()
    
    s_trigrams = extract_trigrams(s_words)
    db_trigrams = extract_trigrams(db_words)
    
    matches = s_trigrams.intersection(db_trigrams)
    if not s_trigrams: return 0.0, set()
    
    # Calculate how many unique student words are part of matching trigrams
    matched_words = set()
    for trigram in matches:
        matched_words.update(trigram.split())
        
    coverage = len(matched_words) / len(s_words)
    return coverage, matched_words

def analyze_document(user_id, paper_path):
    collection = get_user_collection(user_id)
    pages_data = extract_text_from_document(paper_path)
    input_chunks = get_sliding_windows(pages_data)
    
    if not input_chunks: return {"error": "No text extracted."}

    total_words_in_doc = sum(len(re.findall(r'\b\w+\b', item['text'])) for item in input_chunks)
    total_plagiarized_words = 0
    
    source_contributions = {}
    detailed_segments = []

    input_texts = [item['text'] for item in input_chunks]
    input_embeddings = model.encode(input_texts, batch_size=32).tolist()

    batch_results = collection.query(
        query_embeddings=input_embeddings, 
        n_results=3, # Dropped to 3 to save CPU cycles
        include=["documents", "metadatas"] 
    )

    for i, item in enumerate(input_chunks):
        sent_text = item['text']
        candidates_docs = batch_results['documents'][i] if batch_results['documents'] else []
        candidates_meta = batch_results['metadatas'][i] if batch_results['metadatas'] else []

        best_score = 0.0
        best_source = None
        best_match_text = None
        best_matched_words = set()

        for idx, db_doc in enumerate(candidates_docs):
            score, matched_words = calculate_ngram_overlap(sent_text, db_doc)
            if score > best_score:
                best_score = score
                best_matched_words = matched_words
                best_source = candidates_meta[idx]['source']
                best_match_text = db_doc

        match_status = "ORIGINAL"
        if best_score > 0.60: 
            match_status = "EXACT MATCH"
        elif best_score > 0.20: 
            match_status = "PARAPHRASED"

        matched_word_count = len(best_matched_words)
        if matched_word_count > 0:
            total_plagiarized_words += matched_word_count
            source_contributions[best_source] = source_contributions.get(best_source, 0) + matched_word_count

        detailed_segments.append({
            "text": sent_text,
            "page": item['page'],
            "status": match_status,
            "source": best_source if best_score > 0 else None,
            "matched_words": list(best_matched_words), # Pass exact words to frontend
            "matched_db_text": best_match_text if best_score > 0 else None
        })

    final_plag_percent = min((total_plagiarized_words / total_words_in_doc) * 100, 100) if total_words_in_doc > 0 else 0
    
    # Sort sources to assign consistent Turnitin-like colors on frontend
    sources_list = [{"filename": k, "matched_words": v} for k, v in sorted(source_contributions.items(), key=lambda x: x[1], reverse=True)]

    return {
        "summary": {
            "plagiarism_percent": round(final_plag_percent, 2),
            "total_words": total_words_in_doc,
            "plagiarized_words": total_plagiarized_words
        },
        "sources": sources_list,
        "segments": detailed_segments
    }
