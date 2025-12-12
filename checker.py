# import chromadb
# from sentence_transformers import SentenceTransformer
# from utils import extract_text_from_pdf, clean_text, chunk_text
# import os

# # --- CONFIGURATION ---
# DB_PATH = "./my_plagiarism_db"
# COLLECTION_NAME = "condensed_matter" # Must match the one in ingest.py
# THRESHOLD = 0.80 # 0.80 = Paraphrasing, 0.95 = Exact Copy
# # ---------------------

# def check_paper(paper_path):
#     # 1. Load Resources
#     print("Loading resources...")
#     client = chromadb.PersistentClient(path=DB_PATH)
#     collection = client.get_collection(name=COLLECTION_NAME)
#     model = SentenceTransformer('all-MiniLM-L6-v2')

#     # 2. Prepare the Input Paper
#     print(f"Scanning paper: {paper_path}...")
#     text = extract_text_from_pdf(paper_path)
#     text = clean_text(text)
#     input_chunks = chunk_text(text)
    
#     total_chunks = len(input_chunks)
#     plagiarized_chunks = 0
#     report = []

#     print("\n--- DETAILED REPORT ---\n")

#     # 3. Check every chunk against the Database
#     for i, chunk in enumerate(input_chunks):
#         # Create vector for the current chunk
#         query_embedding = model.encode([chunk]).tolist()
        
#         # Query the DB for the closest match
#         results = collection.query(
#             query_embeddings=query_embedding,
#             n_results=1, # We only need the top match
#             include=["documents", "metadatas", "distances"]
#         )

#         # ChromaDB returns distance (0 is identical, 1 is different)
#         # We convert distance to similarity: Similarity = 1 - Distance
#         distance = results['distances'][0][0]
#         similarity = 1 - distance
        
#         source = results['metadatas'][0][0]['source']
#         matched_text = results['documents'][0][0]

#         if similarity >= THRESHOLD:
#             plagiarized_chunks += 1
#             match_type = "EXACT COPY" if similarity > 0.95 else "PARAPHRASED"
            
#             print(f"⚠️  MATCH FOUND (Chunk {i}) - {match_type}")
#             print(f"   Score: {round(similarity * 100, 2)}%")
#             print(f"   Source Book: {source}")
#             print(f"   Student Text: '{chunk[:100]}...'")
#             print(f"   Database Text: '{matched_text[:100]}...'\n")
            
#             report.append({
#                 "chunk": i,
#                 "score": similarity,
#                 "source": source
#             })

#     # 4. Final Calculation
#     plagiarism_percentage = (plagiarized_chunks / total_chunks) * 100
    
#     print("========================================")
#     print(f"FINAL RESULT FOR: {os.path.basename(paper_path)}")
#     print(f"Database Used: {COLLECTION_NAME}")
#     print(f"Total Plagiarism Detected: {round(plagiarism_percentage, 2)}%")
#     print("========================================")

# if __name__ == "__main__":
#     # Change this to the path of the PDF you want to test
#     input_paper = "papers_to_check/my_test_paper.pdf"
    
#     if os.path.exists(input_paper):
#         check_paper(input_paper)
#     else:
#         print(f"Please put a PDF in {input_paper}")
import chromadb
from sentence_transformers import SentenceTransformer
from utils import extract_text_with_metadata, chunk_text_with_page_mapping
import os
from difflib import SequenceMatcher # <--- STANDARD LIBRARY FOR TEXT COMPARISON

# --- CONFIGURATION ---
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter" 

# 1. VECTOR THRESHOLD (The "Broad Net")
# We keep this somewhat loose to find potential matches.
VECTOR_DISTANCE_THRESHOLD = 0.45 

# 2. SEQUENCE THRESHOLD (The "Turnitin" Rule)
# This checks word-for-word similarity. 
# 0.6 means 60% of the words/structure must be IDENTICAL to be flagged.
# Turnitin usually triggers around 0.5-0.7 for a direct block match.
SEQUENCE_MATCH_THRESHOLD = 0.60 
# ---------------------

def calculate_structural_similarity(text1, text2):
    """
    Calculates how many words/characters actually overlap in order.
    This acts like Turnitin's fingerprinting.
    """
    return SequenceMatcher(None, text1, text2).ratio()

def check_paper(paper_path):
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print(f"Checking '{paper_path}' against subject: {COLLECTION_NAME}...")
    
    # Process Input Paper
    pages_data = extract_text_with_metadata(paper_path)
    input_chunks = chunk_text_with_page_mapping(pages_data)
    
    total_chunks = len(input_chunks)
    plagiarized_chunks = 0
    total_similarity_accumulated = 0

    print(f"\nAnalyzing {total_chunks} text segments...\n")

    for i, item in enumerate(input_chunks):
        chunk_text = item['text']
        embedding = model.encode([chunk_text]).tolist()
        
        results = collection.query(
            query_embeddings=embedding,
            n_results=1
        )

        if not results['documents'][0]:
            continue

        # 1. Check Vector Distance (Context/Meaning)
        distance = results['distances'][0][0]
        
        if distance < VECTOR_DISTANCE_THRESHOLD:
            # We found a "Conceptual" match. Now verify with "Structural" match.
            db_text = results['documents'][0][0]
            
            # 2. Check Structural Similarity (Word-for-Word)
            structural_score = calculate_structural_similarity(chunk_text, db_text)
            
            # If the structure is too different, it's just "Same Topic", not plagiarism.
            if structural_score > SEQUENCE_MATCH_THRESHOLD:
                plagiarized_chunks += 1
                total_similarity_accumulated += structural_score
                
                source_book = results['metadatas'][0][0]['source']
                source_page = results['metadatas'][0][0]['page']
                
                print(f"⚠️  MATCH FOUND (Student Page {item['page']})")
                print(f"   Context Match (AI): {round((1-distance)*100, 2)}%")
                print(f"   Word-for-Word Match: {round(structural_score*100, 2)}%")
                print(f"   Source: {source_book} (Page {source_page})")
                print(f"   Student Segment: '{chunk_text[:60]}...'")
                print(f"   Database Match:  '{db_text[:60]}...'\n")

    # Calculate final score based on confirmed structural matches
    if total_chunks > 0:
        final_score = (plagiarized_chunks / total_chunks) * 100
    else:
        final_score = 0.0

    print("========================================")
    print(f"Final Plagiarism Score: {round(final_score, 2)}%")
    print("========================================")
    if final_score < 15:
         print("🟢 Status: Original Work (Low Similarity)")
    elif final_score < 40:
         print("🟡 Status: Moderate Similarity (Check citations)")
    else:
         print("🔴 Status: High Plagiarism Detected")

if __name__ == "__main__":
    # Make sure to point to your PDF
    check_paper("papers_to_check/test_paper.pdf")
