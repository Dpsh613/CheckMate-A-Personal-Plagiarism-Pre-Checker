import fitz  # PyMuPDF
import re
import unicodedata

# --- TEXT CLEANING ---
def clean_and_fix_text(text):
    if not text: return ""
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'-\n\s*', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- MAIN EXTRACTION FUNCTION  ---
def extract_text_with_metadata(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return []

    pages_data = []

    for page_num, page in enumerate(doc):
        page_height = page.rect.height
        header_cutoff = page_height * 0.05 
        footer_cutoff = page_height * 0.92 

        blocks = page.get_text("blocks", sort=True)
        page_text_pieces = []

        for b in blocks:
            y0 = b[1]
            y1 = b[3]
            block_text = b[4]

            if y1 < header_cutoff: continue
            if y0 > footer_cutoff: continue

            cleaned_block = clean_and_fix_text(block_text)
            if len(cleaned_block) > 3:
                page_text_pieces.append(cleaned_block)

        # We join blocks with [[PARA]] to mark them
        full_page_text = ' [[PARA]] '.join(page_text_pieces)
        
        if len(full_page_text) > 50: 
            pages_data.append({
                "page": page_num + 1, 
                "text": full_page_text
            })
            
    return pages_data

# --- CHUNKING FUNCTION (For Database) ---
def chunk_text_with_page_mapping(pages_data, chunk_size=100, overlap=25):
    chunks_with_meta = []
    for page_entry in pages_data:
        text = page_entry['text']
        page_num = page_entry['page']
        
        # Remove the marker for DB chunking, we just want words
        clean_text_for_db = text.replace('[[PARA]]', ' ')
        words = clean_text_for_db.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_words) > 25:
                chunks_with_meta.append({
                    "text": chunk_text,
                    "page": page_num
                })
    return chunks_with_meta

# --- SENTENCE SPLITTER (For Checker/UI) ---
def split_into_sentences(pages_data):
    """
    Splits text into sentences AND marks the end of paragraphs.
    """
    sentences_with_meta = []
    
    for page_entry in pages_data:
        text = page_entry['text']
        page_num = page_entry['page']
        
        # 1. Split by the Paragraph Marker first
        raw_blocks = text.split(' [[PARA]] ')

        for block in raw_blocks:
            # 2. Split block into sentences
            block_sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', block)
            
            # Clean and filter sentences first so we know the true count
            valid_sentences = []
            for sent in block_sentences:
                clean_sent = sent.strip()
                if len(clean_sent) > 5: # Allow short headers
                    valid_sentences.append(clean_sent)

            # 3. Add to list with "End of Paragraph" flag
            for i, sent in enumerate(valid_sentences):
                # Check if this is the last sentence in this specific block
                is_last = (i == len(valid_sentences) - 1)
                
                sentences_with_meta.append({
                    "text": sent,
                    "page": page_num,
                    "is_end_of_paragraph": is_last  # <--- NEW FLAG
                })
            
    return sentences_with_meta